import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import JSON, ForeignKey, String, UniqueConstraint, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def now():
    return datetime.now(UTC).isoformat()


def uid():
    return str(uuid4())


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("kind", "external_id", "version", "content_hash"),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    kind: Mapped[str] = mapped_column(String, index=True)
    external_id: Mapped[str] = mapped_column(String, index=True)
    version: Mapped[str] = mapped_column(String, default="")
    content_hash: Mapped[str] = mapped_column(String)
    content: Mapped[dict] = mapped_column(JSON)
    extra: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[str] = mapped_column(String, default=now)


class Batch(Base):
    __tablename__ = "batches"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    request_id: Mapped[str] = mapped_column(String, unique=True)
    request_hash: Mapped[str] = mapped_column(String)
    budget: Mapped[float]
    config: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(String, default=now)


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    batch_id: Mapped[str] = mapped_column(ForeignKey("batches.id"), index=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    checklist_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    cache_key: Mapped[str] = mapped_column(String, index=True)
    status: Mapped[str] = mapped_column(String, default="queued", index=True)
    record: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    retry_of: Mapped[str | None] = mapped_column(String, nullable=True)
    review_revision: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[str] = mapped_column(String, default=now)
    started_at: Mapped[str | None] = mapped_column(String, nullable=True)
    finished_at: Mapped[str | None] = mapped_column(String, nullable=True)


class Appeal(Base):
    __tablename__ = "appeals"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    criterion_id: Mapped[str] = mapped_column(String)
    author: Mapped[str] = mapped_column(String)
    reason: Mapped[str] = mapped_column(String)
    message_ids: Mapped[list] = mapped_column(JSON)
    proposed: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String, default="open")
    resolution: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[str] = mapped_column(String, default=now)
    resolved_at: Mapped[str | None] = mapped_column(String, nullable=True)


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{path.as_posix()}", connect_args={"check_same_thread": False, "timeout": 30})

        @event.listens_for(self.engine, "connect")
        def configure(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA journal_mode=WAL")

        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(self.engine, expire_on_commit=False)

    def document(self, session, kind, content, extra=None):
        from sqlalchemy import select
        value_hash = digest({"content": content, "metadata": extra or {}})
        version = content.get("version", "") if kind == "checklist" else ""
        external_id = content["id"]
        existing = session.scalar(select(Document).where(Document.kind == kind, Document.external_id == external_id,
            Document.version == version, Document.content_hash == value_hash))
        if existing:
            return existing, False
        if kind == "checklist" and session.scalar(select(Document).where(Document.kind == kind,
                Document.external_id == external_id, Document.version == version)):
            raise ValueError("That checklist ID/version already exists with different content. Save a new version.")
        doc = Document(kind=kind, external_id=external_id, version=version, content_hash=value_hash,
                       content=content, extra=extra or {})
        session.add(doc)
        session.flush()
        return doc, True
