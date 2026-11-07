"""Project explicit criterion-bound review declarations, never grading evidence.

The v5 provider supplies only additional unquoted review IDs. Quoted sources and
other structured criterion links already declare review, so the persisted list
is their exact union in original source order. No wording or score is inspected.
"""


PROJECTION = "derived-groups-and-reviews-v5"


def _pointer(path):
    return "".join("/" + str(part).replace("~", "~0").replace("/", "~1") for part in path)


def _review_unions(result, conversation, checklist):
    audit = result.source_citations
    if (result.semantic_audit is None or result.semantic_audit.version != "coverage-v5"
            or audit is None or audit.projection != PROJECTION):
        raise ValueError("Review projection requires explicit coverage-v5 source provenance")
    criteria = {criterion.id for criterion in checklist.criteria}
    judgments = {judgment.criterion_id: judgment for judgment in result.judgments}
    if len(judgments) != len(result.judgments) or set(judgments) != criteria:
        raise ValueError("Review projection requires each configured judgment exactly once")
    additional = audit.additional_checked_message_ids
    if additional is None or set(additional) != criteria:
        raise ValueError("Additional review provenance must cover every configured criterion exactly")
    messages = {message.id: message for message in conversation.messages}
    order = {message.id: index for index, message in enumerate(conversation.messages)}
    selected = {cid: set() for cid in criteria}

    def ids(values, path):
        if len(values) != len(set(values)) or any(mid not in messages for mid in values):
            raise ValueError(f"{_pointer(path)}: review IDs must be valid unique source messages")
        return set(values)

    def criterion_ids(values, path):
        if len(values) != len(set(values)) or any(cid not in criteria for cid in values):
            raise ValueError(f"{_pointer(path)}: review links need valid unique configured criteria")
        return values

    def sources(values, path):
        found, seen = set(), set()
        for index, item in enumerate(values):
            if item.message_id not in messages:
                raise ValueError(f"{_pointer(path)}: review source must be an original message")
            # Source provenance distinguishes repeated identical text at different
            # offsets. A repeated selection in one source array is still invalid.
            key = audit.selections.get(_pointer((*path, index)), (item.message_id, item.quote))
            if key in seen:
                raise ValueError(f"{_pointer(path)}: duplicate review source selection")
            seen.add(key)
            found.add(item.message_id)
        return found

    for index, judgment in enumerate(result.judgments):
        cid = judgment.criterion_id
        selected[cid].update(ids(additional[cid], ("source_citations", "additional_checked_message_ids", cid)))
        for field in ["evidence", "counterevidence"]:
            selected[cid].update(sources(getattr(judgment, field), ("judgments", index, field)))

    deduction_ids = set()
    for index, deduction in enumerate(result.deductions):
        cid = deduction.criterion_id
        if cid not in criteria or cid in deduction_ids:
            raise ValueError("Deduction review links need one existing configured criterion")
        deduction_ids.add(cid)
        selected[cid].update(sources(deduction.evidence, ("deductions", index, "evidence")))
        selected[cid].update(ids(deduction.checked_message_ids, ("deductions", index, "checked_message_ids")))

    for index, exclusion in enumerate(result.semantic_audit.exclusions):
        linked = criterion_ids(exclusion.criterion_ids, ("semantic_audit", "exclusions", index, "criterion_ids"))
        # The singular exclusion evidence is never promoted into judgment evidence.
        mid = exclusion.evidence.message_id
        if mid not in messages:
            raise ValueError("Semantic review exclusion must reference an original source message")
        for cid in linked:
            selected[cid].add(mid)

    claims = {claim.claim_id: (index, claim) for index, claim in enumerate(result.factual_claims)}
    if None in claims or len(claims) != len(result.factual_claims):
        raise ValueError("Review projection requires unique canonical claim IDs")
    visiting, proof_cache = set(), {}

    def proof_sources(claim_id):
        if claim_id not in claims or claim_id in visiting:
            raise ValueError("Review proof dependencies need existing acyclic canonical claims")
        if claim_id in proof_cache:
            return proof_cache[claim_id]
        index, claim = claims[claim_id]
        visiting.add(claim_id)
        found = set()
        for pindex, premise in enumerate(claim.proof.premises if claim.proof is not None else []):
            found.update(sources(premise.evidence, ("factual_claims", index, "proof", "premises", pindex, "evidence")))
            if premise.depends_on_claim_id is not None:
                found.update(proof_sources(premise.depends_on_claim_id))
        visiting.remove(claim_id)
        proof_cache[claim_id] = found
        return found

    for index, claim in enumerate(result.factual_claims):
        linked = criterion_ids(claim.criterion_ids, ("factual_claims", index, "criterion_ids"))
        found = set(proof_sources(claim.claim_id))
        for field in ["operator_evidence", "dialogue_evidence", "context_evidence"]:
            found.update(sources(getattr(claim, field), ("factual_claims", index, field)))
        assessment = claim.assessment
        if assessment is not None:
            correction = assessment.correction
            if correction is not None:
                for field in ["operator_evidence", "outcome_evidence"]:
                    found.update(sources(getattr(correction, field),
                                         ("factual_claims", index, "assessment", "correction", field)))
                if claim.operator_evidence and correction.operator_evidence:
                    original_end = max(order[item.message_id] for item in claim.operator_evidence)
                    correction_start = min(order[item.message_id] for item in correction.operator_evidence)
                    correction_end = max(order[item.message_id] for item in correction.operator_evidence)
                    if correction_start <= original_end:
                        raise ValueError("Correction must follow the original assertion")
                    if any(order[item.message_id] <= correction_end for item in correction.outcome_evidence):
                        raise ValueError("Independent outcome confirmation must follow the correction")
            impact_ids = criterion_ids([impact.criterion_id for impact in assessment.impacts],
                                       ("factual_claims", index, "assessment", "impacts"))
            if set(impact_ids) != set(linked):
                raise ValueError("Claim impacts must cover each related criterion exactly once")
            for pindex, impact in enumerate(assessment.impacts):
                path = ("factual_claims", index, "assessment", "impacts", pindex)
                selected[impact.criterion_id].update(sources(impact.evidence, (*path, "evidence")))
                selected[impact.criterion_id].update(ids(impact.checked_message_ids, (*path, "checked_message_ids")))
        for cid in linked:
            selected[cid].update(found)

    return {cid: [message.id for message in conversation.messages if message.id in selected[cid]]
            for cid in judgments}


def project_review_links(result, conversation, checklist):
    """Populate v5 persisted review IDs from validated structured declarations."""
    projected = _review_unions(result, conversation, checklist)
    for judgment in result.judgments:
        judgment.checked_message_ids = projected[judgment.criterion_id]


def validate_review_projection(result, conversation, checklist):
    """Reject any saved v5 review list differing from its exact declared union."""
    projected = _review_unions(result, conversation, checklist)
    for judgment in result.judgments:
        if judgment.checked_message_ids != projected[judgment.criterion_id]:
            raise ValueError("Persisted review links must equal the exact chronological declared source union")
