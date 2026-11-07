"""Source coverage and declared support checks, not a semantic entailment oracle.

The ledger exposes excluded content and unproven inference. It cannot establish
that every clause was correctly classified or that an implication is sound.
"""

from .grounding import reference_applicable


def _validate_request_v2(request, index, conversation, messages, order):
    """Keep positive answer proof separate from a checked omission interval."""
    path = f"request_coverage[{index}].support"
    support = request.support
    if support is None:
        raise ValueError(f"{path}: coverage-v2 requires explicit support")
    for name in ["request_message_ids", "answer_message_ids", "withdrawal_message_ids"]:
        values = getattr(request, name)
        if len(values) != len(set(values)):
            raise ValueError(f"request_coverage[{index}].{name}: duplicate message IDs")
    if support.basis != "implied" and support.inference is not None:
        raise ValueError(f"{path}.inference: only an implied answer may declare an inference")
    if request.status == "unanswered":
        if request.answer_message_ids or support.evidence:
            raise ValueError(f"{path}.evidence: unanswered requests have no positive answer evidence; use omission.context_evidence")
        if support.basis != "none" or not support.unresolved_aspects:
            raise ValueError(f"{path}: unanswered requests require basis=none and unresolved aspects")
    elif request.status == "withdrawn":
        if request.answer_message_ids or support.unresolved_aspects:
            raise ValueError(f"{path}: withdrawn requests cannot claim an answer or outstanding aspects")
    elif request.status in {"answered", "partial", "next_step"}:
        if not request.answer_message_ids:
            raise ValueError(f"request_coverage[{index}].answer_message_ids: positive support needs an operator answer")
        if request.status == "next_step" and support.unresolved_aspects:
            raise ValueError(f"{path}.unresolved_aspects: a declared next step cannot retain unanswered aspects")

    missing = request.status in {"partial", "unanswered"}
    if missing != (support.omission is not None):
        raise ValueError(f"{path}.omission: partial/unanswered requests require an omission interval; other statuses require null")
    if not missing:
        return
    omission = support.omission
    if not request.request_message_ids or any(mid not in messages for mid in request.request_message_ids):
        raise ValueError(f"request_coverage[{index}].request_message_ids: omission needs actual customer request sources")
    start, end = omission.start_message_id, omission.end_message_id
    if start not in messages or end not in messages:
        raise ValueError(f"{path}.omission: interval endpoints must be actual source messages")
    earliest = min(request.request_message_ids, key=order.__getitem__)
    if start != earliest or end != conversation.messages[-1].id or order[start] > order[end]:
        raise ValueError(f"{path}.omission: interval must cover the earliest linked request through the final source turn")
    for evidence in omission.context_evidence:
        message = messages.get(evidence.message_id)
        if (message is None or not evidence.quote.strip() or evidence.quote not in message.text
                or not order[start] <= order[evidence.message_id] <= order[end]):
            raise ValueError(f"{path}.omission.context_evidence: quote must be verbatim inside the complete checked interval")


def validate_semantic_coverage(result, conversation, checklist):
    audit = result.semantic_audit
    if audit is None:
        # Historical outputs keep their original contract. The new wire decoder
        # separately requires this field for newly generated grounded results.
        return
    messages = {m.id: m for m in conversation.messages}
    order = {m.id: i for i, m in enumerate(conversation.messages)}
    current = audit.version in {"coverage-v2", "coverage-v3"}
    if not current and (any(r.support and r.support.omission is not None for r in result.request_coverage)
                        or any(c.context_evidence for c in result.factual_claims)):
        raise ValueError("Omission/context evidence requires the coverage-v2 contract")
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
    for index, request in enumerate(result.request_coverage):
        if any(mid not in messages or messages[mid].speaker != "client" for mid in request.request_message_ids):
            raise ValueError("Semantic request sources must be customer messages")
        requested.update(request.request_message_ids)
        support = request.support
        if support is None:
            raise ValueError("Every current request requires explicit answer support")
        if current:
            _validate_request_v2(request, index, conversation, messages, order)
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
    for claim_index, claim in enumerate(result.factual_claims):
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
        if current:
            # Context is reviewable source material, never independent truth proof.
            quotes(claim.context_evidence, {"client", "system"})
            if audit.version == "coverage-v3" and claim.dialogue_evidence and claim.verification_scope in {
                "policy", "grading_rule", "commitment"
            }:
                raise ValueError("Canonical observation proof cannot establish a general policy, rule or promise; separate the interaction premise or use context")
            if claim.dialogue_evidence:
                quotes(claim.dialogue_evidence, {"client", "system"})
                if claim.observation_scope == "system_record" and any(
                    messages[item.message_id].speaker != "system" for item in claim.dialogue_evidence
                ):
                    raise ValueError(f"factual_claims[{claim_index}]: system_record observation evidence must come from system messages")
                if claim.observation_scope == "none" or not (
                    claim.supported_proposition and claim.supported_proposition.strip()
                ):
                    raise ValueError(f"factual_claims[{claim_index}]: dialogue_evidence requires an explicit narrow observation_scope and supported_proposition, including alongside policy references")
            elif claim.observation_scope != "none":
                raise ValueError(f"factual_claims[{claim_index}]: an observation scope requires dialogue evidence; use context_evidence for non-proving reports")
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
