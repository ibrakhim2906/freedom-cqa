"""Regression of the observed fictional browser failure and protected repair path."""

import asyncio
import copy
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import jsonschema
import pytest

from cqa.evaluator import REPAIR_FEEDBACK_BYTES, Evaluator, repair_feedback, schema_for
from cqa.ledger import BudgetExceeded, Ledger
from cqa.models import Conversation, Deduction
from cqa.output_contract import decode_evaluation
from cqa.rubric import load_checklist
from cqa.scoring import validate_evaluation
from cqa.settings import ROOT, Settings


def observed_failure():
    manifest = json.loads((ROOT / "evals/browser-acceptance-v1.json").read_text(encoding="utf-8"))
    conversation = Conversation.model_validate(manifest["conversations"][0])
    checklist = load_checklist()
    text = (ROOT / "tests/fixtures/missing-identity-audit.json").read_text(encoding="utf-8")
    result = decode_evaluation(text)
    return conversation, checklist, text, result


def corrected_wire():
    conversation, checklist, _, result = observed_failure()
    identity = next(c for c in checklist.criteria if c.id == "identity")
    result.deductions.append(Deduction(criterion_id="identity", rule_quote=identity.instruction,
        defect="Account status was disclosed before system confirmation.",
        evidence=[{"message_id": "m6", "quote": "заявка NS-631 отклонена."}],
        checked_message_ids=["m4", "m5", "m6", "m7"],
        overlap_note="Identity prerequisite is separate from the unanswered consultation request."))
    validate_evaluation(result, conversation, checklist, require_audit=True)
    data = result.model_dump()
    audits = {d["criterion_id"]: d for d in data.pop("deductions")}
    data["judgments"] = {j["criterion_id"]: j | {"deduction": audits.get(j["criterion_id"])}
                         for j in data["judgments"]}
    for claim in data["factual_claims"]:
        impacts = []
        for cid in claim["criterion_ids"]:
            judgment = data["judgments"][cid]
            outcome = {"status": judgment["status"], "answer": judgment["answer"]}
            criterion = next(c for c in checklist.criteria if c.id == cid)
            impacts.append({"criterion_id": cid, "when_true": outcome,
                            "when_false": {"status": "scored", "answer": "0"} if cid == "consultation" else outcome,
                            "rule_quote": criterion.levels[0].description,
                            "evidence": claim["operator_evidence"], "checked_message_ids": judgment["checked_message_ids"],
                            "explanation": "Supported factual advice; security ordering is independently established."})
        claim["assessment"] = {"lifecycle": "active", "correction": None, "impacts": impacts}
        claim["supported_proposition"] = claim["claim"]
        claim["observation_scope"] = "system_record"
    data["factual_claims"][0].update(evidence_kind="grading_rule", verification_scope="grading_rule",
        rule_evidence=[{"criterion_id": "identity", "quote": identity.instruction}])
    data["factual_claims"][1].update(evidence_kind="account_state", verification_scope="private_record")
    data["factual_claims"][2].update(verification_scope="interaction", observation_scope="task_completed")
    # Explicit current-wire fixture; the original rejected file stays unchanged.
    # Identity confirmation is context for the normative/private-reference claims,
    # not independent proof of those propositions.
    for claim in data["factual_claims"][:2]:
        claim["context_evidence"] = claim["dialogue_evidence"]
        claim["dialogue_evidence"] = []
        claim["observation_scope"] = "none"
        claim["supported_proposition"] = None
    messages = {m.id: m for m in conversation.messages}
    for request in data["request_coverage"]:
        positive = request["status"] == "answered"
        previous_ids = request["answer_message_ids"]
        if not positive:
            request["answer_message_ids"] = []
        request["support"] = {"basis": "explicit" if request["status"] == "answered" else "none",
            "evidence": [{"message_id": mid, "quote": messages[mid].text} for mid in request["answer_message_ids"]],
            "inference": None, "unresolved_aspects": [] if positive else [request["request"]],
            "omission": None if positive else {
                "start_message_id": min(request["request_message_ids"], key=lambda mid: list(messages).index(mid)),
                "end_message_id": conversation.messages[-1].id,
                "context_evidence": [{"message_id": mid, "quote": messages[mid].text} for mid in previous_ids]}}
    data["semantic_audit"] = {"version": "coverage-v2", "reviewed_message_ids": [
        m.id for m in conversation.messages if m.speaker in {"client", "operator"}], "exclusions": [
        {"evidence": {"message_id": "m5", "quote": messages["m5"].text}, "reason": "context_or_confirmation",
         "criterion_ids": ["identity"], "explanation": "Customer describes performing the verification steps; source confirmation is separate."},
        {"evidence": {"message_id": "m10", "quote": messages["m10"].text}, "reason": "social",
         "criterion_ids": ["closing"], "explanation": "Further-help offer and farewell, not product truth."}]}
    return conversation, checklist, data


def test_actual_rejected_draft_still_fails_strict_validation():
    conversation, checklist, _, result = observed_failure()
    with pytest.raises(ValueError, match="source-linked rule audit: identity"):
        validate_evaluation(result, conversation, checklist, require_audit=True)


@pytest.mark.parametrize("defect", ["missing_binary_audit", "null_binary_audit", "missing_criterion",
                                  "wrong_criterion", "passing_with_audit", "flag_audit"])
def test_provider_contract_rejects_missing_or_misattached_audits(defect):
    conversation, checklist, wire = corrected_wire()
    schema = schema_for(conversation, checklist, grounded=True)
    jsonschema.validate(wire, schema)
    bad = copy.deepcopy(wire)
    if defect == "missing_binary_audit":
        bad["judgments"]["identity"].pop("deduction")
    elif defect == "null_binary_audit":
        bad["judgments"]["identity"]["deduction"] = None
    elif defect == "missing_criterion":
        bad["judgments"].pop("identity")
    elif defect == "wrong_criterion":
        bad["judgments"]["identity"]["deduction"]["criterion_id"] = "consultation"
    elif defect == "passing_with_audit":
        bad["judgments"]["identity"]["answer"] = "yes"
    else:
        bad["judgments"]["serious"]["deduction"] = bad["judgments"]["identity"]["deduction"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)


def test_inline_audits_keep_semantic_validation_and_reject_duplicates():
    conversation, checklist, wire = corrected_wire()
    result = decode_evaluation(json.dumps(wire))
    validate_evaluation(result, conversation, checklist, require_audit=True)
    result.deductions[-1].rule_quote = "An invented policy which was never configured."
    with pytest.raises(ValueError, match="quote the configured"):
        validate_evaluation(result, conversation, checklist, require_audit=True)
    result = decode_evaluation(json.dumps(wire))
    result.deductions.append(result.deductions[0])
    with pytest.raises(ValueError, match="Duplicate deduction"):
        validate_evaluation(result, conversation, checklist, require_audit=True)


def test_supplied_grading_requirement_does_not_need_a_second_product_policy_source():
    conversation, checklist, wire = corrected_wire()
    rule = wire["factual_claims"][0]
    rule["reference_evidence"], rule["dialogue_evidence"] = [], []
    result = decode_evaluation(json.dumps(wire), require_semantic_coverage=True)
    validate_evaluation(result, conversation, checklist, require_audit=True)
    assert next(j for j in result.judgments if j.criterion_id == "identity").answer == "no"
    assert next(j for j in result.judgments if j.criterion_id == "serious").answer == "yes"


@pytest.mark.parametrize("fault", ["invented_rule", "unrelated_rule", "product_truth_from_rule", "wrong_scope"])
def test_rules_cannot_be_used_as_fake_product_or_account_evidence(fault):
    conversation, checklist, wire = corrected_wire()
    claim = wire["factual_claims"][0]
    if fault == "invented_rule":
        claim["rule_evidence"][0]["quote"] = "Broker fees are always zero."
    elif fault == "unrelated_rule":
        claim["rule_evidence"][0]["criterion_id"] = "contact"
    elif fault == "product_truth_from_rule":
        claim["evidence_kind"] = "product_fact"
    else:
        claim["verification_scope"] = "private_record"
    result = decode_evaluation(json.dumps(wire), require_semantic_coverage=True)
    with pytest.raises(ValueError):
        validate_evaluation(result, conversation, checklist, require_audit=True)


def test_new_provider_contract_cannot_omit_semantic_review_or_answer_support():
    conversation, checklist, wire = corrected_wire()
    schema = schema_for(conversation, checklist, grounded=True)
    for fault in ["ledger", "answer_support", "evidence_kind"]:
        bad = copy.deepcopy(wire)
        if fault == "ledger":
            bad["semantic_audit"] = None
        elif fault == "answer_support":
            bad["request_coverage"][0]["support"] = None
        else:
            bad["factual_claims"][0].pop("evidence_kind")
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, schema)
        with pytest.raises(ValueError):
            decode_evaluation(json.dumps(bad), require_semantic_coverage=True)

    def has_defaults(node):
        if isinstance(node, dict):
            return "default" in node or any(has_defaults(v) for v in node.values())
        return isinstance(node, list) and any(has_defaults(v) for v in node)
    assert not has_defaults(schema)


def test_repair_is_preflighted_and_protected_against_concurrent_spending(tmp_path):
    path = tmp_path / "ledger.sqlite3"
    ledger = Ledger(path, .5, budget_group="batch", group_limit=.4)
    competing = Ledger(path, .5, budget_group="other", group_limit=.5)
    hold = ledger.hold("test", .35, .5)
    assert ledger.group_committed("batch") == .35
    with pytest.raises(BudgetExceeded):
        competing.reserve("test", .2, .5)
    first = ledger.reserve("test", .1, .5, hold_id=hold)
    ledger.finish(first, "failed", cost=.03)
    repair = ledger.reserve("test", .2, .5, hold_id=hold)
    ledger.finish(repair, "completed", cost=.04)
    ledger.release(hold)
    assert ledger.committed() == pytest.approx(.07)
    assert ledger.summary()["protected_allowance_usd"] == 0


@pytest.mark.parametrize("outcome", ["success", "invalid_again", "timeout", "cancelled"])
def test_real_attempt_boundary_preserves_rejected_output_and_releases_allowance(tmp_path, outcome):
    async def run():
        conversation, checklist, wire = corrected_wire()
        _, _, original, _ = observed_failure()
        ledger = Ledger(tmp_path / "ledger.sqlite3", 1, budget_group="run", group_limit=1)
        evaluator = Evaluator(Settings(api_key="fictional-test"), ledger, 1)
        def response(text):
            return SimpleNamespace(id="test-only", model="test-only", output_text=text, status="completed",
                                   usage=SimpleNamespace(input_tokens=100, output_tokens=100))
        second = (response(json.dumps(wire)) if outcome == "success" else response(original)
                  if outcome == "invalid_again" else RuntimeError("isolated injected interruption")
                  if outcome == "timeout" else asyncio.CancelledError())
        evaluator.client.responses.create = AsyncMock(side_effect=[response(original), second])
        try:
            if outcome in {"timeout", "cancelled"}:
                with pytest.raises(RuntimeError if outcome == "timeout" else asyncio.CancelledError):
                    await evaluator.evaluate(conversation, checklist)
            else:
                result = await evaluator.evaluate(conversation, checklist)
                assert result["attempt_count"] == 2
                assert result["attempt_records"][0]["raw_output_text"] == original
                assert result["attempt_records"][0]["status"] == "failed"
                assert result["usage"]["estimated_cost_usd"] == pytest.approx(.0024)
                assert result["status"] == ("completed" if outcome == "success" else "failed")
                if outcome == "success":
                    assert result["evaluation"]["judgments"] == decode_evaluation(original).model_dump()["judgments"]
            assert evaluator.client.responses.create.call_count == 2
            assert ledger.summary()["protected_allowance_usd"] == 0
        finally:
            await evaluator.close()
    asyncio.run(run())


def test_insufficient_repair_allowance_makes_zero_paid_requests(tmp_path):
    async def run():
        conversation, checklist, _, _ = observed_failure()
        ledger = Ledger(tmp_path / "ledger.sqlite3", 1, budget_group="small", group_limit=.2)
        evaluator = Evaluator(Settings(api_key="fictional-test"), ledger, 1)
        evaluator.client.responses.create = AsyncMock()
        try:
            with pytest.raises(BudgetExceeded) as failure:
                await evaluator.evaluate(conversation, checklist)
            assert failure.value.required > .2
            evaluator.client.responses.create.assert_not_called()
            assert ledger.committed() == 0
        finally:
            await evaluator.close()
    asyncio.run(run())


def test_repair_feedback_bound_includes_unicode_and_json_escaping():
    feedback = repair_feedback({"error": "invalid_evaluation_ValueError", "raw_output_text": '\\"\nҚ' * 50_000})
    assert feedback["truncated"]
    assert len(json.dumps(feedback, ensure_ascii=False).encode("utf-8")) <= REPAIR_FEEDBACK_BYTES
