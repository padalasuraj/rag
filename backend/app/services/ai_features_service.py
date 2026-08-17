"""AI study features beyond Q&A: summaries and quizzes.

All of these stay grounded: they operate on the actual stored chunks of the
selected source(s), and the quiz cites the passage each question came from.
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from app.models import Chunk, Source
from app.schemas import (
    Citation,
    QuizOption,
    QuizQuestion,
    QuizResponse,
    SummarizeResponse,
)
from app.services import llm_service
from app.utils.helpers import youtube_watch_url
from app.utils.prompts import QUIZ_SYSTEM_PROMPT, SUMMARIZE_PROMPTS, build_context_block

logger = logging.getLogger(__name__)

# Keep prompts within a sane budget for cost/latency.
_MAX_SUMMARY_CHARS = 12_000
_MAX_QUIZ_PASSAGES = 15


def _source_chunks(db, source_id: str) -> list[Chunk]:
    stmt = (
        select(Chunk)
        .where(Chunk.source_id == source_id)
        .order_by(Chunk.chunk_index.asc())
    )
    return list(db.execute(stmt).scalars().all())


def summarize(db, source_id: str, mode: str) -> SummarizeResponse:
    source = db.get(Source, source_id)
    if source is None:
        raise ValueError("Source not found.")
    if mode not in SUMMARIZE_PROMPTS:
        raise ValueError(f"Unknown summarize mode: {mode}")

    chunks = _source_chunks(db, source_id)
    if not chunks:
        raise ValueError("This source has no processed content yet.")

    text = ""
    for c in chunks:
        if len(text) + len(c.text) > _MAX_SUMMARY_CHARS:
            break
        text += c.text + "\n\n"

    result = llm_service.get_llm_provider().complete(
        SUMMARIZE_PROMPTS[mode],
        f"Source: {source.title}\n\nMaterial:\n{text}",
        temperature=0.2,
    )
    return SummarizeResponse(mode=mode, result=result.strip())


def _sample_chunks(chunks: list[Chunk], k: int) -> list[Chunk]:
    """Evenly sample up to k chunks so the quiz spans the whole source."""
    if len(chunks) <= k:
        return chunks
    step = len(chunks) / k
    return [chunks[int(i * step)] for i in range(k)]


def _citation_for_chunk(db, chunk: Chunk) -> Citation:
    source = db.get(Source, chunk.source_id)
    url = None
    if source and source.source_type == "youtube":
        vid = source.meta.get("video_id")
        if vid:
            url = youtube_watch_url(vid, chunk.start_seconds)
    return Citation(
        index=chunk.chunk_index + 1,
        source_id=chunk.source_id,
        chunk_id=chunk.id,
        source_type=source.source_type if source else "text",
        title=source.title if source else "Source",
        snippet=" ".join(chunk.text.split())[:200],
        score=1.0,
        page=chunk.page,
        start_seconds=chunk.start_seconds,
        section=chunk.section,
        url=url,
    )


def generate_quiz(
    db, knowledge_base_id: str, source_id: str | None, num_questions: int
) -> QuizResponse:
    if source_id:
        chunks = _source_chunks(db, source_id)
    else:
        stmt = (
            select(Chunk)
            .where(Chunk.knowledge_base_id == knowledge_base_id)
            .order_by(Chunk.created_at.asc())
        )
        chunks = list(db.execute(stmt).scalars().all())

    if not chunks:
        raise ValueError("No processed content available to build a quiz.")

    sampled = _sample_chunks(chunks, _MAX_QUIZ_PASSAGES)
    passages = [c.text for c in sampled]
    context = build_context_block(passages)

    raw = llm_service.get_llm_provider().complete(
        QUIZ_SYSTEM_PROMPT,
        f"Create {num_questions} questions.\n\nContext passages:\n{context}",
        temperature=0.5,
        json_mode=True,
    )
    data = llm_service.parse_json_response(raw)
    items = data.get("questions", []) if isinstance(data, dict) else []

    questions: list[QuizQuestion] = []
    for item in items[:num_questions]:
        try:
            options = [
                QuizOption(label=o["label"], text=o["text"])
                for o in item["options"]
            ]
            # Map the model's 1-based passage index back to a real chunk.
            p_idx = int(item.get("passage_index", 1)) - 1
            citation = None
            if 0 <= p_idx < len(sampled):
                citation = _citation_for_chunk(db, sampled[p_idx])
            questions.append(
                QuizQuestion(
                    question=item["question"],
                    options=options,
                    correct_label=item["correct_label"],
                    explanation=item.get("explanation", ""),
                    citation=citation,
                )
            )
        except (KeyError, TypeError, ValueError):
            continue  # skip a malformed question rather than failing the batch

    if not questions:
        raise ValueError("Could not generate a valid quiz from this material.")
    return QuizResponse(questions=questions)
