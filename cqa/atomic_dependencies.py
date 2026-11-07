"""Validate declared atomic assertion/proof topology, never infer factual truth.

The model still has to separate semantic propositions and cite entailing sources.
No keyword or conjunction heuristic can establish that a free-text atom is truly
atomic. This contract prevents *declared* atoms, proof premises and fixed facts
from being silently collapsed or laundered through non-proving context.
"""

from .grounding import reference_applicable

_KINDS = ("evidence", "reference_evidence", "rule_evidence")


def _key(kind, item):
    field = {"evidence": "message_id", "reference_evidence": "reference_id", "rule_evidence": "criterion_id"}[
        kind
    ]
    return getattr(item, field), item.quote


def _unique_ids(values, path):
    if any(not isinstance(value, str) or not value.strip() or value != value.strip() for value in values):
        raise ValueError(f"{path}: IDs must be nonempty canonical strings")
    if len(values) != len(set(values)):
        raise ValueError(f"{path}: duplicate IDs")
    return set(values)


def assertion_group_status(group, claims):
    """Truth of an explicitly declared conjunction; never a shared grade branch."""
    statuses = [claims[cid].status for cid in group.claim_ids]
    if not statuses:
        raise ValueError("An empty assertion group has no established truth status")
    if any(status == "contradicted" for status in statuses):
        return "contradicted"
    return "supported" if all(status == "supported" for status in statuses) else "unverified"


def validate_atomic_dependencies(result, conversation, checklist):
    """Validate coverage-v3; historical v1/v2 records keep their original rules.

    Called after ordinary judgment, source, applicability and correction checks.
    The source checks here also protect direct helper callers and transitive
    premises. Flat proving fields must exactly expose all reachable proof leaves.
    Context is never a proof leaf, including when reached through another claim.
    """
    if result.semantic_audit is None or result.semantic_audit.version != "coverage-v3":
        return
    if result.assertion_groups is None:
        raise ValueError("coverage-v3 requires explicit assertion groups")
    claims = result.factual_claims
    ids = [claim.claim_id for claim in claims]
    _unique_ids(ids, "factual_claims.claim_id")
    indexed = dict(zip(ids, claims, strict=True))
    claim_positions = {claim.claim_id: i for i, claim in enumerate(claims)}
    messages = {m.id: m for m in conversation.messages}
    refs = {r.id: r for r in conversation.references}
    criteria = {c.id: c for c in checklist.criteria}
    groups = result.assertion_groups
    _unique_ids([group.group_id for group in groups], "assertion_groups.group_id")
    membership = {}

    def local_keys(kind, items, path):
        """Keep selected offsets distinct even when a source repeats its text.

        Full pipeline validation has already bound these selections to the
        immutable catalog. Standalone authored helper fixtures without a source
        audit retain content keys; a present audit never permits that fallback.
        """
        keys = []
        for i, item in enumerate(items):
            if result.source_citations is None:
                keys.append(_key(kind, item))
                continue
            pointer = "".join("/" + str(part).replace("~", "~0").replace("/", "~1") for part in (*path, i))
            span_id = result.source_citations.selections.get(pointer)
            if not isinstance(span_id, str) or not span_id.strip():
                raise ValueError(f"Atomic proof requires selected source-span provenance at {pointer}")
            keys.append((_key(kind, item)[0], span_id))
        return keys

    def source_check(kind, item, claim, path):
        if not item.quote.strip():
            raise ValueError(f"{path}: proof quotations cannot be empty")
        if kind == "evidence":
            message = messages.get(item.message_id)
            allowed = {"client", "system"}
            if claim.verification_scope == "commitment":
                allowed.add("operator")
            if message is None or message.speaker not in allowed or item.quote not in message.text:
                raise ValueError(f"{path}: proof needs an exact independent source quotation")
        elif kind == "reference_evidence":
            ref = refs.get(item.reference_id)
            if (
                ref is None
                or item.quote not in ref.text
                or not reference_applicable(ref, conversation, derive_dates=True)
            ):
                raise ValueError(f"{path}: proof requires an exact applicable reference")
        else:
            criterion = criteria.get(item.criterion_id)
            if (
                criterion is None
                or item.criterion_id not in claim.criterion_ids
                or claim.evidence_kind != "grading_rule"
            ):
                raise ValueError(f"{path}: only a related grading rule can supply rule proof")
            texts = [
                criterion.instruction,
                *[level.description for level in criterion.levels],
                *criterion.channel_guidance.values(),
            ]
            if not any(item.quote in text for text in texts):
                raise ValueError(f"{path}: proof rule must be verbatim")

    for group in groups:
        linked = _unique_ids(group.claim_ids, f"assertion_groups[{group.group_id}].claim_ids")
        if not linked or not linked <= indexed.keys():
            raise ValueError("Assertion groups must link existing claims")
        if (
            group.composition == "atomic"
            and len(linked) != 1
            or group.composition == "all_of"
            and len(linked) < 2
        ):
            raise ValueError("Atomic groups need one atom; all_of groups need at least two")
        if not group.operator_evidence:
            raise ValueError("Assertion groups require original operator source evidence")
        for item in group.operator_evidence:
            message = messages.get(item.message_id)
            if (
                message is None
                or message.speaker != "operator"
                or not item.quote.strip()
                or item.quote not in message.text
            ):
                raise ValueError("Assertion groups require verbatim operator evidence")
        for cid in linked:
            claim = indexed[cid]
            if cid in membership or claim.assertion_group_id != group.group_id:
                raise ValueError("Every atom must belong to exactly its declared assertion group")
            membership[cid] = group.group_id
            if not claim.operator_evidence or any(
                not any(
                    item.message_id == original.message_id and item.quote in original.quote
                    for original in group.operator_evidence
                )
                for item in claim.operator_evidence
            ):
                raise ValueError("Assertion group source must cover each atom's operator assertion")
    if set(membership) != set(indexed):
        raise ValueError("Every atomic factual claim requires assertion-group membership")

    for claim in claims:
        if claim.assessment is None:
            raise ValueError("Atomic claims require their own dependency assessments")
        for impact in claim.assessment.impacts:
            fixed = impact.fixed_claim_ids
            if fixed is None:
                raise ValueError("Atomic impacts require explicit fixed_claim_ids")
            fixed_set = _unique_ids(fixed, f"claim[{claim.claim_id}].fixed_claim_ids")
            expected = {
                other.claim_id
                for other in claims
                if other is not claim and impact.criterion_id in other.criterion_ids
            }
            if fixed_set != expected:
                raise ValueError(
                    "Atomic counterfactual must hold every other related claim fixed, excluding itself"
                )

    visiting, resolved = set(), {}

    def leaves(cid):
        if cid in visiting:
            raise ValueError("Atomic proof dependencies cannot contain cycles")
        if cid in resolved:
            return resolved[cid]
        claim = indexed[cid]
        claim_path = ("factual_claims", claim_positions[cid])
        proof = claim.proof
        declared = {
            "evidence": claim.dialogue_evidence,
            "reference_evidence": claim.reference_evidence,
            "rule_evidence": claim.rule_evidence,
        }
        result_leaves = {kind: {} for kind in _KINDS}
        if proof is None:
            if claim.status != "unverified" or any(declared.values()):
                raise ValueError("Only an unverified claim without proving sources may declare proof=null")
            resolved[cid] = result_leaves
            return result_leaves
        if not proof.explanation.strip():
            raise ValueError("Atomic proof requires an inference explanation")
        premise_ids = [p.premise_id for p in proof.premises]
        emitted = _unique_ids(premise_ids, f"claim[{cid}].proof.premises")
        required = _unique_ids(proof.required_premise_ids, f"claim[{cid}].proof.required_premise_ids")
        if not emitted or required != emitted:
            raise ValueError("Every declared proof premise must be required exactly once")
        if (
            proof.relation == "direct"
            and len(emitted) != 1
            or proof.relation == "all_of"
            and len(emitted) < 2
        ):
            raise ValueError("Direct proof needs one premise; all_of proof needs at least two")
        visiting.add(cid)
        for premise_index, premise in enumerate(proof.premises):
            local = {kind: getattr(premise, kind) for kind in _KINDS}
            target = premise.depends_on_claim_id
            if target is not None:
                if premise.proposition is not None or any(local.values()) or premise.required_status is None:
                    raise ValueError("Claim-dependent premises use only claim ID and required status")
                if target not in indexed or target == cid:
                    raise ValueError("Proof premise must reference another existing canonical claim")
                actual = indexed[target].status
                if actual == "unverified":
                    if claim.status != "unverified":
                        raise ValueError("An unverified proof dependency cannot establish a known claim")
                elif actual != premise.required_status:
                    raise ValueError(
                        "Proof premise required status conflicts with its actual canonical claim"
                    )
                inherited = leaves(target)
                for kind in _KINDS:
                    result_leaves[kind].update(inherited[kind])
                continue
            if premise.required_status is not None or not any(local.values()):
                raise ValueError("Source-backed proof premises need actual proving citations, not context")
            if premise.proposition is None:
                if proof.relation != "direct":
                    raise ValueError("Only direct singleton proof can alias the canonical claim proposition")
            elif not premise.proposition.strip():
                raise ValueError("Source-premise propositions cannot be empty")
            for kind, items in local.items():
                keys = local_keys(kind, items, (*claim_path, "proof", "premises", premise_index, kind))
                if len(keys) != len(set(keys)):
                    raise ValueError("A proof premise cannot duplicate the same citation")
                for item, key in zip(items, keys, strict=True):
                    source_check(kind, item, claim, f"claim[{cid}].proof[{premise.premise_id}]")
                    result_leaves[kind][key] = item
        visiting.remove(cid)

        # A dependency cannot promote an operator promise into independent proof
        # of completed work, nor hide client leaves under a system/private label.
        operator_leaves = {
            key
            for key, item in result_leaves["evidence"].items()
            if messages[item.message_id].speaker == "operator"
        }
        if operator_leaves:
            own_assertions = set(
                local_keys("evidence", claim.operator_evidence, (*claim_path, "operator_evidence"))
            )
            if claim.verification_scope != "commitment" or not operator_leaves <= own_assertions:
                raise ValueError(
                    "Operator commitments cannot prove a dependent policy, private state or completed action"
                )
        if claim.verification_scope == "commitment" and claim.status == "supported" and not operator_leaves:
            raise ValueError("A supported commitment needs the actual operator promise as proof")
        independent = {key for key in result_leaves["evidence"] if key not in operator_leaves}
        if (
            claim.observation_scope == "system_record" or claim.verification_scope == "private_record"
        ) and any(
            messages[result_leaves["evidence"][key].message_id].speaker != "system" for key in independent
        ):
            raise ValueError(
                "System/private proof cannot launder essential client premises through another claim"
            )
        actual_keys = {
            "evidence": independent,
            "reference_evidence": set(result_leaves["reference_evidence"]),
            "rule_evidence": set(result_leaves["rule_evidence"]),
        }
        for kind, items in declared.items():
            field = "dialogue_evidence" if kind == "evidence" else kind
            keys = local_keys(kind, items, (*claim_path, field))
            if len(keys) != len(set(keys)):
                raise ValueError("Atomic proving fields cannot duplicate a citation")
            if set(keys) != actual_keys[kind]:
                raise ValueError(
                    "Atomic proof must expose the exact union of essential source leaves; context-only premises do not count"
                )
        resolved[cid] = result_leaves
        return result_leaves

    for cid in indexed:
        leaves(cid)
