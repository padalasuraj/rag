"""Application configuration.

All runtime configuration is loaded from environment variables (or a local
`.env` file) via pydantic-settings. Provider choices live here so the rest of
the codebase depends on interfaces instead of concrete SDKs.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _backend_path(path: str) -> str:
    value = Path(path)
    if value.is_absolute():
        return str(value)
    return str(BACKEND_DIR / value)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- App ----------------------------------------------------------------
    app_name: str = "NexusRAG"
    environment: Literal["development", "production", "test"] = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api"

    # Comma-separated list of allowed CORS origins (the frontend dev + prod URLs)
    cors_origins: str = "http://localhost:5173,http://localhost:4173"

    # ---- Storage ------------------------------------------------------------
    # SQLite by default => zero setup. Swap DATABASE_URL to a Postgres DSN in prod.
    database_url: str = "sqlite:///./nexusrag.db"
    # Where uploaded PDFs and Chroma's on-disk index live.
    storage_dir: str = "./storage"
    chroma_dir: str = "./storage/chroma"

    # ---- LLM provider -------------------------------------------------------
    llm_provider: Literal["ollama"] = "ollama"
    llm_model: str = "qwen3:8b"
    frontend_dir: str = "./static"
    llm_temperature: float = 0.1  # low temperature => less drift, more grounded
    llm_max_tokens: int = 1024
    ollama_base_url: str = "http://localhost:11434"
    ollama_timeout_seconds: int = 120

    # ---- Embedding provider -------------------------------------------------
    embedding_provider: Literal["sentence_transformers"] = "sentence_transformers"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimensions: int = 384
    embedding_batch_size: int = 64

    # ---- Vector store -------------------------------------------------------
    vector_store: Literal["chroma", "pinecone", "sql"] = "sql"
    chroma_collection: str | None = None
    pinecone_api_key: str = Field(default="", alias="PINECONE_API_KEY")
    pinecone_index: str = "nexusrag"
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"

    # ---- RAG pipeline knobs -------------------------------------------------
    chunk_size: int = 900          # target characters per chunk
    chunk_overlap: int = 150       # characters shared between adjacent chunks
    retrieval_top_k: int = 12      # candidates pulled from the vector store
    rerank_top_n: int = 5          # chunks actually sent to the LLM after MMR
    similarity_threshold: float = 0.18  # cosine-similarity floor for "found it"
    mmr_lambda: float = 0.6        # 1.0 = pure relevance, 0.0 = pure diversity

    # ---- Uploads ------------------------------------------------------------
    max_upload_mb: int = 25
    max_source_chunks: int = 1000
    allowed_upload_types: str = "application/pdf"

    @model_validator(mode="after")
    def _resolve_relative_paths(self):
        self.storage_dir = _backend_path(self.storage_dir)
        self.chroma_dir = _backend_path(self.chroma_dir)
        self.frontend_dir = _backend_path(self.frontend_dir)
        if self.database_url.startswith(("postgres://", "postgresql://")):
            self.database_url = "postgresql+psycopg://" + self.database_url.split("://", 1)[1]
        if (
            self.database_url.startswith("sqlite:///")
            and not self.database_url.startswith("sqlite:////")
        ):
            db_path = self.database_url.removeprefix("sqlite:///")
            if db_path != ":memory:" and not Path(db_path).is_absolute():
                self.database_url = f"sqlite:///{(BACKEND_DIR / db_path).as_posix()}"
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_upload_type_list(self) -> list[str]:
        return [t.strip() for t in self.allowed_upload_types.split(",") if t.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def chroma_collection_name(self) -> str:
        if self.chroma_collection:
            return self.chroma_collection
        suffix = re.sub(
            r"[^a-zA-Z0-9_]+",
            "_",
            f"{self.embedding_provider}_{self.embedding_model}_{self.embedding_dimensions}",
        ).strip("_")
        return f"nexusrag_chunks_{suffix[:40]}"


@lru_cache
def get_settings() -> Settings:
    """Cached accessor so we build Settings exactly once per process."""
    return Settings()


settings = get_settings()
