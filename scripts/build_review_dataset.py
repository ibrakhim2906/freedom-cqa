"""Fictional development regression pairs, frozen before the v2 prompt comparison.

These provisional labels are authored by AI, not independent Ground Truth.
Do not regenerate v1 or use organizer dialogue text here.
"""

from cqa.models import Conversation, Expectation, Message, Reference, TestCase
from cqa.settings import ROOT


def build():
    cases = []
    reference = Reference(id="fictional-service-policy", provenance="Fictional diagnostic policy, NOT Freedom policy",
        text="Used usernames remain permanently reserved after account closure and can never be reused. "
        "A new registration must use a different username. Reports download at Documents > Reports > PDF. "
        "Report filenames are editable by the user. For a missing public report, support can open a technical "
        "ticket immediately and collect the app version later; version is not required to create the ticket. "
        "In version 4, refresh missing reports with Refresh Reports; only version 5 has a Report Repair button. "
        "Do not prescribe a version-specific fix without first learning the version. To investigate a missing "
        "public instrument listing, the support ticket must contain its exact ticker; do not claim to have "
        "submitted that investigation without it. These generic technical and navigation requests do not "
        "require account identity verification. Public bonds are under Markets > Bonds. The coupon calendar "
        "is under Markets > Coupons. Do not charge privately for support.")
    base = {"contact": ("yes", "Greeting and introduction in the first operator reply."),
            "needs": (None, "All information required for this generic answer was supplied initially."),
            "identity": (None, "Only generic navigation or technical support; policy requires no identity check."),
            "consultation": ("20", "All active substantial questions answered or given the policy-supported next step."),
            "empathy": ("yes", "Polite, directly helpful responses; no ignored complaint."),
            "management": ("10", "Understandable, coherent replies without explicit unannounced waiting."),
            "closing": ("yes", "Offer of further assistance and farewell."),
            "serious": ("no", "No insult, private paid solicitation, or confidential disclosure.")}

    def add(cid, family, turns, changes=None, language="EN", exclude=()):
        expected = base | (changes or {})
        cases.append(TestCase(id=cid, family=family, source="authored",
            label_provenance="ai_authored_provisional", tags=["development_regression", "counterfactual_pair"],
            conversation=Conversation(id=cid, channel="agent chat", language=language,
                messages=[Message(id=f"m{i}", timestamp=f"00:{i:02}", speaker=role, text=text)
                          for i, (role, text) in enumerate(turns, 1)], references=[reference]),
            expectations=[Expectation(criterion_id=key, status="not_applicable" if value is None else "scored",
                answer=value, rationale=why) for key, (value, why) in expected.items() if key not in exclude]))

    end = ("operator", "Can I help with anything else? Goodbye!")
    implicit = [("client", "My old account is closed but its username is unavailable. Can I wait for it to become reusable?"),
                ("operator", "Hello, I'm Mira. Used usernames stay permanently reserved after closure and can never be reused. Choose a different username for the new account."),
                ("client", "So waiting for it is unnecessary?"),
                ("operator", "For the new registration, choose a different username. Can I help with anything else? Goodbye!")]
    add("review-en-implicit", "implicit-answer", implicit)
    unanswered = implicit.copy()
    unanswered[1] = ("operator", "Hello, I'm Mira. Choose a different username for the new account.")
    add("review-en-missing-policy-answer", "implicit-answer", unanswered,
        {"consultation": ("10", "Different-name workaround given, but whether the old name will become reusable is never answered.")})
    add("review-ru-implicit", "implicit-answer", [
        ("client", "Старый счёт закрыт, а логин занят. Стоит ждать, пока его можно будет использовать снова?"),
        ("operator", "Здравствуйте, я Мира. Использованные логины остаются занятыми навсегда даже после закрытия счёта. Для новой регистрации выберите другой логин."),
        ("client", "То есть ждать освобождения не нужно?"),
        ("operator", "Для новой регистрации выберите другой логин. Могу помочь ещё с чем-нибудь? До свидания!")], language="RU")

    progressive = [("client", "Today's public report is missing from Documents > Reports. Please open a technical ticket and give me the right version-specific refresh instructions."),
                   ("operator", "Hello, I'm Mira. I've opened technical ticket T-508 for the missing report. What app version do you use?"),
                   ("client", "Version 4."),
                   ("operator", "I've added version 4 to ticket T-508. In version 4 use Refresh Reports. The technical team will investigate if it remains missing. Can I help with anything else? Goodbye!")]
    add("review-en-progressive", "progressive-clarification", progressive,
        {"needs": ("yes", "Ticket creation does not depend on app version; version is clarified before any version-specific advice.")})
    premature = progressive.copy()
    premature[1] = ("operator", "Hello, I'm Mira. Use the version 5 report repair button to fix it. What app version do you use?")
    premature[-1] = ("operator", "I've now opened technical ticket T-508 and added version 4. The technical team will investigate. Can I help with anything else? Goodbye!")
    add("review-en-premature-fix", "progressive-clarification", premature,
        {"needs": ("no", "Version-specific advice was given before the missing version was clarified."),
         "consultation": ("0", "A key version-specific repair instruction was prescribed without the required version information.")},
        exclude=("management",))
    add("review-kz-progressive", "progressive-clarification", [
        ("client", "Құжаттар > Есептер бөлімінде бүгінгі жалпыға қолжетімді есеп жоқ. Техникалық өтінім ашып, менің нұсқама сай жаңарту жолын түсіндіріңізші."),
        ("operator", "Сәлеметсіз бе, мен Мира. Жоқ есеп бойынша T-508 техникалық өтінімін аштым. Қосымшаның қай нұсқасын қолданасыз?"),
        ("client", "4-нұсқа."),
        ("operator", "T-508 өтініміне 4-нұсқа екенін қостым. 4-нұсқада Refresh Reports түймесін басыңыз. Есеп әлі жоқ болса, техникалық топ тексереді. Тағы көмегім керек пе? Сау болыңыз!")],
        {"needs": ("yes", "Version can be gathered after ticket creation, before any advice that depends on it.")}, language="KZ")

    download = [("client", "How do I download my report as PDF, and can I choose its filename?"),
                ("operator", "Hello, I'm Mira. Open Documents > Reports and choose PDF."),
                ("client", "Downloaded. I no longer need help with the filename; please disregard that question."), end]
    add("review-en-withdrawn", "request-lifecycle", download)
    outstanding = download.copy()
    outstanding[2] = ("client", "Downloaded. I still want to know whether I can choose its filename.")
    add("review-en-outstanding-detail", "request-lifecycle", outstanding,
        {"consultation": ("15", "Download succeeds but the still-active minor filename question remains unanswered.")})

    escalation = [("client", "The public listing for ticker DEMO7 is missing. Please open a technical investigation."),
                  ("operator", "Hello, I'm Mira. I've opened investigation T-612 with ticker DEMO7. The technical team will investigate that missing listing."),
                  ("client", "Thank you."), end]
    add("review-en-concrete-escalation", "escalation-completeness", escalation)
    missing = escalation.copy()
    missing[0] = ("client", "A public instrument listing is missing. Please open a technical investigation.")
    missing[1] = ("operator", "Hello, I'm Mira. Which exact ticker is missing?")
    missing[2] = ("client", "I found the ticker but haven't sent it to you yet.")
    missing[-1] = ("operator", "I've submitted the investigation. Can I help with anything else? Goodbye!")
    add("review-en-required-ticker-missing", "escalation-completeness", missing,
        {"needs": ("no", "The explicitly required ticker was not obtained before claiming to submit the investigation."),
         "consultation": ("0", "Claimed submission lacks the policy-required exact ticker, so the central next step is invalid.")})

    offer = [("client", "Where can I browse public bonds in the app?"),
             ("operator", "Hello, I'm Mira. Open Markets > Bonds. I can also give you a private paid consultation outside the company."),
             ("client", "I found Bonds. No private consultation, thanks."), end]
    add("review-en-private-offer-resolved", "independent-criteria", offer,
        {"serious": ("yes", "Private paid offer is a serious flag even when refused; navigation was nevertheless answered.")},
        exclude=("management", "empathy"))
    renewed = offer.copy()
    renewed[2] = ("client", "I found Bonds. No private consultation, thanks. One more question: where is the coupon calendar?")
    add("review-en-private-offer-new-question", "independent-criteria", renewed,
        {"serious": ("yes", "Private paid offer remains a serious flag."),
         "consultation": ("10", "New substantial coupon-calendar request is not answered before closing.")},
        exclude=("management", "empathy", "needs"))
    return cases


if __name__ == "__main__":
    path = ROOT / "evals/review-v2.jsonl"
    if path.exists():
        raise SystemExit("Refusing to overwrite a frozen review dataset")
    cases = build()
    path.write_text("".join(c.model_dump_json() + "\n" for c in cases), encoding="utf-8")
    print(f"Saved {len(cases)} provisional development cases to {path}")
