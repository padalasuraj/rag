"""Vector store abstraction.

This is the key architectural seam of the project. Every retrieval feature
talks to `VectorStore`, never to Chroma or Pinecone directly. That is the
Dependency Inversion Principle in practice: high-level RAG logic depends on an
abstraction, and concrete databases are plugged in at the edge.

Adding a new backend (pgvector, Weaviate, Qdrant, ...) means implementing this
interface and registering it in the factory — with zero changes to retrieval,
ingestion, or the API layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class VectorRecord:
    id: str
    embedding: list[float]
    text: str
    metadata: dict


@dataclass
class SearchHit:
    id: str
    text: str
    metadata: dict
    score: float  # cosine similarity in [0, 1]; higher is more similar
    embedding: list[float] | None = None  # returned when needed for reranking


class VectorStore(Protocol):
    def upsert(self, records: list[VectorRecord]) -> None:
        """Insert or update vectors."""
        ...

    def query(
        self,
        embedding: list[float],
        top_k: int,
        where: dict | None = None,
    ) -> list[SearchHit]:
        """Return the top_k most similar records, optionally metadata-filtered."""
        ...

    def delete(self, ids: list[str] | None = None, where: dict | None = None) -> None:
        """Delete by ids or by metadata filter (e.g. all chunks of a source)."""
        ...
