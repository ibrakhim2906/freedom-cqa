"""Export actual saved assessments to the organizer's JSON 1.0 format; no API calls."""

import argparse
import json
import os
from pathlib import Path

from backend.importing import parse_import
from cqa.models import Checklist, Conversation
from cqa.rubric import load_checklist
from cqa.settings import ROOT
from cqa.submission import build_submission


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Original organizer API response")
    parser.add_argument("--report", type=Path, action="append", required=True,
                        help="Benchmark report with frozen .suite.jsonl, or downloaded job export; repeat for disjoint inputs")
    parser.add_argument("--checklist", type=Path, help="Exact checklist used by benchmark reports")
    parser.add_argument("--team-name", help="Defaults to the repository's saved submission profile")
    parser.add_argument("--split", choices=["dev", "prod"], required=True)
    parser.add_argument("--output", type=Path, help="Defaults to results/<split>/results.json")
    args = parser.parse_args()
    conversations = [c for c, _ in parse_import(args.source.read_text(encoding="utf-8-sig"))]
    entries = {}
    for path in args.report:
        document = read(path)
        if "rows" in document:
            if not args.checklist:
                parser.error("--checklist is required for benchmark reports")
            checklist = load_checklist(args.checklist)
            frozen = {r["id"]: Conversation.model_validate(r["conversation"])
                      for line in path.with_suffix(".suite.jsonl").read_text(encoding="utf-8").splitlines()
                      if line.strip() for r in [json.loads(line)]}
            records = [(frozen[r["case_id"]], checklist, r["record"]) for r in document["rows"]]
        else:
            records = [(Conversation.model_validate(document["conversation"]["content"]),
                        Checklist.model_validate(document["checklist"]["content"]), document["record"])]
        for source, checklist, record in records:
            if source.id in entries:
                parser.error("Duplicate evaluation ID: select disjoint reports, not a favorable repeated result")
            if record.get("checklist_version", checklist.version) != checklist.version:
                parser.error("Report checklist version does not match --checklist")
            entries[source.id] = source, checklist, record
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
