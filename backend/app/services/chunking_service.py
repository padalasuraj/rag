"""Chunking.

Why chunking matters: embedding models and LLMs have limited context, and
retrieval works best when each stored unit is a coherent, self-contained idea.
We use a recursive, boundary-aware splitter:

- Split on the strongest available boundary first (paragraph -> sentence -> word)
  so we rarely cut mid-thought.
- Keep chunks near `chunk_size` characters.
- Add `chunk_overlap` characters of tail from the previous chunk so a fact that
  straddles a boundary still appears whole in at least one chunk.

Each produced chunk carries positional metadata (page or timestamp) so we can
build precise citations later.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.config import settings
from app.utils.helpers import estimate_tokens

# Ordered from strongest to weakest separators.
_SEPARATORS = ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " "]


@dataclass
class TextChunk:
    text: str
    chunk_index: int
    page: int | None = None
    start_seconds: float | None = None
    section: str | None = None
    token_estimate: int = 0
    extra: dict = field(default_factory=dict)


def _recursive_split(text: str, size: int, seps: list[str]) -> list[str]:
    """Split `text` into pieces <= size, trying separators in order."""
    text = text.strip()
    if len(text) <= size:
        return [text] if text else []

    if not seps:
        # No separators left: hard-cut by size.
        return [text[i : i + size] for i in range(0, len(text), size)]

    sep, *rest = seps
    parts = text.split(sep) if sep != " " else re.split(r"(\s+)", text)
    chunks: list[str] = []
    buf = ""

    for part in parts:
        candidate = f"{buf}{sep}{part}" if buf and sep != " " else buf + part
        if len(candidate) <= size:
            buf = candidate
        else:
            if buf:
                chunks.append(buf)
            if len(part) > size:
                # This single part is still too big -> recurse with weaker seps.
                chunks.extend(_recursive_split(part, size, rest))
                buf = ""
            else:
                buf = part
    if buf:
        chunks.append(buf)
    return [c.strip() for c in chunks if c.strip()]


def _apply_overlap(pieces: list[str], overlap: int) -> list[str]:
    if overlap <= 0 or len(pieces) < 2:
        return pieces
    out = [pieces[0]]
    for prev, cur in zip(pieces, pieces[1:]):
        tail = prev[-overlap:]
        # Start the overlap at a word boundary for readability.
        space = tail.find(" ")
        if space != -1:
            tail = tail[space + 1 :]
        out.append(f"{tail} {cur}".strip())
    return out


def chunk_text(
    text: str,
    *,
    page: int | None = None,
    section: str | None = None,
    size: int | None = None,
    overlap: int | None = None,
    start_index: int = 0,
) -> list[TextChunk]:
    """Chunk a single block of text (one PDF page, one note, etc.)."""
    size = size or settings.chunk_size
    overlap = overlap if overlap is not None else settings.chunk_overlap

    pieces = _recursive_split(text, size, _SEPARATORS)
    pieces = _apply_overlap(pieces, overlap)

    return [
        TextChunk(
            text=piece,
            chunk_index=start_index + i,
            page=page,
            section=section,
            token_estimate=estimate_tokens(piece),
        )
        for i, piece in enumerate(pieces)
    ]


def chunk_pages(pages: list[tuple[int, str]]) -> list[TextChunk]:
    """Chunk PDF pages while preserving page numbers on each chunk.

    `pages` is a list of (page_number, page_text).
    """
    chunks: list[TextChunk] = []
    idx = 0
    for page_number, page_text in pages:
        page_chunks = chunk_text(page_text, page=page_number, start_index=idx)
        chunks.extend(page_chunks)
        idx += len(page_chunks)
    return chunks


def chunk_transcript(segments: list[dict]) -> list[TextChunk]:
    """Chunk a YouTube transcript, attaching the start timestamp of each chunk.

    `segments` is a list of {"text", "start", "duration"}. We greedily pack
    segments up to `chunk_size`, recording the start time of the first segment
    in each chunk so citations can deep-link to the right moment.
    """
    size = settings.chunk_size
    overlap_chars = settings.chunk_overlap
    chunks: list[TextChunk] = []

    buf: list[str] = []
    buf_len = 0
    chunk_start: float | None = None
    idx = 0

    def flush() -> None:
        nonlocal buf, buf_len, chunk_start, idx
        if not buf:
            return
        text = " ".join(buf).strip()
        if text:
            chunks.append(
                TextChunk(
                    text=text,
                    chunk_index=idx,
                    start_seconds=chunk_start,
                    token_estimate=estimate_tokens(text),
                )
            )
            idx += 1
        # Carry a little tail text forward for continuity (approx overlap).
        tail_words = text[-overlap_chars:].split(" ") if overlap_chars else []
        buf = [" ".join(tail_words)] if tail_words else []
        buf_len = len(buf[0]) if buf else 0

    for seg in segments:
        seg_text = (seg.get("text") or "").replace("\n", " ").strip()
        if not seg_text:
            continue
        if chunk_start is None and not buf:
            chunk_start = float(seg.get("start", 0.0))
        if buf_len + len(seg_text) + 1 > size and buf:
            flush()
            chunk_start = float(seg.get("start", 0.0))
        buf.append(seg_text)
        buf_len += len(seg_text) + 1

    flush()
    return chunks
