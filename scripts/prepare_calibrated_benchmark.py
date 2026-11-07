"""Freeze all development inputs, reviewed references and historical comparisons.

No API calls. Original datasets/reports are never modified. Historical results are
selected by declared report order, including failures, never by favorable score.
"""

import hashlib
import json

from cqa.datasets import authored_cases, load_cases, organizer_cases
from cqa.metrics import compare_case, summarize
from cqa.models import Expectation
from cqa.rubric import load_checklist
from cqa.settings import ROOT

REPORT_ORDER = ["baseline-v1", "reference-validation-v2", "organizer-remaining-v2",
                "organizer-tail-v2", "semantic-review-control-v1"]
DESTINATION = ROOT / "artifacts/benchmark/calibrated-v3"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare():
    if DESTINATION.exists():
        raise ValueError("Frozen benchmark directory already exists; preserve it")
    cases = authored_cases() + load_cases(ROOT / "evals/review-v2.jsonl") + organizer_cases()
    assert len(cases) == 117 and len({c.id for c in cases}) == 117
    checklist = load_checklist()
    decisions_path = ROOT / "evals/review-decisions-v1.json"
    decisions = json.loads(decisions_path.read_text(encoding="utf-8"))["decisions"]
    reviewed = {(r["case_id"], r["criterion_id"]): r for r in decisions}
    label_metadata = []
    for case in cases:
        expected = {e.criterion_id: e for e in case.expectations}
        for (cid, criterion), decision in reviewed.items():
            if cid == case.id:
                expected[criterion] = Expectation(criterion_id=criterion, status=decision["status"],
                    answer=decision["answer"], rationale=decision["reason"])
        case.expectations = list(expected.values())
        # Every reference remains model-authored or assisted; none is expert/organizer GT.
        case.label_provenance = "ai_authored_provisional" if expected else "unlabelled"
        for expectation in case.expectations:
            decision = reviewed.get((case.id, expectation.criterion_id))
            label_metadata.append({"case_id": case.id, "criterion_id": expectation.criterion_id,
                "expected_status": expectation.status, "expected_answer": expectation.answer,
                "provenance": decision["review_method"] if decision else "original_ai_authored_provisional",
                "reference_caveat": decision.get("reference_status") if decision else None,
                "source": "review-decisions-v1.json" if decision else
                          "original-authored" if case.source == "authored" else "original-organizer-candidates"})
    first_records, selected_reports = {}, {}
    for name in REPORT_ORDER:
        path = ROOT / f"artifacts/benchmark/{name}.json"
        report = json.loads(path.read_text(encoding="utf-8"))
        for row in report["rows"]:
            if row["record"]["status"] != "skipped_budget" and row["case_id"] not in first_records:
                first_records[row["case_id"]] = row
                selected_reports[row["case_id"]] = {"file": path.name, "sha256": digest(path)}
    assert all(c.id in first_records for c in cases)
    historical_rows = []
    for case in cases:
        old = first_records[case.id]
        historical_rows.append({"case_id": case.id, "source": case.source, "family": case.family,
            "label_provenance": case.label_provenance, "language": case.conversation.language,
            "channel": case.conversation.channel, "record": old["record"],
            "historical_source": selected_reports[case.id],
            "comparison": compare_case(case, old["record"], case.checklist_override or checklist)})
    DESTINATION.mkdir(parents=True)
    (DESTINATION / "checklist.json").write_text(checklist.model_dump_json(indent=2) + "\n", encoding="utf-8")
    suite = DESTINATION / "suite.jsonl"
    suite.write_text("".join(c.model_dump_json() + "\n" for c in cases), encoding="utf-8")
    manifest = {"cases": len(cases), "authored": sum(c.source == "authored" for c in cases),
        "organizer": sum(c.source == "organizer" for c in cases),
        "references": len(label_metadata), "reviewed_references": len(decisions),
        "uncertain_references": sum(e.status == "needs_review" for c in cases for e in c.expectations),
        "custom_checklist_cases": sum(c.checklist_override is not None for c in cases),
        "suite_file_sha256": digest(suite), "review_journal_sha256": digest(decisions_path),
        "checklist": checklist.model_dump(),
        "warning": "Development/calibration data already inspected. AI-authored/assisted references, NOT independent or organizer Ground Truth. Historical comparison changes more than rubric; not a controlled causal A/B.",
        "label_metadata": label_metadata, "historical_report_order": REPORT_ORDER,
        "estimated_new_run_usd": [3.5, 5.0], "proposed_new_run_cap_usd": 5.0}
    (DESTINATION / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                               encoding="utf-8")
    historical = {"selection_rule": "First attempted result in declared report order, retaining failures; never choose best score.",
                  "warning": manifest["warning"], "rows": historical_rows, "summary": summarize(historical_rows)}
    (DESTINATION / "historical-baseline.json").write_text(json.dumps(historical, ensure_ascii=False, indent=2) + "\n",
                                                        encoding="utf-8")
    print(json.dumps({k: v for k, v in manifest.items() if k not in {"checklist", "label_metadata"}}, indent=2))


if __name__ == "__main__":
    prepare()
