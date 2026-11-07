"""Build a source-linked offline inventory; never imports or calls a model client.

Inputs are preserved real results and separately authored review observations.
This report is not an answer source, runtime policy bundle, or new benchmark.
"""

import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path

from cqa.datasets import load_cases
from cqa.models import Evaluation
from cqa.rubric import load_checklist
from cqa.scoring import calculate_score, validate_evaluation
from cqa.settings import ROOT

BASE = ROOT / "artifacts/facts-audit-v1"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, content):
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def billing():
    path = ROOT / "data/runtime/usage.sqlite3"
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
        return {"rows": db.execute("SELECT COUNT(*) FROM usage").fetchone()[0],
                "known_cost_usd": db.execute("SELECT SUM(cost) FROM usage").fetchone()[0],
                "max_call_id": db.execute("SELECT MAX(id) FROM usage").fetchone()[0]}


def main():
    before = read(BASE / "billing-before.json")
    assert billing() == before, "Ledger changed since audit began; inspect concurrent activity before reporting zero spending"
    full_path = ROOT / "artifacts/organizer-65-v1/merged.json"
    full = read(full_path)
    original_protocol = read(ROOT / "artifacts/organizer-65-v1/protocol.json")
    assert digest(ROOT / "data/private/dev.json") == original_protocol["original_source_sha256"]
    assert digest(ROOT / "checklists/freedom-reviewed-015.json") == original_protocol["checklist_sha256"]
    source_path = full_path.with_suffix(".suite.jsonl")
    cases = {c.id: c for c in load_cases(source_path)}
    assert len(cases) == 65
    records = {r["case_id"]: r["record"] for r in full["rows"]}
    provenance = {cid: str(full_path.relative_to(ROOT)) for cid in records}
    overrides = {
        "artifacts/claim-dependencies-v1/focused-candidate.json": {"p1-kz-005", "p1-en-014", "p4-ru-003"},
        "artifacts/claim-dependencies-v1/role-constrained.json": {"p1-ru-018"},
    }
    source_files = [full_path, source_path]
    for name, ids in overrides.items():
        path = ROOT / name
        frozen = {c.id: c for c in load_cases(path.with_suffix(".suite.jsonl"))}
        for row in read(path)["rows"]:
            cid = row["case_id"]
            if cid in ids:
                assert frozen[cid] == cases[cid], "Cannot compare altered source/labels as an audit continuation"
                records[cid], provenance[cid] = row["record"], name
        source_files.extend([path, path.with_suffix(".suite.jsonl")])

    chat = read(BASE / "chats-review.json")
    calls = read(BASE / "calls-review.json")
    materials = read(BASE / "materials-review.json")
    assert set(chat["reviewed_case_ids"]) == {cid for cid, c in cases.items() if c.conversation.channel == "agent chat"}
    assert {c["case_id"] for c in calls["cases"]} == {cid for cid, c in cases.items() if c.conversation.channel == "voice call"}
    assert all(c["full_transcript_reviewed"] for c in calls["cases"])
    findings = chat["findings"] + calls["findings"]
    assert len({f["id"] for f in findings}) == len(findings)
    for item in findings:
        case = cases[item["case_id"]]
        assert set(item["source_message_ids"]) <= {m.id for m in case.conversation.messages}
        assert set(item["criterion_ids"]) <= {c.id for c in load_checklist().criteria}
    requirements_path = ROOT / "audits/fact-requirements-v1.json"
    spans_path = ROOT / "audits/organizer-fact-spans-v1.json"
    requirements = read(requirements_path)
    facts = {f["id"]: f for f in requirements["facts"]}
    occurrence_spec = read(spans_path)
    occurrences = occurrence_spec["source_occurrences"]
    call_topics = {
        "support_service_scope": "F18", "personal_manager_eligibility": "F18", "account_access_permissions": "F18",
        "instrument_order_eligibility": "F19", "order_book_jurisdiction_cause": "F19", "otc_fees_internal_only": "F21",
        "superseded_profile_review_schedule": "F06", "private_order_status": "F07", "conditional_investigation_callback": "F24",
        "instrument_trader_assisted_order": "F19", "market_session": "F20", "trader_contact": "F20",
        "demo_registration_reset": "F22", "support_opening_hours": "F20", "registration_document_country": "F23",
    }
    for case in calls["cases"]:
        messages = {m.id: m for m in cases[case["case_id"]].conversation.messages}
        for item in case["facts_required"]:
            ids = item["source_message_ids"]
            occurrences.append({"case_id": case["case_id"], "fact_id": call_topics[item["topic"]],
                                "operator_message_ids": [mid for mid in ids if messages[mid].speaker == "operator"],
                                "request_message_ids": [mid for mid in ids if messages[mid].speaker == "client"],
                                "outcome_message_ids": [], "evidence_class": "not_established",
                                "specific_question": item["question"], "required_evidence": item["required_evidence"]})
    for item in occurrences:
        assert item["fact_id"] in facts
        messages = {m.id: m for m in cases[item["case_id"]].conversation.messages}
        for field, allowed in [("operator_message_ids", {"operator"}), ("request_message_ids", {"client"}),
                               ("outcome_message_ids", {"client", "system"})]:
            assert all(mid in messages and messages[mid].speaker in allowed for mid in item[field]), item
    covered = {x["case_id"] for x in occurrences} | set(occurrence_spec["no_material_product_assertion_cases"])
    assert covered == set(cases)

    case_index, outcomes = [], Counter()
    checklist = load_checklist(ROOT / "checklists/freedom-reviewed-015.json")
    for cid, case in cases.items():
        record = records[cid]
        assert record["status"] == "completed"
        evaluation = Evaluation.model_validate(record["evaluation"])
        validate_evaluation(evaluation, case.conversation, checklist, require_audit=True)
        assert calculate_score(evaluation, checklist) == record["score"]
        outcome = "provisional" if record["score"]["provisional"] else "numeric"
        outcomes[outcome] += 1
        messages = {m.id: m for m in case.conversation.messages}
        model_claim_ids = {e.message_id for claim in evaluation.factual_claims for e in claim.operator_evidence}
        # Source-message overlap is only a navigation aid, never proof of semantic coverage.
        case_occurrences = []
        for item in [x for x in occurrences if x["case_id"] == cid]:
            case_occurrences.append({**item,
                "operator_span_in_emitted_claim_audit": bool(set(item["operator_message_ids"]) & model_claim_ids)})
        source_dates = sorted({m.timestamp[:10] for m in case.conversation.messages if "T" in m.timestamp})
        case_index.append({"case_id": cid, "language": case.conversation.language, "channel": case.conversation.channel,
                           "record_source": provenance[cid], "workflow_version": record["workflow_version"],
                           "outcome": outcome, "unresolved_criteria": record["score"]["unresolved_criteria"],
                           "source_date_candidates": source_dates, "occurred_on_in_frozen_input": case.conversation.occurred_on,
                           "knowledge_scope": case.conversation.knowledge_scope,
                           "claims_returned": len(evaluation.factual_claims), "requests_returned": len(evaluation.request_coverage),
                           "fact_occurrences": case_occurrences,
                           "finding_ids": [f["id"] for f in findings if f["case_id"] == cid],
                           "source_message_count": len(messages)})

    topic_index = []
    for fid, fact in facts.items():
        relevant = [x for x in occurrences if x["fact_id"] == fid]
        ids = sorted({x["case_id"] for x in relevant})
        provisional = [cid for cid in ids if records[cid]["score"]["provisional"]]
        topic_index.append({**fact, "case_ids": ids, "case_count": len(ids),
                            "provisional_case_ids": provisional,
                            "source_occurrence_count": len(relevant),
                            "warning": "Association is not causal: topic resolution need not finalize the whole conversation."})

    material_manifest = read(BASE / "materials/manifest.json")
    for entry in material_manifest:
        assert digest(Path(entry["path"])) == entry["sha256"]
    source_files.extend([requirements_path, spans_path, BASE / "chats-review.json", BASE / "calls-review.json",
                         BASE / "materials-review.json", ROOT / "references/fbroker-platform-20261107.json",
                         ROOT / "data/private/dev.json", ROOT / "data/private/common_messages.json"])
    after = billing()
    assert after == before
    report = {"audit_version": "1", "paid_api_calls": 0, "incremental_api_cost_usd": 0,
              "billing_before": before, "billing_after": after,
              "provenance": "Assistant source audit after seeing model outputs; not blind human review or organizer Ground Truth.",
              "scope": "All 65 original source transcripts; four organizer PDFs; organizer clarifications; cached scoped guides; saved prior-project probe.",
              "audio_limit": "Five supplied audio links are registered but recordings were not listened to; no audio-quality finding is certified.",
              "result_selection": "Frozen 65-case baseline plus the four explicitly declared later failure rechecks; mixed workflow versions, not a new benchmark.",
              "reviewed_conversations": len(cases), "reviewed_messages": sum(len(c.conversation.messages) for c in cases.values()),
              "latest_available_mixed_outcomes": dict(outcomes),
              "unresolved_criterion_counts": dict(Counter(cid for r in records.values()
                                                          for cid in r["score"]["unresolved_criteria"])),
              "source_occurrence_count": len(occurrences),
              "finding_dispositions": dict(Counter(f["disposition"] for f in findings)),
              "finding_categories": dict(Counter(f["category"] for f in findings)),
              "materials": material_manifest, "materials_review": materials,
              "facts": topic_index, "cases": case_index, "findings": findings,
              "source_files": [{"path": str(p.relative_to(ROOT)), "sha256": digest(p)} for p in source_files]}
    save(BASE / "inventory-and-audit.json", report)
    save(BASE / "billing-after.json", after)
    print(json.dumps({k: report[k] for k in ["reviewed_conversations", "reviewed_messages", "paid_api_calls",
        "incremental_api_cost_usd", "latest_available_mixed_outcomes", "finding_dispositions"]}))
    print(json.dumps({f["id"]: {"title": f["title"], "cases": f["case_count"], "provisional": len(f["provisional_case_ids"])}
                      for f in topic_index}, indent=2))


if __name__ == "__main__":
    main()
