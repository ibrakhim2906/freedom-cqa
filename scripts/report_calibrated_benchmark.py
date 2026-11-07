"""Report new real runs versus frozen historical results using identical references.

Uncertain reference dispositions are separate from determinate-label agreement.
Input rows must be unique: never select the best of repeated candidate outputs.
"""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from cqa.settings import ROOT


def decision_statistics(rows, label_metadata):
    provenance = {(r["case_id"], r["criterion_id"]): r for r in label_metadata}
    groups = defaultdict(lambda: {"checked": 0, "matched": 0})
    mismatches, uncertain = [], []
    for row in rows:
        if row["record"]["status"] == "skipped_budget":
            continue
        for check in row["comparison"]["checks"]:
            label = provenance[(row["case_id"], check["criterion_id"])]
            if (label["expected_status"], label["expected_answer"]) != (
                check["expected_status"], check["expected_answer"]
            ):
                raise ValueError("Result references differ from the frozen manifest")
            entry = {"case_id": row["case_id"], **check, "provenance": label["provenance"],
                     "reference_caveat": label["reference_caveat"]}
            if check["expected_status"] == "needs_review":
                uncertain.append(entry)
                continue
            bucket = groups[label["provenance"]]
            bucket["checked"] += 1
            bucket["matched"] += int(check["matched"])
            if not check["matched"]:
                mismatches.append(entry)
    for group in groups.values():
        group["agreement"] = group["matched"] / group["checked"] if group["checked"] else None
    checked = sum(x["checked"] for x in groups.values())
    matched = sum(x["matched"] for x in groups.values())
    high_impact = [c for r in rows if r["record"]["status"] != "skipped_budget"
                   for c in r["comparison"]["checks"] if c["criterion_id"] in {"identity", "serious"}
                   and c["expected_status"] == "scored"]
    errors = [r["comparison"]["total_absolute_error"] for r in rows
              if r["record"]["status"] == "completed" and r["comparison"]["total_absolute_error"] is not None]
    return {"cases": len(rows), "statuses": dict(Counter(r["record"]["status"] for r in rows)),
        "numeric_totals": sum((r["record"].get("score") or {}).get("total") is not None for r in rows),
        "provisional_totals": sum(bool((r["record"].get("score") or {}).get("provisional")) for r in rows),
        "determinate_reference_checks": checked, "matched": matched,
        "provisional_label_agreement": matched / checked if checked else None,
        "by_reference_provenance": dict(groups), "uncertain_reference_dispositions": uncertain,
        "high_impact_reference_checks": len(high_impact),
        "high_impact_matched": sum(c["matched"] for c in high_impact),
        "potential_high_impact_disagreements": [d for d in mismatches
            if d["criterion_id"] in {"identity", "serious"} and d["expected_status"] == "scored"],
        "full_reference_score_cases": len(errors),
        "full_reference_mean_absolute_error": sum(errors) / len(errors) if errors else None,
        "disagreements": mismatches}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("results", type=Path, nargs="+")
    parser.add_argument("--directory", type=Path, default=ROOT / "artifacts/benchmark/calibrated-v3")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / "artifacts").resolve()):
        raise ValueError("Output must remain in ignored artifacts/")
    manifest = json.loads((args.directory / "manifest.json").read_text(encoding="utf-8"))
    history = json.loads((args.directory / "historical-baseline.json").read_text(encoding="utf-8"))
    rows = [r for path in args.results for r in json.loads(path.read_text(encoding="utf-8"))["rows"]]
    ids = {r["case_id"] for r in rows}
    if len(ids) != len(rows):
        raise ValueError("Duplicate candidate results: no best-result selection is allowed")
    historical = [r for r in history["rows"] if r["case_id"] in ids]
    if len(historical) != len(rows):
        raise ValueError("Historical comparison must cover the same selected cases")
    new = decision_statistics(rows, manifest["label_metadata"])
    old = decision_statistics(historical, manifest["label_metadata"])
    valid_old = {r["case_id"] for r in historical if r["record"]["status"] == "completed"}
    valid_new = {r["case_id"] for r in rows if r["record"]["status"] == "completed"}
    common = valid_old & valid_new
    result = {"warning": manifest["warning"], "historical": old, "candidate": new,
        "candidate_by_source": {source: decision_statistics([r for r in rows if r["source"] == source],
                                                           manifest["label_metadata"])
                                for source in sorted({r["source"] for r in rows})},
        "both_versions_completed": {
            "warning": "Secondary semantic comparison excludes structural failures; full end-to-end results above retain them.",
            "historical": decision_statistics([r for r in historical if r["case_id"] in common], manifest["label_metadata"]),
            "candidate": decision_statistics([r for r in rows if r["case_id"] in common], manifest["label_metadata"])},
        "new_run_cost_usd": round(sum(r["record"]["usage"]["estimated_cost_usd"] for r in rows
                                     if r["record"].get("usage")), 6),
        "candidate_reports": [str(p) for p in args.results]}
    with output.open("x", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)
        file.write("\n")
    for name in ["historical", "candidate"]:
        print(json.dumps({"version": name, **{k: v for k, v in result[name].items()
            if k not in {"disagreements", "uncertain_reference_dispositions"}}}))
    print(json.dumps({"new_cost_usd": result["new_run_cost_usd"], "disagreements": new["disagreements"],
                      "uncertain_reference_dispositions": new["uncertain_reference_dispositions"]}))


if __name__ == "__main__":
    main()
