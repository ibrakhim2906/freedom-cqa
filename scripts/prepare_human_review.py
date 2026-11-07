"""Prepare a private review worksheet without revealing evaluator predictions.

Selection is based on prior AI error review, so this is calibration, not a blind
holdout. No API calls, reference-label changes, or production grading occur here.
"""

import argparse
import hashlib
import json
from pathlib import Path

from cqa.datasets import organizer_cases
from cqa.rubric import load_checklist
from cqa.settings import ROOT

SELECTION = {
    "p1-ru-003": ["consultation"],
    "p1-ru-014": ["needs", "empathy", "management"],
    "p1-kz-008": ["needs", "empathy", "management"],
    "p1-ru-015": ["consultation"],
    "p1-ru-020": ["consultation"],
    "p1-ru-024": ["consultation"],
    "p1-en-006": ["needs"],
    "p1-en-009": ["closing"],
    "p1-kz-013": ["consultation", "serious"],
    "p1-en-013": ["consultation", "empathy"],
    "p4-ru-002": ["identity", "consultation", "closing"],
    "p4-ru-005": ["contact"],
}


def prepare(output: Path):
    output = output.resolve()
    if not output.is_relative_to((ROOT / "artifacts").resolve()):
        raise ValueError("Private source excerpts must stay in ignored artifacts/")
    if output.exists() or output.with_suffix(".json").exists():
        raise ValueError("Review output already exists; preserve previous evidence")
    cases = {c.id: c for c in organizer_cases()}
    checklist = load_checklist()
    criteria = {c.id: c for c in checklist.criteria}
    lines = ["# Human calibration worksheet", "",
        "Private organizer data: do not commit or publish this file.", "",
        "20 judgments across 12 conversations, selected after prior AI error review.",
        "Model predictions and provisional expected labels are omitted. Selection is not blind.",
        "Human review does not create organizer Ground Truth or establish domain expertise.", "",
        "For each item, record status (scored / not_applicable / needs_review), answer,",
        "message IDs and a short rule-based reason. Use only the listed levels; N/A needs",
        "its stated condition. Record ambiguous interpretation separately rather than guessing.",
        "Do not infer audio properties from these transcripts. Audio has not been analyzed.", "",
        "For needs applicability, use the displayed versioned checklist's time anchor.",
        "The original supplied wording did not explicitly settle this scope. Team",
        "decision R002 adopts the first substantive customer request, including the bot phase.", "",
        "Reply format: case ID / criterion / status / answer / message IDs / reason.", ""]
    entries = []
    for cid, targets in SELECTION.items():
        conversation = cases[cid].evaluator_input()
        lines += [f"## {cid}", "", f"Channel: {conversation.channel}; language: {conversation.language}", "",
                  "### Complete source transcript", ""]
        for message in conversation.messages:
            lines += [f"**{message.id} | {message.timestamp} | {message.speaker}**", "", message.text, ""]
        lines += ["### Review items", ""]
        for criterion_id in targets:
            criterion = criteria[criterion_id]
            lines += [f"#### {criterion_id}: {criterion.title}", "", criterion.instruction, ""]
            for level in criterion.levels:
                lines += [f"- {level.value}: {level.description}"]
            if criterion.na_condition:
                lines += ["", f"N/A condition: {criterion.na_condition}"]
            lines += ["", "Decision:", "Evidence IDs:", "Reason / unresolved policy:", ""]
            entries.append({"case_id": cid, "criterion_id": criterion_id, "review_status": "pending",
                            "status": None, "answer": None, "evidence_message_ids": [], "reason": ""})
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    manifest = {"provenance": "Pending human calibration; not organizer Ground Truth",
                "reviewer": None, "reviewer_expertise": None,
                "selection": "Prior AI error review; predictions omitted, not a blind holdout",
                "checklist_id": checklist.id, "checklist_version": checklist.version,
                "worksheet_sha256": hashlib.sha256(output.read_bytes()).hexdigest(), "entries": entries}
    output.with_suffix(".json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(entries)} pending review items across {len(SELECTION)} conversations: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/review/human-calibration-v1.md")
    prepare(parser.parse_args().output)
