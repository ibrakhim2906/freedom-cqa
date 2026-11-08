"""Read-only recording lookup across revisions of the exact same dialogue."""

from urllib.parse import urlsplit

from sqlalchemy import select

from .storage import Document


def matching_recording(session, content):
    """Return one unambiguous supplied recording, without changing stored inputs.

    Reference context may change between assessments. Dialogue identity, channel,
    language and every original message field must still match exactly. Never
    print URLs: supplied links can contain private access tokens.
    """
    if not content.get("id") or not isinstance(content.get("messages"), list) or not content["messages"]:
        return None
    candidates = []
    rows = session.scalars(select(Document).where(
        Document.kind == "conversation", Document.external_id == content["id"])
        .order_by(Document.created_at, Document.id))
    for doc in rows:
        if any(doc.content.get(key) != content.get(key) for key in ("id", "channel", "language", "messages")):
            continue
        value = (doc.extra or {}).get("recording_url")
        if not value:
            continue
        if not isinstance(value, str):
            return None
        candidates.append((doc.id, value))
    if not candidates or len({value for _, value in candidates}) != 1:
        return None
    source_id, url = candidates[0]
    try:
        parsed = urlsplit(url)
        safe = parsed.scheme in {"http", "https"} and bool(parsed.hostname)
    except ValueError:
        safe = False
    if not safe or url != url.strip() or any(char in url for char in "\r\n\t"):
        return None
    return {"url": url, "source_revision_id": source_id, "origin": "matching_source_revision"}
