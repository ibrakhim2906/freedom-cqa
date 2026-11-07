"""Source coverage and declared support checks, not a semantic entailment oracle.

The ledger exposes excluded content and unproven inference. It cannot establish
that every clause was correctly classified or that an implication is sound.
"""

from .grounding import reference_applicable


def validate_semantic_coverage(result, conversation, checklist):
    audit = result.semantic_audit
    if audit is None:
        # Historical outputs keep their original contract. The new wire decoder
        # separately requires this field for newly generated grounded results.
        return
    messages = {m.id: m for m in conversation.messages}
    expected = {m.id for m in conversation.messages if m.speaker in {"client", "operator"}}
    reviewed = audit.reviewed_message_ids
    if len(reviewed) != len(set(reviewed)) or set(reviewed) != expected:
        raise ValueError("Semantic audit must review every client/operator message exactly once")
    criteria = {c.id for c in checklist.criteria}
    judgments = {j.criterion_id: j for j in result.judgments}

    def quotes(items, roles):
        for item in items:
            message = messages.get(item.message_id)
            if (message is None or message.speaker not in roles or not item.quote.strip()
                    or item.quote not in message.text):
                raise ValueError("Semantic support needs a verbatim quote from the correct source role")

    excluded = set()
    exclusion_keys = set()
    for item in audit.exclusions:
        quotes([item.evidence], {"client", "operator"})
        if not item.explanation.strip():
            raise ValueError("Semantic exclusions require an explanation")
        ids = item.criterion_ids
        if len(ids) != len(set(ids)) or any(cid not in criteria for cid in ids):
            raise ValueError("Semantic exclusion references an invalid or duplicate criterion")
        key = (item.evidence.message_id, item.evidence.quote, item.reason)
        if key in exclusion_keys:
            raise ValueError("Duplicate semantic exclusion")
        exclusion_keys.add(key)
        if item.reason not in {"social", "context_or_confirmation"}:
            if not ids:
                raise ValueError("Substantive semantic exclusions require configured criterion links")
            for cid in ids:
                judgment = judgments.get(cid)
                cited = set(judgment.checked_message_ids) | {
                    e.message_id for e in judgment.evidence + judgment.counterevidence
                } if judgment else set()
                if item.evidence.message_id not in cited:
                    raise ValueError("Semantic exclusion must link to a judgment reviewing that source")
        excluded.add(item.evidence.message_id)

    requested = set()
    for request in result.request_coverage:
        if any(mid not in messages or messages[mid].speaker != "client" for mid in request.request_message_ids):
            raise ValueError("Semantic request sources must be customer messages")
        requested.update(request.request_message_ids)
        support = request.support
        if support is None:
            raise ValueError("Every current request requires explicit answer support")
        if any(not aspect.strip() for aspect in support.unresolved_aspects):
            raise ValueError("Unresolved request aspects must be substantive")
        if request.status == "answered" and support.unresolved_aspects:
            raise ValueError("An answered request cannot retain unresolved aspects")
        if request.status == "partial" and not support.unresolved_aspects:
            raise ValueError("A partial request must identify its unresolved aspects")
        if support.basis in {"explicit", "implied"}:
            if request.status not in {"answered", "partial"}:
                raise ValueError("Explicit/implied support requires an answered or partial request")
        elif support.basis == "next_step":
            if request.status != "next_step":
                raise ValueError("Next-step support must match next_step request status")
        elif support.basis == "none":
            if request.status != "unanswered":
                raise ValueError("Absent answer support requires unanswered request status")
        elif support.basis == "withdrawn" and request.status != "withdrawn":
            raise ValueError("Withdrawal support must match withdrawn request status")
        if support.basis == "implied" and not (support.inference and support.inference.strip()):
            raise ValueError("An implied answer requires an inference explanation")
        if support.basis == "withdrawn":
            quotes(support.evidence, {"client"})
            allowed = set(request.withdrawal_message_ids)
        else:
            quotes(support.evidence, {"operator"})
            allowed = set(request.answer_message_ids)
        if support.basis != "none" and not support.evidence:
            raise ValueError("Declared answer support requires source evidence")
        if any(e.message_id not in allowed for e in support.evidence):
            raise ValueError("Answer-support evidence must belong to the linked answer/withdrawal span")

    asserted = set()
    for claim in result.factual_claims:
        quotes(claim.operator_evidence, {"operator"})
        asserted.update(e.message_id for e in claim.operator_evidence)
        if claim.assessment and claim.assessment.lifecycle == "corrected" and claim.assessment.correction:
            correction_sources = claim.assessment.correction.operator_evidence
            quotes(correction_sources, {"operator"})
            # A canonical, independently validated correction is already a
            # reviewed assertion; do not demand a duplicate final-route claim.
            asserted.update(e.message_id for e in correction_sources)
        required_scope = {"grading_rule": "grading_rule", "account_state": "private_record",
                          "workflow_commitment": "commitment"}.get(claim.evidence_kind)
        if required_scope is not None and claim.verification_scope != required_scope:
            raise ValueError("Claim evidence kind and verification scope must agree")
        if claim.evidence_kind in {"product_fact", "general_fact"} and claim.verification_scope not in {"interaction", "policy"}:
            raise ValueError("Product/general claims require interaction or policy verification scope")
        known_truth = claim.status in {"supported", "contradicted"}
        refs = {r.id: r for r in conversation.references}
        applicable_reference = any(
            item.reference_id in refs and item.quote.strip() and item.quote in refs[item.reference_id].text
            and reference_applicable(refs[item.reference_id], conversation, derive_dates=True)
            for item in claim.reference_evidence
        )
        if known_truth and claim.verification_scope == "policy" and not applicable_reference:
            raise ValueError("Verified policy claims require an applicable reference")
        if known_truth and claim.evidence_kind == "account_state" and not applicable_reference:
            quotes(claim.dialogue_evidence, {"client", "system"})
            if (not claim.dialogue_evidence or claim.observation_scope != "system_record"
                    or any(messages[e.message_id].speaker != "system" for e in claim.dialogue_evidence)):
                raise ValueError("Customer reports alone cannot verify private account state")
        if claim.status != "supported":
            continue
        if claim.verification_scope == "commitment" and claim.supported_proposition != claim.claim:
            raise ValueError("Supported commitment must state exactly the proposition being assessed")
        if not claim.dialogue_evidence:
            continue
        quotes(claim.dialogue_evidence, {"client", "system"})
        if claim.observation_scope == "none" or not (claim.supported_proposition and claim.supported_proposition.strip()):
            raise ValueError("Dialogue-supported claims require a declared observation scope and proposition")
        if claim.reference_evidence:
            continue
        if claim.evidence_kind in {"product_fact", "general_fact"}:
            if claim.verification_scope != "interaction" or claim.observation_scope not in {
                "control_visible", "action_completed", "task_completed"
            }:
                raise ValueError("Dialogue observations cannot alone verify general product/policy truth")
            if claim.supported_proposition != claim.claim:
                raise ValueError("Observation proposition must equal the narrowly supported claim")

    for message in conversation.messages:
        if message.speaker == "client" and message.id not in requested | excluded:
            raise ValueError("Every customer message needs request coverage or an explicit exclusion")
        if message.speaker == "operator" and message.id not in asserted | excluded:
            # Being cited as an answer is not an exemption from assertion review.
            raise ValueError("Every operator message needs claim review or an explicit exclusion")
