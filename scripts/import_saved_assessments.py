"""Import a pinned benchmark report into the local UI without inference or ledger writes.

Example: python -m scripts.import_saved_assessments --report artifacts/run.json
         --database data/runtime/app.sqlite3 --checklist checklists/freedom-reviewed-015.json
"""

import argparse
import hashlib
import json
from pathlib import Path

from sqlalchemy import select

from backend.storage import Batch, Job, Store, digest, now
from cqa.datasets import load_cases
from cqa.models import Evaluation
from cqa.rubric import load_checklist
from cqa.scoring import calculate_score, validate_evaluation


def sha(data):
    return hashlib.sha256(data).hexdigest()


def validate_record(record, conversation, checklist):
    """Check the saved result; never repair or substitute its recorded output."""
    if record.get("conversation_id", conversation.id) != conversation.id:
        raise ValueError("Saved record belongs to a different source conversation")
    for key, value in (("checklist_id", checklist.id), ("checklist_version", checklist.version),
                       ("checklist_hash", sha(checklist.model_dump_json().encode()))):
        if record.get(key, value) != value:
            raise ValueError("Saved record does not match the selected checklist: " + key)
    status = record.get("status")
    if status not in {"completed", "failed", "skipped_budget", "cancelled", "interrupted"}:
        raise ValueError("Only finished saved records can be imported; no work will be queued")
    if status != "completed":
        return
    result = Evaluation.model_validate(record.get("evaluation"))
    native = record.get("assessment")
    assessor = (record.get("strategy") in {"assessor", "assessor-reviewed"}
                or str(record.get("claim_contract_version", "")).startswith("rubric-assessor-"))
    if native is not None or assessor:
        from cqa.assessor import validate_native

        if not isinstance(native, dict) or not native.get("contract_version"):
            raise ValueError("Saved assessor result requires its supported native contract")
        validated = validate_native(native, conversation, checklist)
        if native["contract_version"] != validated.native["contract_version"]:
            raise ValueError("Saved assessment envelope disagrees with its validated contract")
        if validated.evaluation != result:
            raise ValueError("Saved evaluation differs from its validated native assessment")
    else:
        validate_evaluation(result, conversation, checklist,
                            require_audit=record.get("audit_contract_enabled", record.get("strategy") == "grounded"))
    computed = calculate_score(result, checklist)
    saved_score = record.get("score")
    if not isinstance(saved_score, dict) or any(
        saved_score.get(key) != computed[key] for key in ("total", "provisional", "flags", "contributions")
    ):
        raise ValueError("Saved score does not match the preserved judgments and checklist")


def import_report(report_path, database_path, checklist_path=None):
    report_path, database_path = Path(report_path).resolve(), Path(database_path).resolve()
    raw = report_path.read_bytes()
    report, report_hash = json.loads(raw.decode("utf-8-sig")), sha(raw)
    suite_path = report_path.with_suffix(".suite.jsonl")
    cases = load_cases(suite_path)
    suite_hash = sha("\n".join(case.model_dump_json() for case in cases).encode())
    if report.get("suite_sha256") != suite_hash:
        raise ValueError("Frozen .suite.jsonl does not match the report's pinned suite hash")
    if report.get("selected_case_ids", [case.id for case in cases]) != [case.id for case in cases]:
        raise ValueError("Frozen suite order/IDs do not match the report selection")
    rows = report.get("rows")
    if not isinstance(rows, list) or not rows or len({row["case_id"] for row in rows}) != len(rows):
        raise ValueError("Report must contain nonempty, unique case rows")
    indexed = {case.id: case for case in cases}
    default_checklist = load_checklist(checklist_path)
    prepared = []
    for row in rows:
        if row["case_id"] not in indexed:
            raise ValueError("Report row is absent from its frozen suite")
        case = indexed[row["case_id"]]
        checklist = case.checklist_override or default_checklist
        record = row["record"]
        validate_record(record, case.conversation, checklist)
        prepared.append((case, checklist, record))

    imported, reused, ids = [], [], []
    store = Store(database_path)
    try:
        # One transaction avoids a partly imported report after any storage conflict.
        with store.session.begin() as session:
            for case, checklist, record in prepared:
                import_key = f"import-{report_hash}-{case.id}"
                request_hash = digest({"report_sha256": report_hash, "suite_sha256": suite_hash,
                                       "case_id": case.id, "checklist": checklist.model_dump()})
                previous = session.scalar(select(Batch).where(Batch.request_id == import_key))
                if previous:
                    if previous.request_hash != request_hash:
                        raise ValueError("This imported report/case already exists with different inputs")
                    jobs = list(session.scalars(select(Job).where(Job.batch_id == previous.id)))
                    if len(jobs) != 1 or jobs[0].record != record:
                        raise ValueError("Existing imported record no longer matches its immutable report")
                    reused.append(jobs[0].id)
                    ids.append({"case_id": case.id, "job_id": jobs[0].id, "status": jobs[0].status})
                    continue
                source_doc, _ = store.document(session, "conversation", case.conversation.model_dump())
                checklist_doc, _ = store.document(session, "checklist", checklist.model_dump())
                batch = Batch(request_id=import_key, request_hash=request_hash, budget=0.0, config={
                    "imported_from_report": str(report_path), "report_sha256": report_hash,
                    "suite_path": str(suite_path), "suite_sha256": suite_hash, "case_id": case.id,
                    "model": record.get("model", report.get("model")),
                    "strategy": record.get("strategy", report.get("strategy")),
                    "original_run_budget_usd": report.get("run_budget_usd"),
                    "original_budget_group": report.get("budget_group"),
                    "original_report_started_at": report.get("started_at"), "imported_at": now(),
                    "notice": "Previously recorded evaluation; imported without a new model call or ledger entry."})
                session.add(batch)
                session.flush()
                job = Job(batch_id=batch.id, conversation_id=source_doc.id, checklist_id=checklist_doc.id,
                          cache_key=import_key, status=record["status"], record=record,
                          started_at=record.get("started_at"), finished_at=record.get("finished_at"))
                session.add(job)
                session.flush()
                imported.append(job.id)
                ids.append({"case_id": case.id, "job_id": job.id, "status": job.status})
    finally:
        store.engine.dispose()
    return {"report": str(report_path), "report_sha256": report_hash, "database": str(database_path),
            "imported": len(imported), "reused": len(reused), "jobs": ids,
            "notice": "Saved records only. No model calls, queue work or usage-ledger changes."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--database", type=Path, default=Path("data/runtime/app.sqlite3"))
    parser.add_argument("--checklist", type=Path,
                        help="Exact checklist used by the report; case-specific saved overrides take precedence")
    args = parser.parse_args()
    print(json.dumps(import_report(args.report, args.database, args.checklist), ensure_ascii=False))


if __name__ == "__main__":
    main()
