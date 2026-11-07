"""Provider transport contract; persisted Evaluation records keep their historical shape."""

from copy import deepcopy

from pydantic import BaseModel

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


def bind_evidence_contracts(schema, conversation):
    """Type answer/omission and observation topology before provider generation.

    These are generic source-role and field relationships, not scoring rules.
    Runtime validation still verifies quotes, ordering and membership in the
    particular linked answer/withdrawal/range selected by the model.
    """
    definitions = schema["$defs"]
    message_ids = [m.id for m in conversation.messages]
    operator_ids = [m.id for m in conversation.messages if m.speaker == "operator"]
    customer_ids = [m.id for m in conversation.messages if m.speaker == "client"]
    system_ids = [m.id for m in conversation.messages if m.speaker == "system"]
    independent_ids = [m.id for m in conversation.messages if m.speaker in {"client", "system"}]
    role_definitions = {}
    role_values = {}
    new_definitions = set()
    for role in ["client", "operator", "system", "bot"]:
        ids = [m.id for m in conversation.messages if m.speaker == role]
        if ids:
            name = "V2" + role.title() + "MessageID"
            definitions[name] = {"type": "string", "enum": ids}
            role_definitions[role] = name
            role_values[role] = ids
            new_definitions.add(name)
    definitions["V2SourceMessageID"] = {"anyOf": [
        {"$ref": f"#/$defs/{name}"} for name in role_definitions.values()]}
    new_definitions.add("V2SourceMessageID")
    definitions["Evidence"]["properties"]["message_id"] = {"$ref": "#/$defs/V2SourceMessageID"}

    def id_type(ids):
        if not ids or ids == message_ids:
            return {"$ref": "#/$defs/V2SourceMessageID"}
        selected = set(ids)
        roles = [role for role, values in role_values.items() if selected.intersection(values)]
        if {mid for role in roles for mid in role_values[role]} != selected:
            # A genuine subset must stay a subset, not expand to its whole role.
            return {"type": "string", "enum": ids}
        relevant = [role_definitions[role] for role in roles]
        values = [{"$ref": f"#/$defs/{name}"} for name in relevant]
        return values[0] if len(values) == 1 else {"anyOf": values}

    def evidence_array(ids, *, nonempty=False):
        evidence = deepcopy(definitions["Evidence"])
        evidence["properties"]["message_id"] = id_type(ids)
        value = {"type": "array", "items": evidence}
        if nonempty:
            value["minItems"] = 1
        if not ids:
            value["maxItems"] = 0
        return value

    def id_array(ids, *, nonempty=False):
        # Never create an empty enum: an empty-role array is explicitly empty.
        value = {"type": "array", "items": id_type(ids)}
        if nonempty:
            value["minItems"] = 1
        if not ids:
            value["maxItems"] = 0
        return value

    omission = definitions["OmissionSupport"]["properties"]
    omission["start_message_id"] = id_type(customer_ids or message_ids)
    omission["end_message_id"] = {"type": "string", "enum": [message_ids[-1]]}
    omission["context_evidence"] = evidence_array(message_ids)

    if not customer_ids:
        # No request can be linked to an actual customer. The unused definition
        # need not contain impossible nonempty arrays or an empty anyOf.
        schema["properties"]["request_coverage"]["maxItems"] = 0
    else:
        request_base = definitions["RequestCoverage"]
        support_base = definitions["AnswerSupport"]
        branches = []
        kinds = [("unanswered", "none"), ("withdrawn", "withdrawn")]
        if operator_ids:
            kinds = [("answered", "explicit"), ("answered", "implied"),
                     ("partial", "explicit"), ("partial", "implied"),
                     ("next_step", "next_step"), *kinds]
        for status, basis in kinds:
            request = deepcopy(request_base)
            properties = request["properties"]
            properties["status"] = {"type": "string", "enum": [status]}
            properties["request_message_ids"] = id_array(customer_ids, nonempty=True)
            positive = status in {"answered", "partial", "next_step"}
            properties["answer_message_ids"] = id_array(operator_ids if positive else [], nonempty=positive)
            properties["withdrawal_message_ids"] = id_array(customer_ids if status == "withdrawn" else [],
                                                            nonempty=status == "withdrawn")
            support = deepcopy(support_base)
            fields = support["properties"]
            fields["basis"] = {"type": "string", "enum": [basis]}
            evidence_ids = customer_ids if status == "withdrawn" else operator_ids if positive else []
            fields["evidence"] = evidence_array(evidence_ids, nonempty=basis != "none")
            fields["inference"] = {"type": "string", "minLength": 1} if basis == "implied" else {"type": "null"}
            fields["unresolved_aspects"] = {"type": "array", "items": {"type": "string", "minLength": 1}}
            if status in {"partial", "unanswered"}:
                fields["unresolved_aspects"]["minItems"] = 1
                fields["omission"] = {"$ref": "#/$defs/OmissionSupport"}
            else:
                fields["unresolved_aspects"]["maxItems"] = 0
                fields["omission"] = {"type": "null"}
            support["required"] = list(fields)
            properties["support"] = support
            request["required"] = list(properties)
            branches.append(request)
        definitions["RequestCoverage"] = {"anyOf": branches}
        # Every reachable request now carries a typed, inline support branch.
        definitions.pop("AnswerSupport")

    claim_base = definitions["FactualClaim"]
    claim_base["properties"]["context_evidence"] = evidence_array(independent_ids)
    claim_base["properties"]["operator_evidence"] = evidence_array(operator_ids, nonempty=bool(operator_ids))
    if not operator_ids:
        schema["properties"]["factual_claims"]["maxItems"] = 0
    no_observation = deepcopy(claim_base)
    no_observation["properties"]["dialogue_evidence"] = evidence_array([])
    no_observation["properties"]["observation_scope"] = {"type": "string", "enum": ["none"]}
    # supported_proposition also represents a declared workflow commitment when
    # no independent observation exists. Preserve that explicit field contract.
    claim_branches = [no_observation]
    if independent_ids:
        observed = deepcopy(claim_base)
        fields = observed["properties"]
        fields["dialogue_evidence"] = evidence_array(independent_ids, nonempty=True)
        fields["observation_scope"] = {"type": "string", "enum": [
            "reported_state", "control_visible", "action_completed", "task_completed"]}
        fields["supported_proposition"] = {"type": "string", "minLength": 1}
        claim_branches.append(observed)
    if system_ids:
        system_record = deepcopy(claim_base)
        fields = system_record["properties"]
        fields["dialogue_evidence"] = evidence_array(system_ids, nonempty=True)
        fields["observation_scope"] = {"type": "string", "enum": ["system_record"]}
        fields["supported_proposition"] = {"type": "string", "minLength": 1}
        claim_branches.append(system_record)
    definitions["FactualClaim"] = {"anyOf": claim_branches}

    # Judgment/audit branches also copy source-ID enums. Reuse the equivalent
    # role-partitioned IDs so the new typed contract does not multiply enums by
    # branch count on long transcripts. This changes no permitted values.
    id_sets = [(message_ids, id_type(message_ids)),
               (operator_ids, id_type(operator_ids)), (customer_ids, id_type(customer_ids)),
               (independent_ids, id_type(independent_ids))]

    def share_ids(node):
        if isinstance(node, dict):
            if node.get("type") == "string" and set(node) <= {"type", "enum", "title"}:
                for ids, reference in id_sets:
                    if ids and node.get("enum") == ids:
                        node.clear()
                        node.update(deepcopy(reference))
                        return
            for value in node.values():
                share_ids(value)
        elif isinstance(node, list):
            for item in node:
                share_ids(item)

    for name, definition in definitions.items():
        if name not in new_definitions:
            share_ids(definition)
    for definition in schema["properties"].values():
        share_ids(definition)
    return schema


def decode_evaluation(text, *, require_claim_dependencies=False, require_semantic_coverage=False,
                      require_evidence_contract=False):
    import json

    data = json.loads(text)
    if require_evidence_contract:
        if not isinstance(data, dict) or not isinstance(data.get("judgments"), dict):
            raise ValueError("Current evidence contract requires explicitly keyed inline judgments")
        if "factual_claims" not in data:
            raise ValueError("Current evidence contract requires an explicit factual_claims list")
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
    if require_evidence_contract:
        audit = data.get("semantic_audit")
        if not isinstance(audit, dict) or audit.get("version") != "coverage-v2":
            raise ValueError("Current evidence contract requires semantic audit coverage-v2")
        for request in data.get("request_coverage", []):
            support = request.get("support")
            if not isinstance(support, dict) or "omission" not in support:
                raise ValueError("Current evidence contract requires an explicit omission field for every request")
        if any("context_evidence" not in claim for claim in data.get("factual_claims", [])):
            raise ValueError("Current evidence contract requires explicit non-proving context evidence")
    result = Evaluation.model_validate(data)
    if require_evidence_contract:
        _require_explicit_fields(result, historical_extensions=True)
    if (require_claim_dependencies or require_semantic_coverage or require_evidence_contract) and any(
        c.assessment is None for c in result.factual_claims
    ):
        raise ValueError("Current claim contract requires an explicit dependency assessment for every claim")
    if require_semantic_coverage or require_evidence_contract:
        if result.semantic_audit is None or any(r.support is None for r in result.request_coverage):
            raise ValueError("Current semantic contract requires a source ledger and explicit answer support")
        required = {"evidence_kind", "rule_evidence", "observation_scope", "supported_proposition", "verification_scope"}
        if any(not required <= set(c) for c in data.get("factual_claims", [])):
            raise ValueError("Current semantic contract requires explicit evidence classes and observation scope")
    return result


def _require_explicit_fields(value, path="evaluation", *, historical_extensions=False):
    """Reject historical model defaults in current provider outputs, recursively.

    Inline deductions have already been copied from explicitly supplied wire
    fields into the persisted shape. No missing evidence or metadata is created.
    """
    if isinstance(value, BaseModel):
        fields = type(value).model_fields
        extensions = {"Evaluation": {"assertion_groups", "source_citations"},
                      "FactualClaim": {"claim_id", "assertion_group_id", "proof"},
                      "ClaimImpact": {"fixed_claim_ids"}}
        allowed = extensions.get(type(value).__name__, set()) if historical_extensions else set()
        missing = set(fields) - value.model_fields_set - allowed
        if missing:
            raise ValueError("Current evidence contract requires explicit fields at " + path +
                             ": " + ", ".join(sorted(missing)))
        for name in fields:
            _require_explicit_fields(getattr(value, name), path + "." + name,
                                     historical_extensions=historical_extensions)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _require_explicit_fields(item, f"{path}[{index}]", historical_extensions=historical_extensions)
    elif isinstance(value, dict):
        for name, item in value.items():
            _require_explicit_fields(item, path + "." + str(name), historical_extensions=historical_extensions)
