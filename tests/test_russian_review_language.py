"""Preparing a Russian review must not translate source evidence or answer IDs."""

import json

import pytest

from cqa.assessor import CONTRACT_VERSION, decode, prepare
from cqa.assessor_challenge import prepare_challenge
from cqa.models import Checklist, Conversation
from cqa.source_spans import build_catalog


@pytest.fixture
def language_source():
    conversation = Conversation.model_validate({
        "id": "mixed-language-example", "channel": "agent chat", "language": "KZ",
        "messages": [
            {"id": "m1", "speaker": "client", "timestamp": "00:00", "text": "Сәлем! Where is my profile?"},
            {"id": "m2", "speaker": "operator", "timestamp": "00:01", "text": "Сәлеметсіз бе! Open Profile in the menu."},
        ],
        "references": [{"id": "guide", "text": "Profile is available in the main menu.", "provenance": "Fictional help article"}],
    })
    checklist = Checklist.model_validate({"id": "language-check", "version": "1", "title": "Check greeting",
        "instructions": [], "criteria": [{"id": "greeting", "title": "Greeting", "instruction": "Greet the customer.",
        "kind": "binary", "weight": 10, "levels": [{"value": "present", "fraction": 1, "description": "Greeting present"},
        {"value": "absent", "fraction": 0, "description": "Greeting absent"}]}]})
    return conversation, checklist


@pytest.mark.parametrize("independent", [False, True])
def test_preparation_requests_russian_but_keeps_sources_and_contract(language_source, independent):
    conversation, checklist = language_source
    arguments = prepare_challenge(conversation, checklist, ["greeting"]) if independent else prepare(conversation, checklist)
    instructions, payload_text, schema, _ = arguments
    assert "clear, natural Russian" in instructions
    assert "never translate or paraphrase a quotation" in instructions
    assert "concise English" not in instructions
    payload = json.loads(payload_text)
    sources = {source["span_id"]: "".join(part["text"] for part in source["parts"])
               for source in payload["source_span_catalog"]["sources"]}
    for original, projected in zip(conversation.messages, payload["conversation"]["messages"], strict=True):
        assert sources[projected["text"]["source_span_id"]] == original.text
    assert conversation.references[0].text in sources.values()
    criterion = schema["properties"]["judgments"]["properties"]["greeting"]
    for branch in criterion["anyOf"]:
        assert branch["properties"]["answer"]["enum"] == ["present", "absent"]
    assert payload["output_contract"] == CONTRACT_VERSION


def test_russian_explanation_decodes_with_original_kazakh_english_quote(language_source):
    conversation, checklist = language_source
    catalog = build_catalog(conversation, checklist)
    span = next(s.span_id for s in catalog.entries.values() if s.kind == "dialogue" and s.source_id == "m2" and s.is_full)
    wire = {"contract_version": CONTRACT_VERSION, "catalog_fingerprint": catalog.fingerprint,
        "judgments": {"greeting": {"status": "scored", "answer": "present", "explanation": "Оператор поздоровался с клиентом.",
            "evidence_span_ids": [span], "counterevidence_span_ids": [], "omission": None, "factual_basis": "not_required",
            "factual_support_span_ids": [], "missing_information": None, "review_warnings": []}},
        "scope_notes": [], "request_coverage": []}
    result = decode(json.dumps(wire, ensure_ascii=False), conversation, checklist)
    judgment = result.evaluation.judgments[0]
    assert judgment.explanation == "Оператор поздоровался с клиентом."
    assert judgment.answer == "present"
    assert judgment.evidence[0].quote == conversation.messages[1].text
