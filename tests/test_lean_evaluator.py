"""Fictional fixtures, independent of every authored/frozen evaluation case."""

import json
from copy import deepcopy

import pytest
from jsonschema import ValidationError

from cqa.models import Checklist, Conversation
from cqa.source_spans import build_catalog
from experiments.lean_evaluator import (
    CONTRACT,
    PROMPT_VERSION,
    common_view,
    decode,
    prepare,
    score,
)


@pytest.fixture
def case():
    conversation = Conversation.model_validate({
        "id": "fictional-do-not-expose-label", "channel": "agent chat", "language": "en",
        "occurred_on": "2026-02-03", "knowledge_scope": "fictional-print-shop",
        "messages": [
            {"id": "a", "timestamp": "09:00", "speaker": "client",
             "text": "Earlier export succeeded. Is the print fee eight?"},
            {"id": "b", "timestamp": "09:01", "speaker": "operator",
             "text": "Export succeeded. Print costs eight. Balance is ninety. I will check the job."},
            {"id": "c", "timestamp": "09:02", "speaker": "system",
             "text": "Job 42 is queued; printing is not completed."},
            {"id": "d", "timestamp": "09:03", "speaker": "client",
             "text": "Export worked earlier; printing is still waiting. When will it finish?"},
        ],
        "references": [{"id": "price", "text": "The print fee is three.",
                        "provenance": "fictional official price card", "scope": "fictional-print-shop",
                        "valid_from": "2026-01-01", "valid_until": "2026-12-31"}],
    })
    checklist = Checklist.model_validate({
        "id": "fictional-rubric", "version": "1", "title": "Print shop", "instructions": [],
        "criteria": [
            {"id": "accuracy", "title": "Accuracy", "instruction": "Deduct for material wrong price advice.",
             "kind": "binary", "weight": 3, "levels": [
                 {"value": "yes", "fraction": 1, "description": "No wrong advice."},
                 {"value": "no", "fraction": 0, "description": "Wrong advice."}]},
            {"id": "answers", "title": "Answers", "instruction": "Answer all material questions.",
             "kind": "binary", "weight": 1, "levels": [
                 {"value": "yes", "fraction": 1, "description": "Every question answered."},
                 {"value": "no", "fraction": 0, "description": "A question omitted."}]},
            {"id": "serious", "title": "Threat", "instruction": "Flag threats.",
             "kind": "flag", "weight": 0, "levels": [
                 {"value": "yes", "fraction": 1, "description": "Threat present."},
                 {"value": "no", "fraction": 0, "description": "No threat."}]},
        ],
    })
    catalog = build_catalog(conversation, checklist)

    def sid(kind, source_id, field=None):
        return next(s.span_id for s in catalog.entries.values()
                    if s.kind == kind and s.source_id == source_id and s.is_full
                    and (field is None or s.field == field))

    a, b, c, d = [sid("dialogue", mid) for mid in "abcd"]
    rule = {cid: sid("rule", cid, "instruction") for cid in ("accuracy", "answers", "serious")}
    price = sid("reference", "price")
    interval = {"start_message_id": "d", "end_message_id": "d", "message_ids": ["d"]}
    response = {
        "contract": CONTRACT, "catalog_fingerprint": catalog.fingerprint,
        "reviewed_message_ids": ["a", "b", "d"], "scope_notes": ["Semantic completeness needs review."],
        "judgments": [
            {"criterion_id": "accuracy", "status": "scored", "answer": "no",
             "explanation": "Eight contradicts the applicable three-unit fee; balance cannot change this failure.",
             "evidence_span_ids": [b], "counterevidence_span_ids": [a], "rule_span_id": rule["accuracy"],
             "omission": None, "uncertainty": None,
             "deduction": {"defect": "Wrong price advice.", "overlap_note": "Separate from missing finish time."}},
            {"criterion_id": "answers", "status": "scored", "answer": "no",
             "explanation": "The final finish-time question receives no later answer.",
             "evidence_span_ids": [], "counterevidence_span_ids": [b], "rule_span_id": rule["answers"],
             "omission": interval, "uncertainty": None,
             "deduction": {"defect": "Finish-time question omitted.", "overlap_note": "Separate from price truth."}},
            {"criterion_id": "serious", "status": "scored", "answer": "no",
             "explanation": "The operator does not threaten the customer.",
             "evidence_span_ids": [b], "counterevidence_span_ids": [], "rule_span_id": rule["serious"],
             "omission": None, "uncertainty": None, "deduction": None},
        ],
        "request_coverage": [
            {"request": "Print fee", "request_span_ids": [a], "status": "answered", "answer_span_ids": [b],
             "withdrawal_span_ids": [], "omission": None,
             "explanation": "The operator states eight; it is an answer with incorrect factual content."},
            {"request": "Finish time", "request_span_ids": [d], "status": "unanswered", "answer_span_ids": [],
             "withdrawal_span_ids": [], "omission": interval, "explanation": "No turn after the final question."},
        ],
        "facts": [
            {"claim": "Print fee is eight.", "criterion_ids": ["accuracy"], "operator_source_span_ids": [b],
             "kind": "policy", "status": "contradicted", "proof_source_span_ids": [price],
             "context_source_span_ids": [a], "uncertain_criterion_ids": [], "negative_interval": None,
             "correction": None, "explanation": "The applicable price card specifies three."},
            {"claim": "The earlier export succeeded.", "criterion_ids": ["accuracy"],
             "operator_source_span_ids": [b], "kind": "interaction", "status": "supported",
             "proof_source_span_ids": [a, d], "context_source_span_ids": [], "uncertain_criterion_ids": [],
             "negative_interval": None, "correction": None,
             "explanation": "Both client reports retain earlier export success, distinct from later printing."},
            {"claim": "Balance is ninety.", "criterion_ids": ["accuracy"], "operator_source_span_ids": [b],
             "kind": "private_state", "status": "unverified", "proof_source_span_ids": [],
             "context_source_span_ids": [c], "uncertain_criterion_ids": [], "negative_interval": None,
             "correction": None,
             "explanation": "Job state does not establish balance. Price error independently fixes the binary failure."},
            {"claim": "Operator will check the job.", "criterion_ids": ["answers"],
             "operator_source_span_ids": [b], "kind": "commitment", "status": "supported",
             "proof_source_span_ids": [b], "context_source_span_ids": [], "uncertain_criterion_ids": [],
             "negative_interval": None, "correction": None,
             "explanation": "Records the observable promise only, not completion or finish-time answer."},
        ],
    }
    return conversation, checklist, response, {"a": a, "b": b, "c": c, "d": d, "price": price, **rule}


def read(case, value=None):
    conversation, checklist, response, _ = case
    return decode(json.dumps(response if value is None else value), conversation, checklist)


def test_native_mixed_truth_preserves_success_and_independent_deductions(case):
    result = read(case)
    assert result.facts[1].status == "supported"
    assert result.facts[2].status == "unverified"
    assert score(result, case[1])["total"] == 0
    assert score(result, case[1])["flags"] == {"serious": "no"}
    projection = common_view(result, case[0], case[1])
    assert projection.semantic_audit is None and projection.source_citations is None
    assert projection.judgments[0].evidence[0].quote == case[0].messages[1].text


def test_prepare_full_source_view_neutral_id_and_distinct_contract(case):
    instructions, payload, schema, cap = prepare(case[0], case[1])
    value = json.loads(payload)
    assert value["conversation"]["id"] == "conversation"
    assert value["output_contract"] == CONTRACT and cap == 6000
    assert PROMPT_VERSION.startswith("lean-span-v1-")
    assert schema["additionalProperties"] is False
    parts = value["source_span_catalog"]["sources"]
    assert all(any("".join(p["text"] for p in source["parts"]) == m.text for source in parts)
               for m in case[0].messages)
    assert "cannot prove semantic" in instructions


@pytest.mark.parametrize("mutation", [
    lambda x, s: x.update(extra=True),
    lambda x, s: x["judgments"][0].update(answer="invented"),
    lambda x, s: x["judgments"][0].update(rule_span_id=s["answers"]),
    lambda x, s: x["judgments"][0].update(deduction=None),
    lambda x, s: x["judgments"][2].update(deduction={"defect": "x", "overlap_note": "y"}),
    lambda x, s: x["judgments"][0].update(evidence_span_ids=[s["price"]]),
    lambda x, s: x["judgments"][0].update(evidence_span_ids=[s["b"], s["b"]]),
    lambda x, s: x["judgments"][0].update(evidence_span_ids=["unknown"]),
    lambda x, s: x["judgments"].append(deepcopy(x["judgments"][0])),
    lambda x, s: x["reviewed_message_ids"].append("c"),
    lambda x, s: x["facts"][0].update(proof_source_span_ids=[s["b"]]),
    lambda x, s: x["facts"][1].update(proof_source_span_ids=[s["b"]]),
    lambda x, s: x["facts"][2].update(status="supported", proof_source_span_ids=[s["a"]]),
    lambda x, s: x["facts"][2].update(proof_source_span_ids=[s["c"]]),
    lambda x, s: x["facts"][2].update(uncertain_criterion_ids=["accuracy"]),
    lambda x, s: x["facts"][2].update(uncertain_criterion_ids=["answers"]),
    lambda x, s: x["facts"][0].update(status="supported", uncertain_criterion_ids=["accuracy"]),
    lambda x, s: x["facts"][3].update(status="contradicted"),
    lambda x, s: x["facts"][3].update(proof_source_span_ids=[s["accuracy"]]),
    lambda x, s: x["request_coverage"][0].update(answer_span_ids=[s["c"]]),
    lambda x, s: x["request_coverage"][0].update(answer_span_ids=[s["a"]]),
    lambda x, s: x["request_coverage"][1].update(omission=None),
    lambda x, s: x["request_coverage"][1]["omission"].update(message_ids=[]),
    lambda x, s: x["request_coverage"][1]["omission"].update(start_message_id="b"),
    lambda x, s: x["judgments"][0].update(status="needs_review", answer="no"),
    lambda x, s: x["judgments"][0].update(status="not_applicable", answer=None, deduction=None),
    lambda x, s: x["judgments"][0].update(answer="yes"),
    lambda x, s: x["facts"][0].update(status="supported", proof_source_span_ids=[]),
    lambda x, s: x["facts"][0].update(criterion_ids=["nonexistent"]),
])
def test_rejects_structural_role_authority_grade_and_omission_errors(case, mutation):
    value = deepcopy(case[2])
    mutation(value, case[3])
    with pytest.raises((ValueError, ValidationError)):
        read(case, value)


@pytest.mark.parametrize("text", ['{"contract":"lean-span-v1","contract":"lean-span-v1"}',
                                  '{"bad":NaN}', '{"bad":Infinity}'])
def test_rejects_duplicate_keys_and_nonfinite_json_before_sources(case, text):
    with pytest.raises(ValueError):
        decode(text, case[0], case[1])


def test_whole_schema_rejects_before_catalog_or_source_resolution(case, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Source resolution must not run for malformed output")

    monkeypatch.setattr("experiments.lean_evaluator.build_catalog", forbidden)
    value = deepcopy(case[2])
    value["facts"][-1]["unexpected"] = "invalid last-field shape"
    with pytest.raises(ValueError, match="Lean schema rejection at /facts/3"):
        read(case, value)


@pytest.mark.parametrize("updates", [{"scope": "other-shop"}, {"valid_until": "2026-01-02"},
                                    {"valid_from": "2026-04-01"},
                                    {"date_basis": "snapshot", "snapshot_on": "2026-02-04",
                                     "valid_from": None, "valid_until": None}])
def test_reference_applicability_not_just_citation_identity(case, updates):
    conversation, checklist, response, _ = case
    reference = conversation.references[0].model_copy(update=updates)
    revised = conversation.model_copy(update={"references": [reference]})
    value = deepcopy(response)
    value["catalog_fingerprint"] = build_catalog(revised, checklist).fingerprint
    with pytest.raises(ValueError, match="date or scope"):
        decode(json.dumps(value), revised, checklist)


def test_input_source_mutation_invalidates_catalog_binding(case):
    conversation, checklist, response, _ = case
    message = conversation.messages[1].model_copy(update={"text": "Changed source."})
    revised = conversation.model_copy(update={"messages": [conversation.messages[0], message,
                                                           *conversation.messages[2:]]})
    with pytest.raises(ValueError, match="fingerprint"):
        decode(json.dumps(response), revised, checklist)


def test_bypassed_reference_date_validation_is_rejected(case):
    conversation, checklist, response, _ = case
    reference = conversation.references[0].model_copy(update={"valid_from": "2026-99-40"})
    revised = conversation.model_copy(update={"references": [reference]})
    with pytest.raises(ValueError):
        decode(json.dumps(response), revised, checklist)


def test_grade_affecting_unknown_localizes_review(case):
    value = deepcopy(case[2])
    value["facts"][2].update(criterion_ids=["answers"], uncertain_criterion_ids=["answers"],
                            explanation="Whether the stated balance answers the second request is unresolved.")
    value["judgments"][1].update(status="needs_review", answer=None, deduction=None,
                                uncertainty="Balance truth can change the applicable answer judgment.")
    result = read(case, value)
    scoring = score(result, case[1])
    assert scoring["provisional"] and scoring["unresolved_criteria"] == ["answers"]
    assert result.judgments[0].deduction is not None


def test_known_material_false_advice_blocks_max_even_with_valid_deduction_shape(case):
    value = deepcopy(case[2])
    value["judgments"][0].update(answer="yes", deduction=None)
    with pytest.raises(ValueError, match="Material wrong advice"):
        read(case, value)


def test_exhaustive_broader_negative_requires_initial_proof_and_all_later_turns(case):
    value = deepcopy(case[2])
    fact = value["facts"][2]
    fact.update(claim="Printing is incomplete from the queued state to end.", status="supported",
                proof_source_span_ids=[case[3]["c"]], context_source_span_ids=[], uncertain_criterion_ids=[],
                negative_interval={"start_message_id": "c", "end_message_id": "d", "message_ids": ["c", "d"]})
    read(case, value)
    fact["negative_interval"]["message_ids"] = ["c"]
    with pytest.raises(ValueError, match="every source-ordered"):
        read(case, value)


def test_reversed_interval_rejected(case):
    value = deepcopy(case[2])
    value["judgments"][1]["omission"].update(start_message_id="d", end_message_id="a", message_ids=[])
    with pytest.raises(ValueError, match="reversed"):
        read(case, value)


def test_reserved_criterion_ids_are_values_and_remain_supported(case):
    conversation, checklist, response, _ = case
    data = checklist.model_dump()
    data["criteria"][0]["id"] = "__proto__"
    revised = Checklist.model_validate(data)
    value = deepcopy(response)
    value["catalog_fingerprint"] = build_catalog(conversation, revised).fingerprint
    value["judgments"][0]["criterion_id"] = "__proto__"
    for fact in value["facts"]:
        fact["criterion_ids"] = ["__proto__" if cid == "accuracy" else cid for cid in fact["criterion_ids"]]
    result = decode(json.dumps(value), conversation, revised)
    assert score(result, revised)["total"] == 0


def test_rules_verify_only_related_grading_rule_facts(case):
    value = deepcopy(case[2])
    value["facts"][2].update(kind="grading_rule", status="supported", claim="Wrong fee loses credit.",
                            context_source_span_ids=[], proof_source_span_ids=[case[3]["accuracy"]])
    read(case, value)
    value["facts"][2]["proof_source_span_ids"] = [case[3]["answers"]]
    with pytest.raises(ValueError, match="related configured rule"):
        read(case, value)


def test_max_grade_has_no_deduction_and_retains_serious_flag(case):
    value = deepcopy(case[2])
    value["facts"] = []
    value["judgments"][0].update(answer="yes", deduction=None, explanation="Fictional positive-path test.")
    value["judgments"][2].update(answer="yes", explanation="Fictional positive flag-path test.")
    result = read(case, value)
    assert score(result, case[1])["total"] == 75
    assert score(result, case[1])["flags"]["serious"] == "yes"


def test_false_consultation_can_coexist_with_independently_clear_management(case):
    conversation, checklist, response, spans = case
    data = checklist.model_dump()
    data["criteria"][1].update(id="management", title="Clear management",
                               instruction="State a clear next action; action completion is not required.")
    revised = Checklist.model_validate(data)
    value = deepcopy(response)
    value["catalog_fingerprint"] = build_catalog(conversation, revised).fingerprint
    value["judgments"][1].update(criterion_id="management", answer="yes", deduction=None, omission=None,
                                evidence_span_ids=[spans["b"]],
                                explanation="Will check the job clearly communicates the next action.")
    value["facts"][3]["criterion_ids"] = ["management"]
    result = decode(json.dumps(value), conversation, revised)
    assert result.judgments[0].answer == "no" and result.judgments[1].answer == "yes"
    assert score(result, revised)["total"] == 25


def test_correction_requires_later_independent_recovery_and_keeps_original_false_fact(case):
    conversation, checklist, response, spans = case
    data = conversation.model_dump()
    data["messages"].extend([
        {"id": "e", "timestamp": "09:04", "speaker": "operator",
         "text": "Correction: price is three. I have restored the excess five."},
        {"id": "f", "timestamp": "09:05", "speaker": "system",
         "text": "Excess five restored, no debit or remaining obligation."},
    ])
    revised = Conversation.model_validate(data)
    rubric = checklist.model_dump()
    rubric["criteria"][0]["instruction"] = (
        "Deduct for material wrong price advice unless explicitly corrected and fully restored without consequences."
    )
    checklist = Checklist.model_validate(rubric)
    catalog = build_catalog(revised, checklist)
    e, f = [next(s.span_id for s in catalog.entries.values()
                 if s.kind == "dialogue" and s.source_id == mid and s.is_full) for mid in ("e", "f")]
    value = deepcopy(response)
    value["catalog_fingerprint"] = catalog.fingerprint
    value["reviewed_message_ids"].append("e")
    for interval in (value["judgments"][1]["omission"], value["request_coverage"][1]["omission"]):
        interval.update(end_message_id="f", message_ids=["d", "e", "f"])
    value["judgments"][0].update(answer="yes", deduction=None,
                                explanation="The rubric allows full recovery after explicit correction and restoration.")
    value["facts"][0]["correction"] = {
        "correction_span_ids": [e], "recovery_span_ids": [f], "remaining_consequences": "none_established",
        "explanation": "Explicit price correction and later independent restoration; original error retained.",
    }
    result = decode(json.dumps(value), revised, checklist)
    assert result.facts[0].status == "contradicted"
    assert result.judgments[1].deduction is not None
    value["facts"][0]["correction"]["recovery_span_ids"] = [e]
    with pytest.raises(ValueError, match="wrong source role"):
        decode(json.dumps(value), revised, checklist)
    value["facts"][0]["correction"]["recovery_span_ids"] = [spans["a"]]
    with pytest.raises(ValueError, match="chronology"):
        decode(json.dumps(value), revised, checklist)
    value["facts"][0]["correction"]["recovery_span_ids"] = [f]
    value["facts"][0]["correction"]["remaining_consequences"] = "present"
    with pytest.raises(ValueError, match="wrong advice"):
        decode(json.dumps(value), revised, checklist)


def test_withdrawal_needs_later_actual_client_source(case):
    value = deepcopy(case[2])
    request = value["request_coverage"][0]
    request.update(status="withdrawn", answer_span_ids=[], withdrawal_span_ids=[case[3]["d"]])
    request["explanation"] = "Fictional structural path: later client source must actually entail withdrawal in review."
    read(case, value)
    request["withdrawal_span_ids"] = [case[3]["a"]]
    with pytest.raises(ValueError, match="follow"):
        read(case, value)


def test_cumulative_request_omission_starts_earliest_and_keeps_earlier_partial_answer(case):
    value = deepcopy(case[2])
    request = value["request_coverage"][1]
    request.update(request_span_ids=[case[3]["a"], case[3]["d"]], status="partial",
                   answer_span_ids=[case[3]["b"]],
                   omission={"start_message_id": "a", "end_message_id": "d", "message_ids": list("abcd")})
    read(case, value)
    request["omission"].update(start_message_id="d", message_ids=["d"])
    with pytest.raises(ValueError, match="linked opportunity"):
        read(case, value)
