"""Separate source-span v3 candidate check: no client, inference or ledger writes.

Old manifests deliberately pin old engines. This command does not loosen those
checks or re-freeze their cases; it preserves the original inputs/expectations
and separately describes the current engine, source catalog and strict schema.
"""

import argparse
import json
import sqlite3
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

from cqa.datasets import load_cases
from cqa.evaluator import REPAIR_FEEDBACK_BYTES, REPAIR_INSTRUCTIONS, Evaluator, schema_for
from cqa.grounding import evidence_context_for
from cqa.models import Evaluation
from cqa.prompt import GROUNDED_SYSTEM, GROUNDED_VERSION, fingerprint, payload_for
from cqa.rubric import load_checklist
from cqa.scoring import calculate_score, validate_evaluation
from cqa.settings import ROOT, Settings
from cqa.source_spans import VERSION as SOURCE_SPAN_VERSION
from cqa.source_spans import build_catalog
from scripts.verify_evidence_contract_candidate import schema_statistics
from scripts.verify_official_acceptance import canonical, expected_evaluation, lf_hash, read, sha

FROZEN_STEMS = ("official-facts-acceptance-v1", "fresh-repeat-v1")
EXPECTED_LEDGER = {"rows": 591, "max_id": 591, "settled_sum": 23.141316}


def ledger_snapshot():
    path = ROOT / "data/runtime/usage.sqlite3"
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
        count, maximum, cost = db.execute("SELECT COUNT(*),MAX(id),SUM(cost) FROM usage").fetchone()
    return {"rows": count, "max_id": maximum, "settled_sum": round(cost or 0, 6)}


def source_identities():
    return [{"path": str(p.relative_to(ROOT)).replace("\\", "/"), "lf_sha256": lf_hash(p)}
            for p in sorted((ROOT / "cqa").glob("*.py"))]


def verify_preserved_receipts():
    """Existing run receipts pin raw bytes without asserting old code is current."""
    preserved = {}

    def add(path, digest):
        assert path not in preserved or preserved[path] == digest, f"Conflicting preservation receipts: {path}"
        assert sha((ROOT / path).read_bytes()) == digest, f"Preserved file changed: {path}"
        preserved[path] = digest

    for item in read(ROOT / "artifacts/evidence-contract-v2/before.json")["preserved"]:
        add(item["path"], item["sha256"])
    for path in ["audits/evidence-contract-v2-live-results.json", "audits/fresh-repeat-v1-results.json"]:
        for item in read(ROOT / path)["source_sha256"]:
            add(item["path"], item["sha256"])
    fresh_marker = read(ROOT / "artifacts/fresh-repeat-live-v1/run-started.json")
    add("evals/fresh-repeat-v1.freeze.json", fresh_marker["freeze_sha256"])
    return [{"path": path, "sha256": digest} for path, digest in sorted(preserved.items())]


def frozen_cases():
    output, arithmetic, labeled, manifests = [], 0, 0, []
    for stem in FROZEN_STEMS:
        path = ROOT / f"evals/{stem}.freeze.json"
        frozen, notes = read(path), read(ROOT / f"evals/{stem}.review.json")
        assert notes["organizer_ground_truth"] is False
        for item in frozen["frozen_files"]:
            assert sha((ROOT / item["path"]).read_bytes()) == item["sha256"], item["path"]
        for item in frozen["dependencies"]:
            assert lf_hash(ROOT / item["path"]) == item["lf_sha256"], item["path"]
        checklist = load_checklist(ROOT / frozen["checklist_file"])
        assert sha(canonical(checklist.model_dump())) == frozen["canonical_checklist_sha256"]
        cases = load_cases(ROOT / f"evals/{stem}.jsonl")
        assert len(cases) == frozen["case_count"] and [c.id for c in cases] == frozen["ordered_case_ids"]
        indexed = {n["case_id"]: n for n in notes["cases"]}
        pins = {p["case_id"]: p for p in frozen["cases"]}
        for case in cases:
            c, pin, note = case.evaluator_input(), pins[case.id], indexed[case.id]
            assert case.checklist_override is None and c == case.conversation
            assert sha(canonical(c.model_dump())) == pin["canonical_conversation_sha256"]
            legacy = payload_for(c, checklist, grounded=True, source_contract=False)
            assert sha(legacy.encode()) == pin["model_payload_sha256"]
            assert evidence_context_for(c) == note["expected_source_context"]
            if len(case.expectations) == len(checklist.criteria):
                expected = expected_evaluation(case, note)
                validate_evaluation(expected, c, checklist)
                assert calculate_score(expected, checklist) == pin["expected_arithmetic"]
                arithmetic += 1
            else:
                assert pin["expected_arithmetic"] is None
                omitted = {x["criterion_id"] for x in note["unscored_rubric_ambiguities"]}
                assert omitted | {e.criterion_id for e in case.expectations} == {c.id for c in checklist.criteria}
            labeled += len(case.expectations)
            output.append((stem, case))
        manifests.append({"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(path.read_bytes()),
                          "baseline_prompt_version": frozen.get("prompt_version", frozen.get("grounded_prompt_version")),
                          "cases": len(cases), "original_engine_identity_retained_not_replaced": True})
    assert len(output) == 14 and labeled == 110 and arithmetic == 12
    return output, manifests, arithmetic, labeled


def latest_organizer_records():
    path = ROOT / "artifacts/organizer-65-v1/merged.json"
    cases = {c.id: c for c in load_cases(path.with_suffix(".suite.jsonl"))}
    assert len(cases) == 65
    protocol = read(ROOT / "artifacts/organizer-65-v1/protocol.json")
    assert sha((ROOT / "data/private/dev.json").read_bytes()) == protocol["original_source_sha256"]
    assert sha((ROOT / "checklists/freedom-reviewed-015.json").read_bytes()) == protocol["checklist_sha256"]
    records = {r["case_id"]: r["record"] for r in read(path)["rows"]}
    overrides = {
        "artifacts/claim-dependencies-v1/focused-candidate.json": {"p1-kz-005", "p1-en-014", "p4-ru-003"},
        "artifacts/claim-dependencies-v1/role-constrained.json": {"p1-ru-018"},
    }
    for name, ids in overrides.items():
        candidate = ROOT / name
        source = {c.id: c for c in load_cases(candidate.with_suffix(".suite.jsonl"))}
        selected = {r["case_id"]: r["record"] for r in read(candidate)["rows"] if r["case_id"] in ids}
        assert set(selected) == ids
        for cid, record in selected.items():
            assert source[cid] == cases[cid], "Organizer override must use the identical frozen source and labels"
            records[cid] = record
    return cases, records


def revalidate_records(rows, cases, checklist):
    counts = Counter()
    for cid, record in rows:
        status = record["status"]
        counts[status] += 1
        if status == "completed":
            evaluation = Evaluation.model_validate(record["evaluation"])
            validate_evaluation(evaluation, cases[cid].conversation, checklist, require_audit=True)
            assert calculate_score(evaluation, checklist) == record["score"]
        else:
            assert record.get("evaluation") is None and record.get("score") is None
    return dict(counts)


def verify_single_copy_view(case, checklist, payload, catalog):
    data = json.loads(payload)
    view = data["source_span_catalog"]
    assert view["fingerprint"] == catalog.fingerprint and view["view"] == "linked-parts-v1"
    sources, declared = {}, []
    for source in view["sources"]:
        span_id = source["span_id"]
        full = catalog.entries[span_id]
        assert full.is_full
        text = "".join(p["text"] for p in source["parts"])
        assert text == full.quote
        sources[span_id] = text
        declared.append(span_id)
        for part in source["parts"]:
            if part["span_id"] is not None:
                fragment = catalog.entries[part["span_id"]]
                assert not fragment.is_full and fragment.quote == part["text"]
                assert (fragment.kind, fragment.source_id, fragment.field) == (full.kind, full.source_id, full.field)
                declared.append(part["span_id"])
    assert len(declared) == len(set(declared)) and set(declared) == set(catalog.entries)
    assert len(sources) == catalog.full_source_count

    def restore(value):
        if isinstance(value, dict):
            if set(value) == {"source_span_id"}:
                assert value["source_span_id"] in sources
                return sources[value["source_span_id"]]
            return {key: restore(item) for key, item in value.items()}
        return [restore(item) for item in value] if isinstance(value, list) else value

    data.pop("source_span_catalog")
    assert data.pop("output_contract") == "span-v3"
    legacy = json.loads(payload_for(case.conversation, checklist, grounded=True, source_contract=False))
    assert restore(data) == legacy, "Linked source view must reconstruct every original source field/context exactly"
    forbidden = {"expectations", "tags", "family", "label_provenance", "source", "semantic_checks"}
    assert not forbidden & data.keys() and not forbidden & data["conversation"].keys()
    assert data["conversation"]["id"] == "conversation" and case.id not in payload
    # If provisional annotation text coincides with source wording, it must
    # already occur in the original allowlisted input, never come from labels.
    original = json.dumps(legacy, ensure_ascii=False, sort_keys=True)
    for expected in case.expectations:
        assert expected.rationale not in payload or expected.rationale in original


def inspect_candidate():
    before = ledger_snapshot()
    assert before == EXPECTED_LEDGER, "This no-paid-tests checkpoint expects the last reconciled ledger unchanged"
    engine_before = source_identities()
    preserved = verify_preserved_receipts()
    frozen, manifests, arithmetic, labeled = frozen_cases()
    organizer_cases, organizer_records = latest_organizer_records()
    checklist = load_checklist(ROOT / "checklists/freedom-reviewed-015.json")
    all_cases = frozen + [("organizer-latest-mixed", c) for c in organizer_cases.values()]
    assert len(all_cases) == 79
    assert GROUNDED_VERSION.startswith("evaluator-v8-")
    settings = Settings(api_key="")
    proxy = SimpleNamespace(settings=settings, grounded=True)
    prepared = []
    repair_extra = REPAIR_FEEDBACK_BYTES + len(REPAIR_INSTRUCTIONS.encode("utf-8")) + 128
    for family, case in all_cases:
        conversation = case.evaluator_input()
        catalog = build_catalog(conversation, checklist)
        request = Evaluator._prepare(proxy, conversation, checklist)
        instructions, payload, schema, cap = request
        assert instructions == GROUNDED_SYSTEM and cap == settings.max_output_tokens
        assert payload == payload_for(conversation, checklist, grounded=True, source_contract=True)
        assert schema == schema_for(conversation, checklist, grounded=True, source_contract=True)
        verify_single_copy_view(case, checklist, payload, catalog)
        statistics = schema_statistics(schema)
        input_bound, reservation = Evaluator._estimate(proxy, request)
        assert input_bound + repair_extra <= 200_000, "Protected repair context must fit without dropping sources"
        prepared.append({"case_id": case.id, "family": family, "candidate_input_fingerprint": fingerprint(conversation, checklist, grounded=True),
            "candidate_payload_sha256": sha(payload.encode()), "candidate_schema_sha256": sha(canonical(schema)),
            "catalog_fingerprint": catalog.fingerprint, "catalog_spans": len(catalog.entries), "full_sources": catalog.full_source_count,
            "single_copy_source_view_reconstructs_original": True, "all_catalog_ids_declared_once": True,
            "input_bound_with_framing": input_bound, "input_bound_with_protected_repair": input_bound + repair_extra,
            "first_request_conservative_reservation_usd": round(reservation, 6), **statistics})
    known = {c.id: c for family, c in frozen if family == FROZEN_STEMS[0]}
    fresh = {c.id: c for family, c in frozen if family == FROZEN_STEMS[1]}
    history = {"organizer_latest_mixed_65": revalidate_records(organizer_records.items(), organizer_cases, checklist)}
    for name, path, cases in [
        ("known_v6", "artifacts/official-facts-live-v1/benchmark.json", known),
        ("known_v7", "artifacts/evidence-contract-live-v2/benchmark.json", known),
        ("fresh_base", "artifacts/fresh-repeat-live-v1/benchmark.json", fresh),
        ("fresh_only_previously_unsubmitted_continuation", "artifacts/fresh-repeat-live-v1/continuation.json", fresh),
    ]:
        rows = read(ROOT / path)["rows"]
        history[name] = revalidate_records(((r["case_id"], r["record"]) for r in rows), cases, checklist)
    assert history["known_v6"] == {"completed": 4, "failed": 2}
    assert history["known_v7"] == {"completed": 6}
    assert history["fresh_base"] == {"completed": 21, "failed": 2, "skipped_budget": 1}
    assert history["fresh_only_previously_unsubmitted_continuation"] == {"completed": 1}
    assert history["organizer_latest_mixed_65"] == {"completed": 65}
    after = ledger_snapshot()
    assert after == before and source_identities() == engine_before, "Offline check requires unchanged billing and stable engine files"
    maxima = {field: max(row[field] for row in prepared) for field in ["schema_bytes", "object_properties", "enum_values",
        "string_budget_characters", "container_nesting_depth", "catalog_spans", "full_sources", "input_bound_with_protected_repair"]}
    return {"kind": "offline_source_span_atomic_v3_candidate_not_api_benchmark", "api_calls": 0, "incremental_api_cost_usd": 0,
        "ledger_before": before, "ledger_after": after, "old_frozen_engine_identities_retained": manifests,
        "old_frozen_inputs_expectations_and_expected_arithmetic_unchanged": True,
        "frozen_labeled_judgments": labeled, "unchanged_full_expected_vectors": arithmetic,
        "candidate_prompt_version": GROUNDED_VERSION, "candidate_prompt_sha256": sha(GROUNDED_SYSTEM.encode()),
        "candidate_source_catalog_version": SOURCE_SPAN_VERSION,
        "verification_script": {"path": "scripts/verify_source_span_candidate.py", "lf_sha256": lf_hash(Path(__file__).resolve())},
        "candidate_configuration": {"model": settings.model, "effort": settings.effort, "max_output_tokens": cap,
            "source_contract": "span-v3", "semantic_audit": "coverage-v3", "no_client_constructed": True},
        "candidate_evaluator_sources": engine_before, "preserved_files": preserved,
        "prepared_cases": prepared, "schema_and_protected_context_maxima": maxima,
        "historical_revalidation": history,
        "accepted_historical_evaluations_revalidated_without_regrading": sum(count.get("completed", 0) for count in history.values()),
        "limitations": ["No v8 provider acceptance, judgment quality, repeatability, latency or actual token cost was measured.",
            "Historical validation is compatibility evidence, not a new model result; old failures and budget skip remain unchanged.",
            "Deterministic source identity and structural proof completeness do not establish semantic entailment or atomization completeness.",
            "The original v6/v7 freeze verifiers remain unchanged and intentionally reject a different current engine.",
            "The ledger baseline is this no-paid-tests checkpoint; a later authorized inference run needs a separately recorded execution protocol."]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", type=Path, help="Record a NEW candidate protocol under ignored artifacts; never overwrite")
    parser.add_argument("--check-protocol", type=Path, help="Check an existing protocol against this exact offline candidate")
    args = parser.parse_args()
    result = inspect_candidate()
    if args.record:
        path = (ROOT / args.record).resolve()
        if not path.is_relative_to((ROOT / "artifacts").resolve()) or path.exists():
            raise ValueError("Use a new artifact protocol filename; preserve every prior checkpoint")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    if args.check_protocol:
        assert read(ROOT / args.check_protocol) == result, "Candidate changed; retain both protocol identities"
    print(f"Verified unchanged frozen 110 labels/12 complete vectors; prepared {len(result['prepared_cases'])} current source-span schemas.")
    print(f"Candidate {GROUNDED_VERSION}; historical accepted records revalidated={result['accepted_historical_evaluations_revalidated_without_regrading']}.")
    print("Ledger unchanged: zero API calls, $0 incremental cost. This is offline evidence; live v8 behavior remains untested.")


if __name__ == "__main__":
    main()
