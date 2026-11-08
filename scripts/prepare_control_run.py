"""Prepare ten control inputs offline, or explicitly rehearse with DEV; never creates model results."""

import argparse
import hashlib
import json
from pathlib import Path

from backend.importing import parse_import, validate_source_envelope
from cqa.grounding import evidence_context_for, select_reference_context
from cqa.models import TestCase
from cqa.rubric import DEFAULT_CHECKLIST_PATH, load_checklist
from cqa.settings import ROOT

SCOPE = "freedom-finance-global-platform"
AS_OF = "2026-11-07"
RATIONALE = (
    "The user authorized the team to choose the policy context and numerically assess each "
    "conversation from available evidence with stated assumptions. Assume the Freedom Finance "
    "Global platform policy snapshot as of 2026-11-07 for this assessment. This conditional "
    "choice does not establish the actual broker, conversation date, historical applicability, "
    "or private account state. Preserve uncertainty about facts the supplied sources do not establish."
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def object_sha(value):
    return sha(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())


def prepare(source, output, *, split="prod"):
    if split not in {"prod", "rehearsal"}:
        raise ValueError("Preparation split must be prod or rehearsal")
    source, output = source.resolve(), output.resolve()
    if output.suffix != ".jsonl" or not output.is_relative_to((ROOT / "artifacts").resolve()):
        raise ValueError("Output must be a .jsonl file inside this checkout's ignored artifacts/")
    raw_source = source.read_bytes()
    content = raw_source.decode("utf-8-sig")
    payload = json.loads(content)
    envelope = payload.get("data", payload) if isinstance(payload, dict) else {}
    source_group = envelope.get("dataset_group_id") if isinstance(envelope, dict) else None
    validate_source_envelope(payload)
    source_groups = [source_group, payload.get("dataset_group_id") if isinstance(payload, dict) else None]
    if split == "prod" and any(str(group or "").strip().upper() == "DEV" for group in source_groups):
        raise ValueError("DEV cannot be labelled PROD; use --split rehearsal for an offline rehearsal")
    if isinstance(payload, dict) and "data" in payload:
        rows = payload["data"].get("records", []) if isinstance(payload["data"], dict) else []
    elif isinstance(payload, dict) and "records" in payload:
        rows = payload["records"]
    else:
        rows = payload if isinstance(payload, list) else [payload]
    parsed = parse_import(content)  # Also applies with_source_date only when source timestamps establish it.
    if len(parsed) != 10 or len({c.id for c, _ in parsed}) != 10:
        raise ValueError("Control preparation requires exactly ten unique conversation IDs")

    pack_path = ROOT / "references/freedom-global-products-20261107.json"
    checklist_path = ROOT / DEFAULT_CHECKLIST_PATH
    pack_raw, checklist_raw = pack_path.read_bytes(), checklist_path.read_bytes()
    checklist = load_checklist()
    if checklist != load_checklist(checklist_path):
        raise ValueError("Control preparation must use the exact application default checklist snapshot")
    if len(json.loads(pack_raw)["references"]) != 9:
        raise ValueError("Expected the existing nine-reference official snapshot")

    cases, case_manifest = [], []
    for raw_row, (conversation, _) in zip(rows, parsed, strict=True):
        row = raw_row.get("conversation", raw_row)
        turns = row.get("transcript", row.get("messages"))
        expected_id = row.get("conversation_id") if "transcript" in row else row.get("id")
        if expected_id != conversation.id or len(turns) != len(conversation.messages):
            raise ValueError("Import changed an original conversation ID or turn count")
        for index, (turn, message) in enumerate(zip(turns, conversation.messages, strict=True), 1):
            if message.id != turn.get("id", f"m{index}") or any(
                getattr(message, field) != turn[field] for field in ("timestamp", "speaker", "text")
            ):
                raise ValueError("Import changed an original turn ID, timestamp, role, or text")
        revised = select_reference_context(conversation, pack_path, SCOPE,
            mode="snapshot_review", as_of=AS_OF, rationale=RATIONALE)
        before, after = conversation.model_dump(), revised.model_dump()
        changed = sorted(key for key in before if before[key] != after[key])
        if set(changed) - {"references", "reference_context"}:
            raise ValueError("Policy selection cannot rewrite original dialogue, date, or scope")
        context = evidence_context_for(revised)
        cases.append(TestCase(id=conversation.id, family="organizer-" + conversation.id,
            source="organizer", label_provenance="unlabelled", tags=[conversation.channel],
            conversation=revised, expectations=[], checklist_override=checklist))
        case_manifest.append({
            "case_id": conversation.id, "original_row_sha256": object_sha(raw_row),
            "original_messages_sha256": object_sha(before["messages"]),
            "imported_conversation_sha256": object_sha(before),
            "prepared_conversation_sha256": object_sha(after),
            "message_ids": [m.id for m in conversation.messages],
            "generated_message_ids": [m.id for turn, m in zip(turns, conversation.messages, strict=True)
                                      if "id" not in turn],
            "supplied_occurred_on": row.get("occurred_on"),
            "imported_occurred_on": conversation.occurred_on,
            "imported_occurred_on_origin": conversation.occurred_on_origin,
            "original_knowledge_scope": conversation.knowledge_scope,
            "source_fields_changed_by_policy_selection": changed,
            "assessment_context": context["assessment"],
            "usable_reference_ids": [r["reference_id"] for r in context["references"] if r["usable"]],
        })
    raw_input = "".join(c.model_dump_json() + "\n" for c in cases).encode()
    manifest = {
        "version": "control-run-input-1", "split": split, "paid_api_calls": 0,
        "source": {"path": str(source), "sha256": sha(raw_source), "dataset_group_id": source_group},
        "reference_pack": {"path": pack_path.relative_to(ROOT).as_posix(), "sha256": sha(pack_raw)},
        "checklist": {"path": checklist_path.relative_to(ROOT).as_posix(), "sha256": sha(checklist_raw),
                      "id": checklist.id, "version": checklist.version, "embedded_in_each_case": True},
        "input": {"path": output.relative_to(ROOT).as_posix(), "sha256": sha(raw_input),
                  "suite_sha256": sha("\n".join(c.model_dump_json() for c in cases).encode())},
        "object_hash_encoding": "SHA256 of UTF-8 JSON, ensure_ascii=False, sort_keys=True, separators=(',', ':').",
        "policy_assumption": RATIONALE,
        "label_policy": "Unlabelled inputs, empty expectations, no copied DEV judgments or scores; evaluator_input() exposes only the conversation.",
        "date_policy": "Actual timestamps remain exact; a missing conversation date is derived only from unanimous offset-aware ISO source dates.",
        "selected_case_ids": [c.id for c in cases], "cases": case_manifest,
    }
    if (source.read_bytes(), pack_path.read_bytes(), checklist_path.read_bytes()) != (
        raw_source, pack_raw, checklist_raw
    ):
        raise ValueError("Source or policy files changed during preparation")
    manifest_path = output.with_suffix(".manifest.json")
    artifacts = [(output, raw_input), (manifest_path,
        (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode())]
    for path, raw in artifacts:
        if path.exists() and path.read_bytes() != raw:
            raise ValueError(f"Refusing to overwrite a different frozen artifact: {path}")
    output.parent.mkdir(parents=True, exist_ok=True)
    for path, raw in artifacts:
        if not path.exists():
            with path.open("xb") as target:
                target.write(raw)
    return {"input": str(output), "manifest": str(manifest_path), "conversations": len(cases),
            "split": split, "input_sha256": sha(raw_input), "paid_api_calls": 0, "results_created": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Actual ten-case organizer PROD JSON")
    parser.add_argument("--output", type=Path, required=True, help="New ignored artifacts/...jsonl path")
    parser.add_argument("--split", choices=["prod", "rehearsal"], default="prod")
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.source, args.output, split=args.split), indent=2))
    except (ValueError, OSError) as error:
        parser.exit(2, str(error) + "\n")


if __name__ == "__main__":
    main()
