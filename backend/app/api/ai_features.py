"""AI feature endpoints: summaries and quizzes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    QuizRequest,
    QuizResponse,
    SummarizeRequest,
    SummarizeResponse,
)
from app.services import ai_features_service
from app.services.llm_service import LLMError
from app.workspace import require_kb, require_source

router = APIRouter(tags=["ai-features"])


@router.post("/summarize", response_model=SummarizeResponse)
def summarize(payload: SummarizeRequest, db: Session = Depends(get_db)):
    require_source(db, payload.source_id)
    try:
        return ai_features_service.summarize(db, payload.source_id, payload.mode)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    except LLMError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))


@router.post("/quiz", response_model=QuizResponse)
def quiz(payload: QuizRequest, db: Session = Depends(get_db)):
    require_kb(db, payload.knowledge_base_id)
    if payload.source_id:
        source = require_source(db, payload.source_id)
        if source.knowledge_base_id != payload.knowledge_base_id:
            raise HTTPException(400, "Source does not belong to this knowledge base.")
    try:
        return ai_features_service.generate_quiz(
            db, payload.knowledge_base_id, payload.source_id, payload.num_questions
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    except LLMError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))
