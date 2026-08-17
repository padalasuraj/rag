"""Application configuration.

All runtime configuration is loaded from environment variables (or a local
`.env` file) via pydantic-settings. Nothing is hard-coded, and every provider
(LLM, embeddings, vector store) is selected here so the rest of the codebase
depends on *interfaces*, never on a concrete SDK.

Why pydantic-settings: it gives us typed, validated config with sane defaults
and a single source of truth. If a required secret is missing we fail loudly
at startup instead of deep inside a request.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
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
    llm_provider: Literal["openai"] = "openai"
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_base_url: str | None = None  # lets you point at Azure/OpenRouter/etc.
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.1  # low temperature => less drift, more grounded
    llm_max_tokens: int = 1024

    # ---- Embedding provider -------------------------------------------------
    embedding_provider: Literal["openai"] = "openai"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    embedding_batch_size: int = 96

    # ---- Vector store -------------------------------------------------------
    vector_store: Literal["chroma", "pinecone"] = "chroma"
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
    allowed_upload_types: str = "application/pdf"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_upload_type_list(self) -> list[str]:
        return [t.strip() for t in self.allowed_upload_types.split(",") if t.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Cached accessor so we build Settings exactly once per process."""
    return Settings()


settings = get_settings()
