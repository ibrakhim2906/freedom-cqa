"""Check unchanged frozen data and describe the new engine without paid inference.

The baseline verifier deliberately pins the OLD engine too. This separate command
does not loosen it or rewrite its manifest: it checks the same immutable case/label
bytes and records the candidate prompt/schema/source identities explicitly.
"""

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import jsonschema

from cqa.datasets import load_cases
from cqa.evaluator import Evaluator, schema_for
from cqa.grounding import evidence_context_for
from cqa.models import Conversation, Evaluation
from cqa.output_contract import decode_evaluation
from cqa.prompt import GROUNDED_SYSTEM, GROUNDED_VERSION, fingerprint, payload_for
from cqa.rubric import load_checklist
from cqa.scoring import calculate_score, validate_evaluation
from cqa.settings import ROOT, Settings
from scripts.verify_official_acceptance import canonical, expected_evaluation, lf_hash, read, sha

FROZEN = ROOT / "evals/official-facts-acceptance-v1.freeze.json"


def schema_statistics(schema):
    properties = enums = chars = 0
    unsupported = []

    def visit(node):
        nonlocal properties, enums, chars
        if isinstance(node, dict):
            unsupported.extend(key for key in node if key in {
                "allOf", "oneOf", "not", "if", "then", "else", "uniqueItems",
                "dependentRequired", "dependentSchemas", "patternProperties"})
            if node.get("type") == "object":
                fields = node.get("properties", {})
                assert node.get("additionalProperties") is False
                assert set(node.get("required", [])) == set(fields)
                properties += len(fields)
                chars += sum(len(name) for name in fields)
            chars += sum(len(name) for name in node.get("$defs", {}))
            if "enum" in node:
                assert node["enum"], "Empty enums are invalid in provider schemas"
                enums += len(node["enum"])
                chars += sum(len(str(v)) for v in node["enum"])
                if len(node["enum"]) > 250:
                    assert sum(len(str(v)) for v in node["enum"]) <= 15_000
            if isinstance(node.get("const"), str):
                chars += len(node["const"])
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    def depth(node, seen=()):
        if not isinstance(node, dict):
            return 0
        if "$ref" in node:
            name = node["$ref"].split("/")[-1]
            assert name not in seen, "Unexpected recursive evidence schema"
            return depth(schema["$defs"][name], (*seen, name))
        alternatives = [depth(child, seen) for child in node.get("anyOf", [])]
        if node.get("type") == "object":
            return 1 + max((depth(child, seen) for child in node.get("properties", {}).values()), default=0)
        if node.get("type") == "array":
            return 1 + depth(node["items"], seen)
        return max(alternatives, default=0)

    jsonschema.Draft202012Validator.check_schema(schema)
    assert schema.get("type") == "object" and "anyOf" not in schema
    visit(schema)
    nesting = depth(schema)
    assert not unsupported, f"Unsupported structured-output keywords: {unsupported}"
    assert properties <= 5000 and enums <= 1000 and chars <= 120_000 and nesting <= 10
    return {"schema_bytes": len(json.dumps(schema).encode()), "object_properties": properties,
            "enum_values": enums, "string_budget_characters": chars, "container_nesting_depth": nesting}


def inspect_candidate():
    frozen = read(FROZEN)
    for entry in frozen["frozen_files"]:
        assert sha((ROOT / entry["path"]).read_bytes()) == entry["sha256"], f"Frozen v1 artifact changed: {entry['path']}"
    for entry in frozen["dependencies"]:
        assert lf_hash(ROOT / entry["path"]) == entry["lf_sha256"], f"Frozen dependency changed: {entry['path']}"
    cases = load_cases(ROOT / "evals/official-facts-acceptance-v1.jsonl")
    notes = {n["case_id"]: n for n in read(ROOT / "evals/official-facts-acceptance-v1.review.json")["cases"]}
    pins = {p["case_id"]: p for p in frozen["cases"]}
    checklist = load_checklist(ROOT / frozen["checklist_file"])
    assert sha(canonical(checklist.model_dump())) == frozen["canonical_checklist_sha256"]
    assert [c.id for c in cases] == frozen["ordered_case_ids"]
    assert GROUNDED_VERSION.startswith("evaluator-v7-")
    settings = Settings(api_key="")  # Data only. No key, Evaluator/client or ledger is constructed.
    proxy = SimpleNamespace(settings=settings, grounded=True)
    prepared = []
    for case in cases:
        c, pin = case.conversation, pins[case.id]
        assert sha(canonical(c.model_dump())) == pin["canonical_conversation_sha256"]
        assert sha(payload_for(c, checklist, grounded=True).encode()) == pin["model_payload_sha256"]
        assert calculate_score(expected_evaluation(case, notes[case.id]), checklist) == pin["expected_arithmetic"]
        assert evidence_context_for(c) == notes[case.id]["expected_source_context"]
        schema = schema_for(c, checklist, grounded=True)
        statistics = schema_statistics(schema)
        _, allowance = Evaluator._estimate(proxy, Evaluator._prepare(proxy, c, checklist))
        prepared.append({"case_id": case.id, "input_fingerprint": fingerprint(c, checklist, grounded=True),
            "schema_sha256": sha(canonical(schema)), **statistics,
            "first_request_conservative_bound_usd": round(allowance, 6),
            "expected_arithmetic_unchanged": True})

    # Explicitly authored contract examples are tests, never new provider results.
    fixture = read(ROOT / "tests/fixtures/evidence-contract-v2-replay.json")
    replay = []
    for item in fixture["cases"]:
        c = Conversation.model_validate(item["conversation"])
        original = item["rejected_coverage_v1_wire"]
        authored = item["authored_coverage_v2_wire"]
        try:
            decode_evaluation(json.dumps(original), require_evidence_contract=True)
        except ValueError:
            rejected = True
        else:
            rejected = False
        assert rejected
        assert authored["judgments"] == original["judgments"]
        ev = decode_evaluation(json.dumps(authored), require_evidence_contract=True)
        jsonschema.Draft202012Validator(schema_for(c, checklist, grounded=True)).validate(authored)
        validate_evaluation(ev, c, checklist, require_audit=True)
        replay.append({"case_id": c.id, "historical_output_still_rejected": True,
                       "explicit_test_encoding_valid": True, "judgments_and_deductions_unchanged": True,
                       "not_an_api_result": True})

    # Revalidate accepted historical records without reinterpreting their v1 contracts.
    historical = ROOT / "artifacts/official-facts-live-v1/benchmark.json"
    history_count = 0
    if historical.exists():
        indexed = {c.id: c for c in cases}
        for row in read(historical)["rows"]:
            record = row["record"]
            if record["status"] == "completed":
                ev = Evaluation.model_validate(record["evaluation"])
                validate_evaluation(ev, indexed[row["case_id"]].conversation, checklist, require_audit=True)
                assert calculate_score(ev, checklist) == record["score"]
                history_count += 1
            else:
                assert record["evaluation"] is None and record["score"] is None

    return {"kind": "offline_evidence_contract_v2_candidate_not_api_benchmark", "api_calls": 0,
        "baseline_freeze_sha256": sha(FROZEN.read_bytes()), "baseline_prompt_version": frozen["grounded_prompt_version"],
        "candidate_prompt_version": GROUNDED_VERSION, "candidate_prompt_sha256": sha(GROUNDED_SYSTEM.encode()),
        "frozen_inputs_labels_and_expected_arithmetic_unchanged": True,
        "frozen_files": frozen["frozen_files"], "dependencies": frozen["dependencies"],
        "candidate_evaluator_sources": [{"path": str(p.relative_to(ROOT)).replace("\\", "/"),
            "lf_sha256": lf_hash(p)} for p in sorted((ROOT / "cqa").glob("*.py"))],
        "candidate_configuration": frozen["grounded_configuration"] | {"evidence_contract": "coverage-v2"},
        "cases": prepared, "test_only_replay": replay,
        "accepted_historical_records_revalidated_if_present": history_count,
        "limitations": ["No provider acceptance or new inference quality/stability measured.",
                       "Authored test encodings do not repair, accept or re-score historical failed outputs.",
                       "This separate candidate identity does not alter or replace the pinned v1 baseline engine."]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", type=Path, help="Write a new candidate protocol under ignored artifacts; never overwrite")
    parser.add_argument("--check-protocol", type=Path, help="Verify a previously recorded candidate protocol")
    args = parser.parse_args()
    result = inspect_candidate()
    if args.record:
        path = (ROOT / args.record).resolve()
        if not path.is_relative_to((ROOT / "artifacts").resolve()) or path.exists():
            raise ValueError("Use a new protocol filename under ignored artifacts/")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    if args.check_protocol:
        assert read(ROOT / args.check_protocol) == result, "Candidate differs from its recorded protocol; keep both versions"
    print("Verified unchanged frozen six-case inputs and all 48 expectations; prepared coverage-v2 offline.")
    print(f"Candidate {GROUNDED_VERSION}; {len(result['test_only_replay'])} explicit test encodings valid; historical failures remain failed.")
    print("No client constructed or API call made. Provider behavior remains untested.")


if __name__ == "__main__":
    main()
