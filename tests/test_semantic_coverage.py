from copy import deepcopy

import pytest

from cqa.models import Checklist, Conversation, Criterion, Evaluation, Level, Message, Reference
from cqa.scoring import calculate_score, validate_evaluation
from cqa.semantic_coverage import validate_semantic_coverage


def fixture():
    conversation = Conversation(id="unseen-audit", channel="agent chat", language="EN", messages=[
        Message(id="q", timestamp="00:01", speaker="client", text="Where can I download the statement?"),
        Message(id="a", timestamp="00:02", speaker="operator", text="Open Documents and choose Download."),
        Message(id="c", timestamp="00:03", speaker="client", text="The Download button is visible."),
        Message(id="bye", timestamp="00:04", speaker="operator", text="Goodbye."),
        Message(id="event", timestamp="00:05", speaker="system", text="Conversation ended.")])
    checklist = Checklist(id="unseen-checklist", version="1", title="Source-independent test", instructions=[],
        criteria=[Criterion(id="completion", title="Completion", instruction="Give a concrete next step.",
            kind="scale", weight=4, levels=[Level(value="complete", fraction=1, description="Concrete next step"),
                                            Level(value="missing", fraction=0, description="No usable next step")])])
    data = {"judgments": [{"criterion_id": "completion", "status": "scored", "answer": "complete",
        "explanation": "Concrete navigation is offered.", "evidence": [{"message_id": "a", "quote": "Open Documents"}],
        "counterevidence": [], "checked_message_ids": ["q", "a", "c", "bye"], "uncertainty": None}],
        "request_coverage": [{"request": "Locate the statement download", "request_message_ids": ["q"],
            "status": "next_step", "answer_message_ids": ["a"], "explanation": "A concrete navigation step.",
            "withdrawal_message_ids": [], "support": {"basis": "next_step", "evidence": [
                {"message_id": "a", "quote": "Open Documents and choose Download."}],
                "inference": None, "unresolved_aspects": []}}],
        "scope_notes": [], "factual_claims": [], "deductions": [],
        "semantic_audit": {"version": "coverage-v1", "reviewed_message_ids": ["q", "a", "c", "bye"],
            "exclusions": [
                {"evidence": {"message_id": "a", "quote": "Open Documents and choose Download."},
                 "reason": "criterion_behavior", "criterion_ids": ["completion"],
                 "explanation": "This instruction is reviewed as a concrete next step, not proof of backend completion."},
                {"evidence": {"message_id": "c", "quote": "The Download button is visible."},
                 "reason": "context_or_confirmation", "criterion_ids": [],
                 "explanation": "The customer confirms finding the control without adding a request."},
                {"evidence": {"message_id": "bye", "quote": "Goodbye."}, "reason": "social", "criterion_ids": [],
                 "explanation": "Farewell only."}]}}
    return conversation, checklist, data


def check(data, conversation, checklist):
    result = Evaluation.model_validate(data)
    validate_semantic_coverage(result, conversation, checklist)
    return result


def test_concrete_next_step_does_not_require_completed_task_or_backend_proof():
    conversation, checklist, data = fixture()
    result = check(data, conversation, checklist)
    validate_evaluation(result, conversation, checklist, require_audit=True)
    assert calculate_score(result, checklist)["total"] == 100


def test_legacy_records_keep_their_historical_contract():
    conversation, checklist, data = fixture()
    data.pop("semantic_audit")
    data["request_coverage"][0].pop("support")
    check(data, conversation, checklist)


@pytest.mark.parametrize("change", ["missing_review", "duplicate_review", "system_review", "uncovered_customer",
                                    "uncovered_operator", "fake_quote", "wrong_role", "unknown_criterion",
                                    "missing_criterion", "unreviewed_exclusion", "blank_explanation"])
def test_missing_message_dispositions_and_invalid_exclusions_are_rejected(change):
    conversation, checklist, data = fixture()
    audit = data["semantic_audit"]
    if change == "missing_review":
        audit["reviewed_message_ids"].remove("c")
    elif change == "duplicate_review":
        audit["reviewed_message_ids"].append("q")
    elif change == "system_review":
        audit["reviewed_message_ids"].append("event")
    elif change == "uncovered_customer":
        audit["exclusions"] = [e for e in audit["exclusions"] if e["evidence"]["message_id"] != "c"]
    elif change == "uncovered_operator":
        audit["exclusions"] = [e for e in audit["exclusions"] if e["evidence"]["message_id"] != "a"]
    elif change == "fake_quote":
        audit["exclusions"][0]["evidence"]["quote"] = "A statement that was never present"
    elif change == "wrong_role":
        audit["exclusions"][0]["evidence"] = {"message_id": "event", "quote": "Conversation ended."}
    elif change == "unknown_criterion":
        audit["exclusions"][0]["criterion_ids"] = ["invented"]
    elif change == "missing_criterion":
        audit["exclusions"][0]["criterion_ids"] = []
    elif change == "unreviewed_exclusion":
        data["judgments"][0]["checked_message_ids"] = ["q"]
        data["judgments"][0]["evidence"] = []
    else:
        audit["exclusions"][0]["explanation"] = " "
    with pytest.raises(ValueError):
        check(data, conversation, checklist)


@pytest.mark.parametrize("change", ["null_support", "status_mismatch", "answered_unresolved", "partial_no_aspect",
                                    "implied_no_inference", "implied_no_evidence", "wrong_evidence_role",
                                    "unlinked_evidence", "fake_quote", "none_for_answered"])
def test_answer_support_requires_consistent_status_scope_and_sources(change):
    conversation, checklist, data = fixture()
    request = data["request_coverage"][0]
    support = request["support"]
    if change == "null_support":
        request["support"] = None
    elif change == "status_mismatch":
        request["status"] = "answered"
    elif change == "answered_unresolved":
        request["status"], support["basis"] = "answered", "explicit"
        support["unresolved_aspects"] = ["The download location is still unanswered"]
    elif change == "partial_no_aspect":
        request["status"], support["basis"] = "partial", "explicit"
    elif change == "implied_no_inference":
        request["status"], support["basis"] = "answered", "implied"
        support["inference"] = " "
    elif change == "implied_no_evidence":
        request["status"], support["basis"] = "answered", "implied"
        support["inference"] = "The operator's actual instruction entails where the document can be obtained."
        support["evidence"] = []
    elif change == "wrong_evidence_role":
        support["evidence"] = [{"message_id": "c", "quote": "The Download button is visible."}]
    elif change == "unlinked_evidence":
        support["evidence"] = [{"message_id": "bye", "quote": "Goodbye."}]
    elif change == "fake_quote":
        support["evidence"][0]["quote"] = "The statement was downloaded successfully"
    else:
        request["status"], support["basis"] = "answered", "none"
    with pytest.raises(ValueError):
        check(data, conversation, checklist)


def add_claim(data, **updates):
    claim = {"claim": "The customer located the Download control.", "criterion_ids": ["completion"],
        "operator_evidence": [{"message_id": "a", "quote": "Open Documents and choose Download."}],
        "status": "supported", "material": True, "reference_evidence": [],
        "dialogue_evidence": [{"message_id": "c", "quote": "The Download button is visible."}],
        "explanation": "Narrow source observation.", "assessment": None, "evidence_kind": "product_fact",
        "rule_evidence": [], "verification_scope": "interaction", "observation_scope": "control_visible",
        "supported_proposition": "The customer located the Download control."}
    claim.update(updates)
    data["factual_claims"] = [claim]
    data["semantic_audit"]["exclusions"] = [e for e in data["semantic_audit"]["exclusions"]
                                               if e["evidence"]["message_id"] != "a"]
    return claim


@pytest.mark.parametrize("fault", ["no_scope", "no_proposition", "policy_scope", "private_from_customer", "narrower_proposition"])
def test_observations_cannot_be_promoted_to_general_policy_or_private_state(fault):
    conversation, checklist, data = fixture()
    claim = add_claim(data)
    if fault == "no_scope":
        claim["observation_scope"] = "none"
    elif fault == "no_proposition":
        claim["supported_proposition"] = " "
    elif fault == "policy_scope":
        claim["verification_scope"] = "policy"
        claim["observation_scope"] = "reported_state"
        claim["supported_proposition"] = "The provider guarantees this route for every account forever."
    elif fault == "private_from_customer":
        claim["evidence_kind"] = "account_state"
        claim["verification_scope"] = "private_record"
        claim["observation_scope"] = "system_record"
    else:
        claim["claim"] = "Every customer can download every report."
    with pytest.raises(ValueError):
        check(data, conversation, checklist)


def test_narrow_control_observation_is_allowed_without_claiming_task_completion():
    conversation, checklist, data = fixture()
    add_claim(data)
    check(data, conversation, checklist)


def test_supplied_system_record_can_establish_particular_account_state():
    conversation, checklist, data = fixture()
    conversation.messages[-1].text = "Account restriction is active."
    add_claim(data, claim="This account has an active restriction.", evidence_kind="account_state",
              verification_scope="private_record", observation_scope="system_record",
              dialogue_evidence=[{"message_id": "event", "quote": "Account restriction is active."}],
              supported_proposition="This account has an active restriction.")
    check(data, conversation, checklist)


def test_explicit_withdrawal_uses_customer_not_operator_evidence():
    conversation, checklist, data = fixture()
    conversation.messages[2].text = "I no longer need the statement."
    request = data["request_coverage"][0]
    request.update(status="withdrawn", withdrawal_message_ids=["c"])
    request["support"].update(basis="withdrawn", evidence=[{"message_id": "c", "quote": "I no longer need the statement."}])
    data["semantic_audit"]["exclusions"][1]["evidence"]["quote"] = conversation.messages[2].text
    check(data, conversation, checklist)
    request["support"]["evidence"] = [{"message_id": "a", "quote": "Open Documents and choose Download."}]
    with pytest.raises(ValueError):
        check(data, conversation, checklist)


def test_legitimate_numeric_deduction_is_not_removed_by_coverage_validation():
    conversation, checklist, data = fixture()
    original = deepcopy(data)
    conversation.messages[1].text = "Everything is somewhere in the app."
    data["judgments"][0]["answer"] = "missing"
    data["judgments"][0]["evidence"] = []
    data["request_coverage"][0].update(status="unanswered", explanation="The operator never identifies a download location.")
    data["request_coverage"][0]["support"].update(basis="none", evidence=[
        {"message_id": "a", "quote": conversation.messages[1].text}], unresolved_aspects=["Where to download the statement"])
    data["semantic_audit"]["exclusions"][0]["evidence"]["quote"] = conversation.messages[1].text
    data["deductions"] = [{"criterion_id": "completion", "rule_quote": "No usable next step",
        "defect": "The vague reply supplies no usable next step.", "evidence": [], "checked_message_ids": ["q", "a"],
        "overlap_note": "Independent configured failure retained."}]
    result = check(data, conversation, checklist)
    validate_evaluation(result, conversation, checklist, require_audit=True)
    assert result.judgments[0].answer == "missing"
    assert calculate_score(result, checklist)["total"] == 0
    assert original["judgments"][0]["answer"] == "complete"


@pytest.mark.parametrize("kind,scope", [("grading_rule", "policy"), ("account_state", "interaction"),
                                        ("workflow_commitment", "interaction")])
def test_verification_scopes_cannot_be_mislabeled(kind, scope):
    conversation, checklist, data = fixture()
    add_claim(data, evidence_kind=kind, verification_scope=scope)
    with pytest.raises(ValueError, match="verification scope must agree"):
        check(data, conversation, checklist)


def test_observable_commitment_does_not_require_fabricated_independent_completion():
    conversation, checklist, data = fixture()
    conversation.messages[0].text = "My statement download is failing. Please investigate."
    conversation.messages[1].text = "I will send this for investigation."
    data["request_coverage"][0]["request"] = "Investigate the failed statement download"
    data["request_coverage"][0]["support"]["evidence"] = [{"message_id": "a", "quote": conversation.messages[1].text}]
    claim = add_claim(data, claim="The operator offers an investigation referral.", evidence_kind="workflow_commitment",
        verification_scope="commitment", operator_evidence=[{"message_id": "a", "quote": conversation.messages[1].text}],
        dialogue_evidence=[], observation_scope="none", supported_proposition="The operator offers an investigation referral.")
    check(data, conversation, checklist)
    claim["supported_proposition"] = "The investigation was completed successfully."
    with pytest.raises(ValueError, match="exactly the proposition"):
        check(data, conversation, checklist)


def test_policy_verification_uses_source_date_context_without_ignoring_conflict():
    conversation, checklist, data = fixture()
    for i, message in enumerate(conversation.messages):
        message.timestamp = f"2026-11-03T10:0{i}:00+05:00"
    conversation.references = [Reference(id="guide", text="Statements can be downloaded from Documents.",
        provenance="Dated fictional platform documentation", valid_from="2026-11-03", valid_until="2026-11-03")]
    add_claim(data, verification_scope="policy", reference_evidence=[
        {"reference_id": "guide", "quote": "Statements can be downloaded from Documents."}])
    check(data, conversation, checklist)
    assert conversation.occurred_on is None  # Source derivation never rewrites a frozen record.
    conversation.occurred_on = "2026-11-07"
    with pytest.raises(ValueError, match="applicable reference"):
        check(data, conversation, checklist)


def corrected_fixture():
    conversation, checklist, data = fixture()
    conversation.messages[1].text = "Use Profile to download the statement."
    conversation.messages[2].text = "There is no download in Profile."
    conversation.messages[3:3] = [
        Message(id="fix", timestamp="00:04", speaker="operator", text="That was incorrect. Use Documents > Download."),
        Message(id="done", timestamp="00:05", speaker="client", text="I downloaded the requested statement.")]
    data["judgments"][0]["evidence"] = [{"message_id": "fix", "quote": "Use Documents > Download."}]
    data["judgments"][0]["checked_message_ids"] = ["q", "a", "c", "fix", "done", "bye"]
    request = data["request_coverage"][0]
    request.update(status="answered", answer_message_ids=["fix"])
    request["support"].update(basis="explicit", evidence=[{"message_id": "fix", "quote": "Use Documents > Download."}])
    claim = add_claim(data, claim="Profile provides this statement download.", status="contradicted",
        operator_evidence=[{"message_id": "a", "quote": conversation.messages[1].text}],
        dialogue_evidence=[{"message_id": "c", "quote": conversation.messages[2].text}],
        observation_scope="none", supported_proposition=None)
    claim["assessment"] = {"lifecycle": "corrected", "correction": {
        "operator_evidence": [{"message_id": "fix", "quote": "That was incorrect. Use Documents > Download."}],
        "outcome_evidence": [{"message_id": "done", "quote": "I downloaded the requested statement."}],
        "reference_evidence": [], "remaining_consequence": "none_established", "explanation": "Successful later correction."},
        "impacts": [{"criterion_id": "completion", "when_true": {"status": "scored", "answer": "complete"},
            "when_false": {"status": "scored", "answer": "complete"}, "rule_quote": "Give a concrete next step.",
            "evidence": [{"message_id": "fix", "quote": "Use Documents > Download."}],
            "checked_message_ids": ["a", "c", "fix", "done"], "explanation": "Corrected final step succeeds."}]}
    audit = data["semantic_audit"]
    audit["reviewed_message_ids"] = ["q", "a", "c", "fix", "done", "bye"]
    next(e for e in audit["exclusions"] if e["evidence"]["message_id"] == "c")["evidence"]["quote"] = conversation.messages[2].text
    audit["exclusions"].append({"evidence": {"message_id": "done", "quote": "I downloaded the requested statement."},
        "reason": "context_or_confirmation", "criterion_ids": [], "explanation": "Outcome confirmation, no new request."})
    return conversation, checklist, data


def test_canonical_correction_source_counts_without_duplicate_final_route_claim():
    conversation, checklist, data = corrected_fixture()
    result = check(data, conversation, checklist)
    validate_evaluation(result, conversation, checklist, require_audit=True)
    assert len(result.factual_claims) == 1
    assert calculate_score(result, checklist)["total"] == 100


def test_an_answer_reference_alone_does_not_substitute_for_canonical_correction_review():
    conversation, checklist, data = corrected_fixture()
    data["factual_claims"][0]["assessment"]["correction"]["operator_evidence"] = [
        {"message_id": "a", "quote": conversation.messages[1].text}]
    with pytest.raises(ValueError, match="Every operator message needs claim review"):
        check(data, conversation, checklist)


def test_customer_report_cannot_certify_contradicted_private_account_state():
    conversation, checklist, data = fixture()
    conversation.messages[2].text = "My account does not have that restriction."
    data["semantic_audit"]["exclusions"][1]["evidence"]["quote"] = conversation.messages[2].text
    add_claim(data, claim="This account has an active restriction.", status="contradicted",
        evidence_kind="account_state", verification_scope="private_record", observation_scope="system_record",
        dialogue_evidence=[{"message_id": "c", "quote": conversation.messages[2].text}], supported_proposition=None)
    with pytest.raises(ValueError, match="Customer reports alone"):
        check(data, conversation, checklist)


def test_one_failed_attempt_cannot_certify_contradicted_general_policy():
    conversation, checklist, data = fixture()
    conversation.messages[2].text = "I could not find a Download option."
    data["semantic_audit"]["exclusions"][1]["evidence"]["quote"] = conversation.messages[2].text
    add_claim(data, claim="All users can always download every statement through this route.", status="contradicted",
        verification_scope="policy", observation_scope="control_visible",
        dialogue_evidence=[{"message_id": "c", "quote": conversation.messages[2].text}], supported_proposition=None)
    with pytest.raises(ValueError, match="policy claims require an applicable reference"):
        check(data, conversation, checklist)


def test_customer_can_establish_specific_interaction_route_failure():
    conversation, checklist, data = fixture()
    conversation.messages[2].text = "That route has no Download option on my screen."
    data["semantic_audit"]["exclusions"][1]["evidence"]["quote"] = conversation.messages[2].text
    add_claim(data, claim="This customer can find Download on this screen through the proposed route.",
        status="contradicted", verification_scope="interaction", observation_scope="control_visible",
        dialogue_evidence=[{"message_id": "c", "quote": conversation.messages[2].text}], supported_proposition=None)
    check(data, conversation, checklist)
