import asyncio
import hashlib
from dataclasses import replace

from sqlalchemy import select

from cqa.evaluator import Evaluator, schema_for
from cqa.ledger import BudgetExceeded, Ledger
from cqa.models import Checklist, Conversation, Evaluation, Judgment
from cqa.prompt import fingerprint
from cqa.scoring import calculate_score, validate_evaluation
from cqa.settings import ROOT

from .storage import Batch, Document, Job, digest, now


class Workflow:
    def __init__(self, store, settings, evaluator_factory=Evaluator):
        self.store, self.settings, self.evaluator_factory = store, settings, evaluator_factory
        self.ledger = Ledger(settings.ledger_path, settings.max_spend)
        self.queue = asyncio.Queue()
        self.task = None
        self.core_hash = hashlib.sha256(b"\n".join(p.read_bytes() for p in sorted((ROOT / "cqa").glob("*.py")))).hexdigest()

    def config(self):
        return {"model": self.settings.model, "effort": self.settings.effort,
                "max_output_tokens": self.settings.max_output_tokens, "timeout": self.settings.timeout,
                "strategy": "grounded", "core_source_sha256": self.core_hash}

    async def start(self):
        interrupted_groups = set()
        with self.store.session.begin() as session:
            for job in session.scalars(select(Job).where(Job.status == "running")):
                interrupted_groups.add(job.batch_id)
                job.status, job.finished_at = "interrupted", now()
                job.record = self.failure("server_restarted_during_evaluation", billing="unknown")
            batch_ids = list(session.scalars(select(Job.batch_id).where(Job.status == "queued").distinct()))
        for group_id in interrupted_groups:
            self.ledger.release_interrupted_group(group_id)
        for batch_id in batch_ids:
            self.queue.put_nowait(batch_id)
        self.task = asyncio.create_task(self.worker())

    async def close(self):
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        self.store.engine.dispose()

    @staticmethod
    def failure(code, *, billing="not_submitted"):
        return {"status": "failed", "error": code, "evaluation": None, "score": None,
                "usage": None, "attempt_records": [], "attempt_count": 0, "billing_state": billing}

    def enqueue(self, request, *, retry_of=None):
        body = request.model_dump()
        with self.store.session.begin() as session:
            previous = session.scalar(select(Batch).where(Batch.request_id == request.request_id))
            if previous:
                if previous.request_hash != digest(body):
                    raise ValueError("Request ID was already used for different inputs")
                return {"batch_id": previous.id, "job_ids": [j.id for j in session.scalars(
                    select(Job).where(Job.batch_id == previous.id))], "reused": [], "idempotent": True}
            checklist_doc = session.get(Document, request.checklist_id)
            if checklist_doc is None or checklist_doc.kind != "checklist":
                raise ValueError("Selected checklist version does not exist")
            checklist = Checklist.model_validate(checklist_doc.content)
            selected, reused = [], []
            for conversation_id in dict.fromkeys(request.conversation_ids):
                doc = session.get(Document, conversation_id)
                if doc is None or doc.kind != "conversation":
                    raise ValueError("Selected conversation revision does not exist")
                conversation = Conversation.model_validate(doc.content)
                key = digest({"conversation_revision": doc.id, "config": self.config(),
                    "input": fingerprint(conversation, checklist, grounded=True),
                    "schema": schema_for(conversation, checklist, grounded=True)})
                existing = session.scalar(select(Job).where(Job.cache_key == key,
                    Job.status.in_(["queued", "running"] if request.force else ["queued", "running", "completed"]))
                    .order_by(Job.created_at.desc()).limit(1))
                if existing:
                    reused.append(existing.id)
                else:
                    selected.append((doc.id, key))
            if not selected:
                return {"batch_id": None, "job_ids": reused, "reused": reused, "idempotent": False}
            self.settings.require_key()
            if request.budget_usd > self.settings.max_spend:
                raise ValueError("Batch budget exceeds the configured lifetime limit")
            batch = Batch(request_id=request.request_id, request_hash=digest(body),
                          budget=request.budget_usd, config=self.config())
            session.add(batch)
            session.flush()
            job_ids = []
            for doc_id, key in selected:
                job = Job(batch_id=batch.id, conversation_id=doc_id, checklist_id=checklist_doc.id,
                          cache_key=key, retry_of=retry_of)
                session.add(job)
                session.flush()
                job_ids.append(job.id)
            batch_id = batch.id
        self.queue.put_nowait(batch_id)
        return {"batch_id": batch_id, "job_ids": job_ids + reused, "reused": reused, "idempotent": False}

    async def worker(self):
        while True:
            batch_id = await self.queue.get()
            try:
                await self.run_batch(batch_id)
            finally:
                self.queue.task_done()

    async def run_batch(self, batch_id):
        with self.store.session() as session:
            batch = session.get(Batch, batch_id)
            jobs = list(session.scalars(select(Job).where(Job.batch_id == batch_id, Job.status == "queued")
                                        .order_by(Job.created_at)))
            config, budget = batch.config, batch.budget
            ids = [j.id for j in jobs]
        if not ids:
            return
        settings = replace(self.settings, model=config["model"], effort=config["effort"],
                           max_output_tokens=config["max_output_tokens"], timeout=config["timeout"])
        grouped_ledger = Ledger(settings.ledger_path, settings.max_spend, budget_group=batch_id, group_limit=budget)
        evaluator = None
        try:
            evaluator = self.evaluator_factory(settings, grouped_ledger, settings.max_spend)
            for job_id in ids:
                with self.store.session.begin() as session:
                    job = session.get(Job, job_id)
                    if job.status != "queued":
                        continue
                    conversation = Conversation.model_validate(session.get(Document, job.conversation_id).content)
                    checklist = Checklist.model_validate(session.get(Document, job.checklist_id).content)
                    job.status, job.started_at = "running", now()
                try:
                    record = await evaluator.evaluate(conversation, checklist)
                except BudgetExceeded as error:
                    record = self.failure("budget_limit")
                    record.update(error_detail=str(error), budget_required_usd=error.required,
                                  budget_available_usd=error.available)
                except asyncio.CancelledError:
                    with self.store.session.begin() as session:
                        job = session.get(Job, job_id)
                        job.status, job.finished_at = "interrupted", now()
                        job.record = self.failure("server_stopped_during_evaluation", billing="unknown")
                    raise
                except Exception as error:  # noqa: BLE001 - do not persist secrets/private exception text
                    record = self.failure("evaluator_" + type(error).__name__, billing="unknown")
                with self.store.session.begin() as session:
                    job = session.get(Job, job_id)
                    job.record, job.status, job.finished_at = record, record["status"], now()
                    if record.get("api_error_code") in {"credit_balance_exhausted", "insufficient_quota"}:
                        for pending in session.scalars(select(Job).where(Job.status == "queued")):
                            pending.status, pending.finished_at = "failed", now()
                            pending.record = self.failure("provider_credit_exhausted_no_request")
        except asyncio.CancelledError:
            raise
        except Exception as error:  # noqa: BLE001 - fail a broken batch visibly, keep the worker alive
            with self.store.session.begin() as session:
                for job in session.scalars(select(Job).where(Job.batch_id == batch_id, Job.status.in_(["queued", "running"]))):
                    job.status, job.finished_at = "failed", now()
                    job.record = self.failure("batch_" + type(error).__name__)
        finally:
            if evaluator:
                await evaluator.close()


def effective_result(job, checklist, appeals):
    if not job.record or job.status != "completed":
        return None
    original = Evaluation.model_validate(job.record["evaluation"])
    judgments = {j.criterion_id: j for j in original.judgments}
    revisions = sorted([a for a in appeals if a.status == "accepted"], key=lambda a: a.resolution["revision"])
    for appeal in revisions:
        judgments[appeal.criterion_id] = Judgment.model_validate(appeal.resolution["after"])
    # Original AI audits remain in the immutable record, not relabelled as human findings.
    reviewed = Evaluation(judgments=list(judgments.values()), request_coverage=original.request_coverage,
                          scope_notes=original.scope_notes)
    return {"judgments": [j.model_dump() for j in reviewed.judgments],
            "score": calculate_score(reviewed, checklist),
            "source": "human_review" if revisions else "ai_original", "accepted_revisions": len(revisions)}


def validate_human_revision(job, checklist, conversation, appeals, replacement):
    current = effective_result(job, checklist, appeals)
    judgments = [replacement if j["criterion_id"] == replacement.criterion_id else Judgment.model_validate(j)
                 for j in current["judgments"]]
    result = Evaluation(judgments=judgments, request_coverage=[], scope_notes=[])
    validate_evaluation(result, conversation, checklist)
    return next(j for j in current["judgments"] if j["criterion_id"] == replacement.criterion_id)
