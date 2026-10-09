"""Ingestion pipeline (runs in the background).

This is the write side of RAG. Every source type funnels through the same core:

    extract -> clean -> chunk -> embed -> upsert vectors -> persist chunk rows

Running it as a FastAPI BackgroundTask keeps the upload/enqueue request fast and
non-blocking; the frontend polls the source's `status` to show live progress.
(For heavy production loads you'd move this to Celery/RQ with Redis — the code
is structured so only the invocation changes.)

Each background function opens its OWN database session, because the request
session is closed once the response is returned.
"""

from __future__ import annotations

import logging

from app.db import SessionLocal
from app.config import settings
from app.models import Chunk, Source
from app.services import embedding_service
from app.services.embedding_service import EmbeddingError
from app.services.chunking_service import (
    TextChunk,
    chunk_pages,
    chunk_text,
    chunk_transcript,
)
from app.services.pdf_service import PDFExtractionError, extract_pdf_pages
from app.services.vectorstore.base import VectorRecord
from app.services.vectorstore.factory import get_vector_store
from app.services.youtube_service import YouTubeError, fetch_transcript
from app.utils.helpers import clean_text

logger = logging.getLogger(__name__)


def _set_status(db, source: Source, status: str, error: str | None = None) -> None:
    source.status = status
    source.error = error
    db.add(source)
    db.commit()


def _clean_meta(meta: dict) -> dict:
    """Vector stores reject null metadata values, so drop Nones."""
    return {k: v for k, v in meta.items() if v is not None}


def _index_chunks(db, source: Source, chunks: list[TextChunk]) -> int:
    """Embed chunks, upsert vectors, and persist chunk rows. Returns count."""
    if not chunks:
        raise ValueError("No content to index after chunking.")
    if len(chunks) > settings.max_source_chunks:
        raise EmbeddingError("This source is too large for the free workspace. Split it into smaller documents and upload again.")

    # 1) Persist chunk rows first so each row's UUID becomes the vector id.
    rows = [
        Chunk(
            source_id=source.id,
            knowledge_base_id=source.knowledge_base_id,
            chunk_index=c.chunk_index,
            text=c.text,
            page=c.page,
            start_seconds=c.start_seconds,
            section=c.section,
            token_estimate=c.token_estimate,
        )
        for c in chunks
    ]
    db.add_all(rows)
    db.flush()  # populate row.id

    # 2) Embed all chunk texts in batches.
    vectors = embedding_service.embed_texts([r.text for r in rows])

    # 3) Upsert into the vector store with citation metadata.
    records = [
        VectorRecord(
            id=row.id,
            embedding=vec,
            text=row.text,
            metadata=_clean_meta(
                {
                    "chunk_id": row.id,
                    "source_id": source.id,
                    "knowledge_base_id": source.knowledge_base_id,
                    "source_type": source.source_type,
                    "title": source.title,
                    "chunk_index": row.chunk_index,
                    "page": row.page,
                    "start_seconds": row.start_seconds,
                    "section": row.section,
                }
            ),
        )
        for row, vec in zip(rows, vectors)
    ]
    store = get_vector_store()
    from app.services.vectorstore.sql_store import SQLVectorStore

    if isinstance(store, SQLVectorStore):
        store.upsert_in_session(db, records)
    else:
        store.upsert(records)

    db.commit()
    return len(rows)


# --------------------------------------------------------------------------- #
# Per-source-type entry points (called via BackgroundTasks)
# --------------------------------------------------------------------------- #


def ingest_pdf(source_id: str, file_bytes: bytes) -> None:
    db = SessionLocal()
    try:
        source = db.get(Source, source_id)
        if source is None:
            return
        _set_status(db, source, "processing")
        pages, meta = extract_pdf_pages(file_bytes)
        source.meta = {**source.meta, **meta}
        chunks = chunk_pages(pages)
        count = _index_chunks(db, source, chunks)
        source.num_chunks = count
        _set_status(db, source, "completed")
        logger.info("event=ingest_ok type=pdf source=%s chunks=%d", source_id, count)
    except PDFExtractionError as exc:
        _fail(db, source_id, str(exc))
    except EmbeddingError as exc:
        _fail(db, source_id, str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("event=ingest_error type=pdf source=%s", source_id)
        _fail(db, source_id, "Failed to process the PDF. Please try another file.")
        _ = exc
    finally:
        db.close()


def ingest_youtube(source_id: str, video_id: str) -> None:
    db = SessionLocal()
    try:
        source = db.get(Source, source_id)
        if source is None:
            return
        _set_status(db, source, "processing")
        segments = fetch_transcript(video_id)
        chunks = chunk_transcript(segments)
        count = _index_chunks(db, source, chunks)
        source.num_chunks = count
        source.meta = {**source.meta, "segment_count": len(segments)}
        _set_status(db, source, "completed")
        logger.info("event=ingest_ok type=youtube source=%s chunks=%d", source_id, count)
    except YouTubeError as exc:
        _fail(db, source_id, str(exc))
    except EmbeddingError as exc:
        _fail(db, source_id, str(exc))
    except Exception:  # noqa: BLE001
        logger.exception("event=ingest_error type=youtube source=%s", source_id)
        _fail(db, source_id, "Failed to process the video transcript.")
    finally:
        db.close()


def ingest_text(source_id: str, content: str) -> None:
    db = SessionLocal()
    try:
        source = db.get(Source, source_id)
        if source is None:
            return
        _set_status(db, source, "processing")
        cleaned = clean_text(content)
        chunks = chunk_text(cleaned, section=source.title)
        count = _index_chunks(db, source, chunks)
        source.num_chunks = count
        source.meta = {**source.meta, "char_count": len(cleaned)}
        _set_status(db, source, "completed")
        logger.info("event=ingest_ok type=text source=%s chunks=%d", source_id, count)
    except EmbeddingError as exc:
        _fail(db, source_id, str(exc))
    except Exception:  # noqa: BLE001
        logger.exception("event=ingest_error type=text source=%s", source_id)
        _fail(db, source_id, "Failed to process the pasted text.")
    finally:
        db.close()


def _fail(db, source_id: str, message: str) -> None:
    db.rollback()
    source = db.get(Source, source_id)
    if source is not None:
        _set_status(db, source, "failed", message)


def delete_source_vectors(source_id: str) -> None:
    """Remove all vectors for a source (used when a source is deleted)."""
    get_vector_store().delete(where={"source_id": source_id})
