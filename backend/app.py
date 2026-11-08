import argparse
import json
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, update
from starlette.middleware.trustedhost import TrustedHostMiddleware

from cqa.evaluator import Evaluator
from cqa.grounding import (
    evidence_context_for,
    reference_applicable,
    reference_rejection_reasons,
    select_reference_context,
)
from cqa.models import Checklist, Conversation, Reference
from cqa.rubric import load_checklist
from cqa.settings import ROOT, Settings

from .comparison import compare_evaluations
from .contracts import (
    AppealRequest,
    ImportRequest,
    ReferenceRequest,
    ResolveRequest,
    RetryRequest,
    RunRequest,
)
from .custom_references import register_custom_reference_routes
from .dataset_presets import apply_fbroker_preset
from .demo import open_demo
from .importing import parse_import
from .recordings import matching_recording
from .service import Workflow, effective_result, validate_human_revision
from .storage import Appeal, Batch, Document, Job, Store, now


def conversation_display_title(content: dict) -> str:
    """Use a short excerpt of the customer's request without changing its language."""
    greetings = {
        "hi", "hello", "hey", "hi there", "hello there", "good morning", "good afternoon", "good evening",
        "здравствуйте", "здравствуй", "привет", "добрый день", "доброе утро", "добрый вечер", "алло",
        "сәлем", "сәлеметсіз бе", "сәлеметсіздер ме", "қайырлы таң", "қайырлы күн", "қайырлы кеш",
        "salom", "assalomu alaykum", "assalom alaykum", "hola", "buenos días", "buenas tardes", "buenas noches",
        "olá", "oi", "bom dia", "boa tarde", "boa noite",
        "yes", "no", "ok", "okay", "thanks", "thank you", "да", "нет", "хорошо", "спасибо", "рахмет",
    }
    placeholders = {
        "inaudible", "unintelligible", "silence", "noise", "audio", "voice message", "image", "attachment",
        "message deleted", "deleted message", "empty message", "call started", "call ended", "customer joined",
        "неразборчиво", "неразборчивая речь", "тишина", "пауза", "шум", "аудио", "голосовое сообщение",
        "изображение", "вложение", "сообщение удалено", "пустое сообщение", "звонок начат", "звонок завершён",
    }
    greeting_pattern = "(?:" + "|".join(re.escape(greeting) for greeting in greetings) + ")"
    for message in content.get("messages", []):
        if message.get("speaker") not in {"client", "customer"}:
            continue
        text = " ".join(message.get("text", "").split())
        words = re.findall(r"[^\W_]+", text.casefold())
        normalized = " ".join(words)
        greeting_only = re.fullmatch(rf"{greeting_pattern}(?: {greeting_pattern})*", normalized)
        if not any(character.isalpha() for character in text) or greeting_only or normalized in placeholders:
            continue
        # Keep words intact where possible, reserving one character for the ellipsis.
        if len(text) > 110:
            excerpt = text[:109]
            if not text[109].isspace() and " " in excerpt:
                excerpt = excerpt.rsplit(" ", 1)[0]
            text = excerpt.rstrip() + "…"
        return text
    channel = "Звонок" if content.get("channel") == "voice call" else "Чат"
    language = str(content.get("language") or "").strip().upper()
    language_name = {"RU": "на русском", "KZ": "на казахском", "KK": "на казахском", "EN": "на английском"}.get(language, language)
    return f"{channel} {language_name}" if language_name else channel


def serious_error_summary(checklist, effective):
    """Only a resolved official flag can confirm or clear a serious error."""
    summary = {"serious_error": None, "serious_error_reason": None}
    if checklist is None or effective is None:
        return summary
    criterion = next((c for c in checklist.criteria if c.id == "serious" and c.kind == "flag"), None)
    if criterion is None or {level.value for level in criterion.levels} != {"yes", "no"}:
        return summary
    judgment = next((j for j in effective["judgments"] if j["criterion_id"] == "serious"), None)
    if (judgment is None or judgment["status"] != "scored" or judgment["answer"] not in {"yes", "no"}
            or effective["score"].get("flags", {}).get("serious") != judgment["answer"]):
        return summary
    return {"serious_error": judgment["answer"] == "yes", "serious_error_reason": judgment["explanation"]}


def create_app(*, settings=None, database_path=None, evaluator_factory=Evaluator):
    settings = settings or Settings.load()
    store = Store(database_path or Path(os.environ.get("CQA_APP_DB", str(ROOT / "data/runtime/app.sqlite3"))))
    workflow = Workflow(store, settings, evaluator_factory)
    ui_checklist = load_checklist()
    with store.session.begin() as session:
        store.document(session, "checklist", ui_checklist.model_dump())

    @asynccontextmanager
    async def lifespan(_):
        await workflow.start()
        try:
            yield
        finally:
            await workflow.close()

    app = FastAPI(title="Freedom CQA", lifespan=lifespan)
    app.state.workflow, app.state.store = workflow, store
    allowed = [f"http://{host}:{port}" for host in ["127.0.0.1", "localhost"] for port in [8000, 5173]]
    app.add_middleware(CORSMiddleware, allow_origins=allowed, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])

    @app.middleware("http")
    async def origin_guard(request: Request, call_next):
        if request.method not in {"GET", "HEAD", "OPTIONS"} and request.headers.get("origin") not in [None, *allowed, str(request.base_url).rstrip("/")]:
            return JSONResponse({"detail": "Request origin is not allowed"}, status_code=403)
        return await call_next(request)

    @app.exception_handler(ValueError)
    async def bad_input(_, error):
        # Our controlled application errors; model validation uses separate safe handlers below.
        return JSONResponse({"detail": str(error)}, status_code=422)

    def require(session, cls, object_id):
        row = session.get(cls, object_id)
        if row is None:
            raise HTTPException(404, "Record not found")
        return row

    def document_view(doc, detail=False, session=None):
        value = {"id": doc.id, "external_id": doc.external_id, "version": doc.version,
                 "content_hash": doc.content_hash, "created_at": doc.created_at}
        if doc.kind == "conversation":
            value.update(channel=doc.content["channel"], language=doc.content["language"],
                         display_title=conversation_display_title(doc.content),
                         message_count=len(doc.content["messages"]), reference_count=len(doc.content.get("references", [])))
        else:
            value.update(title=doc.content["title"], content=doc.content)
        if detail:
            value.update(content=doc.content, metadata=doc.extra)
            if doc.kind == "conversation":
                value["resolved_recording"] = (matching_recording(session, doc.content)
                    if session is not None and not (doc.extra or {}).get("recording_url") else None)
        return value

    register_custom_reference_routes(app, store, document_view)

    @app.post("/api/demo/open")
    async def demo():
        return open_demo(store, ui_checklist)

    def appeal_view(appeal):
        return {key: getattr(appeal, key) for key in ["id", "job_id", "criterion_id", "author", "reason", "message_ids",
                                                    "proposed", "status", "resolution", "created_at", "resolved_at"]}

    def job_view(job):
        return {**{key: getattr(job, key) for key in ["id", "batch_id", "conversation_id", "checklist_id", "status",
                  "retry_of", "review_revision", "created_at", "started_at", "finished_at"]},
                "is_demo": bool((job.record or {}).get("demo"))}

    @app.get("/api/config")
    async def config():
        try:
            settings.require_key()
            configured = True
        except ValueError:
            configured = False
        return {"api_key_configured": configured, "model": settings.model, "strategy": settings.strategy,
                "import_presets": ["fbroker"],
                "default_checklist": {"id": ui_checklist.id, "version": ui_checklist.version},
                "ledger": workflow.ledger.summary(), "worker_concurrency": 1,
                "audio_analysis_available": False}

    @app.post("/api/conversations/import")
    async def import_conversations(body: ImportRequest):
        parsed = parse_import(body.content)
        if body.reference_preset == "fbroker":
            parsed = apply_fbroker_preset(body.content, parsed)
        rows, created = [], 0
        with store.session.begin() as session:
            for conversation, extra in parsed:
                row, fresh = store.document(session, "conversation", conversation.model_dump(), extra)
                created += fresh
                rows.append(document_view(row))
        return {"created": created, "reused": len(parsed) - created, "conversations": rows}

    @app.get("/api/conversations")
    async def conversations():
        with store.session() as session:
            # The queue represents exact source revisions. Never attach an older
            # revision's successful result to a changed, unevaluated transcript.
            latest_job = (select(Job.id).where(Job.conversation_id == Document.id)
                          .order_by(Job.created_at.desc(), Job.id.desc()).limit(1)
                          .correlate(Document).scalar_subquery())
            rows = session.execute(select(Document, Job).outerjoin(Job, Job.id == latest_job)
                .where(Document.kind == "conversation").order_by(Document.created_at.desc())).all()
            job_ids = [job.id for _, job in rows if job is not None]
            appeals_by_job = {}
            if job_ids:
                for appeal in session.scalars(select(Appeal).where(Appeal.job_id.in_(job_ids))):
                    appeals_by_job.setdefault(appeal.job_id, []).append(appeal)
            checklist_ids = {job.checklist_id for _, job in rows if job is not None and job.status == "completed"}
            checklists = {doc.id: Checklist.model_validate(doc.content) for doc in session.scalars(
                select(Document).where(Document.id.in_(checklist_ids)))} if checklist_ids else {}
            result = []
            for doc, job in rows:
                value = document_view(doc)
                value["latest_assessment"] = None
                if job is not None:
                    appeals = appeals_by_job.get(job.id, [])
                    effective = (effective_result(job, checklists[job.checklist_id], appeals)
                                 if job.status == "completed" else None)
                    score = effective["score"] if effective else {}
                    review_ids = set(score.get("unresolved_criteria", [])) | set(
                        score.get("review_recommended_criteria", []))
                    value["latest_assessment"] = {
                        "id": job.id, "status": job.status, "created_at": job.created_at,
                        "total": score.get("total"), "provisional": score.get("provisional", False),
                        "review_recommended_count": len(review_ids),
                        "open_appeals": sum(a.status == "open" for a in appeals),
                        "source": effective["source"] if effective else None,
                        "is_demo": bool((job.record or {}).get("demo")),
                        **serious_error_summary(checklists.get(job.checklist_id), effective),
                    }
                result.append(value)
            return result

    @app.get("/api/conversations/{document_id}")
    async def conversation(document_id: str):
        with store.session() as session:
            doc = require(session, Document, document_id)
            if doc.kind != "conversation":
                raise HTTPException(404, "Conversation not found")
            return document_view(doc, True, session)

    @app.get("/api/reference-packs")
    async def reference_packs():
        return [{"id": p.stem, **json.loads(p.read_text(encoding="utf-8"))} for p in sorted((ROOT / "references").glob("*.json"))]

    @app.get("/api/conversations/{document_id}/evidence-context")
    async def conversation_evidence_context(document_id: str):
        with store.session() as session:
            doc = require(session, Document, document_id)
            if doc.kind != "conversation":
                raise HTTPException(404, "Conversation not found")
            return evidence_context_for(Conversation.model_validate(doc.content))

    def reference_candidate(doc, body, *, require_usable):
        files = {p.stem: p for p in (ROOT / "references").glob("*.json")}
        if body.pack_id not in files:
            raise HTTPException(404, "Reference pack not found")
        if doc.kind != "conversation":
            raise HTTPException(404, "Conversation not found")
        return select_reference_context(Conversation.model_validate(doc.content), files[body.pack_id], body.scope,
            mode=body.mode, occurred_on=body.occurred_on, as_of=body.as_of, rationale=body.rationale,
            pack_id=body.pack_id, require_usable=require_usable)

    @app.post("/api/conversations/{document_id}/references/preview")
    async def preview_reference(document_id: str, body: ReferenceRequest):
        with store.session() as session:
            doc = require(session, Document, document_id)
            candidate = reference_candidate(doc, body, require_usable=False)
            return evidence_context_for(candidate)

    @app.post("/api/conversations/{document_id}/references")
    async def apply_reference(document_id: str, body: ReferenceRequest):
        with store.session.begin() as session:
            doc = require(session, Document, document_id)
            revised = reference_candidate(doc, body, require_usable=True)
            if revised == Conversation.model_validate(doc.content):
                return document_view(doc, True, session)
            new_doc, _ = store.document(session, "conversation", revised.model_dump(),
                                       doc.extra | {"reference_parent_revision_id": doc.id})
            return document_view(new_doc, True, session)

    @app.get("/api/checklists")
    async def checklists():
        with store.session() as session:
            return [document_view(d) for d in session.scalars(select(Document).where(Document.kind == "checklist")
                                                            .order_by(Document.created_at.desc()))]

    @app.post("/api/checklists")
    async def save_checklist(body: Checklist):
        if not all(value.strip() for value in [body.id, body.version, body.title]):
            raise ValueError("Checklist ID, version and title cannot be blank")
        for criterion in body.criteria:
            if not all(value.strip() for value in [criterion.id, criterion.title, criterion.instruction]):
                raise ValueError("Each criterion needs an ID, title and a substantive instruction")
            if any(not level.value.strip() or not level.description.strip() for level in criterion.levels):
                raise ValueError("Every answer level needs a value and a description")
        with store.session.begin() as session:
            doc, created = store.document(session, "checklist", body.model_dump())
            return {"created": created, **document_view(doc)}

    @app.post("/api/evaluations", status_code=202)
    async def evaluate(body: RunRequest):
        return workflow.enqueue(body)

    @app.get("/api/jobs")
    async def jobs(conversation_id: str | None = None):
        with store.session() as session:
            query = select(Job).order_by(Job.created_at.desc()).limit(250)
            if conversation_id:
                query = query.where(Job.conversation_id == conversation_id)
            return [job_view(j) for j in session.scalars(query)]

    @app.get("/api/batches/{batch_id}")
    async def batch_view(batch_id: str):
        with store.session() as session:
            batch = require(session, Batch, batch_id)
            rows = [job_view(j) for j in session.scalars(select(Job).where(Job.batch_id == batch.id).order_by(Job.created_at))]
            return {"id": batch.id, "budget_usd": batch.budget, "committed_usd": workflow.ledger.group_committed(batch.id),
                    "jobs": rows, "created_at": batch.created_at}

    @app.get("/api/jobs/{job_id}")
    async def job_detail(job_id: str):
        with store.session() as session:
            job = require(session, Job, job_id)
            conversation_doc, checklist_doc = session.get(Document, job.conversation_id), session.get(Document, job.checklist_id)
            appeals = list(session.scalars(select(Appeal).where(Appeal.job_id == job_id).order_by(Appeal.created_at)))
            conversation = Conversation.model_validate(conversation_doc.content)
            return {**job_view(job), "record": job.record, "conversation": document_view(conversation_doc, True, session),
                    "runtime": session.get(Batch, job.batch_id).config,
                    "checklist": document_view(checklist_doc, True), "appeals": [appeal_view(a) for a in appeals],
                    "evidence_context": (job.record or {}).get("evidence_context") or evidence_context_for(conversation),
                    "evidence_context_origin": ("captured_with_request" if (job.record or {}).get("evidence_context")
                                                else "reconstructed_for_inspection"),
                    "effective": effective_result(job, Checklist.model_validate(checklist_doc.content), appeals,
                                                  conversation=conversation)}

    @app.get("/api/jobs/{job_id}/reference-options")
    async def review_reference_options(job_id: str):
        with store.session() as session:
            job = require(session, Job, job_id)
            conversation = Conversation.model_validate(session.get(Document, job.conversation_id).content)
            # The exact input version wins over a subsequently edited pack.
            sources = {ref.id: ref for ref in conversation.references}
            for path in sorted((ROOT / "references").glob("*.json")):
                for raw in json.loads(path.read_text(encoding="utf-8"))["references"]:
                    ref = Reference.model_validate(raw)
                    sources.setdefault(ref.id, ref)
            return {"references": [{"reference": ref.model_dump(),
                "usable": reference_applicable(ref, conversation, derive_dates=True),
                "rejection_reasons": reference_rejection_reasons(ref, conversation, derive_dates=True)}
                for ref in sources.values()]}

    @app.get("/api/jobs/{job_id}/comparison-candidates")
    async def comparison_candidates(job_id: str):
        with store.session() as session:
            job = require(session, Job, job_id)
            source = session.get(Document, job.conversation_id)
            candidates = session.scalars(select(Job).join(Document, Job.conversation_id == Document.id).where(
                Document.kind == "conversation", Document.external_id == source.external_id,
                Job.id != job_id, Job.status == "completed").order_by(Job.created_at.desc()).limit(100))
            return [job_view(candidate) for candidate in candidates]

    @app.get("/api/jobs/{job_id}/compare")
    async def compare_saved(job_id: str, baseline: str):
        before = await job_detail(baseline)
        after = await job_detail(job_id)
        return compare_evaluations(before, after)

    @app.get("/api/jobs/{job_id}/export")
    async def export(job_id: str):
        result = await job_detail(job_id)
        return JSONResponse(result, headers={"Content-Disposition": f'attachment; filename="evaluation-{job_id}.json"'})

    @app.post("/api/jobs/{job_id}/retry", status_code=202)
    async def retry(job_id: str, body: RetryRequest):
        with store.session() as session:
            job = require(session, Job, job_id)
            if job.status in {"queued", "running"}:
                raise HTTPException(409, "This evaluation is still active")
            return workflow.enqueue(RunRequest(conversation_ids=[job.conversation_id], checklist_id=job.checklist_id,
                request_id=body.request_id, budget_usd=body.budget_usd, force=True), retry_of=job_id)

    @app.post("/api/jobs/{job_id}/cancel")
    async def cancel(job_id: str):
        with store.session.begin() as session:
            job = require(session, Job, job_id)
            if job.status != "queued":
                raise HTTPException(409, "Only queued evaluations can be cancelled; active requests may already be billable")
            job.status, job.finished_at = "cancelled", now()
            return job_view(job)

    @app.post("/api/jobs/{job_id}/appeals", status_code=201)
    async def submit_appeal(job_id: str, body: AppealRequest):
        with store.session.begin() as session:
            job = require(session, Job, job_id)
            if (job.record or {}).get("demo"):
                raise HTTPException(409, "Учебный разбор подготовлен заранее. Пересмотр доступен для результатов проверки ваших данных.")
            if job.status != "completed":
                raise HTTPException(409, "Only a completed evaluation can be appealed")
            conversation = Conversation.model_validate(session.get(Document, job.conversation_id).content)
            checklist = Checklist.model_validate(session.get(Document, job.checklist_id).content)
            criterion = next((c for c in checklist.criteria if c.id == body.criterion_id), None)
            if criterion is None or any(mid not in {m.id for m in conversation.messages} for mid in body.message_ids):
                raise ValueError("Appeal must reference a configured criterion and actual messages")
            if not body.reason.strip() or not body.author.strip():
                raise ValueError("Appeal author and rationale cannot be blank")
            if body.proposed_status == "scored" and body.proposed_answer not in {l.value for l in criterion.levels}:
                raise ValueError("Proposed answer is not an allowed criterion level")
            if body.proposed_status is None and body.proposed_answer is not None:
                raise ValueError("A proposed answer requires a proposed status")
            if body.proposed_status in {"not_applicable", "needs_review"} and body.proposed_answer is not None:
                raise ValueError("Unscored proposals must have a null answer")
            if body.proposed_status == "not_applicable" and not criterion.na_condition:
                raise ValueError("N/A is forbidden for this criterion")
            if session.scalar(select(Appeal).where(Appeal.job_id == job_id, Appeal.criterion_id == body.criterion_id,
                                                   Appeal.status == "open")):
                raise HTTPException(409, "This criterion already has an open appeal")
            appeal = Appeal(job_id=job_id, criterion_id=body.criterion_id, author=body.author, reason=body.reason,
                message_ids=body.message_ids, proposed={"status": body.proposed_status, "answer": body.proposed_answer}
                if body.proposed_status else None)
            session.add(appeal)
            session.flush()
            return appeal_view(appeal)

    @app.post("/api/appeals/{appeal_id}/resolve")
    async def resolve(appeal_id: str, body: ResolveRequest):
        if not body.reviewer.strip() or not body.rationale.strip():
            raise ValueError("Reviewer and decision rationale cannot be blank")
        with store.session.begin() as session:
            appeal = require(session, Appeal, appeal_id)
            job = require(session, Job, appeal.job_id)
            if appeal.status != "open" or job.review_revision != body.expected_revision:
                raise HTTPException(409, "Review changed. Reload the current evaluation before resolving.")
            checklist = Checklist.model_validate(session.get(Document, job.checklist_id).content)
            conversation = Conversation.model_validate(session.get(Document, job.conversation_id).content)
            appeals = list(session.scalars(select(Appeal).where(Appeal.job_id == job.id)))
            before = next(j for j in effective_result(job, checklist, appeals, conversation=conversation)["judgments"]
                          if j["criterion_id"] == appeal.criterion_id)
            if body.decision == "accept":
                if body.judgment is None or body.judgment.criterion_id != appeal.criterion_id:
                    raise ValueError("Accepting an appeal requires a full replacement judgment for that criterion")
                before = validate_human_revision(job, checklist, conversation, appeals, body.judgment)
                if len({ref.id for ref in body.supporting_references}) != len(body.supporting_references):
                    raise ValueError("Review references must have unique IDs")
                frozen = {ref.id: ref for ref in conversation.references}
                if any(ref.id in frozen and ref != frozen[ref.id] for ref in body.supporting_references):
                    raise ValueError("A review source cannot replace a frozen reference with different content")
                if any(not reference_applicable(ref, conversation, derive_dates=True) for ref in body.supporting_references):
                    raise ValueError("A review reference does not match the original conversation's scope/date")
            elif body.judgment is not None:
                raise ValueError("A rejected appeal cannot replace the judgment")
            elif body.supporting_references:
                raise ValueError("Additional review sources require an accepted decision")
            updated = session.execute(update(Job).where(Job.id == job.id, Job.review_revision == body.expected_revision)
                                      .values(review_revision=body.expected_revision + 1))
            if updated.rowcount != 1:
                raise HTTPException(409, "Another review was saved. Reload before resolving.")
            appeal.status, appeal.resolved_at = ("accepted" if body.decision == "accept" else "rejected"), now()
            appeal.resolution = {"reviewer": body.reviewer, "rationale": body.rationale,
                "revision": body.expected_revision + 1, "before": before,
                "after": body.judgment.model_dump() if body.judgment else before,
                "supporting_references": [r.model_dump() for r in body.supporting_references],
                "assessment_context": evidence_context_for(conversation)["assessment"],
                "source": "human_review"}
            return appeal_view(appeal)

    dist = ROOT / "frontend/dist"
    if dist.exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/favicon.svg")
        async def favicon():
            return FileResponse(dist / "favicon.svg", media_type="image/svg+xml")

        @app.get("/")
        async def index():
            return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache"})

    return app


def main():
    import uvicorn
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run(create_app(), host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
