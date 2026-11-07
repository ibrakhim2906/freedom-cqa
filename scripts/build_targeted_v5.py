"""Freeze policy/overlap contrasts before grader changes; no independent GT claim."""

import hashlib
import html
import json
import re

from cqa.models import Conversation, Expectation, Message, Reference, TestCase
from cqa.rubric import load_checklist
from cqa.settings import ROOT
from scripts.build_core_anchors import build


def official_references():
    specs = [
        ("support", "how-to-get-advice-on-tradernet-3808", "В мобильном приложении платформы", "3. Номер телефона"),
        ("recovery", "how-to-recover-change-tradernet-login-password-3819", "Восстановление пароля 1.", "Смена пароля"),
        ("profile", "how-can-i-update-my-data-3815", "Важно! Подать поручение на актуализацию", "Примечание:"),
    ]
    refs, manifest = [], []
    for index, (rid, slug, start, end) in enumerate(specs):
        raw = (ROOT / f"artifacts/references-v1/{index}.html").read_text(encoding="utf-8")
        plain = html.unescape(re.sub("<[^>]+>", " ", re.sub(r"<(script|style).*?</\1>", "", raw, flags=re.DOTALL)))
        plain = re.sub(r"\s+", " ", plain)
        first = plain.index(start)
        text = plain[first:plain.index(end, first)]
        ref = Reference(id=f"fbroker-{rid}-20261107", text=text,
            provenance="Official fbroker.kz platform help; fetched 2026-11-07. Snapshot scope is platform guidance, "
                       "not rates, withdrawal timing, individual account state, or all Freedom entities. "
                       "Validity window is our conservative assessment window, not an asserted legal effective date.",
            source_url=f"https://fbroker.kz/faq/question/{slug}", retrieved_on="2026-11-07",
            scope="fbroker-kz-platform", valid_from="2026-11-07", valid_until="2026-11-07")
        refs.append(ref)
        manifest.append({"id": ref.id, "source_url": ref.source_url,
                         "raw_sha256": hashlib.sha256(raw.encode()).hexdigest(),
                         "excerpt_sha256": hashlib.sha256(text.encode()).hexdigest()})
    return refs, manifest


def build_cases(refs):
    cases = []
    anchor = build()[5]
    overlap = [("consultation", "scored", "10", "A separate substantive question is unanswered."),
               ("management", "scored", "10", "Clear coherent wording; omission alone is a consultation defect."),
               ("empathy", "scored", "yes", "No expressed difficulty or dissatisfaction and no rude response.")]

    def add(cid, turns, expected, references=None, scope=None, on=None):
        cases.append(TestCase(id=cid, family=cid.rsplit("-", 1)[0], source="authored",
            label_provenance="ai_authored_provisional", tags=["targeted-v5", "frozen-before-inference"],
            conversation=Conversation(id=cid, channel="agent chat", language="EN",
                references=references if references is not None else anchor.conversation.references,
                knowledge_scope=scope, occurred_on=on,
                messages=[Message(id=f"m{i}", timestamp=f"00:{i:02}", speaker=speaker, text=text)
                          for i, (speaker, text) in enumerate(turns, 1)]),
            expectations=[Expectation(criterion_id=c, status=s, answer=a, rationale=r) for c, s, a, r in expected]))

    turns = [(m.speaker, m.text) for m in anchor.conversation.messages]
    add("overlap-omission-only", turns, overlap)
    add("overlap-confusing-wording", [turns[0],
        ("operator", "Hello, I'm Mira. Open the thing there, then select that one."),
        ("client", "Which thing and which option do you mean? Also, where do I change timezone?"),
        ("operator", "Settings > Language > Russian. Can I help with anything else? Goodbye!")],
        [("consultation", "scored", "10", "Language eventually answered, separate timezone request ignored."),
         ("management", "scored", "4", "Customer explicitly has to clarify the operator's unclear wording.")])
    add("overlap-explicit-frustration", [turns[0], turns[1],
        ("client", "That worked. Where is timezone? I am frustrated: you ignored this question twice already."), turns[3]],
        [("consultation", "scored", "10", "The explicit timezone question is unanswered."),
         ("empathy", "scored", "no", "Explicit frustration is ignored; a separately applicable empathy failure.")])

    profile = next(r for r in refs if "profile" in r.id)
    question = ("client", "In the Freedom Broker mobile platform, which section opens the personal-data change request? I only need the location, not submission steps.")
    good = ("operator", "Hello, I'm Mira. Open Menu > Instructions > Personal data > Change information. Can I help with anything else? Goodbye!")
    bad = ("operator", "Hello, I'm Mira. Use Quotes > Bonds > Buy to open the personal-data change request. Can I help with anything else? Goodbye!")
    for suffix, reply, answer in [("supported", good, "20"), ("contradicted", bad, "0")]:
        add(f"facts-profile-{suffix}", [question, reply],
            [("consultation", "scored", answer, "Assess the sole navigation question against applicable official platform help."),
             ("management", "scored", "10", "Wording is clear; factual correctness is assessed separately.")],
            [profile], "fbroker-kz-platform", "2026-11-07")
    for suffix, reference, scope, on in [
        ("wrong-scope", profile, "different-company-platform", "2026-11-07"),
        ("expired", profile, "fbroker-kz-platform", "2025-01-01"),
        ("missing", None, "fbroker-kz-platform", "2026-11-07"),
    ]:
        add(f"facts-profile-{suffix}", [question, good],
            [("consultation", "needs_review", None, "No applicable independent source or customer confirmation establishes this material route.")],
            [reference] if reference else [], scope, on)
    add("facts-withdrawal-unsupported", [
        ("client", "After updating my details, is withdrawal guaranteed to unlock in exactly 10 minutes?"),
        ("operator", "Hello, I'm Mira. Yes, exactly 10 minutes, guaranteed. Goodbye!")],
        [("consultation", "needs_review", None, "The profile source establishes no such withdrawal timing guarantee.")],
        [profile], "fbroker-kz-platform", "2026-11-07")
    return cases


if __name__ == "__main__":
    refs, manifest = official_references()
    cases = build_cases(refs)
    root = ROOT / "artifacts/benchmark/targeted-v5"
    root.mkdir(parents=True, exist_ok=True)
    with (ROOT / "references/fbroker-platform-20261107.json").open("x", encoding="utf-8") as file:
        file.write(json.dumps({"scope": "fbroker-kz-platform", "references": [r.model_dump() for r in refs],
                               "manifest": manifest}, ensure_ascii=False, indent=2) + "\n")
    with (ROOT / "evals/targeted-v5.jsonl").open("x", encoding="utf-8") as file:
        file.write("".join(c.model_dump_json() + "\n" for c in cases))
    with (root / "baseline-checklist.json").open("x", encoding="utf-8") as file:
        file.write(load_checklist().model_dump_json(indent=2) + "\n")
    print(json.dumps({"cases": len(cases), "judgments": sum(len(c.expectations) for c in cases),
                      "label_warning": "Provisional team interpretations and source-based synthetic anchors, not organizer GT."}))
