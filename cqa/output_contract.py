"""Provider transport contract; persisted Evaluation records keep their historical shape."""

from copy import deepcopy

from .models import Evaluation


def bind_judgment_audits(schema, checklist):
    """Require every configured judgment, with an audit on every lower scoring answer.

    This is structural enforcement, not a locally generated justification. The model
    still writes each audit and the original semantic/source validators still run.
    """
    base = schema["$defs"]["Judgment"]
    entries = {}
    for criterion in checklist.criteria:
        branches = []
        maximum = max(level.fraction for level in criterion.levels)
        for level in criterion.levels:
            branch = deepcopy(base)
            fields = branch["properties"]
            fields["criterion_id"] = {"type": "string", "enum": [criterion.id]}
            fields["status"] = {"type": "string", "enum": ["scored"]}
            fields["answer"] = {"type": "string", "enum": [level.value]}
            fields["uncertainty"] = {"type": "null"}
            if criterion.kind != "flag" and level.fraction < maximum:
                audit = deepcopy(schema["$defs"]["Deduction"])
                audit["properties"]["criterion_id"] = {"type": "string", "enum": [criterion.id]}
                fields["deduction"] = audit
            else:
                fields["deduction"] = {"type": "null"}
            branch["required"] = list(fields)
            branches.append(branch)
        for status in ["needs_review", *(["not_applicable"] if criterion.na_condition else [])]:
            branch = deepcopy(base)
            fields = branch["properties"]
            fields["criterion_id"] = {"type": "string", "enum": [criterion.id]}
            fields["status"] = {"type": "string", "enum": [status]}
            fields["answer"] = {"type": "null"}
            fields["deduction"] = {"type": "null"}
            if status == "needs_review":
                fields["uncertainty"] = {"type": "string"}
            branch["required"] = list(fields)
            branches.append(branch)
        entries[criterion.id] = {"anyOf": branches}
    schema["properties"]["judgments"] = {
        "type": "object", "properties": entries, "required": list(entries), "additionalProperties": False,
    }
    schema["properties"].pop("deductions")
    schema["required"].remove("deductions")
    return schema


def decode_evaluation(text, *, require_claim_dependencies=False, require_semantic_coverage=False):
    import json

    data = json.loads(text)
    if isinstance(data.get("judgments"), dict):
        if "deductions" in data:
            raise ValueError("Inline audit output cannot also contain top-level deductions")
        judgments, deductions = [], []
        for criterion_id, item in data["judgments"].items():
            if item.get("criterion_id") != criterion_id:
                raise ValueError("Judgment key and criterion ID must match")
            # Copy exactly what the model supplied. Never invent missing audits.
            item = dict(item)
            if "deduction" not in item:
                raise ValueError("Every inline judgment requires its deduction field")
            deduction = item.pop("deduction")
            if deduction is not None:
                if deduction.get("criterion_id") != criterion_id:
                    raise ValueError("Inline deduction must belong to its judgment")
                deductions.append(deduction)
            judgments.append(item)
        data["judgments"], data["deductions"] = judgments, deductions
    result = Evaluation.model_validate(data)
    if (require_claim_dependencies or require_semantic_coverage) and any(c.assessment is None for c in result.factual_claims):
        raise ValueError("Current claim contract requires an explicit dependency assessment for every claim")
    if require_semantic_coverage:
        if result.semantic_audit is None or any(r.support is None for r in result.request_coverage):
            raise ValueError("Current semantic contract requires a source ledger and explicit answer support")
        required = {"evidence_kind", "rule_evidence", "observation_scope", "supported_proposition", "verification_scope"}
        if any(not required <= set(c) for c in data.get("factual_claims", [])):
            raise ValueError("Current semantic contract requires explicit evidence classes and observation scope")
    return result
