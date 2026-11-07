"""Strict source-selection wire schema; it assigns no truth or grade values."""

import json
from copy import deepcopy

from .models import Evaluation

SPAN_CONTRACT = "span-v3"


def _share_shapes(schema):
    """Reference repeated schema shapes without changing their accepted values."""
    definitions = schema["$defs"]

    def key(node):
        return json.dumps(node, sort_keys=True, separators=(",", ":"))

    def children(node):
        yield from node.get("properties", {}).values()
        yield from node.get("anyOf", [])
        for field in ["items", "additionalProperties"]:
            if isinstance(node.get(field), dict):
                yield node[field]

    counts = {}

    def count(node):
        signature = key(node)
        counts[signature] = counts.get(signature, 0) + 1
        for child in children(node):
            count(child)

    roots = [{k: v for k, v in schema.items() if k != "$defs"}, *definitions.values()]
    for root in roots:
        count(root)
    existing = {key(node): name for name, node in definitions.items()}
    candidates = {signature for signature, n in counts.items() if n > 1 and len(signature) >= 60
                  and (signature in existing or n * (len(signature) - 40) > len(signature) + 24)}
    shared, names = {}, {}

    def copy_children(node):
        result = dict(node)
        if "properties" in node:
            result["properties"] = {name: factor(field) for name, field in node["properties"].items()}
        if "anyOf" in node:
            result["anyOf"] = [factor(option) for option in node["anyOf"]]
        for field in ["items", "additionalProperties"]:
            if isinstance(node.get(field), dict):
                result[field] = factor(node[field])
        return result

    def factor(node):
        signature = key(node)
        if signature not in candidates:
            return copy_children(node)
        if signature in existing:
            return {"$ref": "#/$defs/" + existing[signature]}
        if signature not in names:
            name = f"SpanShared{len(names)}"
            names[signature] = name
            shared[name] = copy_children(node)
        return {"$ref": "#/$defs/" + names[signature]}

    result = copy_children(roots[0])
    result["$defs"] = {name: copy_children(node) for name, node in definitions.items()}
    result["$defs"].update(shared)
    return result


def bind_span_contract(schema, conversation, checklist, catalog):
    """Replace copied quotations with immutable citation IDs in a v2 base schema.

    Historical/persisted records retain their own shapes. Null collections here
    explicitly mean that a branch permits no values; the v3 decoder normalizes
    only after validating this transport shape and resolving selected sources.
    """
    catalog.assert_sources(conversation, checklist)
    wire = deepcopy(schema)
    definitions = wire["$defs"]
    fresh = Evaluation.model_json_schema()["$defs"]
    for name in ["AssertionGroup", "ClaimProof", "ProofPremise"]:
        definitions[name] = deepcopy(fresh[name])
    wire["properties"].pop("source_citations", None)
    wire["properties"]["assertion_groups"] = {"type": "array", "items": {"$ref": "#/$defs/AssertionGroup"}}
    wire["properties"]["contract_version"] = {"type": "string", "enum": [SPAN_CONTRACT]}
    wire["properties"]["catalog_fingerprint"] = {"type": "string", "enum": [catalog.fingerprint]}
    definitions["SemanticAudit"]["properties"]["version"] = {"type": "string", "enum": ["coverage-v3"]}

    roles = {role: [m.id for m in conversation.messages if m.speaker == role]
             for role in ["client", "operator", "system", "bot"]}
    independent = roles["client"] + roles["system"]
    original_evidence = deepcopy(definitions["Evidence"])

    def nonempty_string():
        return {"type": "string", "minLength": 1}

    def source_evidence(ids, *, minimum=0):
        evidence = deepcopy(original_evidence)
        evidence["properties"]["message_id"] = {"type": "string", "enum": ids} if ids else {"type": "string"}
        value = {"type": "array", "items": evidence}
        if minimum:
            value["minItems"] = minimum
        if not ids:
            value["maxItems"] = 0
        return value

    definitions["SemanticExclusion"]["properties"]["evidence"] = source_evidence(
        roles["client"] + roles["operator"])["items"]
    if not roles["client"] + roles["operator"]:
        definitions["SemanticAudit"]["properties"]["exclusions"]["maxItems"] = 0

    # Proof source leaves cannot turn operator assertions into independent truth.
    # The commitment-only variant may cite the actual utterance; runtime additionally
    # checks membership in that claim's operator assertion span.
    premise = deepcopy(definitions["ProofPremise"])
    premise["properties"]["premise_id"] = nonempty_string()

    def source_premise(*, conjunction, commitment=False, private=False):
        result = deepcopy(premise)
        fields = result["properties"]
        fields["proposition"] = nonempty_string() if conjunction else {"type": "null"}
        fields["evidence"] = source_evidence(roles["system"] if private else
                                             independent + (roles["operator"] if commitment else []))
        if not conversation.references:
            fields["reference_evidence"]["maxItems"] = 0
        fields["depends_on_claim_id"] = {"type": "null"}
        fields["required_status"] = {"type": "null"}
        return result

    dependency = deepcopy(premise)
    dependency["properties"]["proposition"] = {"type": "null"}
    dependency["properties"]["depends_on_claim_id"] = nonempty_string()
    dependency["properties"]["required_status"] = {"type": "string", "enum": ["supported", "contradicted"]}
    for field in ["evidence", "reference_evidence", "rule_evidence"]:
        dependency["properties"][field]["maxItems"] = 0
    definitions["SpanDependencyPremise"] = dependency

    for suffix, commitment, private in [("", False, False), ("Commitment", True, False), ("Private", False, True)]:
        direct_name, conjunction_name = "SpanDirectPremise" + suffix, "SpanConjunctPremise" + suffix
        definitions[direct_name] = {"anyOf": [source_premise(conjunction=False, commitment=commitment, private=private),
                                               {"$ref": "#/$defs/SpanDependencyPremise"}]}
        definitions[conjunction_name] = {"anyOf": [source_premise(conjunction=True, commitment=commitment, private=private),
                                                    {"$ref": "#/$defs/SpanDependencyPremise"}]}
        branches = []
        for relation, item_name in [("direct", direct_name), ("all_of", conjunction_name)]:
            proof = deepcopy(definitions["ClaimProof"])
            fields = proof["properties"]
            fields["relation"] = {"type": "string", "enum": [relation]}
            fields["explanation"] = nonempty_string()
            fields["premises"] = {"type": "array", "items": {"$ref": f"#/$defs/{item_name}"},
                                    "minItems": 1 if relation == "direct" else 2}
            fields["required_premise_ids"] = {"type": "array", "items": nonempty_string(),
                                               "minItems": 1 if relation == "direct" else 2}
            if relation == "direct":
                fields["premises"]["maxItems"] = fields["required_premise_ids"]["maxItems"] = 1
            branches.append(proof)
        definitions["SpanClaimProof" + suffix] = {"anyOf": branches}

    group = definitions["AssertionGroup"]
    group["properties"]["group_id"] = nonempty_string()
    group["properties"]["operator_evidence"] = source_evidence(roles["operator"], minimum=1)
    group_branches = []
    for composition in ["atomic", "all_of"]:
        branch = deepcopy(group)
        branch["properties"]["composition"] = {"type": "string", "enum": [composition]}
        branch["properties"]["claim_ids"] = {"type": "array", "items": nonempty_string(),
                                                "minItems": 1 if composition == "atomic" else 2}
        if composition == "atomic":
            branch["properties"]["claim_ids"]["maxItems"] = 1
        group_branches.append(branch)
    definitions["AssertionGroup"] = {"anyOf": group_branches}
    definitions["ClaimImpact"]["properties"]["fixed_claim_ids"] = {"type": "array", "items": nonempty_string()}

    # One claim text is the canonical proposition. Observations explicitly select
    # that proposition instead of generating a second string to compare later.
    observation_branches = []
    for scopes, ids in [(["reported_state", "control_visible", "action_completed", "task_completed"], independent),
                        (["system_record"], roles["system"])]:
        if catalog.ids("dialogue", roles={m.speaker for m in conversation.messages if m.id in ids}):
            observation_branches.append({"type": "object", "properties": {
                "target": {"type": "string", "enum": ["claim"]},
                "scope": {"type": "string", "enum": scopes}}})
    definitions["SpanObservation"] = {"anyOf": observation_branches} if observation_branches else {"type": "null"}
    definitions["SpanSystemObservation"] = next((deepcopy(branch) for branch in observation_branches
        if branch["properties"]["scope"]["enum"] == ["system_record"]), {"type": "null"})
    original_claim = definitions["FactualClaim"]
    while "anyOf" in original_claim:
        original_claim = original_claim["anyOf"][0]
    claim = deepcopy(original_claim)
    fields = claim["properties"]
    for field in ["supported_proposition", "dialogue_evidence", "observation_scope", "reference_evidence", "rule_evidence"]:
        fields.pop(field, None)
    fields["claim_id"] = nonempty_string()
    fields["assertion_group_id"] = nonempty_string()
    fields["observation"] = {"type": "null"}
    claim_branches = []
    for kinds, scopes, commitment, observation in [(["account_state"], ["private_record"], False, "SpanSystemObservation"),
            (["grading_rule"], ["grading_rule"], False, None),
            (["workflow_commitment"], ["commitment"], True, None),
            (["product_fact", "general_fact"], ["policy"], False, None),
            (["product_fact", "general_fact"], ["interaction"], False, "SpanObservation")]:
        for known in [True, False]:
            branch = deepcopy(claim)
            properties = branch["properties"]
            properties["evidence_kind"] = {"type": "string", "enum": kinds}
            properties["verification_scope"] = {"type": "string", "enum": scopes}
            properties["status"] = {"type": "string", "enum": ["supported", "contradicted"] if known else ["unverified"]}
            properties["observation"] = ({"anyOf": [{"$ref": "#/$defs/" + observation}, {"type": "null"}]}
                                         if observation else {"type": "null"})
            proof_ref = {"$ref": "#/$defs/SpanClaimProof" +
                         ("Commitment" if commitment else "Private" if scopes == ["private_record"] else "")}
            properties["proof"] = proof_ref if known else {"anyOf": [proof_ref, {"type": "null"}]}
            claim_branches.append(branch)
    definitions["FactualClaim"] = {"anyOf": claim_branches}
    if not catalog.ids("dialogue", roles={"operator"}):
        wire["properties"]["factual_claims"]["maxItems"] = 0
        wire["properties"]["assertion_groups"]["maxItems"] = 0

    # Each selectable catalog ID is enumerated once, partitioned by its source.
    # Arbitrary source-ID subsets reuse these exact partitions without widening.
    partitions = {}
    for span in catalog.entries.values():
        if span.selectable:
            key = (span.kind, span.source_id, span.role)
            partitions.setdefault(key, []).append(span.span_id)
    span_definitions = {}
    partition_refs = {}
    for index, (key, ids) in enumerate(partitions.items()):
        name = f"SpanSource{index}ID"
        span_definitions[name] = {"type": "string", "enum": ids}
        partition_refs[key] = {"$ref": f"#/$defs/{name}"}

    raw_definitions = deepcopy(definitions)
    selections = {}

    def values(node, seen=()):
        if "enum" in node:
            return set(node["enum"])
        if "const" in node:
            return {node["const"]}
        if "$ref" in node:
            name = node["$ref"].split("/")[-1]
            if name in seen:
                raise ValueError("Unexpected recursive source-ID definition")
            return values(raw_definitions[name], (*seen, name))
        if "anyOf" in node:
            options = [values(option, seen) for option in node["anyOf"]]
            return None if any(option is None for option in options) else set().union(*options)
        return None

    def select_id(kind, owners=None):
        keys = tuple(key for key in partition_refs if key[0] == kind and (owners is None or key[1] in owners))
        refs = [partition_refs[key] for key in keys]
        # This form is reachable only inside a citation collection made null
        # when no source exists. It creates neither an empty enum nor invented ID.
        if not refs:
            return {"type": "string", "pattern": "^$"}
        if len(refs) == 1:
            return deepcopy(refs[0])
        if keys not in selections:
            name = f"SpanSelection{len(selections)}ID"
            selections[keys] = name
            span_definitions[name] = {"anyOf": deepcopy(refs)}
        return {"$ref": "#/$defs/" + selections[keys]}

    def citation_info(node):
        if "$ref" in node:
            name = node["$ref"].split("/")[-1]
            return citation_info(raw_definitions[name])
        fields = node.get("properties", {})
        for owner, kind in [("message_id", "dialogue"), ("reference_id", "reference"), ("criterion_id", "rule")]:
            if set(fields) == {owner, "quote"} and fields["quote"].get("type") == "string":
                return kind, values(fields[owner])
        return None

    def citation_available(info):
        kind, owners = info
        return any(key[0] == kind and (owners is None or key[1] in owners) for key in partition_refs)

    def rewrite(node):
        if isinstance(node, list):
            return [rewrite(child) for child in node]
        if not isinstance(node, dict):
            return node
        if node.get("type") == "array":
            info = citation_info(node["items"])
            if node.get("maxItems") == 0 or info and not citation_available(info):
                return {"type": "null"}
        info = citation_info(node)
        if info:
            kind, owners = info
            return {"type": "object", "properties": {"span_id": select_id(kind, owners)},
                    "required": ["span_id"], "additionalProperties": False}
        # Property names may themselves be "required", "title" or "default".
        # Only schema metadata is removed; maps of configured fields stay intact.
        result = {}
        for key, value in node.items():
            if key in {"default", "required", "title"}:
                continue
            if key == "properties":
                result[key] = {name: rewrite(field) for name, field in value.items()}
            elif key in {"items", "additionalProperties"} and isinstance(value, dict):
                result[key] = rewrite(value)
            elif key == "anyOf":
                result[key] = [rewrite(option) for option in value]
            else:
                result[key] = value
        fields = result.get("properties", {})
        if {"criterion_id", "rule_quote"} <= fields.keys() and fields["rule_quote"].get("type") == "string":
            owners = values(node["properties"].get("criterion_id", {}))
            result["properties"] = {("rule_span_id" if name == "rule_quote" else name):
                (select_id("rule", owners) if name == "rule_quote" else field) for name, field in fields.items()}
        if result.get("type") == "object":
            result["required"] = list(result.get("properties", {}))
            result["additionalProperties"] = False
        return result

    for name, definition in raw_definitions.items():
        definitions[name] = rewrite(definition)
    wire = rewrite({key: value for key, value in wire.items() if key != "$defs"})
    definitions.update(span_definitions)
    wire["$defs"] = definitions
    wire["required"] = list(wire["properties"])
    wire["additionalProperties"] = False
    wire = _share_shapes(wire)
    definitions = wire["$defs"]

    # Unreachable historical transport definitions would still consume provider
    # enum/property limits. Keep only definitions referenced by the actual wire.
    needed = set()

    def collect(node):
        # Visit actual schema positions; configured property names such as
        # "$defs" and "$ref" are data and must not affect graph traversal.
        if "$ref" in node:
            name = node["$ref"].split("/")[-1]
            if name not in needed:
                needed.add(name)
                collect(definitions[name])
        for field in node.get("properties", {}).values():
            collect(field)
        for option in node.get("anyOf", []):
            collect(option)
        for field in ["items", "additionalProperties"]:
            if isinstance(node.get(field), dict):
                collect(node[field])

    collect(wire)
    wire["$defs"] = {name: definition for name, definition in definitions.items() if name in needed}
    return wire
