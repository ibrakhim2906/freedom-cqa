"""Freeze fictional paired claims/corrections and original organizer regressions."""

import json

from cqa.datasets import load_cases
from cqa.models import Checklist, Conversation, Criterion, Expectation, Level, Message, Reference, TestCase
from cqa.settings import ROOT


def build():
    cases = []

    def add(cid, turns, expected, refs=(), language="EN", override=None):
        cases.append(TestCase(id=cid, family=cid.rsplit("-", 1)[0], source="authored",
            label_provenance="ai_authored_provisional", tags=["claims-v1", "paired", "fictional-policy"],
            conversation=Conversation(id=cid, channel="agent chat", language=language,
                messages=[Message(id=f"m{i}", timestamp=f"00:{i:02}", speaker=s, text=t)
                          for i, (s, t) in enumerate(turns, 1)],
                references=[Reference(id=f"r{i}", text=t, provenance="Explicit fictional test facts, not real broker policy")
                            for i, t in enumerate(refs, 1)]),
            expectations=[Expectation(criterion_id=c, status=s, answer=a, rationale=r) for c, s, a, r in expected],
            checklist_override=override))

    def scored(cid, answer, reason):
        return cid, "scored", answer, reason

    security = [("client", "Why is withdrawal blocked on my only account?"),
                ("operator", "Hello, I'm Ada. I can see your private cash balance: 420 credits."),
                ("client", "I have not verified my identity."),
                ("operator", "I cannot explain the withdrawal block or offer any next step. Goodbye.")]
    for suffix, refs in [("unknown", []), ("supported", ["Account audit snapshot: this customer's cash balance is 420 credits."])]:
        add("privacy-truth-" + suffix, security,
            [scored("identity", "no", "Private account disclosure precedes verification regardless of balance truth."),
             scored("serious", "yes", "Premature private-account disclosure remains a serious flag."),
             scored("consultation", "0", "No answer or next step for the sole withdrawal-cause request."),
             scored("management", "10", "Clear wording; no separate established process prerequisite in the source.")], refs)

    ru = [("client", "Где скачать годовой отчёт в учебном приложении?"),
          ("operator", "Здравствуйте, меня зовут Анна. Откройте Профиль > Формы."),
          ("client", "Там нет отчёта.")]
    for suffix, tail, answer in [
        ("corrected", [("operator", "Я ошиблась. Откройте Меню > Документы > Годовой отчёт."),
                       ("client", "Скачал нужный годовой отчёт, спасибо."), ("operator", "До свидания.")], "20"),
        ("unresolved", [("operator", "Используйте Профиль > Формы."),
                        ("client", "Отчёта по-прежнему нет."), ("operator", "До свидания.")], "0")]:
        add("route-recovery-" + suffix, ru + tail,
            [scored("consultation", answer, "Corrected successful outcome versus an uncorrected key wrong route."),
             scored("management", "10", "Clearly worded wrong location is not itself a communication defect.")],
            ["В учебном приложении годовой отчёт скачивается только через Меню > Документы > Годовой отчёт. В Профиль > Формы отчёта нет."], "RU")

    harm = [("client", "Where can I download my saved yearly report in this training app?"),
            ("operator", "Hello, I'm Bea. First choose Settings > Purge archive to retrieve your report.")]
    for suffix, reaction, answer in [
        ("avoided", "I did not click Purge archive. I waited for your next instruction.", "20"),
        ("incurred", "I clicked it as instructed. My saved report was permanently deleted and cannot be restored.", "0")]:
        add("correction-consequence-" + suffix, harm + [("client", reaction),
            ("operator", "That first instruction was wrong. Use Menu > Reports > Download instead."),
            ("client", "I found the Download control." + (" The saved report is still gone." if suffix == "incurred"
                                                        else " I downloaded the saved yearly report successfully.")),
            ("operator", "Goodbye.")],
            [scored("consultation", answer, "A correction does not erase irreversible consequences of key wrong advice."),
             scored("management", "10", "The harmful content does not itself establish unclear wording.")],
            ["Training app: Menu > Reports > Download retrieves saved reports. Settings > Purge archive permanently deletes saved reports and is never a retrieval step."])

    for suffix, refs, status, answer in [
        ("unknown", [], "needs_review", None),
        ("contradicted", ["In this fictional service, profile-update review takes at least one working day. Withdrawal cannot unlock ten minutes after submitting an update."], "scored", "0")]:
        add("timing-dependent-" + suffix, [
            ("client", "Is withdrawal guaranteed to unlock exactly ten minutes after submitting a profile update?"),
            ("operator", "Hello, I'm Cy. Yes, it is guaranteed to unlock exactly ten minutes after submission. Goodbye.")],
            [("consultation", status, answer, "Missing factual evidence changes the grade; an explicitly contradicted key promise fails."),
             scored("management", "10", "The answer is clearly worded regardless of factual correctness.")], refs)

    kz = [("client", "Оқу қосымшасында есепті қайдан жүктеймін?"),
          ("operator", "Сәлеметсіз бе, менің атым Айша. Ана жердегі соны басыңыз."),
          ("client", "Қай жерді, қай батырманы айтасыз?")]
    for suffix, tail, answer in [
        ("corrected", [("operator", "Мәзір > Құжаттар > Есеп бөліміне кіріп, Жүктеу батырмасын басыңыз."),
                       ("client", "Есепті жүктедім, рақмет."), ("operator", "Сау болыңыз.")], "20"),
        ("unclear", [("operator", "Сол жерде іздеңіз."), ("client", "Қалай жүктеуді әлі түсінбедім."),
                     ("operator", "Сау болыңыз.")], "5")]:
        add("clarity-recovery-" + suffix, kz + tail,
            [scored("consultation", answer, "Concrete successful recovery versus only a general hint."),
             scored("management", "4", "The customer had to clarify actual vague wording; successful recovery does not erase it.")],
            ["Оқу қосымшасында есепті жүктеу жолы: Мәзір > Құжаттар > Есеп > Жүктеу."], "KZ")

    for suffix, instruction, answer in [
        ("history", "Select met only if no incorrect navigation instruction was given at any point. Later correction does not erase an earlier incorrect instruction. Otherwise select missed.", "missed"),
        ("outcome", "Select met if the final navigation advice was corrected and the customer explicitly downloaded the requested report without remaining harm. An earlier corrected mistake does not itself fail this outcome criterion. Otherwise select missed.", "met")]:
        custom = Checklist(id="fictional-recovery", version=suffix, title="Configurable recovery policy", instructions=[],
            criteria=[Criterion(id="navigation-policy", title="Navigation policy", instruction=instruction,
                kind="binary", weight=1, levels=[Level(value="met", fraction=1, description="Requirement met"),
                                                Level(value="missed", fraction=0, description="Requirement missed")])])
        add("custom-correction-" + suffix, [("client", "Where do I download the saved report?"),
            ("operator", "Hello, I'm Dee. Use Profile > Forms."), ("client", "There is no report there."),
            ("operator", "That was incorrect. Use Menu > Documents > Report > Download."),
            ("client", "I downloaded the saved report successfully and nothing was lost.")],
            [scored("navigation-policy", answer, "Apply the actual configured treatment of corrected advice.")],
            ["Fictional app: reports are downloaded through Menu > Documents > Report > Download. Profile > Forms has no reports."],
            override=custom)
    return cases


if __name__ == "__main__":
    paired = build()
    path = ROOT / "evals/claim-dependencies-v1.jsonl"
    with path.open("x", encoding="utf-8") as stream:
        stream.write("".join(c.model_dump_json() + "\n" for c in paired))
    source = ROOT / "artifacts/organizer-65-v1/merged.suite.jsonl"
    ids = ["p1-ru-018", "p1-kz-005", "p1-en-014", "p4-ru-003",
           "p1-ru-009", "p1-kz-015", "p1-en-015", "p1-ru-029"]
    organizer = [c for c in load_cases(source) if c.id in ids]
    assert len(organizer) == 8
    folder = ROOT / "artifacts/claim-dependencies-v1"
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "organizer-regressions.jsonl").open("x", encoding="utf-8") as stream:
        stream.write("".join(c.model_dump_json() + "\n" for c in organizer))
    with (folder / "protocol.json").open("x", encoding="utf-8") as stream:
        json.dump({"paired_cases": len(paired), "organizer_ids": ids,
                   "warning": "Paired expectations are assistant-authored provisional labels, not independent GT.",
                   "rule": "Preserve first outcomes and all attempts; no favorable retry selection or silent label edits.",
                   "planned_runs": ["paired baseline before edits", "paired candidate", "organizer candidate"]},
                  stream, indent=2)
    print(json.dumps({"paired": len(paired), "organizer": len(organizer)}))
