"""Freeze unresolved DEV sources for explicitly assumed-policy v3 assessment; no inference."""

import argparse
import hashlib
import json
from pathlib import Path

from cqa.datasets import load_cases
from cqa.grounding import evidence_context_for, select_reference_context
from cqa.models import TestCase
from cqa.rubric import load_checklist
from cqa.settings import ROOT

REPORTS = ["dev-01", "dev-calls-completion-01", "dev-call-final-01"]
SCOPE = "freedom-finance-global-platform"
AS_OF = "2026-11-07"
RATIONALE = (
    "The user explicitly authorized the team to choose the policy context and numerically assess "
    "every conversation from available evidence with stated assumptions. For this reassessment, "
    "assume the Freedom Finance Global platform policy snapshot as of 2026-11-07. This is a "
    "conditional assessment choice, not confirmation of the actual broker, conversation date, "
    "historical applicability, or private account state. Preserve uncertainty about facts that "
    "the supplied sources do not establish."
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def object_sha(value):
    return sha(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())


def file_pin(path):
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path.read_bytes())}


def preserve_or_write(path, raw):
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError(f"Refusing to replace a different frozen artifact: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def prepare(output):
    output = output.resolve()
    if not output.is_relative_to((ROOT / "artifacts").resolve()):
        raise ValueError("Private frozen inputs must remain in ignored artifacts/")
    records, cases, origins, source_files = {}, {}, {}, []
    for name in REPORTS:
        report_path = ROOT / "artifacts/delivery" / (name + ".json")
        suite_path = report_path.with_suffix(".suite.jsonl")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        frozen = load_cases(suite_path)
        if sha("\n".join(c.model_dump_json() for c in frozen).encode()) != report["suite_sha256"]:
            raise ValueError(f"Report's frozen suite hash differs: {name}")
        if [c.id for c in frozen] != report["selected_case_ids"]:
            raise ValueError(f"Report's source selection differs: {name}")
        indexed = {c.id: c for c in frozen}
        if len(report["rows"]) != len(indexed) or {r["case_id"] for r in report["rows"]} != set(indexed):
            raise ValueError(f"Report needs one saved row for each source: {name}")
        pins = {"report": file_pin(report_path), "suite": file_pin(suite_path)}
        source_files.extend(pins.values())
        for row in report["rows"]:
            cid, record = row["case_id"], row["record"]
            case = indexed[cid]
            if cid in cases:
                prior = records[cid]
                if cases[cid] != case or prior.get("status") != "skipped_budget" or any(
                    prior.get(key) for key in ("attempt_count", "usage", "attempt_records")
                ):
                    raise ValueError(f"Continuation would change an evaluated source or record: {cid}")
            elif name != REPORTS[0]:
                raise ValueError(f"Continuation introduces a foreign source: {cid}")
            records[cid], cases[cid] = record, case
            origins[cid] = pins
    if len(cases) != 65 or any(r.get("status") != "completed" for r in records.values()):
        raise ValueError("Expected 65 completed original DEV records after budget continuations")

    pack_path = ROOT / "references/freedom-global-products-20261107.json"
    checklist_path = ROOT / "checklists/freedom-reviewed-016.json"
    checklist = load_checklist(checklist_path)
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    if len(pack["references"]) != 9 or checklist.version != "1-reviewed-016":
        raise ValueError("Expected the existing nine-reference pack and reviewed016 checklist")
    source_files += [file_pin(pack_path), file_pin(checklist_path)]
    selected, provenance, unchanged_ids = [], [], []
    for cid, case in cases.items():
        record = records[cid]
        review = [j for j in record["evaluation"]["judgments"] if j["status"] == "needs_review"]
        if {j["criterion_id"] for j in review} != set(record["score"]["unresolved_criteria"]):
            raise ValueError(f"Saved unresolved score and judgments disagree: {cid}")
        if not review:
            if record["score"]["total"] is None:
                raise ValueError(f"Original numeric record is missing its total: {cid}")
            unchanged_ids.append(cid)
            continue
        revised = select_reference_context(case.conversation, pack_path, SCOPE,
            mode="snapshot_review", as_of=AS_OF, rationale=RATIONALE)
        before = case.conversation.model_dump()
        after = revised.model_dump()
        changed = sorted(k for k in before if before[k] != after[k])
        if changed != ["reference_context", "references"]:
            raise ValueError(f"Reference selection altered original source fields: {cid}")
        new_case = TestCase.model_validate(case.model_dump() | {
            "conversation": after, "checklist_override": checklist.model_dump()})
        if new_case.evaluator_input() != revised or new_case.expectations != case.expectations:
            raise ValueError("Evaluation input must be the conversation alone; labels remain unchanged metadata")
        context = evidence_context_for(revised)
        if sum(r["usable"] for r in context["references"]) != 9:
            raise ValueError(f"Selected official snapshot does not expose all nine references: {cid}")
        selected.append(new_case)
        provenance.append({
            "case_id": cid, **origins[cid],
            "original_record_sha256": object_sha(record),
            "original_case_sha256": object_sha(case.model_dump()),
            "original_conversation_sha256": object_sha(before),
            "original_messages_sha256": object_sha(before["messages"]),
            "reassessment_conversation_sha256": object_sha(after),
            "reassessment_case_sha256": object_sha(new_case.model_dump()),
            "source_fields_changed": changed,
            "original_occurred_on": before["occurred_on"],
            "original_occurred_on_origin": before["occurred_on_origin"],
            "original_knowledge_scope": before["knowledge_scope"],
            "original_checklist_version": record.get("checklist_version"),
            "original_checklist_hash": record.get("checklist_hash"),
            "prior_unresolved_judgments": [{"criterion_id": j["criterion_id"],
                "explanation": j["explanation"], "uncertainty": j.get("uncertainty")} for j in review],
            "selection_reason": "Previously completed assessment contains needs_review judgments; no numeric grade yet.",
            "assessment_context": context["assessment"],
            "usable_reference_ids": [r["reference_id"] for r in context["references"] if r["usable"]],
        })
    if len(selected) != 22 or len(unchanged_ids) != 43:
        raise ValueError("Expected exactly 22 unresolved inputs and 43 preserved numeric results")
    raw = "".join(c.model_dump_json() + "\n" for c in selected).encode()
    manifest = {
        "version": "delivery-reassessment-v3-input-1", "paid_api_calls": 0,
        "purpose": "Frozen inputs only; no new model results, expected grades, or organizer ground truth.",
        "authorization": RATIONALE,
        "selection": "Original dev-01 plus only never-submitted budget completions, then all needs_review cases.",
        "object_hash_encoding": "SHA256 of UTF-8 JSON, ensure_ascii=False, sort_keys=True, separators=(',', ':').",
        "source_files": source_files,
        "input": {"path": output.relative_to(ROOT).as_posix(), "sha256": sha(raw),
                  "suite_sha256": sha("\n".join(c.model_dump_json() for c in selected).encode())},
        "checklist": {**file_pin(checklist_path), "id": checklist.id, "version": checklist.version,
                      "model_sha256": sha(checklist.model_dump_json().encode()), "embedded_in_each_case": True},
        "labels": "Existing source expectations are preserved as TestCase metadata only. evaluator_input() returns only the conversation; no new expectations are authored.",
        "preserved_original_numeric_case_ids": unchanged_ids,
        "selected_case_ids": [c.id for c in selected], "cases": provenance,
    }
    for pin in source_files:
        if sha((ROOT / pin["path"]).read_bytes()) != pin["sha256"]:
            raise ValueError("A frozen source changed during preparation")
    manifest_path = output.with_suffix(".manifest.json")
    preserve_or_write(output, raw)
    preserve_or_write(manifest_path, (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode())
    return {"input": str(output), "manifest": str(manifest_path), "selected": len(selected),
            "preserved_numeric": len(unchanged_ids), "input_sha256": sha(raw), "paid_api_calls": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "artifacts/delivery/reassessment-v3-input.jsonl")
    args = parser.parse_args()
    print(json.dumps(prepare(args.output), indent=2))


if __name__ == "__main__":
    main()
