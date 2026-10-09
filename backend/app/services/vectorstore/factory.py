"""Vector store factory + an in-memory implementation for tests.

`get_vector_store()` returns the backend selected by config. Tests call
`set_vector_store(InMemoryVectorStore())` so the whole RAG pipeline can be
exercised without any external database.
"""

from __future__ import annotations

import logging

from app.config import settings
from app.services.vectorstore.base import SearchHit, VectorRecord, VectorStore

logger = logging.getLogger(__name__)


class InMemoryVectorStore:
    """Cosine-similarity brute-force store. For tests and tiny demos only."""

    def __init__(self) -> None:
        self._records: dict[str, VectorRecord] = {}

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(y * y for y in b) ** 0.5
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    def upsert(self, records: list[VectorRecord]) -> None:
        for r in records:
            self._records[r.id] = r

    def query(self, embedding, top_k, where=None) -> list[SearchHit]:
        def matches(meta: dict) -> bool:
            if not where:
                return True
            return all(meta.get(k) == v for k, v in where.items())

        scored = [
            SearchHit(
                id=r.id,
                text=r.text,
                metadata=r.metadata,
                score=self._cosine(embedding, r.embedding),
                embedding=r.embedding,
            )
            for r in self._records.values()
            if matches(r.metadata)
        ]
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:top_k]

    def delete(self, ids=None, where=None) -> None:
        if ids:
            for _id in ids:
                self._records.pop(_id, None)
        elif where:
            to_drop = [
                rid
                for rid, r in self._records.items()
                if all(r.metadata.get(k) == v for k, v in where.items())
            ]
            for rid in to_drop:
                self._records.pop(rid, None)


_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _store
    if _store is None:
        if settings.vector_store == "chroma":
            from app.services.vectorstore.chroma_store import ChromaVectorStore

            _store = ChromaVectorStore()
        elif settings.vector_store == "pinecone":
            from app.services.vectorstore.pinecone_store import PineconeVectorStore

            _store = PineconeVectorStore()
        elif settings.vector_store == "sql":
            from app.services.vectorstore.sql_store import SQLVectorStore

            _store = SQLVectorStore()
        else:  # pragma: no cover
            raise ValueError(f"Unknown vector store: {settings.vector_store}")
        logger.info("event=vector_store_init backend=%s", settings.vector_store)
    return _store


def set_vector_store(store: VectorStore) -> None:
    """DI hook for tests."""
    global _store
    _store = store
