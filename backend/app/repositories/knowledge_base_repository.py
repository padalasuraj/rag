"""Data-access for knowledge bases.

Repositories keep SQL/ORM details out of the API layer, so routers read as
orchestration and are trivial to test. This one also assembles the per-KB
counts the dashboard needs in a single place.
"""

from __future__ import annotations

from sqlalchemy import func, select

from app.models import Chunk, KnowledgeBase, Source, StoredFile, WorkspaceKnowledgeBase, ChatMessage, QueryLog
from app.workspace import workspace_id
from sqlalchemy import delete as sql_delete
from app.schemas import KnowledgeBaseOut, SourceCounts


def create(db, name: str, description: str, is_demo: bool = False) -> KnowledgeBase:
    kb = KnowledgeBase(name=name, description=description, is_demo=is_demo)
    db.add(kb)
    db.flush()
    db.add(WorkspaceKnowledgeBase(knowledge_base_id=kb.id, workspace_id=workspace_id.get()))
    db.commit()
    db.refresh(kb)
    return kb


def get(db, kb_id: str) -> KnowledgeBase | None:
    ownership = db.get(WorkspaceKnowledgeBase, kb_id)
    if ownership is None or ownership.workspace_id != workspace_id.get():
        return None
    return db.get(KnowledgeBase, kb_id)


def list_all(db) -> list[KnowledgeBase]:
    stmt = (select(KnowledgeBase)
            .join(WorkspaceKnowledgeBase, WorkspaceKnowledgeBase.knowledge_base_id == KnowledgeBase.id)
            .where(WorkspaceKnowledgeBase.workspace_id == workspace_id.get())
            .order_by(KnowledgeBase.updated_at.desc()))
    return list(db.execute(stmt).scalars().all())


def update(db, kb: KnowledgeBase, name: str | None, description: str | None) -> KnowledgeBase:
    if name is not None:
        kb.name = name
    if description is not None:
        kb.description = description
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return kb


def delete(db, kb: KnowledgeBase) -> None:
    source_ids = select(Source.id).where(Source.knowledge_base_id == kb.id)
    db.execute(sql_delete(StoredFile).where(StoredFile.source_id.in_(source_ids)))
    db.execute(sql_delete(WorkspaceKnowledgeBase).where(WorkspaceKnowledgeBase.knowledge_base_id == kb.id))
    db.execute(sql_delete(ChatMessage).where(ChatMessage.knowledge_base_id == kb.id))
    db.execute(sql_delete(QueryLog).where(QueryLog.knowledge_base_id == kb.id))
    db.delete(kb)
    db.commit()


def _counts(db, kb_id: str) -> tuple[SourceCounts, int]:
    rows = db.execute(
        select(Source.source_type, func.count(Source.id))
        .where(Source.knowledge_base_id == kb_id)
        .group_by(Source.source_type)
    ).all()
    counts = SourceCounts()
    for source_type, n in rows:
        counts.total += n
        setattr(counts, source_type, n)
    chunk_count = db.execute(
        select(func.count(Chunk.id)).where(Chunk.knowledge_base_id == kb_id)
    ).scalar_one()
    return counts, chunk_count


def to_out(db, kb: KnowledgeBase) -> KnowledgeBaseOut:
    counts, chunk_count = _counts(db, kb.id)
    out = KnowledgeBaseOut.model_validate(kb)
    out.source_counts = counts
    out.chunk_count = chunk_count
    return out
