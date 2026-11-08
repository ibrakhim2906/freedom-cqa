import json
from copy import deepcopy

import pytest

from cqa.assessor import (
    CONTRACT_VERSION,
    LEGACY_CONTRACT_VERSION,
    LEGACY_PROMPT_HASH,
    PROMPT_VERSION,
    V2_CONTRACT_VERSION,
    V2_PROMPT_HASH,
    decode,
    prepare,
    schema_for,
    validate_native,
)
from cqa.assessor_challenge import disagreement_ids, prepare_challenge, select_review_criteria
from cqa.models import Checklist, Conversation
from cqa.scoring import calculate_score
from cqa.source_spans import build_catalog


@pytest.fixture
def source():
    conversation = Conversation.model_validate({
        "id": "never-send-diagnostic-label", "channel": "agent chat", "language": "KZ",
        "knowledge_scope": "demo", "occurred_on": "2026-11-08",
        "messages": [
            {"id": "m1", "timestamp": "00:01", "speaker": "client", "text": "Сәлем! I cannot open the report."},
            {"id": "m2", "timestamp": "00:02", "speaker": "operator", "text": "Сәлем! I am Dana."},
            {"id": "m3", "timestamp": "00:03", "speaker": "client", "text": "Please investigate the report error."},
            {"id": "m4", "timestamp": "00:04", "speaker": "operator", "text": "I will send the error to support for investigation."},
            {"id": "m5", "timestamp": "00:05", "speaker": "system", "text": "Support request recorded."},
            {"id": "m6", "timestamp": "00:06", "speaker": "client", "text": "The report opened now."},
        ],
        "references": [{"id": "guide", "text": "Report errors may be escalated to support.",
            "provenance": "fictional test procedure", "scope": "demo", "valid_from": "2026-01-01"}],
    })
    checklist = Checklist.model_validate({"id": "custom", "version": "1", "title": "Custom checklist",
        "instructions": [], "criteria": [
            {"id": "hello/custom", "title": "Contact", "instruction": "Greet and introduce yourself.",
                "kind": "binary", "weight": 10, "levels": [
                    {"value": "present", "fraction": 1, "description": "Greeting and name present."},
                    {"value": "absent", "fraction": 0, "description": "Greeting or name missing."}]},
            {"id": "help", "title": "Help", "instruction": "Give a suitable next step; completion is not required.",
                "kind": "scale", "weight": 20, "na_condition": "No customer request.", "levels": [
                    {"value": "done", "fraction": 1, "description": "Suitable next step supplied."},
                    {"value": "partial", "fraction": .5, "description": "A material request remains unanswered."},
                    {"value": "none", "fraction": 0, "description": "No useful answer."}]},
        ]})
    return conversation, checklist


def span(conversation, checklist, kind, source_id):
    return next(s.span_id for s in build_catalog(conversation, checklist).entries.values()
                if s.kind == kind and s.source_id == source_id and s.is_full)


def wire_for(conversation, checklist, *, legacy=False):
    def decision(mid):
        return {"status": "scored", "answer": "present", "explanation": "The operator greets and names herself.",
            "evidence_span_ids": [span(conversation, checklist, "dialogue", mid)], "counterevidence_span_ids": [],
            "omission": None, "factual_basis": "not_required",
            "factual_support_span_ids": [], "missing_information": None, "review_warnings": []}
    hello, help_ = decision("m2"), decision("m4")
    help_.update(answer="done", explanation="A concrete investigation next step addresses the reported error.",
        factual_basis="observable_commitment",
        factual_support_span_ids=[span(conversation, checklist, "dialogue", "m4")],
        review_warnings=["The commitment does not establish that backend investigation is complete."])
    if legacy:
        hello["deduction"] = help_["deduction"] = None
    return {"contract_version": LEGACY_CONTRACT_VERSION if legacy else CONTRACT_VERSION,
        "catalog_fingerprint": build_catalog(conversation, checklist).fingerprint,
        "judgments": {"hello/custom": hello, "help": help_}, "scope_notes": [],
        "request_coverage": [{"request": "Investigate report error.",
            "question_span_ids": [span(conversation, checklist, "dialogue", "m3")],
            "status": "next_step", "answer_span_ids": [span(conversation, checklist, "dialogue", "m4")],
            "withdrawal_span_ids": [], "omission": None, "explanation": "The operator promises support investigation."}]}


def test_compact_assessment_preserves_sources_custom_labels_and_nonblocking_warning(source):
    conversation, checklist = source
    instructions, payload, schema, cap = prepare(conversation, checklist)
    payload = json.loads(payload)
    assert payload["conversation"]["id"] == "conversation"
    assert "never-send-diagnostic-label" not in json.dumps(payload)
    assert cap == 6000 and "backend" in instructions
    assert schema["properties"]["judgments"]["required"] == ["hello/custom", "help"]
    reconstructed = {s["span_id"]: "".join(p["text"] for p in s["parts"])
                     for s in payload["source_span_catalog"]["sources"]}
    for message in payload["conversation"]["messages"]:
        original = next(m for m in conversation.messages if m.id == message["id"])
        assert reconstructed[message["text"]["source_span_id"]] == original.text
    result = decode(json.dumps(wire_for(*source)), *source)
    assert calculate_score(result.evaluation, checklist)["total"] == 100
    assert result.evaluation.judgments[0].evidence[0].quote == "Сәлем! I am Dana."
    assert result.native["criteria"]["help"]["review_warnings"]
    assert result.evaluation.semantic_audit is None
    assert validate_native(result.native, *source).evaluation == result.evaluation


def test_grade_changing_unknown_remains_review_but_other_criterion_scores(source):
    wire = wire_for(*source)
    wire["contract_version"] = V2_CONTRACT_VERSION
    item = wire["judgments"]["help"]
    item.update(status="needs_review", answer=None, factual_basis="unverified", factual_support_span_ids=[],
                missing_information="Whether the stated guaranteed completion time is valid.")
    result = decode(json.dumps(wire), *source)
    assert result.evaluation.judgments[0].answer == "present"
    assert calculate_score(result.evaluation, source[1])["total"] is None
    item.update(status="scored", answer="done")
    with pytest.raises(ValueError, match="Grade-changing"):
        decode(json.dumps(wire), *source)


@pytest.mark.parametrize(("basis", "source_id"), [("observed_interaction", "m4"), ("private_record", "m6")])
def test_operator_promise_and_client_report_cannot_become_independent_private_truth(source, basis, source_id):
    wire = wire_for(*source)
    wire["judgments"]["help"].update(factual_basis=basis,
        factual_support_span_ids=[span(*source, "dialogue", source_id)])
    with pytest.raises(ValueError, match="wrong source role"):
        decode(json.dumps(wire), *source)


def test_mixed_support_keeps_operator_conduct_alongside_independent_support(source):
    wire = wire_for(*source)
    item = wire["judgments"]["help"]
    item.update(factual_basis="mixed_sources", factual_support_span_ids=[
        span(*source, "reference", "guide"), span(*source, "dialogue", "m4"),
        span(*source, "dialogue", "m5")])
    result = decode(json.dumps(wire), *source)
    assert result.evaluation.judgments[1].answer == "done"
    assert {e["message_id"] for e in result.native["criteria"]["help"]["factual_dialogue_evidence"]} == {"m4", "m5"}
    wire["contract_version"] = V2_CONTRACT_VERSION
    with pytest.raises(ValueError, match="wrong source role"):
        decode(json.dumps(wire), *source)


def test_operator_claim_and_policy_alone_do_not_establish_independent_mixed_support(source):
    wire = wire_for(*source)
    wire["judgments"]["help"].update(factual_basis="mixed_sources", factual_support_span_ids=[
        span(*source, "reference", "guide"), span(*source, "dialogue", "m4")])
    with pytest.raises(ValueError, match="independent client/system"):
        decode(json.dumps(wire), *source)


def test_reference_verification_keeps_scope_and_date_checks(source):
    conversation, checklist = source
    wire = wire_for(*source)
    wire["judgments"]["help"].update(factual_basis="policy_reference",
        factual_support_span_ids=[span(*source, "reference", "guide")])
    result = decode(json.dumps(wire), *source)
    assert result.native["criteria"]["help"]["reference_evidence"][0]["reference_id"] == "guide"
    changed = conversation.model_copy(update={"knowledge_scope": "another"})
    wire["catalog_fingerprint"] = build_catalog(changed, checklist).fingerprint
    with pytest.raises(ValueError, match="not applicable"):
        decode(json.dumps(wire), changed, checklist)
    with pytest.raises(ValueError, match="schema rejection"):
        decode(json.dumps(wire_for(*source)), changed, checklist)


def test_real_omission_deduction_is_preserved_with_complete_request_interval(source):
    wire = wire_for(*source)
    item = wire["judgments"]["help"]
    item.update(answer="partial", factual_basis="not_required", factual_support_span_ids=[],
        explanation="A separate material request is still unanswered.",
        omission={"start_message_id": "m3", "end_message_id": "m6"})
    request = wire["request_coverage"][0]
    request.update(status="partial", omission={"start_message_id": "m3", "end_message_id": "m6"})
    result = decode(json.dumps(wire), *source)
    assert calculate_score(result.evaluation, source[1])["total"] == 66.67
    assert result.evaluation.deductions[0].criterion_id == "help"
    assert result.evaluation.deductions[0].defect == item["explanation"]
    assert result.evaluation.deductions[0].rule_quote == source[1].criteria[1].instruction
    request["omission"]["end_message_id"] = "m4"
    with pytest.raises(ValueError, match="through the final message"):
        decode(json.dumps(wire), *source)


def test_v2_binary_failure_derives_deduction_without_accepting_failed_v1(source):
    conversation, checklist = source
    raw = conversation.model_dump()
    raw["messages"][1]["text"] = "Сәлем!"
    conversation = Conversation.model_validate(raw)
    wire = wire_for(conversation, checklist)
    wire["contract_version"] = V2_CONTRACT_VERSION
    item = wire["judgments"]["hello/custom"]
    item.update(answer="absent", explanation="The operator greets but does not introduce herself.")
    result = decode(json.dumps(wire), conversation, checklist)
    assert calculate_score(result.evaluation, checklist)["total"] == 66.67
    assert result.evaluation.deductions[0].defect == item["explanation"]
    assert result.native["criteria"]["hello/custom"]["deduction_origin"] == "criterion_explanation_projection"
    legacy = wire_for(conversation, checklist, legacy=True)
    assert decode(json.dumps(legacy), conversation, checklist).native["contract_version"] == LEGACY_CONTRACT_VERSION
    legacy["judgments"]["hello/custom"].update(answer="absent", explanation=item["explanation"])
    with pytest.raises(ValueError, match="requires a deduction"):
        decode(json.dumps(legacy), conversation, checklist)
    legacy["judgments"]["hello/custom"]["deduction"] = {
        "rule_span_id": span(conversation, checklist, "rule", "help"),
        "defect": item["explanation"], "overlap_note": "Its own criterion must establish the defect."}
    with pytest.raises(ValueError, match="another criterion"):
        decode(json.dumps(legacy), conversation, checklist)


def test_schema_uses_provider_subset_and_json_object_integrity(source):
    schema = schema_for(*source)
    assert "deduction" not in schema["$defs"]
    assert all("deduction" not in d["properties"] for d in schema["properties"]["judgments"]["properties"].values())
    forbidden = {"allOf", "contains", "uniqueItems", "if", "then", "else", "default"}

    def visit(node):
        if isinstance(node, dict):
            assert not forbidden.intersection(node)
            if node.get("type") == "object":
                assert node["additionalProperties"] is False
                assert set(node["required"]) == set(node["properties"])
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)
    visit(schema)
    raw = json.dumps(wire_for(*source))
    with pytest.raises(ValueError, match="Duplicate JSON"):
        decode(raw[:-1] + ', "scope_notes": []}', *source)
    wire = json.loads(raw)
    wire["judgments"]["hello/custom"].update(status="not_applicable", answer=None)
    with pytest.raises(ValueError, match="schema rejection"):
        decode(json.dumps(wire), *source)


def test_conditional_reference_is_recorded_only_for_the_criterion_using_it(source):
    conversation, checklist = source
    raw = conversation.model_dump()
    raw["reference_context"] = {"mode": "snapshot_review", "scope": "demo", "as_of": "2026-11-08",
        "rationale": "Explicit test snapshot.", "pack_id": "test", "pack_sha256": "a" * 64}
    conversation = Conversation.model_validate(raw)
    wire = wire_for(conversation, checklist)
    wire["judgments"]["help"].update(factual_basis="policy_reference",
        factual_support_span_ids=[span(conversation, checklist, "reference", "guide")])
    result = decode(json.dumps(wire), conversation, checklist)
    assert result.native["criteria"]["help"]["uses_conditional_reference"] is True
    assert result.native["criteria"]["hello/custom"]["uses_conditional_reference"] is False
    forged = deepcopy(result.native)
    forged["criteria"]["help"]["uses_conditional_reference"] = False
    assert validate_native(forged, conversation, checklist).native["criteria"]["help"]["uses_conditional_reference"]


def test_current_prompt_respects_combined_custom_criterion_and_arbitrary_levels(source):
    conversation, checklist = source
    changed = checklist.model_dump()
    combined = changed["criteria"][1]
    combined.update(instruction="Judge clarity AND completeness together. Clear but incomplete help earns B.",
        levels=[{"value": "A", "fraction": 1, "description": "Clear and complete."},
                {"value": "B", "fraction": .75, "description": "Clear but incomplete."},
                {"value": "C", "fraction": .25, "description": "Unclear."}])
    checklist = Checklist.model_validate(changed)
    instructions, payload, schema, _ = prepare(conversation, checklist)
    assert "criteria that combine clarity, content, process or other dimensions" in instructions
    assert "Do not penalize clear wording merely because content is incomplete" not in instructions
    assert "cannot settle 10" not in instructions and "could instead require 0" not in instructions
    assert "wrong key recommendation remains a failure" not in instructions
    assert "step's appropriateness independently follows from the present blocker" in instructions
    assert "If the customer explicitly asks about the cause, retention, eligibility," in instructions
    assert "nonblocking warning only if its truth cannot change" in instructions
    assert "the first stored message alone is not necessarily the complete request" in instructions
    assert "do not invent an obstacle from a generic capability question" in instructions
    source_texts = ["".join(part["text"] for part in entry["parts"])
                    for entry in json.loads(payload)["source_span_catalog"]["sources"]]
    assert combined["instruction"] in source_texts
    assert schema["properties"]["judgments"]["properties"]["help"]["properties"]["answer"]["enum"] == [
        "A", "B", "C", None]
    assert LEGACY_PROMPT_HASH == "ca63a00b421bf2746b118db21f56d97b979bd5b5f7ffab2f39b45b87645923e9"
    assert V2_PROMPT_HASH.startswith("7284db5c62ef")
    assert PROMPT_VERSION.startswith("rubric-assessor-v3-")


def test_full_independent_review_scrutinizes_and_detects_a_confident_binary_false_pass(source):
    conversation, checklist = source
    changed = conversation.model_dump()
    changed["messages"][1]["text"] = "Сәлем!"
    conversation = Conversation.model_validate(changed)
    primary_wire = wire_for(conversation, checklist)
    primary = decode(json.dumps(primary_wire), conversation, checklist)
    ids = select_review_criteria(primary.evaluation, checklist, primary.native, max_criteria=1)
    assert ids == ["hello/custom", "help"]
    instructions, payload, schema, _ = prepare_challenge(conversation, checklist, ids)
    task = json.loads(payload)["review_task"]
    assert task == {"mode": "independent", "criterion_ids": ids}
    assert "scrutinize EVERY configured criterion, including full-credit" in instructions
    assert schema["properties"]["judgments"]["required"] == ids
    second_wire = deepcopy(primary_wire)
    second_wire["judgments"]["hello/custom"].update(answer="absent",
        explanation="The operator greeted but never gave her name.")
    second = decode(json.dumps(second_wire), conversation, checklist)
    assert disagreement_ids(primary, second, ids, conversation, checklist) == ["hello/custom"]


def test_v3_preserves_selected_numerical_level_and_visible_uncertainty_without_backporting(source):
    wire = wire_for(*source)
    item = wire["judgments"]["help"]
    item.update(answer="partial", factual_basis="unverified", factual_support_span_ids=[],
        explanation="The proposed action is useful, but a material part remains unanswered under the stated assumption.",
        missing_information="Whether the proposed next step also resolves the customer's separate access restriction.",
        review_warnings=[])
    result = decode(json.dumps(wire), *source)
    judgment = result.evaluation.judgments[1]
    assert judgment.status == "scored" and judgment.answer == "partial"
    assert judgment.uncertainty == item["missing_information"]
    assert calculate_score(result.evaluation, source[1])["total"] == 66.67
    assert result.native["assessment_mode"] == "best_supported_numeric"
    assert result.native["uncertain_criterion_ids"] == ["help"]
    assert result.native["criteria"]["help"]["requires_review"] is True
    assert item["missing_information"] in result.native["criteria"]["help"]["review_warnings"]
    assert validate_native(result.native, *source).evaluation == result.evaluation
    legacy = deepcopy(wire)
    legacy["contract_version"] = V2_CONTRACT_VERSION
    with pytest.raises(ValueError, match="Grade-changing"):
        decode(json.dumps(legacy), *source)
    item.update(status="not_applicable", answer=None)
    with pytest.raises(ValueError, match="requires a scored answer"):
        decode(json.dumps(wire), *source)


def test_v3_requires_configured_answers_including_custom_flags_and_rejects_abstention(source):
    conversation, checklist = source
    changed = checklist.model_dump()
    changed["criteria"].append({"id": "risk/custom", "title": "Risk", "instruction": "Flag the stated risk.",
        "kind": "flag", "weight": 0, "levels": [
            {"value": "escalate", "fraction": 1, "description": "Risk observed."},
            {"value": "clear", "fraction": 0, "description": "Risk not observed."}]})
    checklist = Checklist.model_validate(changed)
    wire = wire_for(conversation, checklist)
    wire["judgments"]["risk/custom"] = deepcopy(wire["judgments"]["hello/custom"])
    wire["judgments"]["risk/custom"].update(answer="escalate", explanation="The selected configured risk is observed.")
    result = decode(json.dumps(wire), conversation, checklist)
    assert calculate_score(result.evaluation, checklist)["flags"] == {"risk/custom": "escalate"}
    schema = schema_for(conversation, checklist)
    binary = schema["properties"]["judgments"]["properties"]["hello/custom"]["properties"]
    assert binary["status"]["enum"] == ["scored"]
    assert binary["answer"]["enum"] == ["present", "absent"]
    wire["judgments"]["hello/custom"].update(status="needs_review", answer=None)
    with pytest.raises(ValueError, match="schema rejection"):
        decode(json.dumps(wire), conversation, checklist)


def test_v3_same_grade_with_new_material_uncertainty_requires_review(source):
    primary = decode(json.dumps(wire_for(*source)), *source)
    second_wire = wire_for(*source)
    second_wire["judgments"]["help"].update(factual_basis="unverified", factual_support_span_ids=[],
        missing_information="Whether the stated support route accepts this type of report error.")
    second = decode(json.dumps(second_wire), *source)
    ids = [criterion.id for criterion in source[1].criteria]
    assert disagreement_ids(primary, second, ids, *source) == ["help"]
    paraphrase = deepcopy(second_wire)
    paraphrase["judgments"]["help"]["missing_information"] = "Eligibility of this error for the proposed support route."
    assert disagreement_ids(second, decode(json.dumps(paraphrase), *source), ids, *source) == []


def test_v3_reconciles_requests_before_grades_without_changing_legacy_order(source):
    instructions, _, schema, _ = prepare(*source)
    assert "request_coverage before choosing criterion grades" in instructions
    assert "made it necessary. A field that is merely common or useful" in instructions
    assert list(schema["properties"]) == schema["required"] == [
        "contract_version", "catalog_fingerprint", "request_coverage", "judgments", "scope_notes"]
    for version in [LEGACY_CONTRACT_VERSION, V2_CONTRACT_VERSION]:
        legacy = schema_for(*source, contract_version=version)
        assert list(legacy["properties"]) == legacy["required"] == [
            "contract_version", "catalog_fingerprint", "judgments", "request_coverage", "scope_notes"]


def test_v3_prior_explanation_can_support_later_confirmation_but_cannot_answer_or_withdraw_it_alone(source):
    conversation, checklist = source
    raw = conversation.model_dump()
    raw["messages"][0]["text"] = "Please cancel the previous investigation."
    raw["messages"][5]["text"] = "So you will send this report error to support?"
    raw["messages"].append({"id": "m7", "timestamp": "00:07", "speaker": "operator", "text": "Yes."})
    conversation = Conversation.model_validate(raw)
    wire = wire_for(conversation, checklist)
    request = wire["request_coverage"][0]
    request.update(request="Confirm the investigation commitment.",
        question_span_ids=[span(conversation, checklist, "dialogue", "m6")],
        answer_span_ids=[span(conversation, checklist, "dialogue", "m4"),
                         span(conversation, checklist, "dialogue", "m7")],
        explanation="The later Yes confirms the earlier explanation of the next step.")
    result = decode(json.dumps(wire), conversation, checklist)
    assert result.evaluation.request_coverage[0].answer_message_ids == ["m4", "m7"]
    for version in [LEGACY_CONTRACT_VERSION, V2_CONTRACT_VERSION]:
        legacy = deepcopy(wire)
        legacy["contract_version"] = version
        if version == LEGACY_CONTRACT_VERSION:
            for judgment in legacy["judgments"].values():
                judgment["deduction"] = None
        with pytest.raises(ValueError, match="cannot precede the request"):
            decode(json.dumps(legacy), conversation, checklist)
    request["answer_span_ids"] = [span(conversation, checklist, "dialogue", "m4")]
    with pytest.raises(ValueError, match="requires an operator response at or after"):
        decode(json.dumps(wire), conversation, checklist)
    request.update(status="withdrawn", answer_span_ids=[],
        withdrawal_span_ids=[span(conversation, checklist, "dialogue", "m1")])
    with pytest.raises(ValueError, match="cannot precede the request"):
        decode(json.dumps(wire), conversation, checklist)


def test_v3_unanswered_request_can_cite_failed_response_without_claiming_success(source):
    conversation, checklist = source
    raw = conversation.model_dump()
    raw["messages"][3]["text"] = "I will investigate the billing error instead."
    raw["messages"][4]["text"] = "A billing investigation was recorded."
    raw["messages"][5]["text"] = "The report error is still unresolved."
    conversation = Conversation.model_validate(raw)
    wire = wire_for(conversation, checklist)
    wire["judgments"]["help"].update(answer="none", factual_basis="not_required", factual_support_span_ids=[],
        explanation="The operator investigated billing instead of the requested report error.")
    request = wire["request_coverage"][0]
    request.update(status="unanswered", omission={"start_message_id": "m3", "end_message_id": "m6"},
        explanation="The linked response concerns another problem; the requested report investigation remains unaddressed.")
    result = decode(json.dumps(wire), conversation, checklist)
    assert result.evaluation.judgments[1].answer == "none"
    assert result.evaluation.request_coverage[0].status == "unanswered"
    assert result.evaluation.request_coverage[0].answer_message_ids == ["m4"]
    for version in [LEGACY_CONTRACT_VERSION, V2_CONTRACT_VERSION]:
        legacy = deepcopy(wire)
        legacy["contract_version"] = version
        if version == LEGACY_CONTRACT_VERSION:
            legacy["judgments"]["hello/custom"]["deduction"] = None
            legacy["judgments"]["help"]["deduction"] = {
                "rule_span_id": span(conversation, checklist, "rule", "help"),
                "defect": wire["judgments"]["help"]["explanation"], "overlap_note": "A distinct failure to address the request."}
        with pytest.raises(ValueError, match="cannot claim an operator answer"):
            decode(json.dumps(legacy), conversation, checklist)
    request["omission"]["end_message_id"] = "m5"
    with pytest.raises(ValueError, match="through the final message"):
        decode(json.dumps(wire), conversation, checklist)
    request.update(status="withdrawn", omission=None,
        withdrawal_span_ids=[span(conversation, checklist, "dialogue", "m6")])
    with pytest.raises(ValueError, match="cannot claim an operator answer"):
        decode(json.dumps(wire), conversation, checklist)
