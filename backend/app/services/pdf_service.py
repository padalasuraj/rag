"""PDF text extraction.

We use PyMuPDF (imported as `fitz`) because it is fast, accurate on real-world
PDFs, and gives per-page text so we can preserve page numbers for citations.

We deliberately extract page-by-page rather than concatenating the whole
document, because the page boundary is the unit we cite ("Page 12 of X.pdf").
"""

from __future__ import annotations

import logging

from app.utils.helpers import clean_text

logger = logging.getLogger(__name__)


class PDFExtractionError(Exception):
    """Raised when a PDF cannot be opened or contains no extractable text."""


def extract_pdf_pages(file_bytes: bytes) -> tuple[list[tuple[int, str]], dict]:
    """Return (pages, metadata).

    `pages` is a list of (1-based page number, cleaned page text) for pages that
    actually contain text. `metadata` includes page_count and, when available,
    the document title/author from the PDF's own metadata.
    """
    import fitz  # PyMuPDF

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:  # noqa: BLE001 - surface a clean domain error
        raise PDFExtractionError("The file could not be opened as a PDF.") from exc

    pages: list[tuple[int, str]] = []
    try:
        for i, page in enumerate(doc):
            raw = page.get_text("text")
            cleaned = clean_text(raw)
            if cleaned:
                pages.append((i + 1, cleaned))
        meta = {
            "page_count": doc.page_count,
            "pdf_title": (doc.metadata or {}).get("title") or "",
            "pdf_author": (doc.metadata or {}).get("author") or "",
        }
    finally:
        doc.close()

    if not pages:
        raise PDFExtractionError(
            "No extractable text found. The PDF may be scanned images "
            "(OCR is required) or empty."
        )

    logger.info("event=pdf_extract pages_with_text=%d total=%d",
                len(pages), meta["page_count"])
    return pages, meta
