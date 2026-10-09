"""Chat endpoints — grounded Q&A over a knowledge base."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ChatMessage, KnowledgeBase
from app.schemas import ChatRequest, ChatResponse, MessageOut
from app.services.embedding_service import EmbeddingError
from app.services.llm_service import LLMError
from app.services import rag_service
from app.services.vectorstore.chroma_store import VectorDimensionError
from app.workspace import require_kb

router = APIRouter(tags=["chat"])

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",  # disable proxy buffering so tokens stream live
}


def _require_kb(db: Session, kb_id: str) -> None:
    require_kb(db, kb_id)


@router.post("/chat")
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """Ask a question. Returns SSE when `stream=true`, else a JSON ChatResponse."""
    _require_kb(db, request.knowledge_base_id)

    if request.stream:
        return StreamingResponse(
            rag_service.answer_stream(db, request),
            media_type="text/event-stream",
            headers=_SSE_HEADERS,
        )
    try:
        result: ChatResponse = rag_service.answer(db, request)
        return result
    except (EmbeddingError, LLMError, VectorDimensionError) as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc


@router.get("/chat/{kb_id}/history", response_model=list[MessageOut])
def history(kb_id: str, db: Session = Depends(get_db)):
    _require_kb(db, kb_id)
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.knowledge_base_id == kb_id)
        .order_by(ChatMessage.created_at.asc())
    )
    return list(db.execute(stmt).scalars().all())


@router.delete("/chat/{kb_id}/history", status_code=status.HTTP_204_NO_CONTENT)
def clear_history(kb_id: str, db: Session = Depends(get_db)):
    _require_kb(db, kb_id)
    db.execute(delete(ChatMessage).where(ChatMessage.knowledge_base_id == kb_id))
    db.commit()
    return None
