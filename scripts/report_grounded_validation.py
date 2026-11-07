"""Preserve first-pass failures and join only pre-inference quota deferrals."""

import argparse
import hashlib
import json
from pathlib import Path

from cqa.metrics import summarize
from cqa.settings import ROOT


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def unique_rows(rows):
    result = {r["case_id"]: r for r in rows}
    if len(result) != len(rows):
        raise ValueError("Duplicate case results cannot be selected by quality")
    return result


def resume_quota_rows(initial, continuation, reconciled_ids):
    original, resumed = unique_rows(initial), unique_rows(continuation)
    for cid, row in resumed.items():
        if cid not in original:
            raise ValueError("Continuation adds a new case")
        before, after = original[cid]["record"], row["record"]
        deferred = before["status"] == "skipped_budget" and not before.get("attempt_records")
        rejected = (before.get("api_error_code") == "credit_balance_exhausted"
                    and before.get("error") == "api_http_429" and before.get("usage") is None
                    and before.get("ledger_call_id") in reconciled_ids
                    and not before.get("raw_output_text") and not before.get("response_id"))
        if not (deferred or rejected):
            raise ValueError("Cannot replace a semantic judgment or an unknown-cost failure")
        if before.get("request_fingerprint") and before["request_fingerprint"] != after.get("request_fingerprint"):
            raise ValueError("Continuation changed the inference request")
        if row["comparison"] != original[cid]["comparison"] and (
            [(c["criterion_id"], c["expected_status"], c["expected_answer"])
             for c in row["comparison"]["checks"]] !=
            [(c["criterion_id"], c["expected_status"], c["expected_answer"])
             for c in original[cid]["comparison"]["checks"]]
        ):
            raise ValueError("Continuation changed reference labels")
        original[cid] = row
    if any(r["record"]["status"] != "completed" for r in original.values()):
        raise ValueError("Completed resumed comparison still has failures")
    return list(original.values())


def stability(initial, repeated):
    old, new = unique_rows(initial), unique_rows(repeated)
    changes, score_drifts = [], []
    count = 0
    for cid, row in new.items():
        before, after = old[cid]["record"], row["record"]
        if before["status"] != "completed" or after["status"] != "completed":
            raise ValueError("Stability requires completed results")
        if before["request_fingerprint"] != after["request_fingerprint"]:
            raise ValueError("Repeated inference request changed")
        a = {j["criterion_id"]: (j["status"], j["answer"]) for j in before["evaluation"]["judgments"]}
        b = {j["criterion_id"]: (j["status"], j["answer"]) for j in after["evaluation"]["judgments"]}
        if set(a) != set(b):
            raise ValueError("Repeated criterion coverage changed")
        count += len(a)
        changes.extend({"case_id": cid, "criterion_id": c, "before": a[c], "after": b[c]}
                       for c in a if a[c] != b[c])
        if before["score"]["total"] != after["score"]["total"]:
            score_drifts.append({"case_id": cid, "before": before["score"]["total"], "after": after["score"]["total"]})
    return {"paired_cases": len(new), "judgments": count, "unchanged": count - len(changes),
            "observed_stability": (count - len(changes)) / count if count else None,
            "changes": changes, "score_drifts": score_drifts,
            "warning": "One repeat per case; not a distribution-level guarantee."}


def report(directory):
    files = ["baseline.json", "candidate.json", "quota-continuation.json", "overlap-repeat.json",
             "regression.json", "organizer-regression.json"]
    baseline, initial, continuation, repeat, regression, organizer = [read(directory / f) for f in files]
    if not all(r["complete"] for r in [baseline, continuation, repeat, regression, organizer]):
        raise ValueError("Required live checks are incomplete")
    reconciliation = read(directory / "quota-reconciliation.json")
    ids = {e["ledger_call_id"] for e in reconciliation["events"] if e["settled_cost_usd"] == 0}
    resumed_rows = resume_quota_rows(initial["rows"], continuation["rows"], ids)
    # Compare actual frozen case objects, not just their diagnostic IDs.
    frozen = {c["id"]: c for c in [json.loads(line) for line in
              (directory / "candidate.suite.jsonl").read_text(encoding="utf-8").splitlines()]}
    for line in (directory / "quota-continuation.suite.jsonl").read_text(encoding="utf-8").splitlines():
        case = json.loads(line)
        if frozen.get(case["id"]) != case:
            raise ValueError("Continuation changed frozen input or labels")
    repeat_result = stability(initial["rows"], repeat["rows"])
    summary = summarize(resumed_rows)
    checks = [c for r in resumed_rows for c in r["comparison"]["checks"]]
    regression_checks = [c for r in regression["rows"] for c in r["comparison"]["checks"]]
    all_labels_match = all(c["matched"] for c in checks + regression_checks)
    organizer_rows = [{"case_id": r["case_id"], "status": r["record"]["status"],
                       "total": r["record"]["score"]["total"],
                       "unresolved": r["record"]["score"]["unresolved_criteria"],
                       "matched": sum(c["matched"] for c in r["comparison"]["checks"]),
                       "checks": len(r["comparison"]["checks"]),
                       "factual_statuses": [c["status"] for c in r["record"]["evaluation"]["factual_claims"]]}
                      for r in organizer["rows"]]
    costs = {f: r["summary"]["estimated_known_cost_usd"] for f, r in
             zip(files, [baseline, initial, continuation, repeat, regression, organizer], strict=True)}
    smoke_path = directory / "default-smoke.json"
    smoke = read(smoke_path) if smoke_path.exists() else None
    if smoke:
        if not smoke["complete"]:
            raise ValueError("Default-path smoke run is incomplete")
        files.append(smoke_path.name)
        costs[smoke_path.name] = smoke["summary"]["estimated_known_cost_usd"]
    return {"warning": "Provisional reference agreement, not organizer Ground Truth accuracy.",
            "baseline": baseline["summary"], "candidate_first_pass": initial["summary"],
            "candidate_after_quota_continuation": summary, "repeat": repeat_result,
            "regression": regression["summary"], "organizer_original": organizer_rows,
            "default_smoke": smoke["summary"] if smoke else None,
            "behavioral_gate_passed": all_labels_match and not repeat_result["changes"] and
                                     not repeat_result["score_drifts"] and all(
                                         r["matched"] == r["checks"] for r in organizer_rows)
                                     and (smoke is None or all(c["matched"] for r in smoke["rows"]
                                                             for c in r["comparison"]["checks"])),
            "organizer_all_numeric": all(not r["unresolved"] for r in organizer_rows),
            "organizer_reference_warning": "These two cases have zero declared reference labels; report observations, not accuracy.",
            "promotion_basis": "Organizer clarification accepts reasonable uncertainty and does not require invented facts "
                               "or exact numeric matches. Preserve the unverified organizer claim and reduced numeric coverage.",
            "costs_usd": costs, "total_phase_cost_usd": round(sum(costs.values()), 6),
            "new_after_topup_cost_usd": round(sum(costs[f] for f in files[2:]), 6),
            "ledger": smoke["ledger"] if smoke else organizer["ledger"],
            "sources": [{"file": f, "sha256": hashlib.sha256((directory / f).read_bytes()).hexdigest()}
                        for f in files]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=ROOT / "artifacts/benchmark/targeted-v5")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    target = args.output.resolve()
    if not target.is_relative_to((ROOT / "artifacts").resolve()):
        raise ValueError("Report must stay in ignored artifacts/")
    result = report(args.directory)
    with target.open("x", encoding="utf-8") as file:
        file.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in
                      {"baseline", "candidate_first_pass", "candidate_after_quota_continuation", "regression", "sources"}}, indent=2))


if __name__ == "__main__":
    main()
