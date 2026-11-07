"""Publish aggregate development metrics only; never copy organizer transcripts."""
import argparse
import json

from cqa.metrics import summarize
from cqa.settings import ROOT


def render(reports):
    rows = [row for report in reports for row in report["rows"]]
    ids = [row["case_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Overlapping cases: report baseline and repairs separately instead of choosing best results")
    summary = summarize(rows)
    lines = ["# Initial real OpenAI benchmark", "",
             "These are development diagnostics against AI-authored provisional expectations.",
             "There are no independent human or organizer Ground Truth labels in this benchmark.",
             "Do not interpret agreement as a hackathon score or blind generalization accuracy.", "",
             f"Model(s): {', '.join(sorted({r['model'] for r in reports}))}.",
             f"Selected cases: {summary['case_count']}. Statuses: `{json.dumps(summary['statuses'])}`.",
             f"Estimated known API cost for these reports: ${summary['estimated_known_cost_usd']:.4f}.",
             f"Attempts with unknown usage: {summary['unknown_cost_attempts']}.", "",
             "## Corpus results", "",
             "| Source | Attempted | Completed | Expected judgments | End-to-end agreement | Completed-only agreement |",
             "| --- | ---: | ---: | ---: | ---: | ---: |"]
    percent = lambda value: f"{value:.1%}" if value is not None else "Not labelled"
    for source, group in summary["by_source"].items():
        lines.append(f"| {source} | {group['attempted']} | {group['completed']} | "
                     f"{group['expected_judgments_attempted']} | {percent(group['end_to_end_agreement'])} | "
                     f"{percent(group['completed_only_agreement'])} |")
    lines += ["", "## Declared criterion checks", "",
              "| Source | Criterion | Matched | Checked |", "| --- | --- | ---: | ---: |"]
    for source, group in summary["by_source"].items():
        for criterion, values in group["per_criterion"].items():
            lines.append(f"| {source} | {criterion} | {values['matched']} | {values['checked']} |")
    lines += ["", "## Failures and disagreements", ""]
    failures = 0
    for row in rows:
        record = row["record"]
        if record["status"] != "completed":
            failures += 1
            lines.append(f"- `{row['case_id']}`: `{record['status']}` / `{record.get('error')}`.")
        elif any(not check["matched"] for check in row["comparison"]["checks"]):
            for check in row["comparison"]["checks"]:
                if not check["matched"]:
                    failures += 1
                    lines.append(f"- `{row['case_id']}` / `{check['criterion_id']}`: expected "
                                 f"`{check['expected_status']}:{check['expected_answer']}`, got "
                                 f"`{check['actual_status']}:{check['actual_answer']}`. Needs label/evidence review.")
    if not failures:
        lines.append("No declared-check disagreements or processing failures in these reports.")
    lines += ["", "## Interpretation limits", "",
              "- Many cases have only targeted partial expectations; other judgments are not accuracy-scored.",
              "- Full-reference score-error cases largely share a simple authored scenario family.",
              "- Related translations and mutations are development cases, not independent holdouts.",
              "- Legal values and verbatim citations are validated; semantic entailment needs further review.",
              "- Call audio was not analyzed. All five supplied real calls are Russian.",
              "- Failures remain failures; no offline scores or generic successful results are substituted.",
              "- Raw outputs, rejected responses, frozen suite snapshots, and usage stay in ignored artifacts/.", ""]
    return "\n".join(lines), summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("reports", nargs="+")
    parser.add_argument("--output", default="docs/BASELINE_RESULTS.md")
    args = parser.parse_args()
    reports = [json.loads((ROOT / filename).read_text(encoding="utf-8")) for filename in args.reports]
    text, summary = render(reports)
    target = ROOT / args.output
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("Wrote aggregate report:", target)
