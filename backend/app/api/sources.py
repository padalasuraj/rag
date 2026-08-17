"""Source ingestion + management endpoints.

Uploads/enqueues return immediately with a `pending` source; the heavy pipeline
runs in a BackgroundTask and the frontend polls GET /sources/{id} for status.
"""

from __future__ import annotations

import os

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import KnowledgeBase, Source
from app.schemas import SourceOut, TextSourceCreate, YouTubeSourceCreate
from app.services import ingestion_service
from app.services.youtube_service import YouTubeError, fetch_metadata
from app.utils.helpers import extract_youtube_id

router = APIRouter(prefix="/sources", tags=["sources"])


def _require_kb(db: Session, kb_id: str) -> KnowledgeBase:
    kb = db.get(KnowledgeBase, kb_id)
    if kb is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Knowledge base not found.")
    return kb


def _pdf_dir() -> str:
    path = os.path.join(settings.storage_dir, "pdfs")
    os.makedirs(path, exist_ok=True)
    return path


# --------------------------------------------------------------------------- #
# Create
# --------------------------------------------------------------------------- #


@router.post("/pdf", response_model=SourceOut, status_code=status.HTTP_202_ACCEPTED)
async def add_pdf(
    background: BackgroundTasks,
    knowledge_base_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    _require_kb(db, knowledge_base_id)

    if file.content_type not in settings.allowed_upload_type_list:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Unsupported file type '{file.content_type}'. Only PDF is allowed.",
        )

    data = await file.read()
    if len(data) == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The uploaded file is empty.")
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"File exceeds the {settings.max_upload_mb} MB limit.",
        )

    title = (file.filename or "document.pdf").rsplit("/", 1)[-1]
    source = Source(
        knowledge_base_id=knowledge_base_id,
        source_type="pdf",
        title=title,
        status="pending",
        meta={"filename": title, "size_bytes": len(data)},
    )
    db.add(source)
    db.commit()
    db.refresh(source)

    # Persist the original file so citations can open the PDF at a page.
    file_path = os.path.join(_pdf_dir(), f"{source.id}.pdf")
    with open(file_path, "wb") as fh:
        fh.write(data)
    source.meta = {**source.meta, "file_path": file_path}
    db.add(source)
    db.commit()
    db.refresh(source)

    background.add_task(ingestion_service.ingest_pdf, source.id, data)
    return source


@router.post("/youtube", response_model=SourceOut, status_code=status.HTTP_202_ACCEPTED)
def add_youtube(
    payload: YouTubeSourceCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    _require_kb(db, payload.knowledge_base_id)

    video_id = extract_youtube_id(payload.url)
    if not video_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "That does not look like a valid YouTube URL."
        )

    # Quick, best-effort metadata so the source card shows a real title now.
    meta = fetch_metadata(video_id)
    source = Source(
        knowledge_base_id=payload.knowledge_base_id,
        source_type="youtube",
        title=meta.get("title", f"YouTube video {video_id}"),
        status="pending",
        meta={
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "channel": meta.get("channel", ""),
            "thumbnail": meta.get("thumbnail", ""),
        },
    )
    db.add(source)
    db.commit()
    db.refresh(source)

    background.add_task(ingestion_service.ingest_youtube, source.id, video_id)
    return source


@router.post("/text", response_model=SourceOut, status_code=status.HTTP_202_ACCEPTED)
def add_text(
    payload: TextSourceCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    _require_kb(db, payload.knowledge_base_id)

    source = Source(
        knowledge_base_id=payload.knowledge_base_id,
        source_type="text",
        title=payload.title,
        status="pending",
        meta={"char_count": len(payload.content)},
    )
    db.add(source)
    db.commit()
    db.refresh(source)

    background.add_task(ingestion_service.ingest_text, source.id, payload.content)
    return source


# --------------------------------------------------------------------------- #
# Read / delete
# --------------------------------------------------------------------------- #


@router.get("", response_model=list[SourceOut])
def list_sources(knowledge_base_id: str, db: Session = Depends(get_db)):
    _require_kb(db, knowledge_base_id)
    stmt = (
        select(Source)
        .where(Source.knowledge_base_id == knowledge_base_id)
        .order_by(Source.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


@router.get("/{source_id}", response_model=SourceOut)
def get_source(source_id: str, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Source not found.")
    return source


@router.post("/{source_id}/reindex", response_model=SourceOut, status_code=202)
def reindex_source(
    source_id: str, background: BackgroundTasks, db: Session = Depends(get_db)
):
    """Re-run ingestion for a source (e.g. after a transient failure)."""
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Source not found.")

    # Clear previous vectors + chunk rows before rebuilding.
    ingestion_service.delete_source_vectors(source_id)
    for chunk in list(source.chunks):
        db.delete(chunk)
    source.status = "pending"
    source.error = None
    source.num_chunks = 0
    db.commit()

    if source.source_type == "youtube":
        background.add_task(
            ingestion_service.ingest_youtube, source.id, source.meta.get("video_id")
        )
    elif source.source_type == "pdf":
        file_path = source.meta.get("file_path")
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status.HTTP_409_CONFLICT, "Original PDF is no longer available.")
        with open(file_path, "rb") as fh:
            background.add_task(ingestion_service.ingest_pdf, source.id, fh.read())
    else:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Text sources cannot be re-indexed automatically."
        )
    db.refresh(source)
    return source


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(source_id: str, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Source not found.")

    ingestion_service.delete_source_vectors(source_id)
    file_path = source.meta.get("file_path")
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass
    db.delete(source)
    db.commit()
    return None


@router.get("/{source_id}/file")
def get_source_file(source_id: str, db: Session = Depends(get_db)):
    """Serve the original PDF so a citation can open it (#page=N)."""
    source = db.get(Source, source_id)
    if source is None or source.source_type != "pdf":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "PDF not found.")
    file_path = source.meta.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "PDF file is unavailable.")
    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=source.meta.get("filename", "document.pdf"),
    )
