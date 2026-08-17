"""Embeddings.

We hide the embedding provider behind a Protocol so the pipeline depends on an
interface, not on OpenAI. Swapping to Cohere, Voyage, or a local
sentence-transformer means adding one class — nothing else changes.

The default OpenAI implementation batches requests (embedding models accept
many inputs per call), which is far cheaper and faster than one call per chunk.
"""

from __future__ import annotations

import logging
from typing import Protocol

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingProvider(Protocol):
    dimensions: int

    def embed(self, texts: list[str]) -> list[list[float]]:
        ...


class OpenAIEmbeddingProvider:
    """OpenAI embeddings (text-embedding-3-* family)."""

    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Add it to your .env to generate embeddings."
            )
        # Imported lazily so the app can start (and tests can run with mocks)
        # even if the SDK/key is unavailable.
        from openai import OpenAI

        self._client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url or None,
        )
        self.model = settings.embedding_model
        self.dimensions = settings.embedding_dimensions
        self._batch = settings.embedding_batch_size

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch):
            batch = texts[start : start + self._batch]
            resp = self._client.embeddings.create(
                model=self.model,
                input=batch,
                dimensions=self.dimensions,
            )
            vectors.extend(item.embedding for item in resp.data)
        logger.info("event=embed count=%d model=%s", len(texts), self.model)
        return vectors


_provider: EmbeddingProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    """Return a cached provider instance selected by configuration."""
    global _provider
    if _provider is None:
        if settings.embedding_provider == "openai":
            _provider = OpenAIEmbeddingProvider()
        else:  # pragma: no cover - guarded by config Literal
            raise ValueError(f"Unknown embedding provider: {settings.embedding_provider}")
    return _provider


def set_embedding_provider(provider: EmbeddingProvider) -> None:
    """Dependency-injection hook used by tests to plug in a mock."""
    global _provider
    _provider = provider


def embed_texts(texts: list[str]) -> list[list[float]]:
    return get_embedding_provider().embed(texts)


def embed_query(text: str) -> list[float]:
    return get_embedding_provider().embed([text])[0]
