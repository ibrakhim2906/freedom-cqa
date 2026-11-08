"""Prepared, explicitly labelled walkthrough; never calls a model or its cache."""

import json

from sqlalchemy import select

from cqa.grounding import evidence_context_for
from cqa.models import Conversation, Evaluation
from cqa.scoring import calculate_score, validate_evaluation
from cqa.settings import ROOT

from .storage import Batch, Job, digest, now

DEMO_VERSION = "prepared-address-ru-v1"


def prepared_demo(checklist):
    raw = json.loads((ROOT / "examples/judge-example.json").read_text(encoding="utf-8"))[0]
    conversation = Conversation.model_validate({**raw, "id": "judge-demo-address-ru-v1"})
    messages = {message.id: message for message in conversation.messages}
    decisions = [
        ("contact", "yes", ["m1"], "Оператор поздоровался на языке клиента и представился в первом сообщении."),
        ("needs", "yes", ["m3", "m4"], "Прежде чем дать инструкцию, оператор уточнил, пользуется ли клиент приложением или сайтом."),
        ("identity", None, ["m2", "m5"], "Оператор дал общую инструкцию по самостоятельному изменению адреса. Он не раскрывал данные счёта и не выполнял защищённых действий, поэтому проверка личности не требовалась."),
        ("consultation", "10", ["m5", "m6", "m7"], "Клиент получил инструкцию по изменению адреса в профиле, но не получил ответа на вопрос об уже оформленном заказе. В приложенной справке указано, что адрес такого заказа сам не меняется. Ответ на первый вопрос есть, а существенный дополнительный вопрос остался открытым: начислено 10 из 20 баллов."),
        ("empathy", "yes", ["m3", "m5"], "Оператор вежливо предложил помощь и дал конкретные шаги, которые помогли клиенту найти нужный раздел. Грубости или пренебрежения в ответах нет."),
        ("management", "10", ["m3", "m5"], "Уточнение и инструкция изложены последовательно и понятно. Пропущенный вопрос учтён в полноте консультации; отдельного нарушения порядка ведения диалога здесь нет."),
        ("closing", "yes", ["m7", "m9"], "Оператор предложил дальнейшую помощь и вежливо попрощался."),
        ("serious", "no", ["m1", "m5", "m9"], "В переписке нет оскорблений, предложения платной услуги в обход компании или раскрытия конфиденциальных сведений. Эта отметка не меняет числовую оценку."),
    ]
    judgments = [{"criterion_id": cid, "status": "not_applicable" if answer is None else "scored",
        "answer": answer, "explanation": explanation,
        "evidence": [{"message_id": mid, "quote": messages[mid].text} for mid in ids],
        "counterevidence": [], "checked_message_ids": list(messages), "uncertainty": None}
        for cid, answer, ids, explanation in decisions]
    consultation = next(c for c in checklist.criteria if c.id == "consultation")
    partial = next(level for level in consultation.levels if level.value == "10")
    evaluation = Evaluation.model_validate({"judgments": judgments,
        "request_coverage": [
            {"request": "Как изменить почтовый адрес в приложении?", "request_message_ids": ["m2"],
             "status": "answered", "answer_message_ids": ["m5"],
             "explanation": "Оператор дал путь к настройке; клиент подтвердил, что нашёл её и сохранил адрес."},
            {"request": "Изменится ли адрес у уже оформленного заказа?", "request_message_ids": ["m6"],
             "status": "unanswered", "answer_message_ids": [],
             "explanation": "Ответ касается адреса в профиле, а не доставки существующего заказа. Вопрос остался без ответа до завершения диалога."},
        ],
        "scope_notes": ["Заранее подготовленный учебный разбор для знакомства с интерфейсом. Запрос к модели не выполнялся.",
                        "Сервис, переписка и справочная статья вымышлены; пример не устанавливает правила реальной компании."],
        "factual_claims": [],
        "deductions": [{"criterion_id": "consultation", "rule_quote": partial.description,
            "defect": "Вопрос об адресе доставки уже оформленного заказа остался без ответа.",
            "overlap_note": "Снижение относится к полноте консультации; отдельного нарушения вежливости или ведения диалога не установлено.",
            "evidence": [{"message_id": "m6", "quote": messages["m6"].text}],
            "checked_message_ids": ["m6", "m7", "m8", "m9"]}],
    })
    validate_evaluation(evaluation, conversation, checklist, require_audit=True)
    context = evidence_context_for(conversation)
    record = {"status": "completed", "demo": {"version": DEMO_VERSION, "prepared": True,
        "label": "Учебный разбор", "description": "Разбор подготовлен заранее. API-ключ и оплата не нужны."},
        "evaluation": evaluation.model_dump(), "score": calculate_score(evaluation, checklist),
        "error": None, "model": "prepared-demo", "prompt_version": DEMO_VERSION,
        "workflow_version": DEMO_VERSION, "response_id": None, "usage": None,
        "attempt_count": 0, "attempt_records": [], "latency_seconds": 0,
        "billing_state": "not_submitted", "evidence_context": context,
        "assessment_context": context["assessment"],
        "assessment": {"contract_version": DEMO_VERSION, "criteria": {"consultation": {
            "factual_basis": "policy_reference", "review_warnings": [], "factual_dialogue_evidence": [],
            "reference_evidence": [{"reference_id": conversation.references[0].id,
                "quote": "Изменение адреса в профиле не меняет адрес доставки уже оформленного заказа."}],
            "uses_conditional_reference": False}}}}
    return conversation, record


def open_demo(store, checklist):
    conversation, record = prepared_demo(checklist)
    key = "demo:" + digest({"version": DEMO_VERSION, "conversation": conversation.model_dump(),
                             "checklist": checklist.model_dump(), "record": record})
    with store.session.begin() as session:
        existing = session.scalar(select(Job).where(Job.cache_key == key, Job.status == "completed"))
        if existing:
            return {"conversation_id": existing.conversation_id, "job_id": existing.id,
                    "checklist_id": existing.checklist_id, "reused": True}
        doc, _ = store.document(session, "conversation", conversation.model_dump(), {"prepared_demo": True})
        rules, _ = store.document(session, "checklist", checklist.model_dump())
        batch = Batch(request_id=key, request_hash=key, budget=0,
                      config={"strategy": "prepared_demo", "model": "none", "paid": False})
        session.add(batch)
        session.flush()
        job = Job(batch_id=batch.id, conversation_id=doc.id, checklist_id=rules.id, cache_key=key,
                  status="completed", record=record, started_at=None, finished_at=now())
        session.add(job)
        session.flush()
        return {"conversation_id": doc.id, "job_id": job.id, "checklist_id": rules.id, "reused": False}
