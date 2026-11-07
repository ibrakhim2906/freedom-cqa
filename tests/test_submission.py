import copy

import pytest

from cqa.grounding import select_reference_context
from cqa.models import Conversation, Deduction, Evaluation, Judgment, Message
from cqa.rubric import official_checklist
from cqa.settings import ROOT
from cqa.submission import build_submission, validate_submission


def fixtures():
    rubric = official_checklist()
    conversation = Conversation(id="official-source-id", language="EN", channel="agent chat", messages=[
        Message(id="customer-z", timestamp="00:01", speaker="client", text="Please explain statement download."),
        Message(id="bot-z", timestamp="00:02", speaker="bot", text="Connecting a human."),
        Message(id="system-z", timestamp="00:03", speaker="system", text="Human joined."),
        Message(id="agent-z", timestamp="00:04", speaker="operator", text="Hi, I am Pat. Open Reports. Goodbye.")])
    answers = {"contact": "yes", "needs": None, "identity": None, "consultation": "15", "empathy": "yes",
               "management": "7", "closing": "yes", "serious": "no"}
    result = Evaluation(judgments=[Judgment(criterion_id=c.id, status="scored" if answers[c.id] else "not_applicable",
        answer=answers[c.id], explanation="Isolated adapter fixture; not a model or Ground Truth claim.",
        evidence=[{"message_id": "agent-z", "quote": "Open Reports."}], counterevidence=[],
        checked_message_ids=[m.id for m in conversation.messages], uncertainty=None) for c in rubric.criteria],
        request_coverage=[], scope_notes=[])
    for cid in ["consultation", "management"]:
        c = next(c for c in rubric.criteria if c.id == cid)
        result.deductions.append(Deduction(criterion_id=cid, rule_quote=c.instruction,
            defect="Isolated numeric adapter fixture", evidence=[], checked_message_ids=["agent-z"],
            overlap_note="Independent fixture defects; no runtime fallback."))
    record = {"status": "completed", "evaluation": result.model_dump(), "model": "TEST-ONLY"}
    originals = [conversation.model_copy(update={"id": f"original-{i}"}) for i in range(10)]
    entries = {c.id: (c, rubric, copy.deepcopy(record)) for c in originals}
    return originals, entries


def test_official_mapping_raw_scales_na_normalization_and_original_turn_numbers():
    originals, entries = fixtures()
    payload = build_submission(originals, entries, "Fixture team", "prod")
    first = payload["results"][0]
    assert first["score"] == {"final_score": 85.38, "critical_flag": False}
    values = {c["criterion_id"]: c["value"] for c in first["criteria"]}
    assert values == {"contact": True, "discovery": None, "identification": None, "consultation": 15,
                      "empathy": True, "dialogue": 7, "closure": True, "critical": False}
    assert all(c["evidence_turns"] == [4] for c in first["criteria"])


def test_review_is_error_not_na_and_missing_failed_records_are_preserved():
    originals, entries = fixtures()
    entries.pop(originals[0].id)
    entries[originals[1].id][2].update(status="failed", evaluation=None, error="provider_failure")
    r = entries[originals[2].id][2]["evaluation"]
    j = next(j for j in r["judgments"] if j["criterion_id"] == "consultation")
    j.update(status="needs_review", answer=None, uncertainty="Missing product source")
    r["deductions"] = [d for d in r["deductions"] if d["criterion_id"] != "consultation"]
    payload = build_submission(originals, entries, "Fixture team", "prod")
    assert len(payload["results"]) == 10
    for row in payload["results"][:3]:
        assert row["status"] == "error" and row["criteria"] == [] and row["score"] is None


@pytest.mark.parametrize("defect", ["duplicate_id", "bad_turn", "bool_as_scale", "int_as_binary", "bad_score",
                                  "critical_zeroing", "bad_na", "missing_criterion"])
def test_submission_validator_rejects_corrupt_or_nonconforming_exports(defect):
    originals, entries = fixtures()
    payload = build_submission(originals, entries, "Fixture team", "prod")
    row = payload["results"][0]
    if defect == "duplicate_id":
        payload["results"][1]["conversation_id"] = row["conversation_id"]
    elif defect == "bad_turn":
        row["criteria"][0]["evidence_turns"] = [0]
    elif defect == "bool_as_scale":
        row["criteria"][3]["value"] = True
    elif defect == "int_as_binary":
        row["criteria"][0]["value"] = 1
    elif defect == "bad_score":
        row["score"]["final_score"] = 99
    elif defect == "critical_zeroing":
        row["criteria"][-1]["value"] = True
        row["score"] = {"final_score": 0, "critical_flag": True}
    elif defect == "bad_na":
        row["criteria"][0]["value"] = None
    else:
        row["criteria"].pop()
    with pytest.raises(ValueError):
        validate_submission(payload, originals, "prod")


def test_source_revision_mismatch_and_wrong_dataset_size_are_rejected():
    originals, entries = fixtures()
    with pytest.raises(ValueError, match="65 DEV"):
        build_submission(originals, entries, "Fixture team", "dev")
    evaluated, checklist, record = entries[originals[1].id]
    altered = evaluated.model_copy(deep=True)
    altered.messages[0].text = "A different source revision"
    entries[originals[1].id] = altered, checklist, record
    with pytest.raises(ValueError, match="source differs"):
        build_submission(originals, entries, "Fixture team", "prod")


def test_critical_flag_does_not_zero_the_final_score():
    originals, entries = fixtures()
    entries[originals[0].id][2]["evaluation"]["judgments"][-1]["answer"] = "yes"
    result = build_submission(originals, entries, "Fixture team", "prod")["results"][0]
    assert result["score"] == {"final_score": 85.38, "critical_flag": True}


def test_dev_preserves_all_65_original_ids_including_missing_assessments():
    originals, _ = fixtures()
    dev = [originals[0].model_copy(update={"id": f"dev-original-{i}"}) for i in range(65)]
    payload = build_submission(dev, {}, "polygon", "dev")
    assert len(payload["results"]) == 65
    assert [r["conversation_id"] for r in payload["results"]] == [c.id for c in dev]
    assert all(r["status"] == "error" and r["score"] is None for r in payload["results"])


def test_conditional_snapshot_context_cannot_be_lost_in_official_score_only_export():
    originals, entries = fixtures()
    original = originals[0]
    _, rubric, record = entries[original.id]
    reviewed = select_reference_context(original, ROOT / "references/freedom-global-products-20261107.json",
        "freedom-finance-global-platform", mode="snapshot_review", as_of="2026-11-07",
        rationale="Explicit hypothetical product review; actual entity/date remains unknown.")
    entries[original.id] = reviewed, rubric, record
    row = build_submission(originals, entries, "Fixture team", "prod")["results"][0]
    assert row["status"] == "error" and row["score"] is None
    assert "Conditional snapshot review" in row["error"]
