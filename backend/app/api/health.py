"""Health and status endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.config import settings
from app.schemas import HealthResponse
from app.services.ollama_client import probe_ollama

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    ai = probe_ollama(settings.llm_model)
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        environment=settings.environment,
        vector_store=settings.vector_store,
        llm_provider=settings.llm_provider,
        llm_model=settings.llm_model,
        embedding_provider=settings.embedding_provider,
        embedding_model=settings.embedding_model,
        ai_provider=ai["provider"],
        ai_status=ai["status"],
        ai_message=ai["message"],
    )
