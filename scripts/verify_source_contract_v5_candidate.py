"""Verify the v5 candidate offline without inference, receipt migration or ledger writes."""

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from cqa.datasets import load_cases
from cqa.evaluator import REPAIR_FEEDBACK_BYTES, REPAIR_INSTRUCTIONS, Evaluator, schema_for
from cqa.models import Evaluation, Judgment
from cqa.prompt import GROUNDED_SYSTEM, GROUNDED_VERSION, payload_for
from cqa.rubric import load_checklist
from cqa.scoring import calculate_score, validate_evaluation
from cqa.settings import ROOT, Settings
from cqa.source_spans import build_catalog
from cqa.span_transport import decode_span_evaluation, decode_span_evaluation_v4
from scripts.verify_evidence_contract_candidate import schema_statistics
from scripts.verify_official_acceptance import canonical, lf_hash, read, sha
from scripts.verify_source_contract_v4_candidate import verify_manual_history
from scripts.verify_source_span_candidate import (
    EXPECTED_LEDGER,
    frozen_cases,
    latest_organizer_records,
    ledger_snapshot,
    revalidate_records,
    source_identities,
    verify_preserved_receipts,
)

NOTE_SCOPE_STEM = "note-scope-contrasts-v1"


def verify_source_view(case, checklist, payload, catalog):
    data = json.loads(payload)
    view = data.pop("source_span_catalog")
    assert view["fingerprint"] == catalog.fingerprint and view["view"] == "linked-parts-v1"
    assert data.pop("output_contract") == "span-v5"
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
    assert len(text) == catalog.full_source_count

    def restore(value):
        if isinstance(value, dict):
            if set(value) == {"source_span_id"}:
                return text[value["source_span_id"]]
            return {key: restore(item) for key, item in value.items()}
        return [restore(item) for item in value] if isinstance(value, list) else value

    original = json.loads(payload_for(case.evaluator_input(), checklist, grounded=True))
    assert restore(data) == original, "Every source/context field must reconstruct without truncation"
    assert data["conversation"]["id"] == "conversation" and case.id not in payload
    forbidden = {"expectations", "tags", "family", "source", "label_provenance", "semantic_checks"}
    assert not forbidden & data.keys() and not forbidden & data["conversation"].keys()


def verify_scope_contrasts():
    """Verify frozen inputs and expected arithmetic, never synthesize a source assessment."""
    path = ROOT / f"evals/{NOTE_SCOPE_STEM}.freeze.json"
    frozen = read(path)
    assert frozen["kind"] == "frozen_new_targeted_diagnostic_not_untouched_holdout"
    assert frozen["frozen_before_inference"] is True
    assert frozen["case_count"] == 3 and frozen["frozen_labeled_judgments"] == 6
    expected_paths = {f"checklists/{NOTE_SCOPE_STEM}.json", f"evals/{NOTE_SCOPE_STEM}.jsonl",
                      f"evals/{NOTE_SCOPE_STEM}.review.json"}
    assert len(frozen["frozen_files"]) == 3
    assert {item["path"] for item in frozen["frozen_files"]} == expected_paths
    for item in frozen["frozen_files"]:
        assert sha((ROOT / item["path"]).read_bytes()) == item["sha256"], item["path"]
    assert frozen["checklist_file"] == f"checklists/{NOTE_SCOPE_STEM}.json"
    checklist = load_checklist(ROOT / frozen["checklist_file"])
    assert [criterion.id for criterion in checklist.criteria] == ["completion_accuracy", "sequence_order"]
    assert [criterion.weight for criterion in checklist.criteria] == [70, 30]
    for criterion in checklist.criteria:
        assert criterion.kind == "binary" and criterion.na_condition is None
        assert [(level.value, level.fraction) for level in criterion.levels] == [("yes", 1), ("no", 0)]
    cases = load_cases(ROOT / f"evals/{NOTE_SCOPE_STEM}.jsonl")
    review = read(ROOT / f"evals/{NOTE_SCOPE_STEM}.review.json")
    assert review["human_expert_labels"] is False and review["organizer_ground_truth"] is False
    ordered = [f"note-scope-{index}" for index in range(1, 4)]
    assert [case.id for case in cases] == frozen["ordered_case_ids"] == ordered
    assert len(frozen["cases"]) == len(review["cases"]) == 3
    assert [item["case_id"] for item in frozen["cases"]] == ordered
    assert [item["case_id"] for item in review["cases"]] == ordered
    truths = [("supported", "contradicted"), ("contradicted", "contradicted"), ("supported", "supported")]
    assert [(note["original_note_truth"], note["backup_truth"]) for note in review["cases"]] == truths
    verified = []
    for index, (case, pin, note) in enumerate(zip(cases, frozen["cases"], review["cases"], strict=True)):
        conversation = case.evaluator_input()
        assert case.source == "authored" and case.label_provenance == "ai_authored_provisional"
        assert case.checklist_override == checklist and conversation == case.conversation
        assert sha(canonical(conversation.model_dump())) == pin["canonical_conversation_sha256"]
        assert [expected.criterion_id for expected in case.expectations] == [c.id for c in checklist.criteria]
        assert [(expected.status, expected.answer) for expected in case.expectations] == [
            ("scored", "yes" if index == 2 else "no")] * 2
        assert len(note["semantic_checks"]) == 4
        assert [item["id"] for item in note["semantic_checks"]] == [f"{case.id}-S{n}" for n in range(1, 5)]
        # These empty source fields are explicitly arithmetic-only. They are not
        # passed to source/semantic validation or presented as a model response.
        expected = Evaluation(judgments=[Judgment(
            criterion_id=item.criterion_id, status=item.status, answer=item.answer,
            explanation=item.rationale, evidence=[], counterevidence=[], checked_message_ids=[], uncertainty=None)
            for item in case.expectations], request_coverage=[], scope_notes=[
                "Frozen expected-vector arithmetic only; no model inference or source assessment was produced."])
        score = calculate_score(expected, checklist)
        assert score == pin["expected_arithmetic"]
        assert score["total"] == [0, 0, 100][index]
        assert [item["points"] for item in score["contributions"]] == [[0, 0], [0, 0], [70, 30]][index]
        verified.append({"case_id": case.id, "canonical_conversation_sha256": pin["canonical_conversation_sha256"],
                         "expected_vector": [item.model_dump() for item in case.expectations],
                         "expected_arithmetic": score})
    control = cases[0].conversation.model_dump(exclude={"id"})
    for case in cases[1:]:
        contrast = case.conversation.model_dump(exclude={"id"})
        contrast["messages"][1]["text"] = control["messages"][1]["text"]
        assert contrast == control, "The prospective controls differ only in their initial system history"
    return cases, checklist, {"path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "sha256": sha(path.read_bytes()), "frozen_files": frozen["frozen_files"],
        "canonical_checklist_sha256": sha(canonical(checklist.model_dump())),
        "unchanged_frozen_labels": 6, "unchanged_full_expected_vectors": 3,
        "expected_totals": [0, 0, 100], "cases": verified,
        "limitations": frozen["limitations"]}


def verify_manual_v4_history(checklist, all_cases):
    directory = ROOT / "artifacts/manual-chat-v3"
    protocol_path = directory / "protocol.frozen.json"
    repair_path = directory / "posthoc-repair-C.protocol.json"
    protocol, repair = read(protocol_path), read(repair_path)
    summary = read(directory / "summary.json")
    prior_audit = read(ROOT / "audits/manual-diagnostics-v3-results.json")
    for item in prior_audit["source_receipts"]:
        assert sha((ROOT / item["path"]).read_bytes()) == item["sha256"], item["path"]
    assert sha((ROOT / protocol["expectations_file"]).read_bytes()) == protocol["expectations_sha256"]
    assert sha((directory / "private-manifest.json").read_bytes()) == protocol["private_manifest_sha256"]
    assert sha((ROOT / "artifacts/source-contract-v4/candidate-protocol.json").read_bytes()) == protocol[
        "candidate_protocol_sha256"]
    for name, digest in protocol["preserved_original_freezes"].items():
        assert sha((ROOT / name).read_bytes()) == digest
    for name, digest in protocol["packet_file_hashes"].items():
        assert sha((directory / name).read_bytes()) == digest
    assert repair["base_protocol_sha256"] == sha(protocol_path.read_bytes())
    assert repair["original_first_pass_stays_failed"] is True
    assert sha((directory / "packet-C-posthoc-repair1.txt").read_bytes()) == repair["repair_packet_sha256"]
    manifest = read(directory / "private-manifest.json")
    assert manifest["wire_contract"] == summary["source_contract"] == "span-v4"
    assert summary["semantic_audit"] == "coverage-v4"
    assert summary["initial_responses"] == 3 and summary["initial_strict_valid"] == 2
    assert summary["initial_strict_rejected"] == 1 and summary["old_failed_results_promoted"] is False
    packets = {item["packet"].removesuffix(".txt").removeprefix("packet-"): item for item in manifest["packets"]}
    initial = {row["packet"]: row for row in summary["rows"]}
    assert set(packets) == set(initial) == {"C", "D", "E"}
    expected_status = {("initial", "C"): "failed", ("initial", "D"): "passed",
                       ("initial", "E"): "passed", ("posthoc_repair", "C"): "passed"}
    receipts, seen, original_c = [], set(), None
    for path in sorted((directory / "results").glob("*/receipt.json")):
        receipt = read(path)
        packet = receipt["packet"]
        posthoc = "repair_protocol_sha256" in receipt
        phase = "posthoc_repair" if posthoc else "initial"
        key = (phase, packet)
        assert key in expected_status and key not in seen
        seen.add(key)
        assert receipt["validation"]["structural_validation"] == expected_status[key]
        assert receipt["api_calls"] == receipt["incremental_api_cost_usd"] == 0
        raw_path = path.parent / receipt.get("local_copy", "original-response.json")
        raw = raw_path.read_bytes()
        digest = receipt["response_sha256"] if posthoc else receipt["raw_response_sha256"]
        assert sha(raw) == digest
        assert digest == (summary["posthoc_repair"]["raw_sha256"] if posthoc else initial[packet]["raw_sha256"])
        if posthoc:
            assert sha(path.read_bytes()) == summary["posthoc_repair"]["receipt_sha256"]
            assert receipt["repair_protocol_sha256"] == sha(repair_path.read_bytes())
            assert receipt["original_first_response_stays_failed"] is True
            assert receipt["original_first_response_sha256"] == repair["original_response_sha256"]
            assert receipt["judgment_vector_unchanged"] is True
        else:
            assert receipt["protocol_sha256"] == sha(protocol_path.read_bytes())
            assert receipt["ledger_unchanged"] == EXPECTED_LEDGER
        conversation = all_cases[packets[packet]["case_id_private_local_mapping"]].evaluator_input()
        assert sha(canonical(conversation.model_dump())) == packets[packet]["canonical_conversation_sha256"]
        wire = json.loads(raw)
        assert wire["contract_version"] == "span-v4" and wire["semantic_audit"]["version"] == "coverage-v4"
        if key == ("initial", "C"):
            original_c = wire["judgments"]
        elif posthoc:
            assert original_c is not None
            assert {cid: (item["status"], item["answer"]) for cid, item in wire["judgments"].items()} == {
                cid: (item["status"], item["answer"]) for cid, item in original_c.items()}
        try:
            result = decode_span_evaluation_v4(raw.decode("utf-8"), conversation, checklist)
            validate_evaluation(result, conversation, checklist, require_audit=True)
        except ValueError as error:
            assert expected_status[key] == "failed", str(error)
            assert str(error) == receipt["validation"]["error"] == initial[packet]["validation_error"]
            status, score = "failed_preserved", None
        else:
            assert expected_status[key] == "passed"
            score = calculate_score(result, checklist)
            assert score == receipt["validation"]["score"]
            assert result.source_citations.additional_checked_message_ids is None
            assert result.source_citations.projection == "derived-groups-v4"
            assert {item.criterion_id: item.checked_message_ids for item in result.judgments} == {
                cid: item["checked_message_ids"] for cid, item in wire["judgments"].items()}
            assert [{"criterion_id": item.criterion_id, "status": item.status, "answer": item.answer}
                    for item in result.judgments] == receipt["validation"]["judgments"]
            status = "accepted_score_unchanged"
        try:
            decode_span_evaluation(raw.decode("utf-8"), conversation, checklist)
        except ValueError as error:
            assert "explicit span-v5" in str(error)
        else:
            raise AssertionError("Current v5 decoding must reject every original v4 manual response")
        receipts.append({"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(path.read_bytes()),
                         "raw_sha256": digest, "packet": packet, "phase": phase,
                         "historical_status": status, "score": score,
                         "semantic_qualification": summary["posthoc_repair"]["semantic_qualification"] if posthoc
                             else initial[packet]["qualification"]})
    assert seen == set(expected_status) and len(receipts) == 4
    assert sum(row["historical_status"] == "accepted_score_unchanged" for row in receipts) == 3
    return receipts, prior_audit["source_receipts"]


def inspect_candidate():
    before = ledger_snapshot()
    assert before == EXPECTED_LEDGER
    engine = source_identities()
    frozen, manifests, vectors, labels = frozen_cases()
    assert labels == 110 and vectors == 12
    organizer, organizer_records = latest_organizer_records()
    checklist = load_checklist(ROOT / "checklists/freedom-reviewed-015.json")
    historical = frozen + [("organizer-latest-mixed", case) for case in organizer.values()]
    assert len(historical) == 79 and GROUNDED_VERSION.startswith("evaluator-v10-")
    protocols = []
    for version, name, schema_key, payload_key in [
        ("span-v3", "artifacts/source-spans-v3/candidate-protocol.json", "candidate_schema_sha256",
         "candidate_payload_sha256"),
        ("span-v4", "artifacts/source-contract-v4/candidate-protocol.json", "schema_sha256", "payload_sha256"),
    ]:
        path = ROOT / name
        rows = read(path)["prepared_cases"]
        old = {row["case_id"]: row for row in rows}
        assert len(rows) == len(old) == 79 and set(old) == {case.id for _, case in historical}
        for _, case in historical:
            conversation = case.evaluator_input()
            schema = schema_for(conversation, checklist, grounded=True, source_contract=True,
                                source_contract_version=version)
            payload = payload_for(conversation, checklist, grounded=True, source_contract=True,
                                  source_contract_version=version)
            assert sha(canonical(schema)) == old[case.id][schema_key], (version, case.id, "schema")
            assert sha(payload.encode()) == old[case.id][payload_key], (version, case.id, "payload")
        protocols.append({"path": name, "sha256": sha(path.read_bytes()), "source_contract": version,
                          "unchanged_schema_and_payload_pairs": 79})
    contrasts, custom_checklist, contrast_manifest = verify_scope_contrasts()
    cases = [(family, case, checklist) for family, case in historical] + [
        (NOTE_SCOPE_STEM, case, custom_checklist) for case in contrasts]
    assert len(cases) == 82
    settings = Settings(api_key="")
    proxy = SimpleNamespace(settings=settings, grounded=True)
    prepared = []
    extra = REPAIR_FEEDBACK_BYTES + len(REPAIR_INSTRUCTIONS.encode()) + 128
    for family, case, selected_checklist in cases:
        conversation = case.evaluator_input()
        request = Evaluator._prepare(proxy, conversation, selected_checklist)
        instructions, payload, schema, cap = request
        assert instructions == GROUNDED_SYSTEM and cap == settings.max_output_tokens == 6000
        assert schema == schema_for(conversation, selected_checklist, grounded=True, source_contract=True)
        assert schema["properties"]["contract_version"]["enum"] == ["span-v5"]
        assert schema["$defs"]["SemanticAudit"]["properties"]["version"]["enum"] == ["coverage-v5"]
        verify_source_view(case, selected_checklist, payload, build_catalog(conversation, selected_checklist))
        bound, reservation = Evaluator._estimate(proxy, request)
        assert bound + extra <= 200_000, case.id
        prepared.append({"case_id": case.id, "family": family, "checklist_id": selected_checklist.id,
            "canonical_checklist_sha256": sha(canonical(selected_checklist.model_dump())),
            "payload_sha256": sha(payload.encode()), "schema_sha256": sha(canonical(schema)),
            "input_with_protected_repair": bound + extra,
            "conservative_first_request_reservation_usd": reservation, **schema_statistics(schema)})
    known = {case.id: case for family, case in frozen if family == "official-facts-acceptance-v1"}
    fresh = {case.id: case for family, case in frozen if family == "fresh-repeat-v1"}
    history = {"organizer_latest_mixed_65": revalidate_records(organizer_records.items(), organizer, checklist)}
    for name, path, inputs in [
        ("known_v6", "artifacts/official-facts-live-v1/benchmark.json", known),
        ("known_v7", "artifacts/evidence-contract-live-v2/benchmark.json", known),
        ("fresh_base", "artifacts/fresh-repeat-live-v1/benchmark.json", fresh),
        ("fresh_unsent_continuation", "artifacts/fresh-repeat-live-v1/continuation.json", fresh),
    ]:
        history[name] = revalidate_records(((row["case_id"], row["record"]) for row in read(ROOT / path)["rows"]),
                                           inputs, checklist)
    assert sum(row.get("completed", 0) for row in history.values()) == 97
    all_cases = {case.id: case for _, case in historical}
    manual_v3 = verify_manual_history(checklist, all_cases)
    manual_v4, preserved_v4 = verify_manual_v4_history(checklist, all_cases)
    preserved = verify_preserved_receipts()
    assert source_identities() == engine and ledger_snapshot() == before
    return {"kind": "offline_source_contract_v5_candidate_not_api_benchmark", "api_calls": 0,
        "incremental_api_cost_usd": 0, "candidate_prompt_version": GROUNDED_VERSION,
        "prompt_sha256": sha(GROUNDED_SYSTEM.encode()), "source_contract": "span-v5", "semantic_audit": "coverage-v5",
        "source_identities": engine, "verification_script_lf_sha256": lf_hash(Path(__file__).resolve()),
        "preserved_original_receipts": preserved, "preserved_manual_v4_materials": preserved_v4,
        "original_frozen_manifests": manifests, "unchanged_frozen_labels": labels,
        "unchanged_full_expected_vectors": vectors, "targeted_scope_contrasts": contrast_manifest,
        "all_79_historical_v3_schemas_and_payloads_unchanged": True,
        "all_79_historical_v4_schemas_and_payloads_unchanged": True,
        "historical_candidate_protocols": protocols, "prepared_request_count": len(prepared), "prepared_cases": prepared,
        "maxima": {field: max(row[field] for row in prepared) for field in ["schema_bytes", "object_properties",
            "enum_values", "string_budget_characters", "container_nesting_depth", "input_with_protected_repair"]},
        "output_token_cap": 6000, "protected_input_cap_bytes": 200_000,
        "api_history": history, "manual_v3_history": manual_v3, "manual_v4_history": manual_v4,
        "accepted_api_historical_scores_unchanged": 97, "ledger_before": before, "ledger_after": ledger_snapshot(),
        "limitations": ["Offline preparation/compatibility does not measure provider acceptance or semantic accuracy.",
            "The three new scope controls are assistant-authored targeted diagnostics, not an untouched holdout.",
            "Expected-vector arithmetic and historical manual validation do not count as new model results.",
            "The initial v4 C failure remains failed; its post hoc repair receives no first-pass credit.",
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
        with path.open("x", encoding="utf-8", newline="\n") as output:
            output.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    if args.check_protocol:
        assert read(ROOT / args.check_protocol) == result, "Candidate changed; preserve old receipt"
    print("Verified 82 current requests, both historical contracts for 79 inputs, 110 original labels/12 vectors,")
    print("six targeted labels/three vectors (0, 0, 100), 97 API scores and six v3/four v4 manual receipts.")
    print(f"Candidate {GROUNDED_VERSION}; $0 API cost; largest protected input "
          f"{result['maxima']['input_with_protected_repair']} bytes.")


if __name__ == "__main__":
    main()
