"""Check saved-result compatibility, new source context and schemas; no inference."""

import hashlib
import json
import sqlite3

import jsonschema

from backend.importing import parse_import
from cqa.datasets import load_cases
from cqa.evaluator import schema_for
from cqa.models import Evaluation
from cqa.prompt import payload_for
from cqa.rubric import load_checklist
from cqa.scoring import calculate_score, validate_evaluation
from cqa.settings import ROOT


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    output = ROOT / "artifacts/evidence-coverage-v1"
    output.mkdir(parents=True, exist_ok=True)
    files = [ROOT / "data/private/dev.json", ROOT / "artifacts/organizer-65-v1/merged.json",
             ROOT / "artifacts/organizer-65-v1/merged.suite.jsonl",
             ROOT / "artifacts/claim-dependencies-v1/focused-candidate.json",
             ROOT / "artifacts/claim-dependencies-v1/role-constrained.json"]
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    billing_path = ROOT / "data/runtime/usage.sqlite3"

    def billing():
        with sqlite3.connect(billing_path.as_uri() + "?mode=ro", uri=True) as db:
            return {"rows": db.execute("SELECT COUNT(*) FROM usage").fetchone()[0],
                    "known_cost": db.execute("SELECT SUM(cost) FROM usage").fetchone()[0],
                    "latest_call": db.execute("SELECT MAX(id) FROM usage").fetchone()[0]}

    before = billing()
    cases = {c.id: c for c in load_cases(files[2])}
    records = {r["case_id"]: r["record"] for r in read(files[1])["rows"]}
    for path, ids in [(files[3], {"p1-kz-005", "p1-en-014", "p4-ru-003"}), (files[4], {"p1-ru-018"})]:
        for row in read(path)["rows"]:
            if row["case_id"] in ids:
                records[row["case_id"]] = row["record"]
    checklist = load_checklist()
    for cid, record in records.items():
        result = Evaluation.model_validate(record["evaluation"])
        assert result.semantic_audit is None, "Saved legacy assessments must not be silently upgraded"
        validate_evaluation(result, cases[cid].conversation, checklist, require_audit=True)
        assert calculate_score(result, checklist) == record["score"]
    imported = parse_import(files[0].read_text(encoding="utf-8"))
    contexts = []
    for conversation, metadata in imported:
        old = cases[conversation.id].conversation
        assert conversation.messages == old.messages
        assert conversation.knowledge_scope == old.knowledge_scope
        schema = schema_for(conversation, checklist, grounded=True)
        jsonschema.Draft202012Validator.check_schema(schema)
        payload = json.loads(payload_for(conversation, checklist, grounded=True))
        temporal = payload["evidence_context"]["temporal"]
        if conversation.channel == "voice call":
            assert conversation.occurred_on == "2026-11-03"
            assert conversation.occurred_on_origin == "source_iso_timestamps"
            assert temporal["origin"] == "iso_timestamp_consensus" and not temporal["has_conflict"]
            assert metadata["temporal_context"]["source_message_ids"]
        else:
            assert conversation.occurred_on is None and conversation.knowledge_scope is None
        contexts.append({"id": conversation.id, "channel": conversation.channel,
                         "occurred_on": conversation.occurred_on, "origin": temporal["origin"],
                         "has_conflict": temporal["has_conflict"]})
    after = billing()
    assert before == after
    assert hashes == {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    report = {"paid_api_calls": 0, "incremental_cost_usd": 0, "billing_before": before, "billing_after": after,
              "historical_assessments_revalidated": len(records), "historical_scores_unchanged": True,
              "fresh_imports": len(imported), "schemas_checked_locally": len(contexts),
              "provider_schema_acceptance_tested": False, "live_model_quality_tested": False,
              "source_hashes_unchanged": hashes, "contexts": contexts,
              "limitation": "Local schema/provenance checks do not establish provider acceptance, entailment or improved live accuracy."}
    path = output / "offline-verification.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in {"contexts", "source_hashes_unchanged"}}, indent=2))


if __name__ == "__main__":
    main()
