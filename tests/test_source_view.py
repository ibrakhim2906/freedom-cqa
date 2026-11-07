import copy
import json

import pytest

from cqa.evaluator import schema_for
from cqa.models import Checklist, Conversation
from cqa.prompt import payload_for
from cqa.source_spans import build_catalog
from cqa.source_view import project_sources


def fixture():
    conversation = Conversation.model_validate({"id": "diagnostic-id-should-not-leak", "channel": "agent chat",
        "language": "KZ", "messages": [
            {"id": "one", "speaker": "client", "timestamp": "00:00", "text": "Сәлеметсіз бе.\r\nPDF 🙂 қайда? "},
            {"id": "two", "speaker": "operator", "timestamp": "00:01", "text": "Open Documents. Then select PDF."}],
        "references": [{"id": "reference", "text": "Documents contains PDF.\r\nNo delivery deadline is specified.",
                        "provenance": "Explicit fictional source"}]})
    rubric = Checklist.model_validate({"id": "custom", "version": "1", "title": "Task", "instructions": ["Use sources."],
        "criteria": [{"id": "default", "title": "Task", "instruction": "Give correct guidance. Preserve uncertainty.",
        "kind": "binary", "weight": 1, "levels": [{"value": "yes", "fraction": 1, "description": "Task addressed."},
                                                  {"value": "no", "fraction": 0, "description": "Task not addressed."}],
        "channel_guidance": {"voice call": "Do not infer diction from a transcript."}}]})
    return conversation, rubric


def test_single_copy_view_preserves_all_characters_and_every_selectable_span():
    c, r = fixture()
    original = json.loads(payload_for(c, r, grounded=True))
    before = copy.deepcopy(original)
    catalog = build_catalog(c, r)
    projected = project_sources(original, c, r, catalog)
    assert original == before
    sources = {s["span_id"]: s for s in projected["source_span_catalog"]["sources"]}
    visible = set(sources)
    for sid, source in sources.items():
        assert "".join(part["text"] for part in source["parts"]) == catalog.entries[sid].quote
        visible.update(p["span_id"] for p in source["parts"] if p["span_id"] is not None)
    assert set(catalog.ids()) <= visible
    for message, source in zip(projected["conversation"]["messages"], c.messages, strict=True):
        sid = message["text"]["source_span_id"]
        assert catalog.entries[sid].source_id == source.id
        assert "".join(p["text"] for p in sources[sid]["parts"]) == source.text
    criterion = projected["checklist"]["criteria"][0]
    sid = criterion["instruction"]["source_span_id"]
    assert catalog.entries[sid].source_id == "default"
    assert catalog.entries[sid].quote == r.criteria[0].instruction
    assert c.id not in json.dumps(projected)
    assert projected["checklist"]["instructions"] == r.instructions


def test_source_projection_rejects_stale_source_and_does_not_use_quote_search():
    c, r = fixture()
    catalog = build_catalog(c, r)
    c.messages[0].text += "Changed."
    with pytest.raises(ValueError, match="does not match"):
        project_sources(json.loads(payload_for(c, r, grounded=True)), c, r, catalog)


@pytest.mark.parametrize("criterion_id", ["default", "title", "required", "type", "if", "properties"])
def test_configured_criterion_names_are_not_removed_as_schema_keywords(criterion_id):
    c, r = fixture()
    r.criteria[0].id = criterion_id
    wire = schema_for(c, r, grounded=True, source_contract=True)
    assert criterion_id in wire["properties"]["judgments"]["properties"]
    assert criterion_id in wire["properties"]["judgments"]["required"]
