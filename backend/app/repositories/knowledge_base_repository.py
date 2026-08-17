"""Data-access for knowledge bases.

Repositories keep SQL/ORM details out of the API layer, so routers read as
orchestration and are trivial to test. This one also assembles the per-KB
counts the dashboard needs in a single place.
"""

from __future__ import annotations

from sqlalchemy import func, select

from app.models import Chunk, KnowledgeBase, Source
from app.schemas import KnowledgeBaseOut, SourceCounts


def create(db, name: str, description: str, is_demo: bool = False) -> KnowledgeBase:
    kb = KnowledgeBase(name=name, description=description, is_demo=is_demo)
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return kb


def get(db, kb_id: str) -> KnowledgeBase | None:
    return db.get(KnowledgeBase, kb_id)


def list_all(db) -> list[KnowledgeBase]:
    stmt = select(KnowledgeBase).order_by(KnowledgeBase.updated_at.desc())
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
