"""Fresh explicit-fact diagnostics frozen before the core workflow experiment.

AI-authored anchors are not independent Ground Truth. Partial security/request
anchors deliberately avoid pretending disputed cross-criterion effects are settled.
"""

import json

from cqa.models import Checklist, Conversation, Criterion, Expectation, Level, Message, Reference, TestCase
from cqa.rubric import load_checklist
from cqa.settings import ROOT


def build():
    policy = Reference(id="fictional-preferences-policy", provenance="Fictional test facts, not Freedom policy",
        text="In this fictional app, change interface language through Settings > Language > Russian. "
        "Appearance > Dark theme changes colors only and cannot change interface language. "
        "Language and color navigation are general preferences, not protected operator actions. "
        "Device timezone can be changed through Settings > Timezone. "
        "For the account examples, the session's account is already known and its balance is 42 units. "
        "Before an operator checks or discloses that balance, identity verification must be confirmed. "
        "A customer's claim to have completed the steps is not confirmation; the system event supplies confirmation. "
        "Generic technical support does not require identity verification.")
    full = {"contact": ("yes", "Greeting and introduction in the first human reply."),
            "needs": (None, "Requested preference is clear from the first substantive request."),
            "identity": (None, "Only generic preference navigation is requested."),
            "consultation": ("20", "Correct complete instructions according to explicit fictional policy."),
            "empathy": ("yes", "Respectful assistance; no expressed dissatisfaction or ignored objection."),
            "management": ("10", "Clear coherent wording without an explicit unannounced wait."),
            "closing": ("yes", "Offer of further help and farewell."),
            "serious": ("no", "No insult, private service, or confidential disclosure.")}
    cases = []

    def add(cid, family, turns, expected, language="EN", override=None):
        cases.append(TestCase(id=cid, family=family, source="authored", label_provenance="ai_authored_provisional",
            tags=["core_anchor_v4", "frozen_before_experiment", "full_reference" if len(expected) ==
                  len((override or load_checklist()).criteria) else "partial_anchor"],
            conversation=Conversation(id=cid, channel="agent chat", language=language, references=[policy],
                messages=[Message(id=f"m{i}", timestamp=f"00:{i:02}", speaker=role, text=text)
                          for i, (role, text) in enumerate(turns, 1)]),
            expectations=[Expectation(criterion_id=key, status="not_applicable" if value is None else "scored",
                answer=value, rationale=why) for key, (value, why) in expected.items()], checklist_override=override))

    start = ("client", "How do I change the app's interface language to Russian?")
    finish = [("client", "I have no other questions."),
              ("operator", "Can I help with anything else? Goodbye!")]
    add("core-language-supported", "language-policy", [start,
        ("operator", "Hello, I'm Mira. Open Settings > Language and choose Russian."), *finish], full)
    add("core-language-wrong", "language-policy", [start,
        ("operator", "Hello, I'm Mira. Open Appearance and choose Dark theme; that changes the interface language to Russian."),
        *finish], full | {"consultation": ("0", "The central instruction contradicts the supplied policy; politeness does not repair it.")})
    add("core-kz-bot-context", "language-policy", [
        ("client", "Қолданбаның интерфейсін орыс тіліне қалай ауыстырамын?"),
        ("bot", "Сәлеметсіз бе! Мен көмекші ботпын. Операторға қосамын."),
        ("operator", "Settings > Language бөлімінде Russian таңдаңыз."),
        ("client", "Ауысты, басқа сұрақ жоқ."),
        ("operator", "Интерфейс тілі орыс тіліне ауысты. Сау болыңыз!")],
        full | {"contact": ("no", "A bot introduction cannot supply the human greeting and self-introduction.")}, language="KZ")

    identity = [("client", "Please tell me my current account balance."),
                ("operator", "Hello, I'm Mira. Please complete identity verification before I check your balance."),
                ("client", "I completed the steps."),
                ("system", "Identity verification successfully completed."),
                ("operator", "Your balance is 42 units."),
                ("client", "No further questions."),
                ("operator", "We have checked your balance. Goodbye!")]
    add("core-confirmation-before", "verification-sequence", identity,
        {"identity": ("yes", "System confirmation precedes protected disclosure."),
         "serious": ("no", "Disclosure follows completed verification under the explicit policy.")})
    late = identity[:3] + [identity[4], identity[3]] + identity[5:]
    add("core-confirmation-after", "verification-sequence", late,
        {"identity": ("no", "Customer assertion and later confirmation cannot authorize earlier disclosure."),
         "serious": ("yes", "Protected balance disclosed before system confirmation.")})
    add("core-late-timezone", "late-request", [start,
        ("operator", "Hello, I'm Mira. Open Settings > Language and choose Russian."),
        ("client", "That worked. A separate question: where do I change the device timezone?"),
        ("operator", "Can I help with anything else? Goodbye!")],
        {"consultation": ("10", "The separate timezone question has no answer or next step; the language question is resolved.")})

    custom = Checklist(id="incident-commitment", version="fresh-v4", title="Incident follow-up contract", instructions=[], criteria=[
        Criterion(id="incident-followup", title="Concrete incident follow-up", kind="scale", weight=7,
            instruction="Assess only the human reply. Complete means a concrete incident reference AND a follow-up channel. "
                        "Partial means exactly one is present. Missing means neither. Do not invent the channel from context.",
            levels=[Level(value="complete", fraction=1, description="Reference and channel explicit."),
                    Level(value="partial", fraction=.5, description="Exactly one explicit."),
                    Level(value="missing", fraction=0, description="Neither explicit.")])])
    add("core-custom-complete", "incident-contract", [
        ("client", "The Notifications screen crashes. Please arrange technical follow-up."),
        ("operator", "Hello, I'm Mira. Incident INC-208 is open for the Notifications crash. We will send updates by email.")],
        {"incident-followup": ("complete", "Both incident reference and email channel are explicit.")}, override=custom)
    add("core-custom-partial-ru", "incident-contract", [
        ("client", "Экран уведомлений закрывается с ошибкой. Организуйте техническую проверку."),
        ("operator", "Здравствуйте, я Мира. По ошибке уведомлений открыто обращение INC-208. Мы сообщим результат.")],
        {"incident-followup": ("partial", "The incident ID is explicit; no follow-up channel is identified.")}, language="RU", override=custom)
    return cases


if __name__ == "__main__":
    cases = build()
    root = ROOT / "artifacts/benchmark/core-v4"
    root.mkdir(parents=True, exist_ok=True)
    path = ROOT / "evals/core-anchors-v4.jsonl"
    with path.open("x", encoding="utf-8") as file:
        file.write("".join(c.model_dump_json() + "\n" for c in cases))
    with (root / "checklist.json").open("x", encoding="utf-8") as file:
        file.write(load_checklist().model_dump_json(indent=2) + "\n")
    plan = {"purpose": "Fresh explicit-fact anchors; not independent Ground Truth or a hidden judge test.",
            "cases": len(cases), "declared_judgments": sum(len(c.expectations) for c in cases),
            "selection": [c.id for c in cases], "budget_cap_new_usd": 1.0,
            "withheld_labels": "Security/order cases omit disputed cross-criterion effects before any model result is seen."}
    with (root / "plan.json").open("x", encoding="utf-8") as file:
        file.write(json.dumps(plan, indent=2) + "\n")
    print(json.dumps(plan))
