"""Organizer JSON 1.0 adapter. No inference and no substitute judgments."""

import hashlib
from decimal import ROUND_HALF_UP, Decimal

from .grounding import evidence_context_for
from .models import Evaluation
from .rubric import official_checklist
from .scoring import calculate_score, validate_evaluation

IDS = {"contact": "contact", "needs": "discovery", "identity": "identification",
       "consultation": "consultation", "empathy": "empathy", "management": "dialogue",
       "closing": "closure", "serious": "critical"}
WEIGHTS = dict(zip(IDS.values(), [10, 15, 20, 20, 15, 15, 5, 0], strict=True))
NULLABLE = {"discovery", "identification", "consultation", "closure"}


def error_result(cid, reason):
    return {"conversation_id": cid, "status": "error", "criteria": [], "score": None, "error": reason}


def result_for(original, evaluated, checklist, record):
    if original.id != evaluated.id or original.messages != evaluated.messages or (
        original.language, original.channel) != (evaluated.language, evaluated.channel):
        raise ValueError("Evaluation source differs from the original dataset")
    if record.get("conversation_id", original.id) != original.id:
        raise ValueError("Model record belongs to a different conversation")
    if record.get("checklist_hash") and record["checklist_hash"] != hashlib.sha256(
        checklist.model_dump_json().encode()).hexdigest():
        raise ValueError("Model record checklist differs from the supplied snapshot")
    expected = official_checklist()
    if {c.id for c in checklist.criteria} != set(IDS):
        raise ValueError("Submission requires exactly the organizer's eight criteria")
    for c in checklist.criteria:
        official = next(x for x in expected.criteria if x.id == c.id)
        if (c.kind, c.weight, {(l.value, l.fraction) for l in c.levels}) != (
            official.kind, official.weight, {(l.value, l.fraction) for l in official.levels}):
            raise ValueError("Submission checklist weights and allowed levels must match the organizer")
    if record.get("status") != "completed" or not record.get("evaluation"):
        return error_result(original.id, record.get("error") or "No completed model assessment available")
    if evidence_context_for(evaluated)["assessment"]["conditional"] or (
        record.get("assessment_context") or {}).get("conditional"):
        return error_result(original.id,
            "Conditional snapshot review does not establish historical applicability; use the full review export")
    result = Evaluation.model_validate(record["evaluation"])
    validate_evaluation(result, evaluated, checklist, require_audit=True)
    unresolved = [j.criterion_id for j in result.judgments if j.status == "needs_review"]
    if unresolved:
        return error_result(original.id, "Unresolved judgments require review, not N/A: " + ", ".join(unresolved))
    score = calculate_score(result, checklist)
    positions = {m.id: i for i, m in enumerate(original.messages, 1)}
    judgments = {j.criterion_id: j for j in result.judgments}
    criteria = []
    for cid, public_id in IDS.items():
        j = judgments[cid]
        value = (None if j.status == "not_applicable" else int(j.answer)
                 if cid in {"consultation", "management"} else j.answer == "yes")
        # Retain original array positions, including bot/client/system events. A
        # checked omission span is meaningful evidence when no positive quote exists.
        cited = [e.message_id for e in j.evidence + j.counterevidence] or j.checked_message_ids
        criteria.append({"criterion_id": public_id, "value": value, "rationale": j.explanation,
                         "evidence_turns": sorted({positions[mid] for mid in cited})})
    return {"conversation_id": original.id, "status": "ok", "criteria": criteria,
            "score": {"final_score": score["total"], "critical_flag": judgments["serious"].answer == "yes"}}


def build_submission(conversations, entries, team_name, split):
    """entries maps original IDs to (source snapshot, checklist snapshot, actual record)."""
    if split not in {"dev", "prod"} or len(conversations) != (65 if split == "dev" else 10):
        raise ValueError("Expected 65 DEV conversations or 10 PROD conversations")
    if not team_name.strip() or len({c.id for c in conversations}) != len(conversations):
        raise ValueError("Team name and unique original conversation IDs are required")
    if set(entries) - {c.id for c in conversations}:
        raise ValueError("An evaluation ID is absent from the supplied original dataset")
    models, results = set(), []
    for original in conversations:
        if original.id not in entries:
            results.append(error_result(original.id, "No evaluation record supplied"))
            continue
        evaluated, checklist, record = entries[original.id]
        model = record.get("resolved_model") or record.get("model")
        if model:
            models.add(model)
        results.append(result_for(original, evaluated, checklist, record))
    payload = {"schema_version": "1.0", "team_name": team_name.strip(),
               "model": {"mode": "external_api", "name": ", ".join(sorted(models)) or "No model calls recorded"},
               "results": results}
    validate_submission(payload, conversations, split)
    return payload


def validate_submission(payload, conversations, split):
    if set(payload) != {"schema_version", "team_name", "model", "results"} or payload["schema_version"] != "1.0":
        raise ValueError("Invalid submission envelope")
    if not isinstance(payload["team_name"], str) or not payload["team_name"].strip():
        raise ValueError("Submission requires a team name")
    model = payload["model"]
    if set(model) != {"mode", "name"} or model["mode"] not in {"local", "external_api", "hybrid"} or (
        not isinstance(model["name"], str) or not model["name"].strip()):
        raise ValueError("Invalid model provenance")
    rows, originals = payload["results"], {c.id: c for c in conversations}
    if len(rows) != (65 if split == "dev" else 10) or len(originals) != len(rows):
        raise ValueError("Submission count does not match the original dataset")
    ids = [r["conversation_id"] for r in rows]
    if len(set(ids)) != len(ids) or set(ids) != set(originals):
        raise ValueError("Submission has missing, duplicate or foreign conversation IDs")
    for row in rows:
        if row["status"] == "error":
            if set(row) != {"conversation_id", "status", "criteria", "score", "error"} or (
                row["criteria"] != [] or row["score"] is not None or not isinstance(row["error"], str)
                or not row["error"].strip()):
                raise ValueError("Errors must be explicit, with empty criteria and null score")
            continue
        if row["status"] != "ok" or set(row) != {"conversation_id", "status", "criteria", "score"}:
            raise ValueError("Invalid result record")
        items = row["criteria"]
        if not isinstance(items, list) or len(items) != 8 or {x["criterion_id"] for x in items} != set(IDS.values()):
            raise ValueError("An ok record needs each official criterion exactly once")
        earned, applicable = Decimal(0), Decimal(0)
        values = {}
        for item in items:
            if set(item) != {"criterion_id", "value", "rationale", "evidence_turns"} or (
                not isinstance(item["rationale"], str) or not item["rationale"].strip()):
                raise ValueError("Criterion requires a rationale and source turn numbers")
            cid, value = item["criterion_id"], item["value"]
            values[cid] = value
            turns = item["evidence_turns"]
            if not isinstance(turns, list) or not turns or len(turns) != len(set(turns)) or any(type(n) is not int or not
                1 <= n <= len(originals[row["conversation_id"]].messages) for n in turns):
                raise ValueError("Evidence must use original 1-based transcript positions")
            if value is None:
                if cid not in NULLABLE:
                    raise ValueError("N/A is forbidden for this criterion")
                continue
            if cid in {"consultation", "dialogue"}:
                if type(value) is not int or value not in ([0, 5, 10, 15, 20] if cid == "consultation" else [0, 4, 7, 10]):
                    raise ValueError("Scale value must be an allowed raw score")
                fraction = Decimal(value) / (20 if cid == "consultation" else 10)
            else:
                if type(value) is not bool:
                    raise ValueError("Binary values must be booleans")
                fraction = Decimal(int(value))
            applicable += WEIGHTS[cid]
            earned += fraction * WEIGHTS[cid]
        expected = float((100 * earned / applicable).quantize(Decimal(".01"), rounding=ROUND_HALF_UP))
        score = row["score"]
        if set(score) != {"final_score", "critical_flag"} or type(score["critical_flag"]) is not bool or (
            score["critical_flag"] != values["critical"] or type(score["final_score"]) not in {int, float}
            or score["final_score"] != expected):
            raise ValueError("Final score or critical flag disagrees with criterion values")
