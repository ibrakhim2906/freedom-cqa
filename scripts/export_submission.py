"""Export actual saved assessments to the organizer's JSON 1.0 format; no API calls."""

import argparse
import json
import os
from pathlib import Path

from backend.importing import parse_import, validate_source_envelope
from cqa.models import Checklist, Conversation
from cqa.rubric import load_checklist
from cqa.settings import ROOT
from cqa.submission import build_submission


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def validate_source_group(content, split):
    """Reject an explicitly failed response or known DEV input labelled PROD."""
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return  # parse_import also supports JSONL; it validates that format below.
    if not isinstance(payload, dict):
        return
    validate_source_envelope(payload)
    envelope = payload.get("data")
    groups = [payload.get("dataset_group_id")]
    if isinstance(envelope, dict):
        groups.append(envelope.get("dataset_group_id"))
    if split == "prod" and any(str(group or "").strip().upper() == "DEV" for group in groups):
        raise ValueError("DEV cannot be exported as PROD; use the actual organizer control dataset")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Original organizer API response")
    parser.add_argument("--report", type=Path, action="append", required=True,
                        help="Benchmark report with frozen .suite.jsonl, or downloaded job export; repeat for disjoint inputs")
    parser.add_argument("--completion-report", type=Path, action="append", default=[],
                        help="Explicitly complete only budget-skipped, never-submitted records in --report")
    parser.add_argument("--reassessment-report", type=Path, action="append", default=[],
                        help="Explicit new-policy assessments of previously unresolved inputs; preserve earlier reports")
    parser.add_argument("--correction-report", type=Path, action="append", default=[],
                        help="Predeclared corrections or unsubmitted completions within the reassessed subset")
    parser.add_argument("--correction-reason", help="Required provenance reason when applying a correction report")
    parser.add_argument("--checklist", type=Path, help="Exact checklist used by benchmark reports")
    parser.add_argument("--team-name", help="Defaults to the repository's saved submission profile")
    parser.add_argument("--split", choices=["dev", "prod"], required=True)
    parser.add_argument("--output", type=Path, help="Defaults to results/<split>/results.json")
    args = parser.parse_args()
    if args.correction_report and not (args.correction_reason or "").strip():
        parser.error("--correction-report requires an explicit --correction-reason")
    source_content = args.source.read_text(encoding="utf-8-sig")
    try:
        validate_source_group(source_content, args.split)
    except ValueError as error:
        parser.error(str(error))
    conversations = [c for c, _ in parse_import(source_content)]
    entries, reassessed_ids = {}, set()
    selected_reports = ([(p, "original") for p in args.report] +
                        [(p, "completion") for p in args.completion_report] +
                        [(p, "reassessment") for p in args.reassessment_report] +
                        [(p, "correction") for p in args.correction_report])
    for path, mode in selected_reports:
        document = read(path)
        if "rows" in document:
            if not args.checklist:
                parser.error("--checklist is required for benchmark reports")
            checklist = load_checklist(args.checklist)
            frozen = {r["id"]: (Conversation.model_validate(r["conversation"]),
                      Checklist.model_validate(r["checklist_override"]) if r.get("checklist_override") else checklist)
                      for line in path.with_suffix(".suite.jsonl").read_text(encoding="utf-8").splitlines()
                      if line.strip() for r in [json.loads(line)]}
            records = [(*frozen[r["case_id"]], r["record"]) for r in document["rows"]]
        else:
            records = [(Conversation.model_validate(document["conversation"]["content"]),
                        Checklist.model_validate(document["checklist"]["content"]), document["record"])]
        for source, checklist, record in records:
            if source.id in entries:
                previous_source, previous_checklist, previous = entries[source.id]
                never_submitted = (previous.get("status") == "skipped_budget" and
                                   not previous.get("attempt_count") and not previous.get("usage") and
                                   not previous.get("attempt_records"))
                same_dialogue = (previous_source.messages == source.messages and
                                 previous_source.channel == source.channel and previous_source.language == source.language)
                was_unresolved = (previous.get("status") == "completed" and
                    any(j.get("status") == "needs_review" for j in
                        (previous.get("evaluation") or {}).get("judgments", [])))
                linked_repair = (str(previous.get("error", "")).startswith("invalid_evaluation_") and
                                 previous.get("response_id") and
                                 record.get("repair_parent_response_id") == previous["response_id"])
                permitted = (mode == "completion" and never_submitted and previous_source == source and
                             previous_checklist == checklist) or (
                             mode == "reassessment" and was_unresolved and same_dialogue) or (
                             mode == "correction" and source.id in reassessed_ids and previous_source == source and
                             previous_checklist == checklist and (never_submitted or linked_repair or
                             (previous.get("assessment") or {}).get("contract_version") == "rubric-assessor-v3"))
                if not permitted:
                    parser.error("Duplicate ID is not an explicitly permitted budget completion or unresolved-policy reassessment")
            elif mode != "original":
                parser.error("Completion/reassessment input must already exist in an original report")
            if record.get("checklist_version", checklist.version) != checklist.version:
                parser.error("Report checklist version does not match --checklist")
            entries[source.id] = source, checklist, record
            if mode == "reassessment":
                reassessed_ids.add(source.id)
    team_name = args.team_name or read(ROOT / "config/submission.json")["team_name"]
    payload = build_submission(conversations, entries, team_name, args.split)
    output = args.output or Path("results") / args.split / "results.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, output)
    print(json.dumps({"output": str(output), "records": len(payload["results"]),
        "ok": sum(r["status"] == "ok" for r in payload["results"]),
        "error": sum(r["status"] == "error" for r in payload["results"]),
        "notice": "Local export only; no Git commit, push or publication performed"}))


if __name__ == "__main__":
    main()
