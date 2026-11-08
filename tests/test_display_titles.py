"""Readable conversation titles are deterministic excerpts, never model output."""

import pytest

from backend.app import conversation_display_title


def conversation(*messages, channel="agent chat", language="RU"):
    return {"id": "raw-internal-id", "channel": channel, "language": language, "messages": list(messages)}


@pytest.mark.parametrize("greeting,customer_request", [
    ("Здравствуйте!", "Как получить отчёт?"),
    ("Алло, здравствуйте!", "Как получить отчёт?"),
    ("Hello!", "Can I change my phone number?"),
    ("Сәлеметсіз бе!", "Шотты қалай ашуға болады?"),
])
def test_title_uses_first_customer_request_in_its_original_language(greeting, customer_request):
    content = conversation(
        {"speaker": "system", "text": "Customer joined the chat"},
        {"speaker": "operator", "text": "Operator introduction is not the customer's request"},
        {"speaker": "client", "text": greeting},
        {"speaker": "client", "text": "[неразборчиво]"},
        {"speaker": "client", "text": f"  {customer_request}  \n"},
        {"speaker": "client", "text": "A later request"},
    )
    assert conversation_display_title(content) == customer_request


def test_title_keeps_a_request_in_the_same_message_as_a_greeting():
    content = conversation({"speaker": "client", "text": "Hello,\ncan I\tchange my card PIN?"})
    assert conversation_display_title(content) == "Hello, can I change my card PIN?"


def test_long_title_ends_at_a_word_boundary_without_changing_the_source():
    request = "Please explain how I can download the monthly account statement and transaction history for my business account without visiting a branch."
    content = conversation({"speaker": "client", "text": request})
    title = conversation_display_title(content)
    assert len(title) <= 110
    assert title.endswith("…")
    assert request.startswith(title[:-1] + " ")
    assert content["messages"][0]["text"] == request
    assert conversation_display_title(content) == title


@pytest.mark.parametrize("channel,language,expected", [
    ("voice call", "en", "Звонок на английском"),
    ("agent chat", "RU", "Чат на русском"),
    ("agent chat", "", "Чат"),
])
def test_missing_request_has_descriptive_fallback_without_an_id(channel, language, expected):
    content = conversation(
        {"speaker": "client", "text": "Hello!"},
        {"speaker": "client", "text": "[silence]"},
        {"speaker": "client", "text": "..."},
        {"speaker": "operator", "text": "An agent message"},
        channel=channel, language=language,
    )
    assert conversation_display_title(content) == expected
