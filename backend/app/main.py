"""NexusRAG API entrypoint.

Wires together configuration, logging, CORS, request tracing, a safe global
exception handler (no stack traces leak to clients), and all routers.
"""

from __future__ import annotations

import logging
import os
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import (
    ai_features,
    analytics,
    chat,
    health,
    knowledge_bases,
    sources,
)
from app.config import settings
from app.db import init_db
from app.logging_config import Timer, configure_logging, request_id_ctx

configure_logging(settings.log_level)
logger = logging.getLogger("nexusrag")

app = FastAPI(
    title=f"{settings.app_name} API",
    version="1.0.0",
    description="Retrieval-Augmented Generation over PDFs, YouTube videos, and text.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_context(request: Request, call_next):
    """Attach a request id and log method/path/status/latency for every call."""
    token = request_id_ctx.set(uuid.uuid4().hex[:8])
    with Timer() as timer:
        response = await call_next(request)
    logger.info(
        "http_request method=%s path=%s status=%s duration_ms=%s",
        request.method,
        request.url.path,
        response.status_code,
        timer.elapsed_ms,
    )
    response.headers["X-Request-ID"] = request_id_ctx.get()
    request_id_ctx.reset(token)
    return response


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Log the full technical detail server-side; return a generic message.
    logger.exception("unhandled_error path=%s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."},
    )


@app.on_event("startup")
def on_startup() -> None:
    os.makedirs(settings.storage_dir, exist_ok=True)
    os.makedirs(settings.chroma_dir, exist_ok=True)
    init_db()
    logger.info(
        "startup app=%s env=%s vector_store=%s llm=%s key_present=%s",
        settings.app_name,
        settings.environment,
        settings.vector_store,
        settings.llm_model,
        bool(settings.openai_api_key),
    )


# Mount routers under the configurable API prefix.
for module in (health, knowledge_bases, sources, chat, ai_features, analytics):
    app.include_router(module.router, prefix=settings.api_prefix)


@app.get("/")
def root() -> dict:
    return {"name": settings.app_name, "docs": "/docs", "api": settings.api_prefix}
