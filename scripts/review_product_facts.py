"""Check researched facts and preserve conditional reviews; no model/network path.

This joins manual notes to frozen source/results. It never writes to the app store,
benchmark labels, provider ledger or saved assessments. Its arithmetic is a manual
review hypothesis, not a new evaluation or organizer Ground Truth.
"""

import hashlib
import json
import sqlite3
from urllib.parse import urlparse

from cqa.datasets import load_cases
from cqa.grounding import attach_reference_pack, reference_applicable, reference_rejection_reasons
from cqa.models import Conversation, Evaluation, Judgment, Message, Reference
from cqa.rubric import load_checklist
from cqa.scoring import calculate_score, validate_evaluation
from cqa.settings import ROOT

BASE = ROOT / "artifacts/product-research-v1"
CATALOG = ROOT / "audits/official-product-sources-20261107.json"
REVIEWS = ROOT / "audits/product-fact-reviews-v1.json"
PACK = ROOT / "references/freedom-global-products-20261107.json"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def billing():
    path = ROOT / "data/runtime/usage.sqlite3"
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
        return dict(zip(["rows", "max_id", "settled_sum"], db.execute(
            "SELECT COUNT(*), MAX(id), SUM(cost) FROM usage").fetchone(), strict=True))


def main():
    before = read(BASE / "billing-before.json")
    assert billing() == before, "Ledger changed; do not report this as a zero-spend audit without inspection"
    prior = read(ROOT / "artifacts/facts-audit-v1/inventory-and-audit.json")
    for entry in prior["source_files"]:
        assert digest(ROOT / entry["path"]) == entry["sha256"], f"Preserved input changed: {entry['path']}"
    protocol = read(ROOT / "artifacts/organizer-65-v1/protocol.json")
    assert digest(ROOT / "checklists/freedom-reviewed-015.json") == protocol["checklist_sha256"]

    catalog, reviews, pack = read(CATALOG), read(REVIEWS), read(PACK)
    assert catalog["kind"] == "official_source_catalog_not_score_labels"
    assert reviews["kind"] == "assistant_manual_end_to_end_review_not_ground_truth"
    sources = {s["id"]: s for s in catalog["sources"]}
    assert len(sources) == len(catalog["sources"]) == 18
    known_topics = {f["id"] for f in read(ROOT / "audits/fact-requirements-v1.json")["facts"]}
    snapshots = {digest(p): p.name for p in (BASE / "raw").iterdir() if p.is_file()}
    for source in sources.values():
        assert urlparse(source["url"]).hostname in {"fbroker.kz", "tradernet.global"}
        assert source["effective_date"] is None, "Research did not establish actual effective dates"
        assert set(source["fact_ids"]) <= known_topics
        assert len((source["short_quote"] or "").split()) <= 25
        assert source["snapshot_sha256"] in snapshots, f"Missing exact cached snapshot: {source['id']}"
        assert source["facts"] and source["does_not_establish"] and source["issuer_scope"]
    for topic in catalog["topic_resolutions"]:
        assert topic["fact_id"] in known_topics
        assert set(topic["source_ids"]) <= sources.keys()

    refs = [Reference.model_validate(r) for r in pack["references"]]
    assert len(refs) == len({r.id for r in refs}) == 9
    assert len(pack["manifest"]) == len(refs)
    manifests = {m["id"]: m for m in pack["manifest"]}
    for ref in refs:
        source, manifest = sources[ref.id], manifests[ref.id]
        assert ref.source_url == source["url"] == manifest["source_url"]
        assert ref.scope == pack["scope"] == "freedom-finance-global-platform"
        assert ref.valid_from == ref.valid_until == ref.retrieved_on == "2026-11-07"
        assert "Curated official-source summary:" in ref.text
        assert digest_text(ref.text) == manifest["summary_sha256"]
        assert manifest["source_snapshot_sha256"] == source["snapshot_sha256"]
        assert not any(token in ref.text + ref.provenance for token in ["p1-", "p4-", "expected_score"])

    # Explicitly known current context is a separate fixture, not a rewritten
    # organizer transcript. Missing/wrong context must still reject sources.
    fixture = Conversation(id="offline-reference-context-check", channel="agent chat", language="EN",
                           messages=[Message(id="m1", timestamp="00:00", speaker="client",
                                             text="Which account can hold funds before a purchase?")])
    attached = attach_reference_pack(fixture, PACK, pack["scope"], "2026-11-07")
    assert all(reference_applicable(r, attached) for r in attached.references)
    assert all("missing_scope" in reference_rejection_reasons(r, fixture) for r in refs)
    assert all("missing_occurrence_date" in reference_rejection_reasons(r, fixture) for r in refs)
    wrong = attached.model_copy(update={"knowledge_scope": "another-broker"})
    old = attached.model_copy(update={"occurred_on": "2026-11-03"})
    assert all(not reference_applicable(r, wrong) for r in refs)
    assert all(not reference_applicable(r, old) for r in refs)

    checklist = load_checklist(ROOT / reviews["checklist_file"])
    cases = {c.id: c for c in load_cases(ROOT / reviews["source_transcripts_file"])}
    records = {r["case_id"]: r["record"] for r in read(ROOT / reviews["source_result_file"])["rows"]}
    assert len({r["case_id"] for r in reviews["cases"]}) == len(reviews["cases"]) == 5
    packets = []
    for review in reviews["cases"]:
        case, record = cases[review["case_id"]], records[review["case_id"]]
        original = Evaluation.model_validate(record["evaluation"])
        validate_evaluation(original, case.conversation, checklist)
        assert calculate_score(original, checklist) == record["score"]
        assert case.conversation.occurred_on is None and case.conversation.knowledge_scope is None
        assert not case.conversation.references
        assert set(review["source_ids"]) <= sources.keys()
        mids = {m.id: m for m in case.conversation.messages}
        assert len(review["judgments"]) == len(checklist.criteria) == 8
        indexed = {j["criterion_id"]: j for j in review["judgments"]}
        assert set(indexed) == {c.id for c in checklist.criteria}
        judgments = []
        for criterion in checklist.criteria:
            j = indexed[criterion.id]
            assert set(j["source_message_ids"]) <= mids.keys() and j["source_message_ids"]
            assert j["status"] in {"scored", "not_applicable", "needs_review"}
            if j["status"] == "scored":
                assert j["answer"] in {level.value for level in criterion.levels}
            else:
                assert j["answer"] is None
            if j["status"] == "not_applicable":
                assert criterion.na_condition
            judgments.append(Judgment(criterion_id=criterion.id, status=j["status"], answer=j["answer"],
                                      explanation=j["reason"], evidence=[], counterevidence=[],
                                      checked_message_ids=j["source_message_ids"], uncertainty=None))
        for request in review["requests"]:
            assert request["source_message_ids"]
            assert all(mids[mid].speaker == "client" for mid in request["source_message_ids"])
            assert all(mids[mid].speaker == "operator" for mid in request["operator_answer_ids"])
        for fact in review["fact_checks"]:
            assert all(mids[mid].speaker == "operator" for mid in fact["operator_message_ids"])
        # Arithmetic only. Deliberately not a runtime Evaluation validation:
        # factual applicability is conditional, and old provider claims remain
        # untouched rather than silently promoted to "supported".
        hypothesis = Evaluation(judgments=judgments, request_coverage=[], scope_notes=[
            "Conditional manual-review arithmetic only; not a model output or verified original context."])
        packets.append({"case_id": case.id, "original_conversation": case.conversation.model_dump(),
                        "frozen_evaluation": original.model_dump(), "frozen_score": record["score"],
                        "frozen_result_provenance": {key: record.get(key) for key in [
                            "model", "prompt_version", "checklist_version", "ledger_call_id", "input_fingerprint"]},
                        "manual_review": review, "conditional_manual_arithmetic": calculate_score(hypothesis, checklist)})

    after = billing()
    assert after == before
    out = {"kind": "conditional_manual_review_packet_not_benchmark", "review_context": reviews["review_context"],
           "paid_model_calls": 0, "incremental_api_cost_usd": 0,
           "billing_before": before, "billing_after": after,
           "preserved_previous_source_hashes": prior["source_files"],
           "new_artifact_hashes": [{"path": str(p.relative_to(ROOT)), "sha256": digest(p)}
                                   for p in [CATALOG, REVIEWS, PACK]],
           "source_snapshot_files": {sid: snapshots[s["snapshot_sha256"]] for sid, s in sources.items()},
           "cases": packets}
    path = BASE / "complete-assessment-reviews.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"18 cached official sources; 9 scoped references; {len(packets)} complete eight-criterion reviews")
    for packet in packets:
        score = packet["conditional_manual_arithmetic"]
        print(f"{packet['case_id']}: conditional total={score['total']}; unresolved={score['unresolved_criteria']}")
    print("Original sources/results/checklist unchanged. Ledger unchanged. Incremental API cost: $0.")


def digest_text(value):
    return hashlib.sha256(value.encode()).hexdigest()


if __name__ == "__main__":
    main()
