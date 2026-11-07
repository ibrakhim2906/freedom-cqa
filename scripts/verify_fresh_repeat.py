"""Verify the prospective fresh/repeated suite without inference or ledger writes."""

import json

from cqa.datasets import load_cases
from cqa.evaluator import schema_for
from cqa.grounding import evidence_context_for
from cqa.prompt import GROUNDED_SYSTEM, GROUNDED_VERSION, fingerprint, payload_for
from cqa.rubric import load_checklist
from cqa.scoring import calculate_score, validate_evaluation
from cqa.settings import ROOT
from scripts.verify_evidence_contract_candidate import schema_statistics
from scripts.verify_official_acceptance import canonical, expected_evaluation, lf_hash, read, sha

STEM = "fresh-repeat-v1"


def verify(*, require_execution_receipts=False):
    freeze = read(ROOT / f"evals/{STEM}.freeze.json")
    notes = read(ROOT / f"evals/{STEM}.review.json")
    assert freeze["kind"] == "pre_inference_fresh_repeated_development_freeze"
    assert not notes["organizer_ground_truth"] and not notes["human_expert_labels"]
    for item in freeze["frozen_files"]:
        assert sha((ROOT / item["path"]).read_bytes()) == item["sha256"], item["path"]
    for item in freeze["dependencies"] + freeze["evaluator_sources"]:
        assert lf_hash(ROOT / item["path"]) == item["lf_sha256"], item["path"]
    for item in freeze["review_provenance"] + freeze["execution_procedures"]:
        path = ROOT / item["path"]
        if path.exists():
            assert sha(path.read_bytes()) == item["sha256"], item["path"]
        elif require_execution_receipts:
            raise ValueError(f"Execution requires the original local receipt: {item['path']}")
    assert freeze["prompt_version"] == GROUNDED_VERSION
    assert freeze["prompt_sha256"] == sha(GROUNDED_SYSTEM.encode())
    checklist = load_checklist(ROOT / freeze["checklist_file"])
    assert sha(canonical(checklist.model_dump())) == freeze["canonical_checklist_sha256"]
    cases = load_cases(ROOT / f"evals/{STEM}.jsonl")
    ids = [c.id for c in cases]
    assert len(cases) == freeze["case_count"] == 8 and ids == freeze["ordered_case_ids"]
    assert freeze["repeat_count"] == 3 and len(freeze["round_orders"]) == 3
    for order in freeze["round_orders"]:
        assert len(order) == len(ids) and set(order) == set(ids)
    assert freeze["initial_evaluations"] == len(cases) * freeze["repeat_count"] == 24
    indexed = {item["case_id"]: item for item in notes["cases"]}
    pins = {item["case_id"]: item for item in freeze["cases"]}
    labeled = semantic = 0
    for case in cases:
        assert case.source == "authored" and case.label_provenance == "ai_authored_provisional"
        assert case.checklist_override is None and case.evaluator_input() == case.conversation
        c, note, pin = case.conversation, indexed[case.id], pins[case.id]
        expected_ids = {x.criterion_id for x in case.expectations}
        rubric_ids = {x.id for x in checklist.criteria}
        assert len(expected_ids) == len(case.expectations) and expected_ids <= rubric_ids
        omitted = {item["criterion_id"] for item in note["unscored_rubric_ambiguities"]}
        assert not expected_ids & omitted and expected_ids | omitted == rubric_ids
        assert sha(canonical(c.model_dump())) == pin["canonical_conversation_sha256"]
        assert fingerprint(c, checklist, grounded=True) == pin["input_fingerprint"]
        payload = payload_for(c, checklist, grounded=True)
        assert sha(payload.encode()) == pin["model_payload_sha256"]
        wire = schema_for(c, checklist, grounded=True)
        assert sha(canonical(wire)) == pin["schema_sha256"]
        schema_statistics(wire)
        assert evidence_context_for(c) == note["expected_source_context"]
        data = json.loads(payload)
        forbidden = {"expectations", "tags", "family", "label_provenance", "source", "semantic_checks"}
        assert data["conversation"]["id"] == "conversation"
        assert not forbidden & data.keys() and not forbidden & data["conversation"].keys()
        assert case.id not in payload and all(e.rationale not in payload for e in case.expectations)
        mids = {m.id for m in c.messages}
        for check in note["semantic_checks"]:
            assert check["id"] and check["expectation"]
            assert set(check["source_message_ids"]) <= mids
        if not omitted:
            expected = expected_evaluation(case, note)
            validate_evaluation(expected, c, checklist)
            assert calculate_score(expected, checklist) == pin["expected_arithmetic"]
        else:
            assert pin["expected_arithmetic"] is None
        labeled += len(case.expectations)
        semantic += len(note["semantic_checks"])
    for pair in notes["pairs"]:
        a, b = [next(c.conversation for c in cases if c.id == cid) for cid in pair["case_ids"]]
        assert len(a.messages) == len(b.messages)
        changed = [x.id for x, y in zip(a.messages, b.messages, strict=True) if x != y]
        assert changed == pair["changed_message_ids"]
        assert a.references == b.references and a.knowledge_scope == b.knowledge_scope
        assert a.occurred_on == b.occurred_on and a.reference_context == b.reference_context
    assert labeled == freeze["labeled_judgments"] and semantic == freeze["semantic_checks"]
    assert freeze["expected_pair_comparisons"] == labeled * freeze["repeat_count"]
    return freeze


if __name__ == "__main__":
    manifest = verify()
    print(f"Verified eight fresh cases, {manifest['labeled_judgments']} frozen provisional labels, "
          f"{manifest['semantic_checks']} semantic checks, and 24 planned initial evaluations.")
    print("Expected-label ambiguities remain unscored; no client or API call was made.")
