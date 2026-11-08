"""One no-inference HTTP walkthrough using genuine saved delivery assessments.

All mutations happen in a temporary database. The appeal is explicitly a workflow
demonstration of a disputed rubric interpretation, not a revised benchmark label.
"""

import argparse
import json
import sqlite3
from contextlib import closing
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.storage import digest
from cqa.models import Checklist, Conversation
from cqa.settings import Settings
from cqa.submission import result_for
from scripts.import_saved_assessments import import_report


def run(report_path):
    def no_inference(*args, **kwargs):
        raise AssertionError("This saved-result walkthrough must never instantiate an evaluator")

    def response(client, method, url, *, expected=200, **kwargs):
        result = client.request(method, url, **kwargs)
        if result.status_code != expected:
            raise AssertionError(f"{method} {url}: HTTP {result.status_code}, expected {expected}: {result.text}")
        return result.json()

    with TemporaryDirectory(prefix="cqa-delivery-workflow-") as directory:
        database = Path(directory) / "app.sqlite3"
        ledger = Path(directory) / "usage.sqlite3"
        imported = import_report(report_path, database,
                                 Path(__file__).resolve().parents[1] / "checklists/freedom-reviewed-015.json")
        jobs = {row["case_id"]: row["job_id"] for row in imported["jobs"]}
        settings = Settings(api_key="", ledger_path=ledger, strategy="assessor")
        app = create_app(settings=settings, database_path=database, evaluator_factory=no_inference)
        with TestClient(app) as client:
            before_id, after_id = jobs["delivery-custom-channel"], jobs["delivery-custom-channel-and-time"]
            before = response(client, "GET", f"/api/jobs/{before_id}")
            after = response(client, "GET", f"/api/jobs/{after_id}")
            comparison = response(client, "GET", f"/api/jobs/{after_id}/compare", params={"baseline": before_id})
            assert comparison["same_conversation"] and not comparison["source_changed"]
            assert comparison["checklist_changed"] and comparison["score_delta"] == -100
            assert comparison["criteria"][0]["rule_changed"] and comparison["criteria"][0]["outcome_changed"]

            changed = deepcopy(after["checklist"]["content"])
            changed["criteria"][0]["instruction"] += " A stated time must include its timezone."
            response(client, "POST", "/api/checklists", expected=422, json=changed)
            changed["version"] = "workflow-smoke-3"
            saved = response(client, "POST", "/api/checklists", json=changed)
            assert saved["created"] and saved["content"] == changed
            assert response(client, "GET", f"/api/jobs/{before_id}")["checklist"] == before["checklist"]

            reviewed_id = jobs["delivery-kz-corrected-prerequisite"]
            original = response(client, "GET", f"/api/jobs/{reviewed_id}")
            original_record_hash = digest(original["record"])
            assert original["effective"]["score"]["total"] == 75.63
            criterion = next(j for j in original["effective"]["judgments"] if j["criterion_id"] == "consultation")
            assert criterion["answer"] == "20"
            messages = {m["id"]: m for m in original["conversation"]["content"]["messages"]}
            rationale = ("Temporary workflow demonstration only: the reviewer applies a history-sensitive "
                         "interpretation to the explicitly wrong original key instruction. The later correction "
                         "and verified recovery remain counterevidence. This disputed ordinal was excluded "
                         "before inference; this action does not create a benchmark reference label.")
            appeal = response(client, "POST", f"/api/jobs/{reviewed_id}/appeals", expected=201, json={
                "criterion_id": "consultation", "author": "Workflow demonstration",
                "reason": rationale, "message_ids": ["m4", "m6", "m7"],
                "proposed_status": "scored", "proposed_answer": "0"})
            replacement = deepcopy(criterion)
            replacement.update(answer="0", explanation=rationale,
                evidence=[{"message_id": "m4", "quote": messages["m4"]["text"]}],
                counterevidence=[{"message_id": mid, "quote": messages[mid]["text"]} for mid in ["m6", "m7"]],
                checked_message_ids=list(messages), uncertainty=None)
            resolution_body = {"decision": "accept", "reviewer": "Temporary workflow reviewer",
                "rationale": rationale, "expected_revision": original["review_revision"], "judgment": replacement}
            decision = response(client, "POST", f"/api/appeals/{appeal['id']}/resolve", json=resolution_body)
            assert decision["resolution"]["before"]["answer"] == "20"
            assert decision["resolution"]["after"]["answer"] == "0"
            response(client, "POST", f"/api/appeals/{appeal['id']}/resolve", expected=409, json=resolution_body)
            updated = response(client, "GET", f"/api/jobs/{reviewed_id}")
            assert updated["effective"]["score"]["total"] == 50.63
            assert updated["effective"]["source"] == "human_review"
            assert digest(updated["record"]) == original_record_hash
            exported = response(client, "GET", f"/api/jobs/{reviewed_id}/export")
            assert exported["effective"] == updated["effective"] and exported["appeals"] == updated["appeals"]

            official = []
            for case_id, job_id in jobs.items():
                if case_id.startswith("delivery-custom-"):
                    continue
                detail = response(client, "GET", f"/api/jobs/{job_id}")
                conversation = Conversation.model_validate(detail["conversation"]["content"])
                checklist = Checklist.model_validate(detail["checklist"]["content"])
                row = result_for(conversation, conversation, checklist, detail["record"])
                assert row["status"] == "ok" and len(row["criteria"]) == 8
                official.append(row)
            original_ai_row = next(row for row in official if row["conversation_id"] == original["conversation"]["external_id"])
            assert original_ai_row["score"]["final_score"] == 75.63

        # A fresh application/store instance reopens the saved human decision.
        reopened_app = create_app(settings=settings, database_path=database, evaluator_factory=no_inference)
        with TestClient(reopened_app) as client:
            reopened = response(client, "GET", f"/api/jobs/{reviewed_id}")
            assert reopened["effective"]["score"]["total"] == 50.63
            assert reopened["appeals"][0]["resolution"]["after"]["answer"] == "0"
            assert digest(reopened["record"]) == original_record_hash
        with closing(sqlite3.connect(ledger)) as connection:
            assert connection.execute("SELECT COUNT(*) FROM usage").fetchone()[0] == 0

        return {"status": "passed", "source_report": str(Path(report_path).resolve()),
            "source_report_sha256": imported["report_sha256"], "imported_real_records": imported["imported"],
            "custom_checklist_comparison": {"before": 100, "after": 0, "delta": -100, "same_source": True},
            "new_checklist_saved": saved["content"]["version"], "old_version_mutation_rejected": True,
            "appeal_demo": {"original_ai_score": 75.63, "human_reviewed_score": 50.63,
                "original_ai_record_sha256": original_record_hash, "ai_record_preserved": True,
                "history_exported": True, "stale_resolution_rejected": True, "reopened_successfully": True},
            "official_rows_validated": len(official), "official_row_basis": "original_saved_AI_record",
            "limitation": "Full review export preserves human decisions. The existing official adapter/CLI uses original AI records, not effective human revisions. This check covers six per-record exports, not a fabricated10-record PROD file.",
            "api_calls": 0, "new_ledger_rows": 0, "runtime_database": "temporary and removed"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=Path("artifacts/delivery/focused-02.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(args.report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as output:
            json.dump(result, output, ensure_ascii=False, indent=2)
            output.write("\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
