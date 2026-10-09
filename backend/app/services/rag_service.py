"""RAG orchestration — where everything comes together.

For each question we:
1. Contextualize it against recent conversation (resolve "it"/"its"/"that")
   BUT only to build a better retrieval query; the answer stays grounded in the
   knowledge base, never in the model's memory of the chat.
2. Retrieve + rerank chunks.
3. If nothing clears the relevance bar, return the fixed "not found" message —
   no LLM call, no hallucination.
4. Otherwise generate a grounded answer with [n] citations and attach the real
   source metadata for each cited chunk.

Citations are derived from retrieved-chunk metadata in code, so the UI's sources
always correspond to passages that actually existed.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Iterator

from sqlalchemy import select

from app.config import settings
from app.models import ChatMessage, QueryLog, Source
from app.schemas import ChatResponse, Citation
from app.services.embedding_service import EmbeddingError
from app.services.llm_service import LLMError
from app.services import llm_service
from app.services.retrieval_service import retrieve
from app.services.vectorstore.base import SearchHit
from app.services.vectorstore.chroma_store import VectorDimensionError
from app.utils.helpers import youtube_watch_url
from app.utils.prompts import (
    CONTEXTUALIZE_SYSTEM_PROMPT,
    GROUNDED_SYSTEM_PROMPT,
    RELATED_QUESTIONS_SYSTEM_PROMPT,
    build_grounded_user_prompt,
)

logger = logging.getLogger(__name__)

NOT_FOUND_MESSAGE = (
    "I couldn't find enough information about this in the provided sources."
)


def _recent_history(db, kb_id: str, limit: int = 6) -> list[ChatMessage]:
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.knowledge_base_id == kb_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    return list(reversed(db.execute(stmt).scalars().all()))


def _contextualize(db, kb_id: str, question: str) -> str:
    history = _recent_history(db, kb_id)
    if len(history) < 2:
        return question  # nothing to resolve against yet
    convo = "\n".join(f"{m.role}: {m.content}" for m in history[-4:])
    user = f"Conversation so far:\n{convo}\n\nLatest question: {question}"
    try:
        rewritten = llm_service.get_llm_provider().complete(
            CONTEXTUALIZE_SYSTEM_PROMPT, user, temperature=0.0
        )
        rewritten = rewritten.strip().strip('"')
        return rewritten or question
    except Exception:  # noqa: BLE001 - never fail a chat over query rewriting
        logger.warning("event=contextualize_failed kb=%s", kb_id)
        return question


def _snippet(text: str, limit: int = 240) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit].rstrip() + "…"


def _build_citations(db, hits: list[SearchHit]) -> list[Citation]:
    """Map reranked hits to Citation objects with deep links."""
    source_ids = {h.metadata.get("source_id") for h in hits if h.metadata.get("source_id")}
    sources = {
        s.id: s
        for s in db.execute(
            select(Source).where(Source.id.in_(source_ids))
        ).scalars()
    }

    citations: list[Citation] = []
    for i, hit in enumerate(hits):
        meta = hit.metadata
        source = sources.get(meta.get("source_id"))
        source_type = meta.get("source_type", "text")
        url = None
        if source_type == "youtube" and source:
            video_id = source.meta.get("video_id")
            if video_id:
                url = youtube_watch_url(video_id, meta.get("start_seconds"))
        citations.append(
            Citation(
                index=i + 1,
                source_id=meta.get("source_id", ""),
                chunk_id=meta.get("chunk_id", hit.id),
                source_type=source_type,
                title=meta.get("title", source.title if source else "Source"),
                snippet=_snippet(hit.text),
                score=round(hit.score, 4),
                page=meta.get("page"),
                start_seconds=meta.get("start_seconds"),
                section=meta.get("section"),
                url=url,
            )
        )
    return citations


def _related_questions(question: str, passages: list[str]) -> list[str]:
    try:
        context = "\n\n".join(passages[:4])
        raw = llm_service.get_llm_provider().complete(
            RELATED_QUESTIONS_SYSTEM_PROMPT,
            f"Question: {question}\n\nContext:\n{context}",
            temperature=0.4,
        )
        data = llm_service.parse_json_response(raw)
        if isinstance(data, list):
            return [str(q) for q in data][:3]
    except Exception:  # noqa: BLE001
        pass
    return []


def _persist_turn(
    db,
    kb_id: str,
    question: str,
    answer: str,
    citations: list[Citation],
    hits: list[SearchHit],
    latency_ms: float,
    grounded: bool,
) -> None:
    db.add(ChatMessage(knowledge_base_id=kb_id, role="user", content=question))
    db.add(
        ChatMessage(
            knowledge_base_id=kb_id,
            role="assistant",
            content=answer,
            citations=[c.model_dump() for c in citations],
        )
    )
    scores = [h.score for h in hits]
    db.add(
        QueryLog(
            knowledge_base_id=kb_id,
            question=question,
            num_results=len(hits),
            avg_score=round(sum(scores) / len(scores), 4) if scores else 0.0,
            top_score=round(max(scores), 4) if scores else 0.0,
            latency_ms=round(latency_ms, 1),
            grounded=grounded,
            source_ids=list({c.source_id for c in citations}),
        )
    )
    db.commit()


# --------------------------------------------------------------------------- #
# Public entry points
# --------------------------------------------------------------------------- #


def answer(db, request) -> ChatResponse:
    """Blocking (non-streaming) grounded answer."""
    start = time.perf_counter()
    query = _contextualize(db, request.knowledge_base_id, request.question)
    hits = retrieve(
        request.knowledge_base_id, query, source_type_filter=request.source_type_filter
    )

    if not hits:
        latency = (time.perf_counter() - start) * 1000
        _persist_turn(
            db, request.knowledge_base_id, request.question,
            NOT_FOUND_MESSAGE, [], [], latency, grounded=False,
        )
        return ChatResponse(
            answer=NOT_FOUND_MESSAGE, grounded=False, citations=[],
            related_questions=[], latency_ms=round(latency, 1),
        )

    passages = [h.text for h in hits]
    citations = _build_citations(db, hits)
    text = llm_service.get_llm_provider().complete(
        GROUNDED_SYSTEM_PROMPT, build_grounded_user_prompt(query, passages)
    )
    related = _related_questions(query, passages)
    latency = (time.perf_counter() - start) * 1000
    _persist_turn(
        db, request.knowledge_base_id, request.question, text, citations, hits,
        latency, grounded=True,
    )
    return ChatResponse(
        answer=text, grounded=True, citations=citations,
        related_questions=related, latency_ms=round(latency, 1),
    )


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def answer_stream(db, request) -> Iterator[str]:
    """Server-sent-events generator for the streaming chat endpoint.

    Event protocol (each `data:` line is a JSON object with a `type`):
      - {"type":"citations", "grounded":bool, "citations":[...]}   (sent first)
      - {"type":"token", "text":"..."}                             (many)
      - {"type":"done", "related_questions":[...], "latency_ms":n} (last)
      - {"type":"error", "message":"..."}
    """
    start = time.perf_counter()
    try:
        query = _contextualize(db, request.knowledge_base_id, request.question)
        hits = retrieve(
            request.knowledge_base_id, query,
            source_type_filter=request.source_type_filter,
        )

        if not hits:
            yield _sse({"type": "citations", "grounded": False, "citations": []})
            yield _sse({"type": "token", "text": NOT_FOUND_MESSAGE})
            latency = (time.perf_counter() - start) * 1000
            _persist_turn(
                db, request.knowledge_base_id, request.question,
                NOT_FOUND_MESSAGE, [], [], latency, grounded=False,
            )
            yield _sse({"type": "done", "related_questions": [], "latency_ms": round(latency, 1)})
            return

        passages = [h.text for h in hits]
        citations = _build_citations(db, hits)
        yield _sse({
            "type": "citations",
            "grounded": True,
            "citations": [c.model_dump() for c in citations],
        })

        collected: list[str] = []
        for delta in llm_service.get_llm_provider().stream(
            GROUNDED_SYSTEM_PROMPT, build_grounded_user_prompt(query, passages)
        ):
            collected.append(delta)
            yield _sse({"type": "token", "text": delta})

        answer_text = "".join(collected)
        related = _related_questions(query, passages)
        latency = (time.perf_counter() - start) * 1000
        _persist_turn(
            db, request.knowledge_base_id, request.question, answer_text,
            citations, hits, latency, grounded=True,
        )
        yield _sse({
            "type": "done",
            "related_questions": related,
            "latency_ms": round(latency, 1),
        })
    except (EmbeddingError, LLMError, VectorDimensionError) as exc:
        logger.warning("event=chat_stream_provider_error kb=%s error=%s", request.knowledge_base_id, exc)
        yield _sse({"type": "error", "message": str(exc)})
    except Exception as exc:  # noqa: BLE001
        logger.exception("event=chat_stream_error kb=%s", request.knowledge_base_id)
        yield _sse({
            "type": "error",
            "message": "Something went wrong while generating the answer. "
                       "Please try again.",
        })
        _ = exc
