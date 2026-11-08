import argparse
import json
import os
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
from .importing import parse_import
from .service import Workflow, effective_result, validate_human_revision
from .storage import Appeal, Batch, Document, Job, Store, now


def create_app(*, settings=None, database_path=None, evaluator_factory=Evaluator):
    settings = settings or Settings.load()
    store = Store(database_path or Path(os.environ.get("CQA_APP_DB", str(ROOT / "data/runtime/app.sqlite3"))))
    workflow = Workflow(store, settings, evaluator_factory)
    with store.session.begin() as session:
        store.document(session, "checklist", load_checklist().model_dump())

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

    def document_view(doc, detail=False):
        value = {"id": doc.id, "external_id": doc.external_id, "version": doc.version,
                 "content_hash": doc.content_hash, "created_at": doc.created_at}
        if doc.kind == "conversation":
            value.update(channel=doc.content["channel"], language=doc.content["language"],
                         message_count=len(doc.content["messages"]), reference_count=len(doc.content.get("references", [])))
        else:
            value.update(title=doc.content["title"], content=doc.content)
        if detail:
            value.update(content=doc.content, metadata=doc.extra)
        return value

    def appeal_view(appeal):
        return {key: getattr(appeal, key) for key in ["id", "job_id", "criterion_id", "author", "reason", "message_ids",
                                                    "proposed", "status", "resolution", "created_at", "resolved_at"]}

    def job_view(job):
        return {key: getattr(job, key) for key in ["id", "batch_id", "conversation_id", "checklist_id", "status",
                                                 "retry_of", "review_revision", "created_at", "started_at", "finished_at"]}

    @app.get("/api/config")
    async def config():
        try:
            settings.require_key()
            configured = True
        except ValueError:
            configured = False
        return {"api_key_configured": configured, "model": settings.model, "strategy": settings.strategy,
                "default_checklist": {"id": load_checklist().id, "version": load_checklist().version},
                "ledger": workflow.ledger.summary(), "worker_concurrency": 1,
                "audio_analysis_available": False}

    @app.post("/api/conversations/import")
    async def import_conversations(body: ImportRequest):
        parsed = parse_import(body.content)
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
            return [document_view(d) for d in session.scalars(select(Document).where(Document.kind == "conversation")
                                                            .order_by(Document.created_at.desc()))]

    @app.get("/api/conversations/{document_id}")
    async def conversation(document_id: str):
        with store.session() as session:
            doc = require(session, Document, document_id)
            if doc.kind != "conversation":
                raise HTTPException(404, "Conversation not found")
            return document_view(doc, True)

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
                return document_view(doc, True)
            new_doc, _ = store.document(session, "conversation", revised.model_dump(),
                                       doc.extra | {"reference_parent_revision_id": doc.id})
            return document_view(new_doc, True)

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
            return {**job_view(job), "record": job.record, "conversation": document_view(conversation_doc, True),
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

        @app.get("/")
        async def index():
            return FileResponse(dist / "index.html")

    return app


def main():
    import uvicorn
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run(create_app(), host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
