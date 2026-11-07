"""Merge deferred-only continuations; never replace an actual attempted result."""

import argparse
import hashlib
import json
from pathlib import Path

from cqa.metrics import summarize
from cqa.settings import ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("segments", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-total-cost-usd", type=float, required=True)
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to((ROOT / "artifacts").resolve()):
        raise ValueError("Merged results must stay in ignored artifacts/")
    reports = [json.loads(p.read_text(encoding="utf-8")) for p in args.segments]
    initial = reports[0]
    ids = initial["selected_case_ids"]
    selected = {}
    for report in reports:
        for key in ["model", "reasoning_effort", "max_output_tokens", "evaluator_source_sha256"]:
            if report[key] != initial[key]:
                raise ValueError("Incompatible run settings or evaluator source")
        for row in report["rows"]:
            cid = row["case_id"]
            if cid not in ids:
                raise ValueError("Continuation adds a case outside the original selection")
            previous = selected.get(cid)
            if previous and previous["record"]["status"] != "skipped_budget":
                if row["record"]["status"] != "skipped_budget":
                    raise ValueError("Actual attempt repeated: refusing best-result selection")
                continue
            selected[cid] = row
    rows = [selected[cid] for cid in ids]
    summary = summarize(rows)
    if summary["estimated_known_cost_usd"] > args.max_total_cost_usd + 1e-9:
        raise ValueError("Merged known spending exceeds the declared aggregate ceiling")
    result = {**initial, "rows": rows, "summary": summary, "ledger": reports[-1]["ledger"],
        "complete": all(r["record"]["status"] == "completed" for r in rows),
        "aggregate_control_cap_usd": args.max_total_cost_usd,
        "merge_rule": "Replace only unattempted budget skips; actual attempted results are never replaced.",
        "segments": [{"file": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in args.segments]}
    with args.output.open("x", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)
        file.write("\n")
    print(json.dumps({"cases": len(rows), "complete": result["complete"],
                      "cost_usd": summary["estimated_known_cost_usd"], "statuses": summary["statuses"]}))


if __name__ == "__main__":
    main()
