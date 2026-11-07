"""Resume a provider-rejected repair or merge this frozen 65-case audit.

This is recovery tooling, not an additional semantic retry policy. All paid
attempts remain in the merged record; completed or exhausted results are locked.
"""

import argparse
import asyncio
import hashlib
import json
from uuid import uuid4

from cqa.datasets import load_cases
from cqa.evaluator import Evaluator, repair_feedback
from cqa.ledger import Ledger
from cqa.metrics import compare_case, summarize
from cqa.rubric import load_checklist
from cqa.settings import ROOT, Settings

BASE = ROOT / "artifacts/organizer-65-v1"
CHECKLIST = ROOT / "checklists/freedom-reviewed-015.json"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_new(path, data):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def source_hash():
    return hashlib.sha256(b"\n".join(
        p.read_bytes() for p in sorted((ROOT / "cqa").glob("*.py")))).hexdigest()


def verify_settings(report, settings):
    assert report["evaluator_source_sha256"] == source_hash(), "Evaluator changed during frozen run"
    assert report["model"] == settings.model
    assert report["reasoning_effort"] == settings.effort
    assert report["max_output_tokens"] == settings.max_output_tokens
    assert report["strategy"] == "grounded"


async def resume():
    output = BASE / "repair-continuation.json"
    assert not output.exists(), "Repair continuation already exists; refusing duplicate call"
    assert not (BASE / "repair-continuation.intent.json").exists(), "Repair intent exists; inspect ledger before recovery"
    first, plan = read(BASE / "first-pass.json"), read(BASE / "continuation-plan.json")
    settings = Settings.load()
    verify_settings(first, settings)
    assert len(plan["pending_repair"]) == 1
    cid = plan["pending_repair"][0]["case_id"]
    row = next(r for r in first["rows"] if r["case_id"] == cid)
    prior = row["record"]["attempt_records"]
    assert len(prior) == 2
    rejected, credit = prior
    assert rejected["error"].startswith("invalid_evaluation_") and rejected.get("usage")
    assert credit["error"] == "api_http_429" and credit["billing_state"] == "provider_rejected"
    assert credit["settled_cost_usd"] == 0 and credit.get("usage") is None
    cases = load_cases(BASE / "first-pass.suite.jsonl")
    case = next(c for c in cases if c.id == cid)
    checklist = load_checklist(CHECKLIST)
    assert rejected["checklist_hash"] == hashlib.sha256(checklist.model_dump_json().encode()).hexdigest()
    ledger = Ledger(settings.ledger_path, settings.max_spend,
                    budget_group="credit-repair-" + str(uuid4()), group_limit=1)
    with ledger.connect() as db:
        settled = db.execute("SELECT cost FROM usage WHERE id=?", (credit["ledger_call_id"],)).fetchone()
    assert settled == (0.0,), "Provider-rejected request must have settled zero cost"
    evaluator = Evaluator(settings, ledger, settings.max_spend, strategy="grounded")
    feedback = repair_feedback(rejected)
    _, reservation = evaluator._estimate(evaluator._prepare(case.conversation, checklist, feedback))
    hold = ledger.hold(settings.model, reservation, settings.max_spend)
    # Persist intent before submission: a crash must never trigger an invisible retry.
    write_new(BASE / "repair-continuation.intent.json", {
        "case_id": cid, "source_hash": source_hash(), "rejected_call": rejected["ledger_call_id"],
        "credit_call": credit["ledger_call_id"], "reservation_usd": reservation})
    try:
        attempt = await evaluator._attempt(case.conversation, checklist, feedback, hold_id=hold)
    finally:
        ledger.release(hold)
        await evaluator.close()
    assert attempt["input_fingerprint"] == rejected["input_fingerprint"]
    combined = evaluator._combine([*prior, attempt])
    combined["continuation_reason"] = "One paid repair after a zero-cost provider rejection; no fresh grading retry"
    merged_row = {**row, "record": combined, "comparison": compare_case(case, combined, checklist)}
    write_new(output, {"row": merged_row, "new_attempt": attempt,
                       "new_cost_usd": (attempt.get("usage") or {}).get("estimated_cost_usd", 0),
                       "evaluator_source_sha256": source_hash(), "ledger": ledger.summary()})
    print(json.dumps({"case": cid, "status": attempt["status"], "error": attempt.get("error"),
                      "new_cost_usd": (attempt.get("usage") or {}).get("estimated_cost_usd")}))


def merge():
    first, second = read(BASE / "first-pass.json"), read(BASE / "continuation.json")
    plan, repair = read(BASE / "continuation-plan.json"), read(BASE / "repair-continuation.json")
    verify_settings(first, Settings.load())
    for key in ["model", "reasoning_effort", "max_output_tokens", "evaluator_source_sha256", "strategy"]:
        assert second[key] == first[key], f"Changed {key}"
    assert repair["evaluator_source_sha256"] == first["evaluator_source_sha256"]
    assert len(second["rows"]) == len(plan["unsubmitted_ids"]) == 17
    assert set(second["selected_case_ids"]) == set(plan["unsubmitted_ids"])
    original_cases = {c.id: c for c in load_cases(BASE / "first-pass.suite.jsonl")}
    for case in load_cases(BASE / "continuation.suite.jsonl"):
        assert case == original_cases[case.id], "Frozen continuation source changed"
    rows = {r["case_id"]: r for r in first["rows"]}
    for row in second["rows"]:
        prior = rows[row["case_id"]]["record"]
        assert prior["error"] == "provider_credit_exhausted_no_request"
        assert prior["attempt_count"] == 0 and prior["billing_state"] == "not_submitted"
        rows[row["case_id"]] = row
    row = repair["row"]
    old_attempts = rows[row["case_id"]]["record"]["attempt_records"]
    assert row["record"]["attempt_records"][:-1] == old_attempts
    assert row["record"]["attempt_records"][-1] == repair["new_attempt"]
    rows[row["case_id"]] = row
    for failure in plan["preserved_validation_failures"]:
        cid = failure["case_id"]
        assert rows[cid] == next(r for r in first["rows"] if r["case_id"] == cid)
    ordered = [rows[cid] for cid in first["selected_case_ids"]]
    assert len(ordered) == 65 and all(r["record"].get("attempt_count", 0) > 0 for r in ordered)
    summary = summarize(ordered)
    expected_cost = (first["summary"]["estimated_known_cost_usd"]
                     + second["summary"]["estimated_known_cost_usd"] + repair["new_cost_usd"])
    assert abs(summary["estimated_known_cost_usd"] - expected_cost) < 0.000002
    files = [BASE / name for name in ["first-pass.json", "continuation.json", "repair-continuation.json"]]
    output = BASE / "merged.json"
    write_new(output, {**first, "rows": ordered, "summary": summary,
                       "complete": all(r["record"]["status"] == "completed" for r in ordered),
                       "all_cases_submitted": True,
                       "ledger": Ledger(Settings.load().ledger_path, Settings.load().max_spend).summary(),
                       "merge_rule": plan["merge_rule"],
                       "segments": [{"file": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                                    for p in files]})
    with output.with_suffix(".suite.jsonl").open("xb") as stream:
        stream.write((BASE / "first-pass.suite.jsonl").read_bytes())
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["repair", "merge"])
    args = parser.parse_args()
    if args.action == "repair":
        asyncio.run(resume())
    else:
        merge()
