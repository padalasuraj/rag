"""Pinecone implementation of VectorStore (production alternative).

Enable by setting VECTOR_STORE=pinecone and PINECONE_API_KEY in .env. The index
is created on first use as a serverless index with cosine metric matching our
embedding dimensionality.

Note how the *only* thing that changes versus Chroma is this adapter: retrieval,
ingestion, and the API layer are untouched. That is the payoff of the
VectorStore abstraction.
"""

from __future__ import annotations

import logging

from app.config import settings
from app.services.vectorstore.base import SearchHit, VectorRecord

logger = logging.getLogger(__name__)


class PineconeVectorStore:
    def __init__(self) -> None:
        if not settings.pinecone_api_key:
            raise RuntimeError("PINECONE_API_KEY is not set but VECTOR_STORE=pinecone.")
        from pinecone import Pinecone, ServerlessSpec

        self._pc = Pinecone(api_key=settings.pinecone_api_key)
        existing = {ix["name"] for ix in self._pc.list_indexes()}
        if settings.pinecone_index not in existing:
            self._pc.create_index(
                name=settings.pinecone_index,
                dimension=settings.embedding_dimensions,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud=settings.pinecone_cloud, region=settings.pinecone_region
                ),
            )
        self._index = self._pc.Index(settings.pinecone_index)

    @staticmethod
    def _to_pinecone_filter(where: dict | None) -> dict | None:
        if not where:
            return None
        # Pinecone treats multiple top-level keys as implicit AND.
        return {k: {"$eq": v} for k, v in where.items()}

    def upsert(self, records: list[VectorRecord]) -> None:
        if not records:
            return
        vectors = [
            {
                "id": r.id,
                "values": r.embedding,
                # Pinecone stores text inside metadata for retrieval.
                "metadata": {**r.metadata, "text": r.text},
            }
            for r in records
        ]
        # Upsert in batches to stay within request limits.
        for start in range(0, len(vectors), 100):
            self._index.upsert(vectors=vectors[start : start + 100])
        logger.info("event=vector_upsert backend=pinecone count=%d", len(records))

    def query(
        self,
        embedding: list[float],
        top_k: int,
        where: dict | None = None,
    ) -> list[SearchHit]:
        res = self._index.query(
            vector=embedding,
            top_k=top_k,
            include_metadata=True,
            include_values=True,
            filter=self._to_pinecone_filter(where),
        )
        hits: list[SearchHit] = []
        for match in res.get("matches", []):
            meta = dict(match.get("metadata") or {})
            text = meta.pop("text", "")
            values = match.get("values") or None
            hits.append(
                SearchHit(
                    id=match["id"],
                    text=text,
                    metadata=meta,
                    score=float(match.get("score", 0.0)),
                    embedding=list(values) if values else None,
                )
            )
        return hits

    def delete(self, ids: list[str] | None = None, where: dict | None = None) -> None:
        if ids:
            self._index.delete(ids=ids)
        elif where:
            self._index.delete(filter=self._to_pinecone_filter(where))
