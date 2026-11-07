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
