import argparse
import asyncio
import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime

from .datasets import load_cases, load_suite
from .evaluator import Evaluator
from .ledger import BudgetExceeded, Ledger
from .metrics import compare_case, summarize
from .rubric import load_checklist
from .settings import ROOT, Settings


def save_report(path, rows, metadata, ledger):
    payload = {**metadata, "summary": summarize(rows), "ledger": ledger.summary(), "rows": rows}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


async def benchmark(args):
    settings = Settings.load(args.model)
    if args.concurrency is not None:
        settings = replace(settings, concurrency=args.concurrency)
        settings.validate()
    settings.require_key()
    cases = load_cases(ROOT / args.cases_file) if args.cases_file else load_suite(args.suite)
    if args.case:
        cases = [c for c in cases if c.id in args.case]
        if {c.id for c in cases} != set(args.case):
            raise ValueError("Requested case IDs are not all present in this suite")
    if args.limit:
        cases = cases[:args.limit]
    if not cases:
        raise ValueError("Suite selection is empty")
    if not 0 < args.budget_usd <= settings.max_spend:
        raise ValueError("Run budget must be positive and within the local lifetime limit")
    output = (ROOT / args.output).resolve()
    if not output.is_relative_to((ROOT / "artifacts").resolve()):
        raise ValueError("Benchmark output must stay in Git-ignored artifacts/")
    if output.exists():
        raise ValueError("Output already exists; use a new filename to preserve previous evidence")
    output.parent.mkdir(parents=True, exist_ok=True)
    checklist = load_checklist(args.checklist)
    ledger = Ledger(settings.ledger_path, settings.max_spend)
    before = ledger.committed()
    ceiling = min(settings.max_spend, before + args.budget_usd)
    strategy = getattr(args, "strategy", "direct")
    evaluator = Evaluator(settings, ledger, ceiling, strategy=strategy)
    metadata = {"started_at": datetime.now(UTC).isoformat(),
                "suite": "case-file" if args.cases_file else args.suite,
                "model": settings.model, "reasoning_effort": settings.effort, "strategy": strategy,
                "max_output_tokens": settings.max_output_tokens, "concurrency": settings.concurrency,
                "timeout_seconds": settings.timeout,
                "run_budget_usd": args.budget_usd, "lifetime_committed_before_usd": before,
                "suite_sha256": hashlib.sha256("\n".join(c.model_dump_json() for c in cases).encode()).hexdigest(),
                "selected_case_ids": [c.id for c in cases], "complete": False}
    metadata["evaluator_source_sha256"] = hashlib.sha256(b"\n".join(
        path.read_bytes() for path in sorted((ROOT / "cqa").glob("*.py")))).hexdigest()
    # Freeze exactly what was selected BEFORE any model result is seen, outside inference.
    output.with_suffix(".suite.jsonl").write_text("".join(c.model_dump_json() + "\n" for c in cases), encoding="utf-8")
    semaphore = asyncio.Semaphore(settings.concurrency)
    rows = []
    async def run_case(case):
        async with semaphore:
            selected = case.checklist_override or checklist
            try:
                record = await evaluator.evaluate(case.evaluator_input(), selected)
            except BudgetExceeded:
                record = {"status": "skipped_budget", "error": "budget_limit", "evaluation": None, "score": None}
            except Exception as error:  # noqa: BLE001 - preserve failed cases without logging private exception text
                record = {"status": "failed", "error": "runner_" + type(error).__name__,
                          "evaluation": None, "score": None}
            row = {"case_id": case.id, "source": case.source, "family": case.family,
                   "label_provenance": case.label_provenance, "language": case.conversation.language,
                   "channel": case.conversation.channel, "record": record,
                   "comparison": compare_case(case, record, selected)}
            rows.append(row)
            save_report(output, rows, metadata, ledger)
            checks = row["comparison"]["checks"]
            print(json.dumps({"case": case.id, "status": record["status"], "error": record.get("error"),
                              "matched": sum(c["matched"] for c in checks), "checked": len(checks),
                              "total": (record.get("score") or {}).get("total")}), flush=True)
    try:
        await asyncio.gather(*(run_case(case) for case in cases))
    finally:
        await evaluator.close()
    rows.sort(key=lambda r: next(i for i, c in enumerate(cases) if c.id == r["case_id"]))
    metadata["complete"] = len(rows) == len(cases) and all(r["record"]["status"] == "completed" for r in rows)
    report = save_report(output, rows, metadata, ledger)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print("Saved:", output)


def main():
    parser = argparse.ArgumentParser(prog="cqa")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check-config", help="Check configuration without printing the key or calling OpenAI")
    check.add_argument("--model")
    inventory = sub.add_parser("inventory", help="List dataset counts; no API calls")
    inventory.add_argument("--suite", choices=["authored", "organizer", "organizer-sample", "combined"], default="combined")
    run = sub.add_parser("benchmark")
    run.add_argument("--suite", choices=["authored", "organizer", "organizer-sample", "combined"], default="combined")
    run.add_argument("--case", action="append")
    run.add_argument("--cases-file", help="Frozen JSONL diagnostics; expectations stay outside inference")
    run.add_argument("--concurrency", type=int, help="Override local concurrency (1-8) for this run")
    run.add_argument("--limit", type=int)
    run.add_argument("--model")
    run.add_argument("--strategy", choices=["direct", "evidence-first"], default="direct")
    run.add_argument("--checklist")
    run.add_argument("--budget-usd", type=float, default=1.0)
    run.add_argument("--output", default="artifacts/benchmark/baseline-v1.json")
    args = parser.parse_args()
    try:
        if args.command == "check-config":
            settings = Settings.load(args.model)
            settings.require_key()
            print(json.dumps({"api_key_configured": True, "model": settings.model,
                              "lifetime_limit_usd": settings.max_spend, "concurrency": settings.concurrency}))
        elif args.command == "inventory":
            cases = load_suite(args.suite)
            print(json.dumps({"cases": len(cases), "expected_judgments": sum(len(c.expectations) for c in cases),
                              "sources": sorted({c.source for c in cases}),
                              "label_provenance": sorted({c.label_provenance for c in cases})}, indent=2))
        else:
            asyncio.run(benchmark(args))
    except ValueError as error:
        parser.exit(2, str(error) + "\n")


if __name__ == "__main__":
    main()
