"""Compare the same frozen cases without choosing the best result per case.

Prints only aggregate metrics and criterion/answer changes, not private transcripts.
"""

import argparse
import json
from pathlib import Path

from cqa.settings import ROOT


def compare(control, candidate):
    if control["suite_sha256"] != candidate["suite_sha256"]:
        raise ValueError("Comparison requires exactly the same frozen suite")
    old = {r["case_id"]: r for r in control["rows"]}
    new = {r["case_id"]: r for r in candidate["rows"]}
    if len(old) != len(control["rows"]) or len(new) != len(candidate["rows"]) or set(old) != set(new):
        raise ValueError("Comparison requires identical, unique result case IDs")
    changes = []
    for cid, before in old.items():
        after = new[cid]
        a = {j["criterion_id"]: j for j in (before["record"].get("evaluation") or {}).get("judgments", [])}
        b = {j["criterion_id"]: j for j in (after["record"].get("evaluation") or {}).get("judgments", [])}
        for criterion in sorted(set(a) | set(b)):
            previous = {k: a.get(criterion, {}).get(k) for k in ["status", "answer"]}
            current = {k: b.get(criterion, {}).get(k) for k in ["status", "answer"]}
            if previous != current:
                changes.append({"case_id": cid, "criterion_id": criterion,
                                "control": previous, "candidate": current})
    return {"warning": "Targeted development comparison against AI-authored provisional labels, NOT organizer accuracy.",
            "suite_sha256": control["suite_sha256"], "cases": len(old),
            "control": control["summary"], "candidate": candidate["summary"], "judgment_changes": changes}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("control", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / "artifacts").resolve()):
        raise ValueError("Comparison output must stay in ignored artifacts/")
    result = compare(json.loads(args.control.read_text(encoding="utf-8")),
                     json.loads(args.candidate.read_text(encoding="utf-8")))
    with output.open("x", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)
        file.write("\n")
    for side in ["control", "candidate"]:
        summary = result[side]
        print(json.dumps({"side": side, "cost_usd": summary["estimated_known_cost_usd"],
                          "statuses": summary["statuses"], "provisional_agreement": summary["by_source"]}))
    print(json.dumps({"judgment_changes": result["judgment_changes"]}))


if __name__ == "__main__":
    main()
