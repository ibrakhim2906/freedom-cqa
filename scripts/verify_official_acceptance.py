"""Verify the frozen six-case development suite without inference or app writes.

This command never constructs an Evaluator/client or touches the usage ledger.
Schema preparation is imported only as a pure function. Numeric values here are
expected-vector arithmetic, not model results or organizer Ground Truth.
"""

import hashlib
import json

from cqa.datasets import load_cases
from cqa.evaluator import schema_for
from cqa.grounding import evidence_context_for
from cqa.models import Evaluation, Judgment
from cqa.prompt import GROUNDED_VERSION, fingerprint, payload_for
from cqa.rubric import load_checklist
from cqa.scoring import calculate_score, validate_evaluation
from cqa.settings import ROOT

STEM = "official-facts-acceptance-v1"
SUITE = ROOT / f"evals/{STEM}.jsonl"
NOTES = ROOT / f"evals/{STEM}.review.json"
MANIFEST = ROOT / f"evals/{STEM}.freeze.json"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(value):
    return hashlib.sha256(value).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def lf_hash(path):
    # Match Git's LF checkout across Windows/Linux while preserving all other
    # source bytes. Raw creation receipts are recorded separately, not rewritten.
    return sha(path.read_bytes().replace(b"\r\n", b"\n"))


def expected_evaluation(case, note):
    return Evaluation(judgments=[Judgment(
        criterion_id=e.criterion_id, status=e.status, answer=e.answer,
        explanation=e.rationale, evidence=[], counterevidence=[],
        checked_message_ids=note["criterion_spans"][e.criterion_id],
        uncertainty=e.rationale if e.status == "needs_review" else None)
        for e in case.expectations], request_coverage=[], scope_notes=[
            "Expected-vector arithmetic only. No model inference or factual claim audit was produced."])


def main():
    freeze, notes = read(MANIFEST), read(NOTES)
    assert freeze["kind"] == "pre_inference_development_acceptance_freeze"
    assert notes["organizer_ground_truth"] is False
    for entry in freeze["frozen_files"]:
        assert sha((ROOT / entry["path"]).read_bytes()) == entry["sha256"], f"Frozen v1 file changed: {entry['path']}"
    for entry in freeze["dependencies"]:
        assert lf_hash(ROOT / entry["path"]) == entry["lf_sha256"], f"Pinned dependency changed: {entry['path']}"
    for entry in freeze["evaluator_sources"]:
        assert lf_hash(ROOT / entry["path"]) == entry["lf_sha256"], f"Evaluator changed: {entry['path']}"
    assert freeze["grounded_prompt_version"] == GROUNDED_VERSION
    checklist = load_checklist(ROOT / freeze["checklist_file"])
    assert sha(canonical(checklist.model_dump())) == freeze["canonical_checklist_sha256"]
    cases = load_cases(SUITE)
    assert len(cases) == freeze["case_count"] == 6
    assert [c.id for c in cases] == freeze["ordered_case_ids"]
    indexed_notes = {n["case_id"]: n for n in notes["cases"]}
    assert len(indexed_notes) == 6
    pinned = {p["case_id"]: p for p in freeze["cases"]}
    pack = read(ROOT / freeze["reference_pack_file"])
    pack_refs = {r["id"]: r for r in pack["references"]}
    total_judgments = 0
    for case in cases:
        assert case.source == "authored" and case.label_provenance == "ai_authored_provisional"
        assert case.checklist_override is None
        note, pin = indexed_notes[case.id], pinned[case.id]
        c = case.evaluator_input()
        assert c == case.conversation
        assert {r.id: r.model_dump() for r in c.references} == pack_refs
        expected = expected_evaluation(case, note)
        validate_evaluation(expected, c, checklist)
        assert len(case.expectations) == len(checklist.criteria) == 8
        total_judgments += len(case.expectations)
        score = calculate_score(expected, checklist)
        assert score == pin["expected_arithmetic"]
        assert sha(canonical(c.model_dump())) == pin["canonical_conversation_sha256"]
        assert fingerprint(c, checklist, grounded=True) == pin["input_fingerprint"]
        payload = payload_for(c, checklist, grounded=True)
        assert sha(payload.encode()) == pin["model_payload_sha256"]
        assert sha(canonical(schema_for(c, checklist, grounded=True))) == pin["schema_sha256"]
        context = evidence_context_for(c)
        assert context == note["expected_source_context"]
        assert context["assessment"]["conditional"] == pin["conditional_snapshot_review"]
        if c.reference_context:
            assert c.reference_context.pack_sha256 == freeze["reference_pack_raw_sha256_at_freeze"]
        model_input = json.loads(payload)
        assert model_input["conversation"]["id"] == "conversation"
        assert not {"expectations", "tags", "family", "label_provenance", "source"} & model_input.keys()
        assert not {"expectations", "tags", "family", "label_provenance", "source"} & model_input["conversation"].keys()
        assert case.id not in payload
        assert all(e.rationale not in payload for e in case.expectations)
        assert model_input["usable_reference_ids"] == [r["reference_id"] for r in context["references"] if r["usable"]]
        mids = {m.id: m for m in c.messages}
        for request in note["request_checks"]:
            assert all(mids[mid].speaker == "client" for mid in request["request_message_ids"])
            assert all(mids[mid].speaker == "operator" for mid in request["operator_answer_ids"])
        for fact in note["fact_checks"]:
            assert all(mids[mid].speaker == "operator" for mid in fact["operator_message_ids"])
            assert set(fact["usable_source_ids"]) <= set(model_input["usable_reference_ids"])
            assert fact["expected_status"] in {"supported", "unverified"}
        expected_deductions = set()
        for criterion in checklist.criteria:
            j = next(e for e in case.expectations if e.criterion_id == criterion.id)
            if j.status == "scored" and criterion.kind != "flag":
                fraction = next(l.fraction for l in criterion.levels if l.value == j.answer)
                if fraction < max(l.fraction for l in criterion.levels):
                    expected_deductions.add(criterion.id)
        assert {d["criterion_id"] for d in note["preserved_deductions"]} == expected_deductions
        for deduction in note["preserved_deductions"]:
            criterion = next(x for x in checklist.criteria if x.id == deduction["criterion_id"])
            assert set(deduction["source_message_ids"]) <= mids.keys()
            assert any(deduction["rule_quote"] in text for text in [
                criterion.instruction, *[l.description for l in criterion.levels]])
        print(f"{case.id}: expected consultation={next(e.answer or e.status for e in case.expectations if e.criterion_id == 'consultation')}; expected total={score['total']}; usable sources={len(model_input['usable_reference_ids'])}; conditional={pin['conditional_snapshot_review']}")

    # Paired controls isolate the spoken next action and source applicability.
    first, second, positive, _, call, negative = [c.conversation for c in cases]
    assert first.messages[0] == second.messages[0]
    assert first.messages[2:] == second.messages[2:]
    assert second.messages[1].text.startswith(first.messages[1].text)
    assert first.messages[1].text != second.messages[1].text
    assert first.references == second.references and first.reference_context == second.reference_context
    assert [(m.speaker, m.text) for m in positive.messages] == [(m.speaker, m.text) for m in negative.messages]
    assert all(r["usable"] for r in evidence_context_for(positive)["references"])
    assert all(not r["usable"] and set(r["rejection_reasons"]) == {"scope_mismatch", "snapshot_date_mismatch"}
               for r in evidence_context_for(negative)["references"])
    assert call.occurred_on is None and call.knowledge_scope is None
    assert call.reference_context.mode == "snapshot_review"
    assert call.channel == "voice call" and not json.loads(payload_for(call, checklist, grounded=True))["audio_available_to_evaluator"]
    assert total_judgments == 48
    print("Frozen six-case suite verified: 48 provisional expectations; labels excluded from model input; no API requests.")


if __name__ == "__main__":
    main()
