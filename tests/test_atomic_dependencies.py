"""Offline declared-proof regressions; authored fixtures are never API results."""

from copy import deepcopy

import pytest

from cqa.atomic_dependencies import assertion_group_status, validate_atomic_dependencies
from cqa.datasets import load_cases
from cqa.models import Checklist, Conversation, Evaluation
from cqa.rubric import load_checklist
from cqa.scoring import calculate_score
from cqa.settings import ROOT
from cqa.source_spans import build_catalog


def evidence(mid, quote):
    return {"message_id": mid, "quote": quote}


def source_premise(pid, *, proposition=None, dialogue=(), references=(), rules=()):
    return {
        "premise_id": pid,
        "proposition": proposition,
        "evidence": list(dialogue),
        "reference_evidence": list(references),
        "rule_evidence": list(rules),
        "depends_on_claim_id": None,
        "required_status": None,
    }


def dependency(pid, target, status="supported"):
    return {
        "premise_id": pid,
        "proposition": None,
        "evidence": [],
        "reference_evidence": [],
        "rule_evidence": [],
        "depends_on_claim_id": target,
        "required_status": status,
    }


def proof(*premises):
    return {
        "relation": "direct" if len(premises) == 1 else "all_of",
        "premises": list(premises),
        "required_premise_ids": [p["premise_id"] for p in premises],
        "explanation": "Every listed premise is independently needed; source existence is not an entailment oracle.",
    }


def impact(answer="20", false="0", fixed=()):
    return {
        "criterion_id": "consultation",
        "when_true": {"status": "scored", "answer": answer},
        "when_false": {"status": "scored", "answer": false},
        "rule_quote": "Correct complete advice",
        "evidence": [],
        "checked_message_ids": ["m1", "m2", "m3", "m4"],
        "explanation": "Other named atoms stay in their actual truth/lifecycle states.",
        "fixed_claim_ids": list(fixed),
    }


def atom(
    cid,
    text,
    operator,
    *,
    status="supported",
    dialogue=(),
    references=(),
    claim_proof=None,
    scope="interaction",
    observation="reported_state",
    fixed=(),
    group="g",
):
    return {
        "claim": text,
        "claim_id": cid,
        "assertion_group_id": group,
        "criterion_ids": ["consultation"],
        "operator_evidence": [operator],
        "status": status,
        "material": True,
        "reference_evidence": list(references),
        "dialogue_evidence": list(dialogue),
        "rule_evidence": [],
        "context_evidence": [],
        "evidence_kind": "general_fact",
        "verification_scope": scope,
        "observation_scope": observation,
        "supported_proposition": text if dialogue or scope == "commitment" else None,
        "explanation": "Explicitly authored proof-contract test, not provider inference.",
        "assessment": {"lifecycle": "active", "correction": None, "impacts": [impact(fixed=fixed)]},
        "proof": claim_proof,
    }


def observation_fixture():
    conversation = Conversation.model_validate(
        {
            "id": "unseen-proof-chain",
            "channel": "agent chat",
            "language": "EN",
            "knowledge_scope": "test-portal",
            "occurred_on": "2026-11-07",
            "messages": [
                {
                    "id": "m1",
                    "timestamp": "2026-11-07T11:01:00+05:00",
                    "speaker": "client",
                    "text": "Confirm what was completed.",
                },
                {
                    "id": "m2",
                    "timestamp": "2026-11-07T11:02:00+05:00",
                    "speaker": "client",
                    "text": "I have not downloaded the sample.",
                },
                {
                    "id": "m3",
                    "timestamp": "2026-11-07T11:03:00+05:00",
                    "speaker": "system",
                    "text": "No client action occurred after m2 through m4.",
                },
                {
                    "id": "m4",
                    "timestamp": "2026-11-07T11:04:00+05:00",
                    "speaker": "operator",
                    "text": "No action occurred later. The sample was downloaded and opened.",
                },
            ],
        }
    )
    checklist = Checklist.model_validate(
        {
            "id": "proof-check",
            "version": "1",
            "title": "Novel proof task",
            "instructions": [],
            "criteria": [
                {
                    "id": "consultation",
                    "title": "Advice",
                    "instruction": "Correct complete advice",
                    "kind": "scale",
                    "weight": 100,
                    "levels": [
                        {"value": "20", "fraction": 1, "description": "Correct complete advice"},
                        {"value": "0", "fraction": 0, "description": "Wrong key assurance"},
                    ],
                }
            ],
        }
    )
    before, after = (
        evidence("m2", conversation.messages[1].text),
        evidence("m3", conversation.messages[2].text),
    )
    operator = evidence("m4", conversation.messages[-1].text)
    later = atom(
        "later",
        "No action occurred later.",
        operator,
        dialogue=[after],
        observation="system_record",
        claim_proof=proof(source_premise("p1", dialogue=[after])),
        fixed=["complete"],
    )
    complete = atom(
        "complete",
        "The sample was downloaded and opened.",
        operator,
        status="contradicted",
        dialogue=[before, after],
        fixed=["later"],
        claim_proof=proof(
            source_premise(
                "initial-state", proposition="The sample was not downloaded at m2.", dialogue=[before]
            ),
            dependency("no-later-action", "later"),
        ),
    )
    data = {
        "judgments": [
            {
                "criterion_id": "consultation",
                "status": "scored",
                "answer": "0",
                "explanation": "The final requested completion assurance is contradicted.",
                "evidence": [operator],
                "counterevidence": [],
                "checked_message_ids": [m.id for m in conversation.messages],
                "uncertainty": None,
            }
        ],
        "request_coverage": [],
        "scope_notes": [],
        "factual_claims": [later, complete],
        "deductions": [],
        "semantic_audit": {
            "version": "coverage-v3",
            "reviewed_message_ids": ["m1", "m2", "m4"],
            "exclusions": [],
        },
        "assertion_groups": [
            {
                "group_id": "g",
                "composition": "all_of",
                "operator_evidence": [operator],
                "claim_ids": ["later", "complete"],
            }
        ],
    }
    return conversation, checklist, data


def validate(data, conversation, checklist):
    result = Evaluation.model_validate(data)
    before = result.model_dump()
    validate_atomic_dependencies(result, conversation, checklist)
    assert result.model_dump() == before, "Validation must not repair evidence, grades or deductions"
    return result


def test_mixed_truth_group_keeps_separate_atoms_and_transitive_negative_observation_proof():
    c, checklist, data = observation_fixture()
    result = validate(data, c, checklist)
    index = {f.claim_id: f for f in result.factual_claims}
    assert assertion_group_status(result.assertion_groups[0], index) == "contradicted"
    assert result.factual_claims[0].status == "supported"
    assert result.factual_claims[1].status == "contradicted"
    assert calculate_score(result, checklist)["total"] == 0


@pytest.mark.parametrize(
    "fault",
    [
        "missing_group",
        "duplicate_claim",
        "unknown_group_claim",
        "wrong_membership",
        "shared_atomic_group",
        "missing_group_source",
        "wrong_group_role",
        "uncovered_atom",
        "group_duplicate_link",
    ],
)
def test_declared_atoms_cannot_disappear_or_share_one_atomic_assertion_slot(fault):
    c, checklist, data = observation_fixture()
    if fault == "missing_group":
        data["assertion_groups"] = []
    elif fault == "duplicate_claim":
        data["factual_claims"][1]["claim_id"] = "later"
    elif fault == "unknown_group_claim":
        data["assertion_groups"][0]["claim_ids"].append("missing")
    elif fault == "wrong_membership":
        data["factual_claims"][1]["assertion_group_id"] = "other"
    elif fault == "shared_atomic_group":
        data["assertion_groups"][0]["composition"] = "atomic"
    elif fault == "missing_group_source":
        data["assertion_groups"][0]["operator_evidence"] = []
    elif fault == "wrong_group_role":
        data["assertion_groups"][0]["operator_evidence"] = [evidence("m2", c.messages[1].text)]
    elif fault == "uncovered_atom":
        data["assertion_groups"][0]["operator_evidence"] = [evidence("m4", "No action occurred later.")]
    else:
        data["assertion_groups"][0]["claim_ids"].append("later")
    with pytest.raises(ValueError):
        validate(data, c, checklist)


@pytest.mark.parametrize(
    "fixed", [None, [], ["later", "later"], ["complete"], ["missing"], ["later", "complete"]]
)
def test_counterfactual_must_explicitly_hold_all_other_related_atoms_fixed(fixed):
    c, checklist, data = observation_fixture()
    data["factual_claims"][1]["assessment"]["impacts"][0]["fixed_claim_ids"] = fixed
    with pytest.raises(ValueError, match="fixed|duplicate"):
        validate(data, c, checklist)


@pytest.mark.parametrize(
    "fault",
    [
        "missing_required",
        "extra_required",
        "duplicate_required",
        "missing_premise",
        "direct_many",
        "all_of_single",
        "all_of_alias",
        "empty_source",
        "fake_quote",
        "operator_proof",
        "context_only",
        "extra_flat_proof",
        "missing_flat_proof",
        "source_with_dependency_status",
        "source_empty_proposition",
    ],
)
def test_every_required_proof_premise_needs_its_actual_proving_source(fault):
    c, checklist, data = observation_fixture()
    claim = data["factual_claims"][1]
    p = claim["proof"]
    if fault == "missing_required":
        p["required_premise_ids"].pop()
    elif fault == "extra_required":
        p["required_premise_ids"].append("invented")
    elif fault == "duplicate_required":
        p["required_premise_ids"].append("initial-state")
    elif fault == "missing_premise":
        p["premises"].pop()
    elif fault == "direct_many":
        p["relation"] = "direct"
    elif fault == "all_of_single":
        data["factual_claims"][0]["proof"]["relation"] = "all_of"
    elif fault == "all_of_alias":
        p["premises"][0]["proposition"] = None
    elif fault == "empty_source":
        p["premises"][0]["evidence"] = []
    elif fault == "fake_quote":
        p["premises"][0]["evidence"][0]["quote"] = "Invented noncompletion"
    elif fault == "operator_proof":
        p["premises"][0]["evidence"] = claim["operator_evidence"]
    elif fault == "context_only":
        claim["context_evidence"] = [claim["dialogue_evidence"].pop(0)]
    elif fault == "extra_flat_proof":
        claim["dialogue_evidence"].append(evidence("m1", c.messages[0].text))
    elif fault == "missing_flat_proof":
        claim["dialogue_evidence"].pop()
    elif fault == "source_with_dependency_status":
        p["premises"][0]["required_status"] = "supported"
    else:
        p["premises"][0]["proposition"] = " "
    with pytest.raises(ValueError):
        validate(data, c, checklist)


@pytest.mark.parametrize(
    "fault",
    [
        "unknown",
        "self",
        "cycle",
        "wrong_required_status",
        "missing_required_status",
        "dependency_with_source",
        "dependency_with_proposition",
        "unverified_required_fact",
    ],
)
def test_canonical_claim_dependencies_cannot_be_missing_cyclic_or_unverified_for_known_truth(fault):
    c, checklist, data = observation_fixture()
    first, second = data["factual_claims"]
    dep = second["proof"]["premises"][1]
    if fault == "unknown":
        dep["depends_on_claim_id"] = "missing"
    elif fault == "self":
        dep["depends_on_claim_id"] = "complete"
    elif fault == "cycle":
        first["proof"] = proof(dependency("back", "complete", "contradicted"))
    elif fault == "wrong_required_status":
        dep["required_status"] = "contradicted"
    elif fault == "missing_required_status":
        dep["required_status"] = None
    elif fault == "dependency_with_source":
        dep["evidence"] = first["dialogue_evidence"]
    elif fault == "dependency_with_proposition":
        dep["proposition"] = "A duplicated dependency proposition"
    else:
        first.update(status="unverified", proof=None, dialogue_evidence=[])
    with pytest.raises(ValueError):
        validate(data, c, checklist)


@pytest.mark.parametrize("scope", ["system_record", "private_record"])
def test_transitive_client_premise_cannot_be_laundered_as_system_or_private_record(scope):
    c, checklist, data = observation_fixture()
    claim = data["factual_claims"][1]
    if scope == "system_record":
        claim["observation_scope"] = scope
    else:
        claim.update(verification_scope=scope, evidence_kind="account_state")
    with pytest.raises(ValueError, match="essential client"):
        validate(data, c, checklist)


def test_unverified_dependency_can_remain_explicitly_unverified_without_fabricated_sources():
    c, checklist, data = observation_fixture()
    first, second = data["factual_claims"]
    first.update(
        status="unverified",
        proof=None,
        dialogue_evidence=[],
        observation_scope="none",
        supported_proposition=None,
    )
    second.update(status="unverified", dialogue_evidence=second["dialogue_evidence"][:1])
    validate(data, c, checklist)


def test_operator_promise_is_observable_commitment_but_cannot_prove_completed_action():
    c, checklist, data = observation_fixture()
    promise = data["factual_claims"][0]
    c.messages[-1].text = "I will investigate. The task is complete."
    selected = evidence("m4", "I will investigate.")
    promise.update(
        claim="The operator promises to investigate.",
        operator_evidence=[selected],
        evidence_kind="workflow_commitment",
        verification_scope="commitment",
        observation_scope="none",
        dialogue_evidence=[],
        proof=proof(source_premise("said", dialogue=[selected])),
    )
    data["assertion_groups"][0]["operator_evidence"] = [evidence("m4", c.messages[-1].text)]
    completed = data["factual_claims"][1]
    completed.update(
        operator_evidence=[evidence("m4", "The task is complete.")],
        dialogue_evidence=[],
        status="supported",
        proof=proof(dependency("only-promise", "later")),
    )
    with pytest.raises(ValueError, match="commitments cannot prove"):
        validate(data, c, checklist)
    data["factual_claims"] = [promise]
    data["assertion_groups"][0].update(composition="atomic", claim_ids=["later"])
    promise["assessment"]["impacts"][0]["fixed_claim_ids"] = []
    validate(data, c, checklist)


def corrected_fixture():
    """Separately authored v3 audit of the unchanged frozen07 source, not a replay promotion."""
    case = next(c for c in load_cases(ROOT / "evals/fresh-repeat-v1.jsonl") if c.id == "frv1-07")
    c, checklist = case.conversation, load_checklist(ROOT / "checklists/freedom-reviewed-015.json")
    m = {x.id: x for x in c.messages}
    ref = c.references[0]
    specs = [
        (
            "route",
            "The stated app route submits a change request.",
            "m2",
            "Откройте Меню",
            "supported",
            "Eligible trading accounts beginning with 7",
        ),
        (
            "old",
            "Confirm executes the change immediately without review.",
            "m2",
            "Это сразу исполняет",
            "contradicted",
            "Confirm sends it for checking; execution follows review.",
        ),
        (
            "review",
            "Confirm submits for review and execution follows review.",
            "m6",
            "«Подтвердить» только",
            "supported",
            "Confirm sends it for checking; execution follows review.",
        ),
        (
            "deadline",
            "The supplied guide gives no review deadline.",
            "m6",
            "Срок проверки",
            "supported",
            "The guide gives no review/unlock deadline.",
        ),
    ]
    atoms = []
    for cid, statement, mid, _, status, source in specs:
        quote = source if source in ref.text else ref.text
        cite = {"reference_id": ref.id, "quote": quote}
        a = atom(
            cid,
            statement,
            evidence(mid, m[mid].text),
            status=status,
            scope="policy",
            observation="none",
            references=[cite],
            claim_proof=proof(source_premise("source", references=[cite])),
            fixed=[item[0] for item in specs if item[0] != cid],
            group="initial" if mid == "m2" else "final",
        )
        a["evidence_kind"] = "product_fact"
        a["assessment"]["impacts"][0]["rule_quote"] = next(
            x.instruction for x in checklist.criteria if x.id == "consultation"
        )
        if cid == "deadline":
            a["assessment"]["impacts"][0]["when_false"]["answer"] = "15"
        if cid == "old":
            a["assessment"].update(
                lifecycle="corrected",
                correction={
                    "operator_evidence": [evidence("m6", m["m6"].text)],
                    "outcome_evidence": [
                        evidence("m7", "Новый адрес после отправки заявки нигде не использовал.")
                    ],
                    "reference_evidence": [cite],
                    "remaining_consequence": "none_established",
                    "explanation": "Source-backed explicit correction, with no downstream use established.",
                },
            )
            a["assessment"]["impacts"][0]["when_false"]["answer"] = "20"
        atoms.append(a)
    judgments = [
        {
            "criterion_id": e.criterion_id,
            "status": e.status,
            "answer": e.answer,
            "explanation": e.rationale,
            "evidence": [],
            "counterevidence": [],
            "checked_message_ids": list(m),
            "uncertainty": e.rationale if e.status == "needs_review" else None,
        }
        for e in case.expectations
    ]
    deductions = [
        {
            "criterion_id": cid,
            "rule_quote": next(x.instruction for x in checklist.criteria if x.id == cid),
            "defect": defect,
            "evidence": [],
            "checked_message_ids": list(m),
            "overlap_note": "Independently required conduct deduction remains.",
        }
        for cid, defect in [
            ("contact", "First response lacks operator introduction."),
            ("management", "Unannounced hold."),
        ]
    ]
    data = {
        "judgments": judgments,
        "request_coverage": [],
        "scope_notes": [],
        "factual_claims": atoms,
        "deductions": deductions,
        "semantic_audit": {"version": "coverage-v3", "reviewed_message_ids": [], "exclusions": []},
        "assertion_groups": [
            {
                "group_id": "initial",
                "composition": "all_of",
                "operator_evidence": [evidence("m2", m["m2"].text)],
                "claim_ids": ["route", "old"],
            },
            {
                "group_id": "final",
                "composition": "all_of",
                "operator_evidence": [evidence("m6", m["m6"].text)],
                "claim_ids": ["review", "deadline"],
            },
        ],
    }
    return c, checklist, data


def test_atomic_corrected_advice_keeps_frozen_grade_and_real_contact_hold_deductions():
    c, checklist, data = corrected_fixture()
    result = validate(data, c, checklist)
    assert calculate_score(result, checklist)["total"] == 77.69
    assert {d.criterion_id for d in result.deductions} == {"contact", "management"}
    assert (
        next(f for f in result.factual_claims if f.claim_id == "deadline")
        .assessment.impacts[0]
        .when_false.answer
        == "15"
    )
    assert next(f for f in result.factual_claims if f.claim_id == "old").assessment.lifecycle == "corrected"


@pytest.mark.parametrize("version", [None, "coverage-v1", "coverage-v2"])
def test_historical_validation_is_inert_and_does_not_reinterpret_legacy_compound_claims(version):
    c, checklist, data = corrected_fixture()
    data["semantic_audit"] = (
        None if version is None else {"version": version, "reviewed_message_ids": [], "exclusions": []}
    )
    data.pop("assertion_groups")
    for claim in data["factual_claims"]:
        for field in ["claim_id", "assertion_group_id", "proof"]:
            claim.pop(field)
        for item in claim["assessment"]["impacts"]:
            item.pop("fixed_claim_ids")
    result = validate(data, c, checklist)
    assert calculate_score(result, checklist)["total"] == 77.69


def test_proofless_known_claim_and_unverified_claim_with_unexplained_proof_sources_are_rejected():
    c, checklist, data = observation_fixture()
    for status in ["supported", "contradicted", "unverified"]:
        changed = deepcopy(data)
        changed["factual_claims"][0].update(status=status, proof=None)
        with pytest.raises(ValueError, match="proof=null"):
            validate(changed, c, checklist)


@pytest.mark.parametrize(
    "fault", ["unknown_reference", "nonverbatim", "wrong_scope", "expired", "unverified_wrong_scope"]
)
def test_source_premises_require_actual_applicable_references_even_for_unverified_claims(fault):
    c, checklist, data = corrected_fixture()
    claim = data["factual_claims"][0]
    citation = claim["proof"]["premises"][0]["reference_evidence"][0]
    if fault == "unknown_reference":
        citation["reference_id"] = "not-in-supplied-source"
    elif fault == "nonverbatim":
        citation["quote"] = "This invented quote cannot be a proof premise."
    elif fault in {"wrong_scope", "unverified_wrong_scope"}:
        c.references[0].scope = "another-entity"
        if fault == "unverified_wrong_scope":
            claim["status"] = "unverified"
    else:
        c.references[0].date_basis = "policy_validity"
        c.references[0].snapshot_on = None
        c.references[0].valid_until = "2026-11-06"
    with pytest.raises(ValueError, match="applicable reference"):
        validate(data, c, checklist)


def rule_fixture():
    c, checklist, data = observation_fixture()
    c.messages[-1].text = "The criterion requires correct complete advice."
    operator = evidence("m4", c.messages[-1].text)
    rule = {"criterion_id": "consultation", "quote": checklist.criteria[0].instruction}
    claim = atom(
        "rule",
        "The criterion requires correct complete advice.",
        operator,
        claim_proof=proof(source_premise("rule-source", rules=[rule])),
        scope="grading_rule",
        observation="none",
    )
    claim.update(evidence_kind="grading_rule", rule_evidence=[rule])
    data["factual_claims"] = [claim]
    data["assertion_groups"] = [
        {"group_id": "g", "composition": "atomic", "operator_evidence": [operator], "claim_ids": ["rule"]}
    ]
    return c, checklist, data


def test_supplied_grading_rule_can_prove_its_normative_claim_without_product_policy_invention():
    c, checklist, data = rule_fixture()
    validate(data, c, checklist)


@pytest.mark.parametrize("fault", ["unknown_rule", "nonverbatim_rule", "product_truth_from_rule"])
def test_rule_premises_cannot_supply_unrelated_or_product_fact_truth(fault):
    c, checklist, data = rule_fixture()
    claim = data["factual_claims"][0]
    rule = claim["proof"]["premises"][0]["rule_evidence"][0]
    if fault == "unknown_rule":
        rule["criterion_id"] = "not-configured"
    elif fault == "nonverbatim_rule":
        rule["quote"] = "Always award maximum points."
    else:
        claim.update(evidence_kind="product_fact", verification_scope="policy")
    with pytest.raises(ValueError, match="rule"):
        validate(data, c, checklist)


def test_group_truth_never_promotes_unknown_atom_or_empty_group_to_all_supported():
    c, checklist, data = observation_fixture()
    data["factual_claims"][1].update(
        status="unverified",
        proof=None,
        dialogue_evidence=[],
        observation_scope="none",
        supported_proposition=None,
    )
    result = validate(data, c, checklist)
    index = {claim.claim_id: claim for claim in result.factual_claims}
    assert assertion_group_status(result.assertion_groups[0], index) == "unverified"
    result.assertion_groups[0].claim_ids = []
    with pytest.raises(ValueError, match="empty assertion group"):
        assertion_group_status(result.assertion_groups[0], index)


def test_group_cannot_receive_a_shared_counterfactual_or_hide_mixed_truth_under_one_grade_branch():
    c, checklist, data = observation_fixture()
    data["assertion_groups"][0]["impacts"] = [impact()]
    with pytest.raises(ValueError, match="Extra inputs"):
        validate(data, c, checklist)


def test_known_false_atom_keeps_declared_conjunction_false_even_with_another_unknown_atom():
    c, checklist, data = observation_fixture()
    data["factual_claims"][0].update(
        status="unverified",
        proof=None,
        dialogue_evidence=[],
        observation_scope="none",
        supported_proposition=None,
    )
    # The second atom can no longer claim a proved falsity through this now
    # unknown dependency, so give it the two explicit independent source leaves.
    second = data["factual_claims"][1]
    after = evidence("m3", c.messages[2].text)
    second["proof"]["premises"][1] = source_premise(
        "no-later-action", proposition="No later client action occurred.", dialogue=[after]
    )
    result = validate(data, c, checklist)
    index = {claim.claim_id: claim for claim in result.factual_claims}
    assert assertion_group_status(result.assertion_groups[0], index) == "contradicted"


@pytest.mark.parametrize(
    "fault",
    ["empty_group_links", "blank_group_id", "duplicate_group_id", "blank_claim_id", "duplicate_premise_id"],
)
def test_group_and_proof_identifiers_are_nonempty_unique_canonical_links(fault):
    c, checklist, data = observation_fixture()
    if fault == "empty_group_links":
        data["assertion_groups"][0]["claim_ids"] = []
    elif fault == "blank_group_id":
        data["assertion_groups"][0]["group_id"] = " "
    elif fault == "duplicate_group_id":
        data["assertion_groups"].append(deepcopy(data["assertion_groups"][0]))
    elif fault == "blank_claim_id":
        data["factual_claims"][0]["claim_id"] = " "
    else:
        data["factual_claims"][1]["proof"]["premises"][1]["premise_id"] = "initial-state"
    with pytest.raises(ValueError):
        validate(data, c, checklist)


@pytest.mark.parametrize("private", [False, True])
@pytest.mark.parametrize("audited", [False, True])
def test_client_truth_cannot_be_hidden_behind_a_supported_dependency_alias(private, audited):
    c, checklist, data = observation_fixture()
    c.messages[1].text = "I downloaded and opened the sample PDF."
    c.messages[-1].text = "The sample PDF was opened. The account record was updated."
    client = evidence("m2", c.messages[1].text)
    operator = evidence("m4", c.messages[-1].text)
    observed = atom(
        "session",
        "The sample PDF was opened.",
        operator,
        dialogue=[client],
        observation="task_completed",
        fixed=["account"],
        claim_proof=proof(source_premise("observed", dialogue=[client])),
    )
    parent = atom(
        "account",
        "The account record was updated.",
        operator,
        dialogue=[client],
        observation="system_record",
        fixed=["session"],
        claim_proof=proof(dependency("indirect-client-proof", "session")),
    )
    if private:
        parent.update(evidence_kind="account_state", verification_scope="private_record")
    data["factual_claims"] = [observed, parent]
    data["judgments"][0]["evidence"] = [operator]
    data["assertion_groups"][0].update(operator_evidence=[operator], claim_ids=["session", "account"])
    if audited:
        attach_source_audit(data, c, checklist)
    with pytest.raises(ValueError, match="essential client premises"):
        validate(data, c, checklist)


def attach_source_audit(data, conversation, checklist, overrides=None):
    """Select real catalog entries for helper tests, without a provider client."""
    catalog = build_catalog(conversation, checklist)
    selections = {}

    def pointer(parts):
        return "".join("/" + str(part).replace("~", "~0").replace("/", "~1") for part in parts)

    def select(parts, kind, source_id, quote):
        found = next(
            span.span_id
            for span in catalog.entries.values()
            if span.kind == kind and span.source_id == source_id and span.quote == quote
        )
        selections[pointer(parts)] = found

    def walk(value, path=()):
        if isinstance(value, list):
            for i, item in enumerate(value):
                walk(item, (*path, i))
        elif isinstance(value, dict):
            if "quote" in value:
                for field, kind in [
                    ("message_id", "dialogue"),
                    ("reference_id", "reference"),
                    ("criterion_id", "rule"),
                ]:
                    if field in value:
                        select(path, kind, value[field], value["quote"])
                        break
            for key, item in value.items():
                if key == "source_citations":
                    continue
                if key == "rule_quote":
                    select((*path, key), "rule", value["criterion_id"], item)
                else:
                    walk(item, (*path, key))

    walk(data)
    selections.update(overrides or {})
    data["source_citations"] = {
        "version": "source-spans-v1",
        "catalog_fingerprint": catalog.fingerprint,
        "selections": selections,
        "spans": {
            sid: {
                field: getattr(catalog.entries[sid], field)
                for field in ["kind", "source_id", "field", "role", "start", "end"]
            }
            for sid in set(selections.values())
        },
    }
    return catalog


def repeated_span_fixture():
    c, checklist, data = observation_fixture()
    c.messages[1].text = "Confirmed.\nConfirmed.\nConfirmed."
    c.messages[-1].text = "The source repeats the confirmation."
    operator = evidence("m4", c.messages[-1].text)
    repeated = [evidence("m2", "Confirmed."), evidence("m2", "Confirmed.")]
    claim = atom(
        "confirmed",
        "The source repeats the confirmation.",
        operator,
        dialogue=repeated,
        observation="task_completed",
        claim_proof=proof(source_premise("repeated", dialogue=repeated)),
    )
    data["factual_claims"] = [claim]
    data["judgments"][0].update(answer="20", evidence=[operator])
    data["assertion_groups"] = [
        {
            "group_id": "g",
            "composition": "atomic",
            "operator_evidence": [operator],
            "claim_ids": ["confirmed"],
        }
    ]
    catalog = build_catalog(c, checklist)
    repeated_ids = [
        span.span_id
        for span in catalog.entries.values()
        if span.kind == "dialogue" and span.source_id == "m2" and span.quote == "Confirmed."
    ]
    assert len(repeated_ids) == 3
    overrides = {}
    for i, sid in enumerate(repeated_ids[:2]):
        overrides[f"/factual_claims/0/dialogue_evidence/{i}"] = sid
        overrides[f"/factual_claims/0/proof/premises/0/evidence/{i}"] = sid
    attach_source_audit(data, c, checklist, overrides)
    return c, checklist, data, repeated_ids


def select_audited_span(data, conversation, checklist, pointer, span_id):
    catalog = build_catalog(conversation, checklist)
    audit = data["source_citations"]
    assert audit["catalog_fingerprint"] == catalog.fingerprint
    audit["selections"][pointer] = span_id
    audit["spans"] = {
        sid: {
            field: getattr(catalog.entries[sid], field)
            for field in ["kind", "source_id", "field", "role", "start", "end"]
        }
        for sid in set(audit["selections"].values())
    }


def test_distinct_same_text_offsets_are_distinct_proof_leaves_and_flat_sources():
    c, checklist, data, selected = repeated_span_fixture()
    result = validate(data, c, checklist)
    assert result.factual_claims[0].dialogue_evidence[0] == result.factual_claims[0].dialogue_evidence[1]
    assert selected[0] != selected[1]
    assert calculate_score(result, checklist)["total"] == 100


@pytest.mark.parametrize("field", ["dialogue_evidence", "proof/premises/0/evidence"])
def test_selecting_same_span_twice_is_still_a_duplicate_citation(field):
    c, checklist, data, ids = repeated_span_fixture()
    select_audited_span(data, c, checklist, f"/factual_claims/0/{field}/1", ids[0])
    with pytest.raises(ValueError, match="duplicate"):
        validate(data, c, checklist)


def test_equal_text_at_another_offset_cannot_replace_an_essential_proof_leaf():
    c, checklist, data, ids = repeated_span_fixture()
    select_audited_span(data, c, checklist, "/factual_claims/0/dialogue_evidence/1", ids[2])
    with pytest.raises(ValueError, match="exact union"):
        validate(data, c, checklist)


@pytest.mark.parametrize(
    "path", ["/factual_claims/0/dialogue_evidence/0", "/factual_claims/0/proof/premises/0/evidence/0"]
)
def test_present_source_audit_never_falls_back_to_quote_equality_when_selection_is_missing(path):
    c, checklist, data, _ = repeated_span_fixture()
    data["source_citations"]["selections"].pop(path)
    with pytest.raises(ValueError, match="selected source-span provenance"):
        validate(data, c, checklist)


def audited_commitment_fixture():
    c, checklist, data = observation_fixture()
    c.messages[-1].text = "I will investigate.\nI will investigate."
    operator = evidence("m4", "I will investigate.")
    claim = atom(
        "promise",
        "The operator promises to investigate.",
        operator,
        scope="commitment",
        observation="none",
        claim_proof=proof(source_premise("said", dialogue=[operator])),
    )
    claim["evidence_kind"] = "workflow_commitment"
    data["factual_claims"] = [claim]
    data["judgments"][0].update(answer="20", evidence=[operator])
    data["assertion_groups"] = [
        {
            "group_id": "g",
            "composition": "atomic",
            "operator_evidence": [evidence("m4", c.messages[-1].text)],
            "claim_ids": ["promise"],
        }
    ]
    catalog = attach_source_audit(data, c, checklist)
    choices = [
        span.span_id
        for span in catalog.entries.values()
        if span.kind == "dialogue" and span.source_id == "m4" and span.quote == "I will investigate."
    ]
    assert len(choices) == 2
    return c, checklist, data, choices


def test_commitment_proof_uses_the_same_selected_operator_occurrence_as_its_assertion():
    c, checklist, data, choices = audited_commitment_fixture()
    select_audited_span(data, c, checklist, "/factual_claims/0/operator_evidence/0", choices[1])
    select_audited_span(data, c, checklist, "/factual_claims/0/proof/premises/0/evidence/0", choices[1])
    validate(data, c, checklist)
    select_audited_span(data, c, checklist, "/factual_claims/0/proof/premises/0/evidence/0", choices[0])
    with pytest.raises(ValueError, match="Operator commitments cannot prove"):
        validate(data, c, checklist)


def test_commitment_assertion_selection_cannot_fall_back_to_equal_quote_without_provenance():
    c, checklist, data, _ = audited_commitment_fixture()
    data["source_citations"]["selections"].pop("/factual_claims/0/operator_evidence/0")
    with pytest.raises(ValueError, match="selected source-span provenance"):
        validate(data, c, checklist)
