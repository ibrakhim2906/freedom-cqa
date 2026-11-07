"""Verify v4 candidate without inference, historical migration or ledger writes."""

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from cqa.evaluator import REPAIR_FEEDBACK_BYTES, REPAIR_INSTRUCTIONS, Evaluator, schema_for
from cqa.prompt import GROUNDED_SYSTEM, GROUNDED_VERSION, payload_for
from cqa.rubric import load_checklist
from cqa.scoring import calculate_score, validate_evaluation
from cqa.settings import ROOT, Settings
from cqa.source_spans import build_catalog
from cqa.span_transport import decode_span_evaluation, decode_span_evaluation_v3
from scripts.verify_evidence_contract_candidate import schema_statistics
from scripts.verify_official_acceptance import canonical, lf_hash, read, sha
from scripts.verify_source_span_candidate import (
    EXPECTED_LEDGER,
    frozen_cases,
    latest_organizer_records,
    ledger_snapshot,
    revalidate_records,
    source_identities,
    verify_preserved_receipts,
)


def verify_source_view(case, checklist, payload, catalog):
    data = json.loads(payload)
    view = data.pop("source_span_catalog")
    assert view["fingerprint"] == catalog.fingerprint and view["view"] == "linked-parts-v1"
    assert data.pop("output_contract") == "span-v4"
    declared, text = [], {}
    for source in view["sources"]:
        sid = source["span_id"]
        full = catalog.entries[sid]
        assert full.is_full
        text[sid] = "".join(part["text"] for part in source["parts"])
        assert text[sid] == full.quote
        declared.append(sid)
        for part in source["parts"]:
            if part["span_id"] is not None:
                fragment = catalog.entries[part["span_id"]]
                assert not fragment.is_full and fragment.quote == part["text"]
                assert (fragment.kind, fragment.source_id, fragment.field) == (full.kind, full.source_id, full.field)
                declared.append(fragment.span_id)
    assert len(declared) == len(set(declared)) and set(declared) == set(catalog.entries)

    def restore(value):
        if isinstance(value, dict):
            if set(value) == {"source_span_id"}:
                return text[value["source_span_id"]]
            return {key: restore(item) for key, item in value.items()}
        return [restore(item) for item in value] if isinstance(value, list) else value

    old = json.loads(payload_for(case.evaluator_input(), checklist, grounded=True))
    assert restore(data) == old, "Every source/context field must reconstruct without truncation"
    assert data["conversation"]["id"] == "conversation" and case.id not in payload
    assert not {"expectations", "tags", "family", "source", "label_provenance", "semantic_checks"} & data.keys()
    assert not {"expectations", "tags", "family", "source", "label_provenance", "semantic_checks"} & data["conversation"].keys()


def verify_manual_history(checklist, all_cases):
    baseline = read(ROOT / "artifacts/manual-chat-v2/protocol.frozen.json")
    assert sha((ROOT / baseline["expectations_file"]).read_bytes()) == baseline["expectations_sha256"]
    for name, digest in baseline["preserved_original_freezes"].items():
        assert sha((ROOT / name).read_bytes()) == digest
    assert sha((ROOT / "artifacts/manual-chat-v2/private-manifest.json").read_bytes()) == baseline["private_manifest_sha256"]
    receipts = []
    for family in ["manual-chat-v1", "manual-chat-v2"]:
        directory = ROOT / "artifacts" / family
        manifest = read(directory / "private-manifest.json")
        packet_cases = {p["packet"].removesuffix(".txt").removeprefix("packet-"):
                        p["case_id_private_local_mapping"] for p in manifest["packets"]}
        names = ("validation-receipt.json",) if family == "manual-chat-v1" else ("receipt.json",)
        for name in names:
            for path in sorted((directory / "results").glob("*/" + name)):
                receipt = read(path)
                packet = receipt["packet"]
                raw_path = path.parent / receipt["local_copy"]
                raw = raw_path.read_bytes()
                assert sha(raw) == receipt["raw_response_sha256"]
                conversation = all_cases[packet_cases[packet]].evaluator_input()
                expected = receipt["validation"]
                try:
                    result = decode_span_evaluation_v3(raw.decode("utf-8"), conversation, checklist)
                    validate_evaluation(result, conversation, checklist, require_audit=True)
                except ValueError as error:
                    assert expected["structural_validation"] == "failed", str(error)
                    status, total = "failed_preserved", None
                else:
                    assert expected["structural_validation"] == "passed"
                    assert calculate_score(result, checklist) == expected["score"]
                    status, total = "accepted_score_unchanged", expected["score"]["total"]
                try:
                    decode_span_evaluation(raw.decode("utf-8"), conversation, checklist)
                except ValueError:
                    pass
                else:
                    raise AssertionError("Historical v3 response must never be accepted by current v4 decoder")
                receipts.append({"path": str(path.relative_to(ROOT)).replace("\\", "/"),
                    "sha256": sha(path.read_bytes()), "raw_sha256": sha(raw), "historical_status": status, "total": total})
    assert len(receipts) == 6
    assert sum(r["historical_status"] == "accepted_score_unchanged" for r in receipts) == 3
    return receipts


def inspect_candidate():
    before = ledger_snapshot()
    assert before == EXPECTED_LEDGER
    engine = source_identities()
    frozen, manifests, vectors, labels = frozen_cases()
    organizer, organizer_records = latest_organizer_records()
    checklist = load_checklist(ROOT / "checklists/freedom-reviewed-015.json")
    cases = frozen + [("organizer-latest-mixed", c) for c in organizer.values()]
    assert len(cases) == 79 and GROUNDED_VERSION.startswith("evaluator-v9-")
    old = read(ROOT / "artifacts/source-spans-v3/candidate-protocol.json")
    old_cases = {row["case_id"]: row for row in old["prepared_cases"]}
    settings = Settings(api_key="")
    proxy = SimpleNamespace(settings=settings, grounded=True)
    prepared = []
    extra = REPAIR_FEEDBACK_BYTES + len(REPAIR_INSTRUCTIONS.encode()) + 128
    for family, case in cases:
        conversation = case.evaluator_input()
        old_schema = schema_for(conversation, checklist, grounded=True, source_contract=True,
                                source_contract_version="span-v3")
        assert sha(canonical(old_schema)) == old_cases[case.id]["candidate_schema_sha256"], case.id
        old_payload = payload_for(conversation, checklist, grounded=True, source_contract=True,
                                  source_contract_version="span-v3")
        assert sha(old_payload.encode()) == old_cases[case.id]["candidate_payload_sha256"], case.id
        request = Evaluator._prepare(proxy, conversation, checklist)
        instructions, payload, schema, cap = request
        assert instructions == GROUNDED_SYSTEM and cap == settings.max_output_tokens == 6000
        assert schema == schema_for(conversation, checklist, grounded=True, source_contract=True)
        assert schema["properties"]["contract_version"]["enum"] == ["span-v4"]
        verify_source_view(case, checklist, payload, build_catalog(conversation, checklist))
        bound, reservation = Evaluator._estimate(proxy, request)
        assert bound + extra <= 200_000, case.id
        prepared.append({"case_id": case.id, "family": family, "payload_sha256": sha(payload.encode()),
            "schema_sha256": sha(canonical(schema)), "input_with_protected_repair": bound + extra,
            "conservative_first_request_reservation_usd": reservation, **schema_statistics(schema)})
    known = {c.id: c for family, c in frozen if family == "official-facts-acceptance-v1"}
    fresh = {c.id: c for family, c in frozen if family == "fresh-repeat-v1"}
    history = {"organizer_latest_mixed_65": revalidate_records(organizer_records.items(), organizer, checklist)}
    for name, path, inputs in [
        ("known_v6", "artifacts/official-facts-live-v1/benchmark.json", known),
        ("known_v7", "artifacts/evidence-contract-live-v2/benchmark.json", known),
        ("fresh_base", "artifacts/fresh-repeat-live-v1/benchmark.json", fresh),
        ("fresh_unsent_continuation", "artifacts/fresh-repeat-live-v1/continuation.json", fresh),
    ]:
        history[name] = revalidate_records(((r["case_id"], r["record"]) for r in read(ROOT / path)["rows"]), inputs, checklist)
    manual = verify_manual_history(checklist, {c.id: c for _, c in cases})
    assert source_identities() == engine and ledger_snapshot() == before
    return {"kind": "offline_source_contract_v4_candidate_not_api_benchmark", "api_calls": 0,
        "incremental_api_cost_usd": 0, "candidate_prompt_version": GROUNDED_VERSION,
        "prompt_sha256": sha(GROUNDED_SYSTEM.encode()), "source_contract": "span-v4", "semantic_audit": "coverage-v4",
        "source_identities": engine, "verification_script_lf_sha256": lf_hash(Path(__file__).resolve()),
        "preserved_original_receipts": verify_preserved_receipts(), "original_frozen_manifests": manifests,
        "unchanged_frozen_labels": labels, "unchanged_full_expected_vectors": vectors,
        "all_79_historical_v3_schemas_and_payloads_unchanged": True, "prepared_cases": prepared,
        "maxima": {field: max(row[field] for row in prepared) for field in ["schema_bytes", "object_properties",
            "enum_values", "string_budget_characters", "container_nesting_depth", "input_with_protected_repair"]},
        "api_history": history, "manual_v3_history": manual,
        "accepted_api_historical_scores_unchanged": sum(v.get("completed", 0) for v in history.values()),
        "ledger_before": before, "ledger_after": ledger_snapshot(),
        "limitations": ["Offline preparation/compatibility does not measure provider acceptance or semantic accuracy.",
            "New manual inference must use a separately frozen execution protocol and unchanged expectations."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path)
    parser.add_argument("--check-protocol", type=Path)
    args = parser.parse_args()
    result = inspect_candidate()
    if args.record:
        path = (ROOT / args.record).resolve()
        assert path.is_relative_to(ROOT / "artifacts") and not path.exists(), "Use a new ignored artifact path"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    if args.check_protocol:
        assert read(ROOT / args.check_protocol) == result, "Candidate changed; preserve old receipt"
    print("Verified 79 current schemas, 110 original frozen labels, 97 historical API scores and six manual receipts.")
    print(f"Candidate {GROUNDED_VERSION}; $0 API cost; largest protected input {result['maxima']['input_with_protected_repair']} bytes.")


if __name__ == "__main__":
    main()
