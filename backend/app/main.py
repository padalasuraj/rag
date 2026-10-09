"""NexusRAG API entrypoint.

Wires together configuration, logging, CORS, request tracing, a safe global
exception handler (no stack traces leak to clients), and all routers.
"""

from __future__ import annotations

import logging
import os
import uuid
import re
import secrets
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
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
from app.workspace import workspace_id

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
async def private_workspace(request: Request, call_next):
    cookie = request.cookies.get("nexus_workspace", "")
    fresh = not re.fullmatch(r"[a-f0-9]{64}", cookie)
    identity = secrets.token_hex(32) if fresh else cookie
    token = workspace_id.set(identity)
    try:
        response = await call_next(request)
        if fresh:
            response.set_cookie("nexus_workspace", identity, max_age=31536000,
                                httponly=True, secure=settings.environment == "production", samesite="lax")
        return response
    finally:
        workspace_id.reset(token)


@app.get(f"{settings.api_prefix}/session")
def session():
    return {"status": "ok"}


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
        "startup app=%s env=%s vector_store=%s llm_provider=%s llm=%s embedding_provider=%s embedding_model=%s",
        settings.app_name,
        settings.environment,
        settings.vector_store,
        settings.llm_provider,
        settings.llm_model,
        settings.embedding_provider,
        settings.embedding_model,
    )


# Mount routers under the configurable API prefix.
for module in (health, knowledge_bases, sources, chat, ai_features, analytics):
    app.include_router(module.router, prefix=settings.api_prefix)


frontend = Path(settings.frontend_dir)
if (frontend / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=frontend / "assets"), name="assets")


@app.get("/{path:path}", include_in_schema=False)
def frontend_page(path: str):
    if path == settings.api_prefix.lstrip("/") or path.startswith(settings.api_prefix.lstrip("/") + "/"):
        return JSONResponse(status_code=404, content={"detail": "Endpoint not found."})
    index = frontend / "index.html"
    if index.is_file():
        candidate = (frontend / path).resolve()
        if candidate.is_relative_to(frontend.resolve()) and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index)
    if not path:
        return {"name": settings.app_name, "docs": "/docs", "api": settings.api_prefix}
    return JSONResponse(status_code=404, content={"detail": "Page not found."})
