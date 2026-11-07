"""Strict source selections and explicit proposition aliases, never output repair.

The provider selects immutable source IDs. Only after the complete transport
schema validates do we resolve those selections into the historical display
shape. No source search, spelling correction, metadata inference or score change
occurs here. Persisted selections are revalidated when an assessment is checked.
"""

import json

import jsonschema

from .models import Evaluation
from .output_contract import _require_explicit_fields
from .source_spans import VERSION, build_catalog

CONTRACT = "span-v3"
_LIST_FIELDS = frozenset({
    "evidence", "counterevidence", "checked_message_ids", "request_coverage", "factual_claims", "scope_notes",
    "operator_evidence", "dialogue_evidence", "context_evidence", "reference_evidence", "rule_evidence",
    "criterion_ids", "claim_ids", "fixed_claim_ids", "premises", "required_premise_ids", "assertion_groups",
    "reviewed_message_ids", "exclusions", "answer_message_ids", "request_message_ids", "withdrawal_message_ids",
    "unresolved_aspects", "impacts", "outcome_evidence",
})
_SOURCE_MARKER = "__selected_source_span"
_RULE_MARKER = "__selected_rule_span"


def _pointer(path):
    return "".join("/" + str(part).replace("~", "~0").replace("/", "~1") for part in path)


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Source-span transport forbids duplicate object fields")
        value[key] = item
    return value


def _reject_constant(_):
    raise ValueError("Source-span transport requires standard JSON values")


def _citation_constraint(path, field):
    if field == "reference_evidence":
        return "reference", None
    if field == "rule_evidence":
        return "rule", None
    if field == "operator_evidence":
        return "dialogue", {"operator"}
    if field == "outcome_evidence":
        return "dialogue", {"client", "system"}
    if field == "context_evidence":
        omission = len(path) >= 4 and path[-2:] == ("support", "omission")
        return "dialogue", None if omission else {"client", "system"}
    if field == "evidence" and len(path) == 3 and path[:2] == ("semantic_audit", "exclusions"):
        return "dialogue", {"client", "operator"}
    return "dialogue", None


def decode_span_evaluation(text, conversation, checklist):
    # Delayed import avoids evaluator/schema/decoder import cycles. Preparation is
    # pure and does not construct an evaluator, client or usage ledger.
    from .evaluator import schema_for

    catalog = build_catalog(conversation, checklist)
    catalog.assert_sources(conversation, checklist)
    data = json.loads(text, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    if not isinstance(data, dict) or data.get("contract_version") != CONTRACT:
        raise ValueError("Current evaluator requires the explicit span-v3 transport; no legacy fallback")
    if data.get("catalog_fingerprint") != catalog.fingerprint:
        raise ValueError("Source-span selection belongs to a different catalog/source revision")
    schema = schema_for(conversation, checklist, grounded=True, source_contract=True)
    try:
        jsonschema.Draft202012Validator(schema).validate(data)
    except jsonschema.ValidationError as error:
        raise ValueError("Span transport schema mismatch at " + _pointer(error.absolute_path)) from None

    def resolve(value, path=(), kind="dialogue", roles=None, owner=None):
        if isinstance(value, list):
            return [resolve(item, (*path, i), kind, roles, owner) for i, item in enumerate(value)]
        if not isinstance(value, dict):
            return value
        if set(value) == {"span_id"} and isinstance(value["span_id"], str):
            selection = value["span_id"]
            result = catalog.resolve(selection, kind=kind, roles=roles,
                                     criterion_id=owner if kind == "rule" else None)
            return {**result, _SOURCE_MARKER: selection}
        owner = value.get("criterion_id", owner)
        resolved = {}
        for key, item in value.items():
            if key == "rule_span_id" and isinstance(item, str):
                rule = catalog.resolve(item, kind="rule", criterion_id=owner)
                resolved["rule_quote"] = rule["quote"]
                resolved[_RULE_MARKER] = item
                continue
            child_kind, child_roles = _citation_constraint(path, key)
            if key in _LIST_FIELDS and item is None:
                # The validated branch explicitly required literal null for a
                # forbidden collection. Missing fields and nonempty lists never
                # arrive here as substitutes for that declaration.
                item = []
            resolved[key] = resolve(item, (*path, key), child_kind, child_roles, owner)
        return resolved

    resolved = resolve(data)
    resolved.pop("contract_version")
    resolved.pop("catalog_fingerprint")
    claims = resolved["factual_claims"]
    indexed = {c["claim_id"]: c for c in claims}
    if len(indexed) != len(claims):
        raise ValueError("Canonical claim IDs must be unique")
    visiting, leaf_cache = set(), {}

    def leaves(cid):
        if cid not in indexed or cid in visiting:
            raise ValueError("Proof dependency must be an existing acyclic canonical claim")
        if cid in leaf_cache:
            return leaf_cache[cid]
        visiting.add(cid)
        found = {name: {} for name in ["evidence", "reference_evidence", "rule_evidence"]}
        proof = indexed[cid]["proof"]
        for premise in proof["premises"] if proof is not None else []:
            target = premise["depends_on_claim_id"]
            if target is not None:
                child = leaves(target)
                for name, selected in found.items():
                    selected.update(child[name])
            else:
                for name, selected in found.items():
                    for citation in premise[name]:
                        selected[citation[_SOURCE_MARKER]] = citation
        visiting.remove(cid)
        leaf_cache[cid] = found
        return found

    messages = {m.id: m for m in conversation.messages}
    for claim in claims:
        proof_sources = leaves(claim["claim_id"])
        claim["reference_evidence"] = [dict(e) for e in proof_sources["reference_evidence"].values()]
        claim["rule_evidence"] = [dict(e) for e in proof_sources["rule_evidence"].values()]
        dialogue = [dict(e) for e in proof_sources["evidence"].values()]
        if claim["verification_scope"] == "commitment":
            # Operator evidence establishes only the explicitly declared promise.
            # It is never projected as independent dialogue proof of completion.
            dialogue = [e for e in dialogue if messages[e["message_id"]].speaker != "operator"]
        observation = claim.pop("observation")
        if observation is None:
            if dialogue:
                raise ValueError("Essential dialogue proof requires explicitly declared observation metadata")
            claim["dialogue_evidence"], claim["observation_scope"] = [], "none"
            claim["supported_proposition"] = claim["claim"] if claim["verification_scope"] == "commitment" else None
        else:
            if observation["target"] != "claim":
                raise ValueError("Observation must explicitly target its single canonical claim")
            if not dialogue:
                raise ValueError("An observation requires actual proving dialogue selections")
            claim["dialogue_evidence"] = dialogue
            claim["observation_scope"] = observation["scope"]
            # Explicit reference alias, not a second generated proposition and
            # not a claim that a contradicted proposition is true.
            claim["supported_proposition"] = claim["claim"]
    judgments, deductions = [], []
    for cid, judgment in resolved["judgments"].items():
        if judgment["criterion_id"] != cid:
            raise ValueError("Judgment key and criterion ID must match")
        deduction = judgment.pop("deduction")
        if deduction is not None:
            if deduction["criterion_id"] != cid:
                raise ValueError("Inline deduction must belong to its judgment")
            deductions.append(deduction)
        judgments.append(judgment)
    resolved["judgments"], resolved["deductions"] = judgments, deductions
    selections = {}

    def collect(value, path=()):
        if isinstance(value, dict):
            if _SOURCE_MARKER in value:
                selections[_pointer(path)] = value.pop(_SOURCE_MARKER)
            if _RULE_MARKER in value:
                selections[_pointer((*path, "rule_quote"))] = value.pop(_RULE_MARKER)
            for key, item in value.items():
                collect(item, (*path, key))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                collect(item, (*path, index))

    collect(resolved)
    resolved["source_citations"] = {"version": VERSION, "catalog_fingerprint": catalog.fingerprint,
                                    "selections": selections, "spans": {
        sid: {field: getattr(catalog.entries[sid], field) for field in ["kind", "source_id", "field", "role", "start", "end"]}
        for sid in sorted(set(selections.values()))}}
    result = Evaluation.model_validate(resolved)
    _require_explicit_fields(result)
    validate_source_citations(result, conversation, checklist)
    return result


def validate_source_citations(result, conversation, checklist):
    current = result.semantic_audit is not None and result.semantic_audit.version == "coverage-v3"
    if not current:
        if result.source_citations is not None or result.assertion_groups is not None or any(
            c.claim_id is not None or c.assertion_group_id is not None or c.proof is not None or
            c.assessment and any(i.fixed_claim_ids is not None for i in c.assessment.impacts)
            for c in result.factual_claims
        ):
            raise ValueError("Source/atomic dependency extensions require coverage-v3; no contract downgrade")
        return
    audit = result.source_citations
    if audit is None or audit.version != VERSION:
        raise ValueError("Source contract requires explicit source-citation provenance")
    catalog = build_catalog(conversation, checklist)
    if audit.catalog_fingerprint != catalog.fingerprint:
        raise ValueError("Saved source-citation catalog does not match source/checklist revision")
    if set(audit.spans) != set(audit.selections.values()):
        raise ValueError("Source navigation metadata must match exactly the selected immutable spans")
    for sid, metadata in audit.spans.items():
        original = catalog.entries.get(sid)
        if original is None or metadata.model_dump() != {
            field: getattr(original, field) for field in ["kind", "source_id", "field", "role", "start", "end"]
        }:
            raise ValueError("Selected source offsets/identity differ from their immutable catalog")
    expected = set()

    def check(value, path=()):
        if isinstance(value, dict):
            if "quote" in value:
                source_key = next((key for key in ["message_id", "reference_id", "criterion_id"] if key in value), None)
                if source_key is None:
                    raise ValueError("A quoted source needs its actual source identity")
                kind = {"message_id": "dialogue", "reference_id": "reference", "criterion_id": "rule"}[source_key]
                pointer = _pointer(path)
                selection = audit.selections.get(pointer)
                resolved = catalog.resolve(selection, kind=kind)
                if resolved != {source_key: value[source_key], "quote": value["quote"]}:
                    raise ValueError("Saved citation differs from its explicitly selected immutable source span")
                expected.add(pointer)
            for key, item in value.items():
                if key == "rule_quote":
                    pointer = _pointer((*path, key))
                    resolved = catalog.resolve(audit.selections.get(pointer), kind="rule",
                                               criterion_id=value.get("criterion_id"))
                    if resolved["quote"] != item:
                        raise ValueError("Saved rule quote differs from its selected criterion span")
                    expected.add(pointer)
                else:
                    check(item, (*path, key))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                check(item, (*path, index))

    check(result.model_dump(exclude={"source_citations"}))
    if set(audit.selections) != expected:
        raise ValueError("Source provenance must cover every quoted slot exactly, with no unused selections")
    _validate_span_dependencies(result, catalog)


def _validate_span_dependencies(result, catalog):
    """Compare exact selected offsets, not only identical quote text in a source."""
    selections = result.source_citations.selections
    indexed = {claim.claim_id: (i, claim) for i, claim in enumerate(result.factual_claims)}
    if len(indexed) != len(result.factual_claims):
        raise ValueError("Canonical claim IDs must be unique")
    visiting, cached = set(), {}

    def selected(path, values):
        return {selections[_pointer((*path, i))] for i in range(len(values))}

    def leaves(cid):
        if cid not in indexed or cid in visiting:
            raise ValueError("Proof dependencies must be existing acyclic canonical claims")
        if cid in cached:
            return cached[cid]
        index, claim = indexed[cid]
        visiting.add(cid)
        found = set()
        proof = claim.proof
        for pindex, premise in enumerate(proof.premises if proof is not None else []):
            if premise.depends_on_claim_id is not None:
                found.update(leaves(premise.depends_on_claim_id))
            else:
                for field in ["evidence", "reference_evidence", "rule_evidence"]:
                    found.update(selected(("factual_claims", index, "proof", "premises", pindex, field),
                                          getattr(premise, field)))
        visiting.remove(cid)
        operator = {sid for sid in found if catalog.entries[sid].role == "operator"}
        if operator:
            own = selected(("factual_claims", index, "operator_evidence"), claim.operator_evidence)
            if claim.verification_scope != "commitment" or not operator <= own:
                raise ValueError("A promise's exact source selection cannot prove another atom or completed action")
        flat = set()
        for field in ["dialogue_evidence", "reference_evidence", "rule_evidence"]:
            flat.update(selected(("factual_claims", index, field), getattr(claim, field)))
        if flat != found - operator:
            raise ValueError("Flat proof must preserve the exact selected spans of all essential premises")
        cached[cid] = found
        return found

    for cid in indexed:
        leaves(cid)
    for index, group in enumerate(result.assertion_groups or []):
        spans = [catalog.entries[sid] for sid in selected(("assertion_groups", index, "operator_evidence"),
                                                         group.operator_evidence)]
        for cid in group.claim_ids:
            if cid not in indexed:
                raise ValueError("Assertion groups must reference existing canonical claims")
            cindex, claim = indexed[cid]
            for sid in selected(("factual_claims", cindex, "operator_evidence"), claim.operator_evidence):
                atom = catalog.entries[sid]
                if not any(s.kind == atom.kind and s.source_id == atom.source_id and
                           s.start <= atom.start and s.end >= atom.end for s in spans):
                    raise ValueError("Assertion group must cover the actual selected atom source occurrence")
