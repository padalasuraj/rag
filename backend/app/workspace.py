"""A private browser workspace without an account setup flow."""

from contextvars import ContextVar

from fastapi import HTTPException

workspace_id = ContextVar("workspace_id", default="legacy")


def require_kb(db, kb_id):
    from app.repositories.knowledge_base_repository import get

    kb = get(db, kb_id)
    if kb is None:
        raise HTTPException(404, "Knowledge base not found.")
    return kb


def require_source(db, source_id):
    from app.models import Source

    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(404, "Source not found.")
    require_kb(db, source.knowledge_base_id)
    return source
