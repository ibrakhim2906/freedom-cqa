"""Offline evidence-contract regressions; no client and no synthetic runtime repair.

The replay fixtures preserve rejected provider payloads and separately authored v2
encodings. Passing a test never promotes the old failed run into an accepted result.
"""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from cqa.evaluator import schema_for
from cqa.models import Checklist, Conversation, Evaluation
from cqa.output_contract import decode_evaluation
from cqa.rubric import load_checklist
from cqa.scoring import calculate_score, validate_evaluation

FIXTURE = Path(__file__).parent / "fixtures/evidence-contract-v2-replay.json"


def replay_rows():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]


def assert_current(data, conversation, checklist):
    result = Evaluation.model_validate(data)
    validate_evaluation(result, conversation, checklist, require_audit=True)
    return result


def wire(data):
    """Test-only serialization of explicit fixtures; does not fill source fields."""
    raw = deepcopy(data)
    audits = {d["criterion_id"]: d for d in raw.pop("deductions")}
    raw["judgments"] = {j["criterion_id"]: j | {"deduction": audits.get(j["criterion_id"])}
                        for j in raw["judgments"]}
    return raw


def novel_fixture():
    conversation = Conversation.model_validate({
        "id": "fresh-evidence-contract", "channel": "agent chat", "language": "EN",
        "knowledge_scope": "northstar-workspace", "occurred_on": "2026-11-07",
        "messages": [
            {"id": "intro-c", "timestamp": "00:00", "speaker": "client", "text": "Hello."},
            {"id": "intro-o", "timestamp": "00:01", "speaker": "operator", "text": "Hello, I'm Quinn."},
            {"id": "query", "timestamp": "00:02", "speaker": "client",
             "text": "Where is Download and which file type does it return?"},
            {"id": "guide", "timestamp": "00:03", "speaker": "operator",
             "text": "Download is in Documents."},
            {"id": "visible", "timestamp": "00:04", "speaker": "client",
             "text": "I can see the Download control."},
            {"id": "late", "timestamp": "00:05", "speaker": "client",
             "text": "Does the export include attachments?"},
            {"id": "farewell", "timestamp": "00:06", "speaker": "operator", "text": "Goodbye."},
            {"id": "ended", "timestamp": "00:07", "speaker": "system", "text": "Conversation ended."},
        ],
        "references": [{"id": "northstar-manual", "text": "Download is in Documents.",
                        "scope": "northstar-workspace", "provenance": "Fictional source for an unseen test."}],
    })
    checklist = Checklist.model_validate({"id": "unseen-support-rubric", "version": "1", "title": "Custom rubric",
        "instructions": [], "criteria": [
            {"id": "coverage", "title": "Useful coverage", "kind": "scale", "weight": 20,
             "instruction": "Resolve all substantial questions or provide concrete next steps.",
             "levels": [{"value": "complete", "fraction": 1, "description": "All questions covered"},
                        {"value": "partial", "fraction": .5, "description": "A material question remains open"},
                        {"value": "missing", "fraction": 0, "description": "No usable answer or wrong key advice"}]},
            {"id": "finish", "title": "Closing", "kind": "binary", "weight": 5,
             "instruction": "Offer further help and say goodbye.",
             "levels": [{"value": "yes", "fraction": 1, "description": "Help offer and goodbye"},
                        {"value": "no", "fraction": 0, "description": "A required closing element is absent"}]},
        ]})
    all_ids = [m.id for m in conversation.messages]
    advice = {"message_id": "guide", "quote": "Download is in Documents."}
    visible = {"message_id": "visible", "quote": "I can see the Download control."}
    goodbye = {"message_id": "farewell", "quote": "Goodbye."}
    data = {
        "judgments": [
            {"criterion_id": "coverage", "status": "scored", "answer": "partial",
             "explanation": "Location is answered, but file type and attachments are still unanswered.",
             "evidence": [advice], "counterevidence": [], "checked_message_ids": all_ids, "uncertainty": None},
            {"criterion_id": "finish", "status": "scored", "answer": "no",
             "explanation": "The operator says goodbye without offering further help.",
             "evidence": [goodbye], "counterevidence": [], "checked_message_ids": all_ids, "uncertainty": None},
        ],
        "request_coverage": [
            {"request": "Locate Download and explain the returned file type.", "request_message_ids": ["query"],
             "status": "partial", "answer_message_ids": ["guide"], "withdrawal_message_ids": [],
             "explanation": "The location is provided; the requested file type is not.",
             "support": {"basis": "explicit", "evidence": [advice], "inference": None,
                 "unresolved_aspects": ["Returned file type"], "omission": {
                     "start_message_id": "query", "end_message_id": "ended",
                     "context_evidence": [{"message_id": "query", "quote": "which file type does it return?"}, goodbye]}}},
            {"request": "Determine whether attachments are included.", "request_message_ids": ["late"],
             "status": "unanswered", "answer_message_ids": [], "withdrawal_message_ids": [],
             "explanation": "No answer or next step occurs after this late question.",
             "support": {"basis": "none", "evidence": [], "inference": None,
                 "unresolved_aspects": ["Attachment inclusion"], "omission": {
                     "start_message_id": "late", "end_message_id": "ended",
                     "context_evidence": [{"message_id": "late", "quote": "Does the export include attachments?"},
                                          {"message_id": "ended", "quote": "Conversation ended."}]}}},
        ],
        "scope_notes": ["Authored test fixture; not provider inference or policy about a real product."],
        "factual_claims": [{"claim": "Download is in Documents.", "criterion_ids": ["coverage"],
            "operator_evidence": [advice], "status": "supported", "material": True,
            "reference_evidence": [{"reference_id": "northstar-manual", "quote": "Download is in Documents."}],
            "dialogue_evidence": [visible], "context_evidence": [],
            "explanation": "The reference supports navigation; the customer only confirms control visibility.",
            "evidence_kind": "product_fact", "rule_evidence": [], "verification_scope": "policy",
            "observation_scope": "control_visible", "supported_proposition": "The customer sees Download.",
            "assessment": {"lifecycle": "active", "correction": None, "impacts": [
                {"criterion_id": "coverage", "when_true": {"status": "scored", "answer": "partial"},
                 "when_false": {"status": "scored", "answer": "missing"},
                 "rule_quote": "No usable answer or wrong key advice", "evidence": [advice],
                 "checked_message_ids": all_ids,
                 "explanation": "Correct navigation earns partial credit; wrong key advice could earn zero."}]}}],
        "deductions": [
            {"criterion_id": "coverage", "rule_quote": "A material question remains open",
             "defect": "Two requested details remain unanswered.", "evidence": [], "checked_message_ids": all_ids,
             "overlap_note": "Content coverage is separate from the closing behavior."},
            {"criterion_id": "finish", "rule_quote": "Offer further help and say goodbye.",
             "defect": "No offer of further help accompanies the goodbye.", "evidence": [goodbye],
             "checked_message_ids": ["farewell", "ended"], "overlap_note": "Independent closing requirement."},
        ],
        "semantic_audit": {"version": "coverage-v2",
            "reviewed_message_ids": [m.id for m in conversation.messages if m.speaker in {"client", "operator"}],
            "exclusions": [
                {"evidence": {"message_id": "intro-c", "quote": "Hello."}, "reason": "social",
                 "criterion_ids": [], "explanation": "Customer greeting only."},
                {"evidence": {"message_id": "intro-o", "quote": "Hello, I'm Quinn."}, "reason": "social",
                 "criterion_ids": [], "explanation": "Greeting and introduction, outside this custom rubric."},
                {"evidence": visible, "reason": "context_or_confirmation", "criterion_ids": [],
                 "explanation": "Control visibility is not export completion or another request."},
                {"evidence": goodbye, "reason": "social", "criterion_ids": [],
                 "explanation": "Farewell only, independently assessed by the closing criterion."},
            ]},
    }
    return conversation, checklist, data


def test_unseen_partial_and_unanswered_requests_keep_distinct_negative_proof_and_deductions():
    conversation, checklist, data = novel_fixture()
    result = assert_current(data, conversation, checklist)
    assert calculate_score(result, checklist)["total"] == 40
    assert {d.criterion_id for d in result.deductions} == {"coverage", "finish"}
    assert result.request_coverage[1].answer_message_ids == []
    assert result.request_coverage[1].support.evidence == []
    assert {e.message_id for e in result.request_coverage[1].support.omission.context_evidence} == {"late", "ended"}


@pytest.mark.parametrize("fault", ["answer_id", "positive_quote", "inference", "missing_aspect", "missing_omission",
                                   "partial_without_omission", "partial_without_answer", "early_end", "late_start",
                                   "reversed", "unknown_start", "unknown_end", "outside_quote", "fake_quote"])
def test_omission_contract_rejects_invalid_or_truncated_proof(fault):
    conversation, checklist, data = novel_fixture()
    request = data["request_coverage"][1]
    support = request["support"]
    omission = support["omission"]
    if fault == "answer_id":
        request["answer_message_ids"] = ["farewell"]
    elif fault == "positive_quote":
        support["evidence"] = [{"message_id": "farewell", "quote": "Goodbye."}]
    elif fault == "inference":
        support["inference"] = "A nonanswer somehow entails the answer."
    elif fault == "missing_aspect":
        support["unresolved_aspects"] = []
    elif fault == "missing_omission":
        support["omission"] = None
    elif fault == "partial_without_omission":
        data["request_coverage"][0]["support"]["omission"] = None
    elif fault == "partial_without_answer":
        data["request_coverage"][0]["answer_message_ids"] = []
    elif fault == "early_end":
        omission["end_message_id"] = "farewell"
    elif fault == "late_start":
        omission["start_message_id"] = "farewell"
    elif fault == "reversed":
        omission.update(start_message_id="ended", end_message_id="late")
    elif fault == "unknown_start":
        omission["start_message_id"] = "not-a-source"
    elif fault == "unknown_end":
        omission["end_message_id"] = "not-a-source"
    elif fault == "outside_quote":
        omission["context_evidence"] = [{"message_id": "intro-c", "quote": "Hello."}]
    else:
        omission["context_evidence"][0]["quote"] = "The export was completed successfully."
    with pytest.raises(ValueError):
        assert_current(data, conversation, checklist)


@pytest.mark.parametrize("fault", ["customer_answer", "unlinked_operator", "answered_omission", "explicit_inference"])
def test_positive_support_stays_role_bound_and_separate_from_omissions(fault):
    conversation, checklist, data = novel_fixture()
    request = data["request_coverage"][0]
    support = request["support"]
    if fault == "customer_answer":
        support["evidence"] = [{"message_id": "visible", "quote": "I can see the Download control."}]
    elif fault == "unlinked_operator":
        support["evidence"] = [{"message_id": "farewell", "quote": "Goodbye."}]
    elif fault == "answered_omission":
        request["status"] = "answered"
        support["unresolved_aspects"] = []
    else:
        support["inference"] = "An inference supplied for an explicit answer is misplaced."
    with pytest.raises(ValueError):
        assert_current(data, conversation, checklist)


@pytest.mark.parametrize("fault", ["scope_none", "empty_proposition", "context_role", "context_fake_quote",
                                   "context_only_policy", "context_only_private", "general_from_visibility"])
def test_observation_and_nonproving_context_do_not_weaken_truth_verification(fault):
    conversation, checklist, data = novel_fixture()
    claim = data["factual_claims"][0]
    if fault == "scope_none":
        claim["observation_scope"] = "none"
    elif fault == "empty_proposition":
        claim["supported_proposition"] = " "
    elif fault == "context_role":
        claim["context_evidence"] = [{"message_id": "guide", "quote": "Download is in Documents."}]
    elif fault == "context_fake_quote":
        claim["context_evidence"] = [{"message_id": "visible", "quote": "I completed an export."}]
    elif fault in {"context_only_policy", "context_only_private"}:
        claim.update(reference_evidence=[], context_evidence=claim["dialogue_evidence"], dialogue_evidence=[],
                     observation_scope="none", supported_proposition=None)
        if fault == "context_only_private":
            claim.update(evidence_kind="account_state", verification_scope="private_record")
    else:
        claim.update(reference_evidence=[], verification_scope="interaction",
                     claim="Every account can export every type of file.")
    with pytest.raises(ValueError):
        assert_current(data, conversation, checklist)


def test_unverified_customer_context_is_not_forced_into_an_observation_claim():
    conversation, checklist, data = novel_fixture()
    claim = data["factual_claims"][0]
    claim.update(status="unverified", reference_evidence=[], context_evidence=claim["dialogue_evidence"],
                 dialogue_evidence=[], observation_scope="none", supported_proposition=None)
    j = data["judgments"][0]
    j.update(status="needs_review", answer=None, uncertainty="The policy is not independently verified.")
    data["deductions"] = [d for d in data["deductions"] if d["criterion_id"] != "coverage"]
    result = assert_current(data, conversation, checklist)
    assert result.factual_claims[0].status == "unverified"
    assert result.factual_claims[0].dialogue_evidence == []
    assert calculate_score(result, checklist)["total"] is None


def test_unverified_dialogue_assertion_still_requires_its_explicit_observation_metadata():
    conversation, checklist, data = novel_fixture()
    claim = data["factual_claims"][0]
    claim.update(status="unverified", reference_evidence=[], observation_scope="none", supported_proposition=None)
    data["judgments"][0].update(status="needs_review", answer=None, uncertainty="No policy verification.")
    data["deductions"] = [d for d in data["deductions"] if d["criterion_id"] != "coverage"]
    with pytest.raises(ValueError, match="observation_scope"):
        assert_current(data, conversation, checklist)


def test_context_only_quote_cannot_keep_a_declared_independent_observation_scope():
    conversation, checklist, data = novel_fixture()
    claim = data["factual_claims"][0]
    claim["context_evidence"], claim["dialogue_evidence"] = claim["dialogue_evidence"], []
    with pytest.raises(ValueError, match="observation scope requires dialogue evidence"):
        assert_current(data, conversation, checklist)


def test_policy_reference_does_not_let_a_customer_quote_masquerade_as_a_system_record():
    conversation, checklist, data = novel_fixture()
    claim = data["factual_claims"][0]
    assert claim["reference_evidence"]
    claim["observation_scope"] = "system_record"
    with pytest.raises(ValueError, match="system_record"):
        assert_current(data, conversation, checklist)


def test_actual_system_record_can_corroborate_a_narrow_observation_alongside_policy_reference():
    conversation, checklist, data = novel_fixture()
    system_text = "The Download control was displayed to this customer."
    conversation.messages[-1].text = system_text
    data["request_coverage"][1]["support"]["omission"]["context_evidence"][-1]["quote"] = system_text
    claim = data["factual_claims"][0]
    claim.update(dialogue_evidence=[{"message_id": "ended", "quote": system_text}],
                 observation_scope="system_record",
                 supported_proposition="The system records the Download control as displayed to this customer.")
    result = assert_current(data, conversation, checklist)
    assert calculate_score(result, checklist)["total"] == 40
    assert result.factual_claims[0].reference_evidence
    assert result.factual_claims[0].observation_scope == "system_record"


def test_context_and_omission_fields_do_not_remove_independently_required_deduction_audits():
    conversation, checklist, data = novel_fixture()
    data["deductions"] = [d for d in data["deductions"] if d["criterion_id"] != "coverage"]
    with pytest.raises(ValueError, match="deduction"):
        assert_current(data, conversation, checklist)


@pytest.mark.parametrize("index", [0, 1])
def test_recorded_failures_remain_rejected_and_explicit_test_encodings_preserve_grades(index):
    row = replay_rows()[index]
    conversation = Conversation.model_validate(row["conversation"])
    original = row["rejected_coverage_v1_wire"]
    authored = row["authored_coverage_v2_wire"]
    assert authored["judgments"] == original["judgments"]
    with pytest.raises(ValueError):
        result = decode_evaluation(json.dumps(original), require_claim_dependencies=True,
                                   require_semantic_coverage=True)
        validate_evaluation(result, conversation, load_checklist(), require_audit=True)
    with pytest.raises(ValueError):
        decode_evaluation(json.dumps(original), require_claim_dependencies=True,
                          require_semantic_coverage=True, require_evidence_contract=True)
    result = decode_evaluation(json.dumps(authored), require_claim_dependencies=True,
                               require_semantic_coverage=True, require_evidence_contract=True)
    validate_evaluation(result, conversation, load_checklist(), require_audit=True)
    assert calculate_score(result, load_checklist())["total"] == [76.92, 77.69][index]
    assert next(j for j in result.judgments if j.criterion_id == "consultation").answer == "10"
    if index:
        claim = result.factual_claims[0]
        assert claim.observation_scope == "control_visible"
        assert claim.supported_proposition == "The customer can see the Use Margin setting."
        assert next(j for j in result.judgments if j.criterion_id == "management").answer == "7"


@pytest.mark.parametrize("missing", ["omission", "context_evidence"])
def test_current_decoder_rejects_missing_new_fields_instead_of_defaulting_them(missing):
    _, _, data = novel_fixture()
    raw = wire(data)
    if missing == "omission":
        raw["request_coverage"][0]["support"].pop("omission")
    else:
        raw["factual_claims"][0].pop("context_evidence")
    with pytest.raises(ValueError):
        decode_evaluation(json.dumps(raw), require_evidence_contract=True,
                          require_claim_dependencies=True, require_semantic_coverage=True)


def test_historical_v1_validation_remains_inert_for_absent_new_fields():
    conversation, checklist, data = novel_fixture()
    data["semantic_audit"]["version"] = "coverage-v1"
    for request in data["request_coverage"]:
        request["support"].pop("omission")
    for claim in data["factual_claims"]:
        claim.pop("context_evidence")
    result = assert_current(data, conversation, checklist)
    assert calculate_score(result, checklist)["total"] == 40


def test_unseen_complete_v2_fixture_satisfies_current_provider_schema():
    import jsonschema

    conversation, checklist, data = novel_fixture()
    jsonschema.validate(wire(data), schema_for(conversation, checklist, grounded=True))
