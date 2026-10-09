"""Embeddings.

We hide embeddings behind a Protocol so ingestion and retrieval depend on an
interface, not a concrete model runtime. The default provider uses a local
Sentence Transformers model and batches chunks for faster ingestion.
"""

from __future__ import annotations

import logging
from typing import Protocol

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingError(RuntimeError):
    """User-facing embedding failure that can be shown on source cards."""


class EmbeddingProvider(Protocol):
    dimensions: int

    def embed(self, texts: list[str]) -> list[list[float]]:
        ...


def _load_sentence_transformer(model_name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


class SentenceTransformerEmbeddingProvider:
    """Local embeddings from sentence-transformers."""

    def __init__(self) -> None:
        self.model = settings.embedding_model
        self.dimensions = settings.embedding_dimensions
        self._batch = settings.embedding_batch_size
        try:
            self._model = _load_sentence_transformer(self.model)
        except ImportError as exc:
            raise EmbeddingError(
                "Sentence Transformers is not installed. Run: pip install -r requirements.txt"
            ) from exc
        except OSError as exc:
            raise EmbeddingError(
                f"Embedding model '{self.model}' is unavailable. Install it once while online, "
                "then restart the backend."
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise EmbeddingError(
                f"Could not load embedding model '{self.model}'. Install it once while "
                "online, verify sentence-transformers is installed, then restart the backend."
            ) from exc

        actual_dimensions = self._model.get_sentence_embedding_dimension()
        if actual_dimensions and actual_dimensions != self.dimensions:
            raise EmbeddingError(
                f"Embedding dimension mismatch: model '{self.model}' produces "
                f"{actual_dimensions} dimensions, but EMBEDDING_DIMENSIONS is "
                f"{self.dimensions}. Update EMBEDDING_DIMENSIONS or rebuild the "
                "local Chroma collection for this model."
            )

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors: list[list[float]] = []
        try:
            for start in range(0, len(texts), self._batch):
                batch = texts[start : start + self._batch]
                encoded = self._model.encode(
                    batch,
                    batch_size=self._batch,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                )
                vectors.extend(encoded.astype(float).tolist())
        except RuntimeError as exc:
            message = str(exc).lower()
            if "out of memory" in message or "not enough memory" in message:
                raise EmbeddingError(
                    "Embedding failed because the system ran out of memory. "
                    "Try a smaller embedding model or close other applications."
                ) from exc
            raise EmbeddingError("Failed to generate local embeddings.") from exc

        for vector in vectors:
            if len(vector) != self.dimensions:
                raise EmbeddingError(
                    f"Embedding dimension mismatch: expected {self.dimensions}, "
                    f"got {len(vector)}. Rebuild the local Chroma collection after "
                    "changing embedding models."
                )
        logger.info(
            "event=embed provider=sentence_transformers count=%d model=%s",
            len(texts),
            self.model,
        )
        return vectors


_provider: EmbeddingProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    """Return a cached provider instance selected by configuration."""
    global _provider
    if _provider is None:
        if settings.embedding_provider == "sentence_transformers":
            _provider = SentenceTransformerEmbeddingProvider()
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
