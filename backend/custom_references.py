"""Attach user-provided text sources without fetching URLs or evaluating a model."""

import json
from typing import Literal
from urllib.parse import urlsplit

from fastapi import HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from cqa.grounding import evidence_context_for
from cqa.models import Conversation, Reference, validate_iso_date

from .storage import Document, digest

MAX_DOCUMENT_CHARS = 100_000
MAX_REQUEST_CHARS = 300_000
MAX_REQUEST_BYTES = 2_000_000
MAX_CUSTOM_DOCUMENTS = 100


class CustomReferenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=MAX_DOCUMENT_CHARS)
    source_url: str | None = Field(default=None, max_length=2048)
    source_note: str | None = Field(default=None, max_length=1000)
    scope: str | None = Field(default=None, max_length=200)
    date_kind: Literal["unknown", "snapshot", "validity"] = "unknown"
    snapshot_on: str | None = None
    valid_from: str | None = None
    valid_until: str | None = None

    @field_validator("title", "text")
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError("empty_field")
        # The evidence text is preserved exactly, including whitespace.
        return value

    @field_validator("source_url", "source_note", "scope", "snapshot_on", "valid_from", "valid_until")
    @classmethod
    def optional_text(cls, value):
        return value.strip() or None if value is not None else None

    @field_validator("source_url")
    @classmethod
    def safe_source_url(cls, value):
        if value is None:
            return value
        try:
            parsed = urlsplit(value)
            if (parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username is not None
                    or parsed.password is not None or any(character.isspace() or ord(character) < 32 for character in value)):
                raise ValueError("invalid_url")
        except ValueError:
            raise ValueError("invalid_url") from None
        return value

    @model_validator(mode="after")
    def explicit_dates(self):
        for value in (self.snapshot_on, self.valid_from, self.valid_until):
            if value is not None:
                try:
                    validate_iso_date(value)
                except ValueError:
                    raise ValueError("invalid_date") from None
        if self.date_kind == "unknown" and any((self.snapshot_on, self.valid_from, self.valid_until)):
            raise ValueError("inconsistent_dates")
        if self.date_kind == "snapshot" and (not self.snapshot_on or self.valid_from or self.valid_until):
            raise ValueError("snapshot_date_required")
        if self.date_kind == "validity" and (self.snapshot_on or not (self.valid_from or self.valid_until)):
            raise ValueError("validity_dates_required")
        if self.valid_from and self.valid_until and self.valid_from > self.valid_until:
            raise ValueError("reversed_dates")
        return self


class CustomReferencesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    documents: list[CustomReferenceInput] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def bounded_text(self):
        if sum(len(document.text) for document in self.documents) > MAX_REQUEST_CHARS:
            raise ValueError("total_text_limit")
        return self


def _reference(document):
    values = document.model_dump()
    reference_id = "custom-" + digest(values)[:24]
    provenance = (f"Документ пользователя: {document.title}. "
                  "Предоставлен пользователем; официальность и подлинность приложением не проверялись.")
    if document.source_note:
        provenance += f" Описание источника пользователем: {document.source_note}."
    if document.scope is None:
        provenance += " Область применения не указана; соответствие продукту диалога не подтверждено."
    if document.date_kind == "unknown":
        provenance += " Дата актуальности и период действия не указаны; действие на дату диалога не подтверждено."
    reference = Reference(id=reference_id, text=document.text, provenance=provenance,
        source_url=document.source_url, scope=document.scope,
        date_basis="snapshot" if document.date_kind == "snapshot" else "policy_validity",
        snapshot_on=document.snapshot_on, valid_from=document.valid_from, valid_until=document.valid_until)
    metadata = {key: value for key, value in values.items() if key != "text"}
    metadata["origin"] = "user_provided"
    return reference, metadata


def prepare_custom_references(conversation, request):
    """Keep the original date, scope, context and all existing sources unchanged."""
    indexed = {reference.id: reference for reference in conversation.references}
    additions, documents, added, reused = {}, [], 0, 0
    for item in request.documents:
        reference, metadata = _reference(item)
        if reference.id in indexed:
            if reference != indexed[reference.id]:
                raise HTTPException(409, detail={"code": "reference_conflict"})
            reused += 1
        else:
            indexed[reference.id] = reference
            added += 1
        additions[reference.id] = metadata
        if reference.id not in {document["id"] for document in documents}:
            warnings = ["user_provided"]
            if item.source_note is None and item.source_url is None:
                warnings.append("source_unknown")
            if item.scope is None:
                warnings.append("scope_unknown")
            if item.date_kind == "unknown":
                warnings.append("date_unknown")
            documents.append({"id": reference.id, "title": item.title, "warnings": warnings})
    if sum(reference_id.startswith("custom-") for reference_id in indexed) > MAX_CUSTOM_DOCUMENTS:
        raise HTTPException(422, detail={"code": "document_count_limit"})
    revised = Conversation.model_validate(conversation.model_dump() | {
        "references": [reference.model_dump() for reference in indexed.values()]})
    context = evidence_context_for(revised)
    applicability = {item["reference_id"]: item for item in context["references"]}
    for document in documents:
        current = applicability[document["id"]]
        document.update(usable=current["usable"], rejection_reasons=current["rejection_reasons"])
    return revised, additions, {"added": added, "reused": reused, "documents": documents, "context": context}


async def _request_body(request):
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > MAX_REQUEST_BYTES:
            raise HTTPException(413, detail={"code": "request_too_large"})
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(422, detail={"code": "invalid_json"}) from None
    try:
        return CustomReferencesRequest.model_validate(value)
    except ValidationError as error:
        issue = error.errors(include_input=False, include_url=False)[0]
        location = issue["loc"]
        names = set(CustomReferenceInput.model_fields) | {"documents"}
        field = next((item for item in reversed(location) if isinstance(item, str) and item in names), None)
        index = next((item + 1 for item in location if isinstance(item, int)), None)
        context_error = str(issue.get("ctx", {}).get("error", ""))
        codes = {"empty_field", "invalid_url", "invalid_date", "inconsistent_dates", "snapshot_date_required",
                 "validity_dates_required", "reversed_dates", "total_text_limit"}
        code = context_error if context_error in codes else "invalid_field"
        raise HTTPException(422, detail={"code": code, "field": field, "document_index": index}) from None


def register_custom_reference_routes(app, store, document_view):
    def source(session, document_id):
        document = session.get(Document, document_id)
        if document is None or document.kind != "conversation":
            raise HTTPException(404, detail={"code": "conversation_not_found"})
        return document

    @app.post("/api/conversations/{document_id}/custom-references/preview")
    async def preview(document_id: str, request: Request):
        body = await _request_body(request)
        with store.session() as session:
            document = source(session, document_id)
            _, _, summary = prepare_custom_references(Conversation.model_validate(document.content), body)
            return summary

    @app.post("/api/conversations/{document_id}/custom-references")
    async def attach(document_id: str, request: Request):
        body = await _request_body(request)
        with store.session.begin() as session:
            document = source(session, document_id)
            original = Conversation.model_validate(document.content)
            revised, metadata, summary = prepare_custom_references(original, body)
            if revised == original:
                saved = document
            else:
                extra = dict(document.extra or {})
                previous = extra.get("custom_reference_documents", {})
                extra["custom_reference_documents"] = (previous if isinstance(previous, dict) else {}) | metadata
                extra["reference_parent_revision_id"] = document.id
                saved, _ = store.document(session, "conversation", revised.model_dump(), extra)
            return document_view(saved, True, session) | {"custom_reference_summary": summary}
