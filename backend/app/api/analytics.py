"""Analytics endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import KnowledgeBase
from app.schemas import AnalyticsResponse
from app.services import analytics_service
from app.workspace import require_kb

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/{knowledge_base_id}", response_model=AnalyticsResponse)
def analytics(knowledge_base_id: str, db: Session = Depends(get_db)):
    require_kb(db, knowledge_base_id)
    return analytics_service.compute_analytics(db, knowledge_base_id)
