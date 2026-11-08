"""Offline reference wiring checks, with no provider or production-store access.

The capturing evaluator exercises the real provider request preparation, then returns
an explicitly synthetic result. These checks prove data flow and mechanical safeguards,
not model accuracy or the semantic correctness of an arbitrary assessment.
"""

import copy
import json
import time
from types import SimpleNamespace
from typing import ClassVar

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from cqa.evaluator import Evaluator
from cqa.grounding import select_reference_context
from cqa.models import Conversation, Evaluation, Judgment
from cqa.rubric import load_checklist
from cqa.scoring import calculate_score, validate_evaluation
from cqa.settings import ROOT, Settings

PACK_ID = "freedom-global-products-20261107"
PACK_PATH = ROOT / "references" / f"{PACK_ID}.json"
SCOPE = "freedom-finance-global-platform"
SNAPSHOT = "2026-11-07"
CONVERSATION = {"id": "new-product-question", "channel": "agent chat", "language": "EN", "messages": [
    {"id": "question", "timestamp": "00:01", "speaker": "client", "text": "Where can I see a broker report?"},
    {"id": "reply", "timestamp": "00:02", "speaker": "operator", "text": "Hello, I'm Mira. Open Broker Reports."}]}
CHECKLIST = {"id": "request-preparation-check", "version": "1", "title": "Request preparation fixture",
             "instructions": [], "criteria": [{"id": "clarity", "title": "Clear instructions",
                 "instruction": "Assess whether the instructions are clear.", "kind": "binary", "weight": 10,
                 "levels": [{"value": "clear", "fraction": 1, "description": "Clear"},
                            {"value": "unclear", "fraction": 0, "description": "Unclear"}]}]}


class CapturingPreparationEvaluator:
    """A test-only seam; never made selectable in the runtime configuration."""

    captures: ClassVar[list] = []

    def __init__(self, settings, _ledger, _ceiling):
        self.settings = settings

    async def close(self):
        pass

    async def evaluate(self, conversation, checklist):
        mode = SimpleNamespace(grounded=self.settings.strategy == "grounded",
                               assessor=self.settings.strategy in {"assessor", "assessor-reviewed"},
                               settings=self.settings)
        prepared = Evaluator._prepare(mode, conversation, checklist)
        type(self).captures.append({"conversation": conversation.model_dump(),
                                   "payload": json.loads(prepared[1]), "instructions": prepared[0]})
        result = Evaluation(judgments=[Judgment(criterion_id=c.id, status="scored", answer=c.levels[0].value,
            explanation="Synthetic transport fixture only; no model inference occurred.", evidence=[],
            counterevidence=[], checked_message_ids=[m.id for m in conversation.messages], uncertainty=None)
            for c in checklist.criteria], request_coverage=[], scope_notes=["TEST ONLY"])
        return {"status": "completed", "evaluation": result.model_dump(), "score": calculate_score(result, checklist),
                "error": None, "usage": None, "model": "TEST-ONLY", "attempt_count": 0}


@pytest.fixture
def client(tmp_path):
    CapturingPreparationEvaluator.captures = []
    settings = Settings(api_key="not-a-real-key", ledger_path=tmp_path / "usage.sqlite3", max_spend=1)
    app = create_app(settings=settings, database_path=tmp_path / "app.sqlite3",
                     evaluator_factory=CapturingPreparationEvaluator)
    with TestClient(app) as session:
        yield session
    assert app.state.workflow.ledger.committed() == 0


def imported(client, value=None):
    response = client.post("/api/conversations/import", json={"content": json.dumps(value or CONVERSATION)})
    assert response.status_code == 200, response.text
    return response.json()["conversations"][0]["id"]


def selection(**updates):
    return {"pack_id": PACK_ID, "scope": SCOPE, "mode": "snapshot_review", "as_of": SNAPSHOT,
            "rationale": "Explicit current-product review; original date and entity remain unconfirmed.", **updates}


def apply(client, cid, body=None):
    response = client.post(f"/api/conversations/{cid}/references", json=body or selection())
    assert response.status_code == 200, response.text
    return response.json()["id"]


def checklist_id(client):
    response = client.post("/api/checklists", json=CHECKLIST)
    assert response.status_code == 200, response.text
    return response.json()["id"]


def evaluated(client, cid, checklist, key):
    response = client.post("/api/evaluations", json={"conversation_ids": [cid], "checklist_id": checklist,
                                                   "request_id": key, "budget_usd": .5})
    assert response.status_code == 202, response.text
    for _ in range(100):
        detail = client.get(f"/api/jobs/{response.json()['job_ids'][0]}").json()
        if detail["status"] not in {"queued", "running"}:
            assert detail["status"] == "completed", detail
            return detail
        time.sleep(.01)
    pytest.fail("Isolated test worker did not finish")


@pytest.mark.parametrize("actual_date", [None, "2026-11-03"])
def test_snapshot_preview_revision_payload_and_export_preserve_actual_context(client, actual_date):
    source = copy.deepcopy(CONVERSATION)
    if actual_date:
        source["occurred_on"] = actual_date
    cid = imported(client, source)
    original = client.get(f"/api/conversations/{cid}").json()["content"]
    count = len(client.get("/api/conversations").json())
    preview = client.post(f"/api/conversations/{cid}/references/preview", json=selection())
    assert preview.status_code == 200, preview.text
    evidence = preview.json()
    assert evidence["assessment"]["conditional"] is True
    assert evidence["temporal"]["occurred_on"] == actual_date
    assert evidence["assessment"]["as_of"] == SNAPSHOT
    assert len([r for r in evidence["references"] if r["usable"]]) == 9
    assert len(client.get("/api/conversations").json()) == count  # Preview is read-only.
    revised = apply(client, cid)
    assert revised != cid
    assert apply(client, cid) == revised  # Reapplying identical context reuses the same immutable revision.
    content = client.get(f"/api/conversations/{revised}").json()["content"]
    assert content["occurred_on"] == actual_date
    assert content["knowledge_scope"] is None
    assert content["messages"] == original["messages"]
    assert content["reference_context"]["mode"] == "snapshot_review"
    assert content["reference_context"]["pack_sha256"]
    assert len(content["references"]) == 9
    assert all(r["date_basis"] == "snapshot" and r["snapshot_on"] == SNAPSHOT for r in content["references"])
    assert all(not r.get("valid_from") and not r.get("valid_until") for r in content["references"])
    job = evaluated(client, revised, checklist_id(client), "snapshot")
    captured = CapturingPreparationEvaluator.captures[-1]
    assert set(captured["payload"]["usable_reference_ids"]) == {r["id"] for r in content["references"]}
    assert captured["payload"]["conversation"]["occurred_on"] == actual_date
    assert captured["payload"]["conversation"]["knowledge_scope"] is None
    assert "expectations" not in captured["payload"]
    sent_context, saved_context = captured["payload"]["evidence_context"], job["evidence_context"]
    assert sent_context["assessment"] == saved_context["assessment"]
    assert sent_context["references"] == saved_context["references"]
    # The billable payload omits duplicated original timestamps, while the saved
    # context retains them for inspection. Eligibility facts must be identical.
    assert sent_context["temporal"] == {k: v for k, v in saved_context["temporal"].items()
                                         if k not in {"source_timestamps", "unusable_timestamps"}}
    assert job["effective"]["assessment_context"]["conditional"] is True
    exported = client.get(f"/api/jobs/{job['id']}/export").json()
    assert exported["evidence_context"] == job["evidence_context"]
    assert exported["conversation"]["content"]["reference_context"] == content["reference_context"]
    assert client.get(f"/api/conversations/{cid}").json()["content"] == original


def test_actual_date_mode_uses_source_date_and_refuses_snapshot_date_substitution(client):
    source = copy.deepcopy(CONVERSATION)
    for i, message in enumerate(source["messages"]):
        message["timestamp"] = f"2026-11-07T12:00:0{i}+05:00"
    cid = imported(client, source)
    context = client.get(f"/api/conversations/{cid}/evidence-context").json()
    assert context["temporal"]["occurred_on"] == SNAPSHOT
    body = selection(mode="conversation_date", as_of=None,
                     rationale="Provider and platform confirmed; actual date comes from original source timestamps.")
    revised = apply(client, cid, body)
    applied = client.get(f"/api/conversations/{revised}/evidence-context").json()
    assert not applied["assessment"]["conditional"]
    assert all(r["usable"] for r in applied["references"])
    invalid = body | {"occurred_on": "2026-11-03"}
    assert client.post(f"/api/conversations/{cid}/references", json=invalid).status_code == 422
    historical = copy.deepcopy(CONVERSATION) | {"id": "historical-source", "occurred_on": "2026-11-03"}
    old_id = imported(client, historical)
    preview = client.post(f"/api/conversations/{old_id}/references/preview", json=body)
    assert preview.status_code == 200
    assert not any(r["usable"] for r in preview.json()["references"])
    assert client.post(f"/api/conversations/{old_id}/references", json=body).status_code == 422


def test_wrong_or_missing_context_cannot_silently_activate_sources(client):
    cid = imported(client)
    actual = selection(mode="conversation_date", as_of=None, rationale="Known broker, but actual date is unavailable.")
    response = client.post(f"/api/conversations/{cid}/references/preview", json=actual)
    assert response.status_code == 200, response.text
    assert not any(r["usable"] for r in response.json()["references"])
    assert client.post(f"/api/conversations/{cid}/references", json=actual).status_code == 422
    assert client.post(f"/api/conversations/{cid}/references", json=selection(as_of="2026-11-08")).status_code == 422
    assert client.post(f"/api/conversations/{cid}/references", json=selection(rationale=" ")).status_code == 422
    different = copy.deepcopy(CONVERSATION) | {"id": "other-company", "knowledge_scope": "another-broker"}
    other_id = imported(client, different)
    assert client.post(f"/api/conversations/{other_id}/references", json=selection()).status_code == 422


def test_cache_retry_history_and_appeal_sources_keep_the_frozen_context(client):
    cid, checklist = imported(client), checklist_id(client)
    old_job = evaluated(client, cid, checklist, "old-input")
    revised = apply(client, cid)
    new_job = evaluated(client, revised, checklist, "new-input")
    assert new_job["id"] != old_job["id"]
    assert not CapturingPreparationEvaluator.captures[0]["payload"]["usable_reference_ids"]
    assert len(CapturingPreparationEvaluator.captures[1]["payload"]["usable_reference_ids"]) == 9
    assert evaluated(client, revised, checklist, "cached-input")["id"] == new_job["id"]
    assert len(CapturingPreparationEvaluator.captures) == 2
    retried = client.post(f"/api/jobs/{old_job['id']}/retry", json={"request_id": "retry-old", "budget_usd": .5})
    assert retried.status_code == 202
    for _ in range(100):
        retry = client.get(f"/api/jobs/{retried.json()['job_ids'][0]}").json()
        if retry["status"] == "completed":
            break
        time.sleep(.01)
    assert retry["conversation_id"] == cid
    assert not retry["conversation"]["content"]["references"]
    assert not CapturingPreparationEvaluator.captures[-1]["payload"]["usable_reference_ids"]
    original_record = copy.deepcopy(new_job["record"])
    options = client.get(f"/api/jobs/{new_job['id']}/reference-options").json()["references"]
    usable = [r["reference"] for r in options if r["usable"]]
    blocked = [r for r in options if not r["usable"]]
    assert len(usable) == 9 and blocked
    assert all(r["rejection_reasons"] for r in blocked)
    appeal = client.post(f"/api/jobs/{new_job['id']}/appeals", json={"criterion_id": "clarity", "author": "Reviewer",
        "reason": "Check the official product evidence without rewriting the AI assessment.", "message_ids": ["reply"]})
    assert appeal.status_code == 201
    resolution = {"decision": "accept", "reviewer": "QA", "rationale": "Context-bound human review, not model inference.",
                  "expected_revision": 0, "judgment": new_job["effective"]["judgments"][0],
                  "supporting_references": [blocked[0]["reference"]]}
    endpoint = f"/api/appeals/{appeal.json()['id']}/resolve"
    assert client.post(endpoint, json=resolution).status_code == 422
    resolution["supporting_references"] = usable[:1]
    saved = client.post(endpoint, json=resolution)
    assert saved.status_code == 200, saved.text
    after = client.get(f"/api/jobs/{new_job['id']}").json()
    assert after["effective"]["assessment_context"]["conditional"] is True
    assert after["record"] == original_record
    assert after["appeals"][0]["resolution"]["assessment_context"] == after["evidence_context"]["assessment"]


def partial_assessment(topic):
    """Unseen minimal pairs with genuine unanswered questions, not expected runtime keys."""
    if topic == "d-account":
        request = "Which account buys shares? My funds are on D."
        advice = "D funds cannot be used directly for trading. Use the trading account."
        followup = "How do I get the money from D into that purchase?"
        sid = "ffg-d-account-20261107"
    else:
        request = "Where can I disable Use Margin?"
        advice = "Open Order Settings to find Use Margin."
        followup = "Does disabling it change a position I already own?"
        sid = "tradernet-margin-14230-20261107"
    original = Conversation.model_validate({"id": "novel-review-fixture", "channel": "agent chat", "language": "EN",
        "messages": [{"id": "m1", "timestamp": "00:01", "speaker": "client", "text": request},
                     {"id": "m2", "timestamp": "00:02", "speaker": "operator", "text": "Hello, I'm Mira. " + advice},
                     {"id": "m3", "timestamp": "00:03", "speaker": "client", "text": followup},
                     {"id": "m4", "timestamp": "00:04", "speaker": "operator", "text": "Goodbye."}]})
    conversation = select_reference_context(original, PACK_PATH, SCOPE, mode="snapshot_review", as_of=SNAPSHOT,
        rationale="Explicit current product context for isolated strict-validation fixture.", pack_id=PACK_ID)
    rubric = load_checklist()
    mids = [m.id for m in original.messages]
    judgments = []
    outcomes = {"needs": None, "identity": None, "consultation": "10", "management": "10", "closing": "no", "serious": "no"}
    for criterion in rubric.criteria:
        answer = outcomes.get(criterion.id, "yes")
        judgments.append({"criterion_id": criterion.id, "status": "not_applicable" if answer is None else "scored",
            "answer": answer, "explanation": "Source-specific isolated validation fixture.", "evidence": [],
            "counterevidence": [], "checked_message_ids": mids, "uncertainty": None})
    consultation = next(c for c in rubric.criteria if c.id == "consultation")
    closing = next(c for c in rubric.criteria if c.id == "closing")
    source = next(r for r in conversation.references if r.id == sid)
    quote = {"message_id": "m2", "quote": advice}
    data = {"judgments": judgments, "scope_notes": ["Conditional snapshot review"],
        "request_coverage": [
            {"request": request, "request_message_ids": ["m1"], "status": "partial" if topic == "d-account" else "answered",
             "answer_message_ids": ["m2"], "explanation": "The operator gives limited actual advice, not the reference's unspoken answer.",
             "support": {"basis": "explicit", "evidence": [quote], "inference": None,
                         "unresolved_aspects": [followup] if topic == "d-account" else []}},
            {"request": followup, "request_message_ids": ["m3"], "status": "unanswered", "answer_message_ids": [],
             "explanation": "No later human answer or concrete next step exists.",
             "support": {"basis": "none", "evidence": [], "inference": None, "unresolved_aspects": [followup]}}],
        "deductions": [
            {"criterion_id": "consultation", "rule_quote": consultation.levels[2].description,
             "defect": "The customer's substantial follow-up remains unanswered.", "evidence": [],
             "checked_message_ids": ["m3", "m4"], "overlap_note": "No independent empathy or management failure is inferred."},
            {"criterion_id": "closing", "rule_quote": closing.instruction[:35], "defect": "A farewell alone lacks the required recap/help offer.",
             "evidence": [{"message_id": "m4", "quote": "Goodbye."}], "checked_message_ids": ["m4"],
             "overlap_note": "Separate closing conduct, not the consultation omission repeated."}],
        "factual_claims": [{"claim": advice, "criterion_ids": ["consultation"], "operator_evidence": [quote],
            "status": "supported", "material": True, "reference_evidence": [{"reference_id": sid, "quote": source.text}],
            "dialogue_evidence": [], "explanation": "The official snapshot supports this limited operator assertion.",
            "assessment": {"lifecycle": "active", "correction": None, "impacts": [{"criterion_id": "consultation",
                "when_true": {"status": "scored", "answer": "10"}, "when_false": {"status": "scored", "answer": "0"},
                "rule_quote": consultation.instruction[:35], "evidence": [quote], "checked_message_ids": mids,
                "explanation": "True advice earns partial credit; materially wrong key advice could require zero. The open question remains either way."}]},
            "evidence_kind": "product_fact", "rule_evidence": [], "observation_scope": "none",
            "supported_proposition": None, "verification_scope": "policy"}],
        "semantic_audit": {"version": "coverage-v1", "reviewed_message_ids": mids,
            "exclusions": [{"evidence": {"message_id": "m4", "quote": "Goodbye."}, "reason": "social",
                            "criterion_ids": [], "explanation": "Farewell, not a product assertion."}]}}
    return conversation, rubric, data


@pytest.mark.parametrize("topic", ["d-account", "margin"])
def test_official_truth_support_does_not_remove_unanswered_question_deductions(topic):
    conversation, rubric, data = partial_assessment(topic)
    result = Evaluation.model_validate(data)
    validate_evaluation(result, conversation, rubric, require_audit=True)
    assert calculate_score(result, rubric)["total"] == 76.92
    assert next(j for j in result.judgments if j.criterion_id == "empathy").answer == "yes"
    assert next(j for j in result.judgments if j.criterion_id == "management").answer == "10"
    # Merely adding supported official facts does not justify promoting the declared
    # grade past its still-open customer request/dependency and deduction contract.
    next(j for j in data["judgments"] if j["criterion_id"] == "consultation")["answer"] = "20"
    with pytest.raises(ValueError):
        validate_evaluation(Evaluation.model_validate(data), conversation, rubric, require_audit=True)


@pytest.mark.parametrize("topic", ["d-account", "margin"])
def test_reference_words_cannot_be_fabricated_as_an_operator_answer(topic):
    conversation, rubric, data = partial_assessment(topic)
    missing = data["request_coverage"][-1]
    source = conversation.references[0]
    missing.update(status="answered", answer_message_ids=[source.id])
    missing["support"] = {"basis": "explicit", "evidence": [{"message_id": source.id, "quote": source.text}],
                          "inference": None, "unresolved_aspects": []}
    with pytest.raises(ValueError, match="actual customer|operator messages"):
        validate_evaluation(Evaluation.model_validate(data), conversation, rubric, require_audit=True)
