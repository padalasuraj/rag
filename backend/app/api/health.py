"""Health and status endpoint.

The frontend hits this on load to detect whether the backend is configured
(e.g. whether an OpenAI key is present) and to show which providers are active.
It never returns the key itself — only whether one is set.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.config import settings
from app.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        environment=settings.environment,
        vector_store=settings.vector_store,
        llm_model=settings.llm_model,
        embedding_model=settings.embedding_model,
        openai_key_present=bool(settings.openai_api_key),
    )
