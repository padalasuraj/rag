"""Analytics — aggregate knowledge-base health and usage from the DB.

Everything here is a read over the metadata we already persist during ingestion
and chat, so analytics adds no runtime cost to the hot path.
"""

from __future__ import annotations

from collections import Counter

from sqlalchemy import func, select

from app.models import Chunk, QueryLog, Source
from app.schemas import AnalyticsResponse, SourceUsage


def compute_analytics(db, knowledge_base_id: str) -> AnalyticsResponse:
    total_sources = (
        db.execute(
            select(func.count(Source.id)).where(
                Source.knowledge_base_id == knowledge_base_id
            )
        ).scalar_one()
    )
    total_chunks = (
        db.execute(
            select(func.count(Chunk.id)).where(
                Chunk.knowledge_base_id == knowledge_base_id
            )
        ).scalar_one()
    )

    logs = list(
        db.execute(
            select(QueryLog).where(QueryLog.knowledge_base_id == knowledge_base_id)
        ).scalars()
    )
    questions_asked = len(logs)
    grounded_rate = (
        sum(1 for log in logs if log.grounded) / questions_asked
        if questions_asked
        else 0.0
    )
    avg_score = (
        sum(log.avg_score for log in logs) / questions_asked
        if questions_asked
        else 0.0
    )
    avg_latency = (
        sum(log.latency_ms for log in logs) / questions_asked
        if questions_asked
        else 0.0
    )

    # Most-queried sources: count how often each source contributed to answers.
    hits: Counter[str] = Counter()
    for log in logs:
        for sid in log.source_ids or []:
            hits[sid] += 1

    top_sources: list[SourceUsage] = []
    if hits:
        source_rows = {
            s.id: s
            for s in db.execute(
                select(Source).where(Source.id.in_(list(hits.keys())))
            ).scalars()
        }
        for sid, count in hits.most_common(5):
            src = source_rows.get(sid)
            if src:
                top_sources.append(
                    SourceUsage(
                        source_id=sid,
                        title=src.title,
                        source_type=src.source_type,
                        query_hits=count,
                    )
                )

    return AnalyticsResponse(
        knowledge_base_id=knowledge_base_id,
        total_sources=total_sources,
        total_chunks=total_chunks,
        questions_asked=questions_asked,
        grounded_answer_rate=round(grounded_rate, 3),
        avg_retrieval_score=round(avg_score, 3),
        avg_latency_ms=round(avg_latency, 1),
        most_queried_sources=top_sources,
    )
