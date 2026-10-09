"""ChromaDB implementation of VectorStore (the default backend).

Chroma persists to local disk and needs no external account. We store
precomputed embeddings from the configured local provider, use cosine distance,
and create provider/model-specific collection names by default so old vectors
from a different embedding model are not mixed silently.
"""

from __future__ import annotations

import logging

from app.config import settings
from app.services.vectorstore.base import SearchHit, VectorRecord

logger = logging.getLogger(__name__)


class VectorDimensionError(RuntimeError):
    """Raised when vectors do not match the configured embedding dimensions."""


class ChromaVectorStore:
    def __init__(self) -> None:
        import chromadb

        self._client = chromadb.PersistentClient(path=settings.chroma_dir)
        self._collection = self._client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={
                "hnsw:space": "cosine",
                "embedding_provider": settings.embedding_provider,
                "embedding_model": settings.embedding_model,
                "embedding_dimensions": settings.embedding_dimensions,
            },
            embedding_function=None,
        )
        self._validate_collection_metadata()

    def _validate_collection_metadata(self) -> None:
        metadata = self._collection.metadata or {}
        expected = {
            "embedding_provider": settings.embedding_provider,
            "embedding_model": settings.embedding_model,
            "embedding_dimensions": settings.embedding_dimensions,
        }
        missing = [key for key in expected if key not in metadata]
        if missing and self._collection.count() > 0:
            raise VectorDimensionError(
                f"Chroma collection '{settings.chroma_collection_name}' contains "
                "vectors but has no embedding provider metadata. It may have been "
                "created with an older or different embedding model. Use the "
                "generated local collection name or rebuild the collection before "
                "indexing more documents."
            )
        for key, value in expected.items():
            if key in metadata and metadata[key] != value:
                raise VectorDimensionError(
                    f"Chroma collection '{settings.chroma_collection_name}' was created "
                    f"for {metadata.get('embedding_provider')} / "
                    f"{metadata.get('embedding_model')} / "
                    f"{metadata.get('embedding_dimensions')} dimensions, but the current "
                    f"configuration is {settings.embedding_provider} / "
                    f"{settings.embedding_model} / {settings.embedding_dimensions}. "
                    "Use the generated local collection name or rebuild the collection."
                )

    @staticmethod
    def _validate_vector_dimensions(embeddings: list[list[float]]) -> None:
        for embedding in embeddings:
            if len(embedding) != settings.embedding_dimensions:
                raise VectorDimensionError(
                    f"Embedding dimension mismatch: expected {settings.embedding_dimensions}, "
                    f"got {len(embedding)}. Rebuild the local Chroma collection after "
                    "changing embedding models."
                )

    def upsert(self, records: list[VectorRecord]) -> None:
        if not records:
            return
        embeddings = [r.embedding for r in records]
        self._validate_vector_dimensions(embeddings)
        try:
            self._collection.upsert(
                ids=[r.id for r in records],
                embeddings=embeddings,
                documents=[r.text for r in records],
                metadatas=[r.metadata for r in records],
            )
        except Exception as exc:  # noqa: BLE001
            raise VectorDimensionError(
                "Could not write vectors to Chroma. If you recently changed the "
                "embedding model, rebuild the local Chroma collection."
            ) from exc
        logger.info("event=vector_upsert backend=chroma count=%d", len(records))

    @staticmethod
    def _to_chroma_where(where: dict | None) -> dict | None:
        """Translate a flat {field: value} equality filter to Chroma syntax."""
        if not where:
            return None
        conditions = [{k: {"$eq": v}} for k, v in where.items()]
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    def query(
        self,
        embedding: list[float],
        top_k: int,
        where: dict | None = None,
    ) -> list[SearchHit]:
        self._validate_vector_dimensions([embedding])
        try:
            result = self._collection.query(
                query_embeddings=[embedding],
                n_results=top_k,
                where=self._to_chroma_where(where),
                include=["documents", "metadatas", "distances", "embeddings"],
            )
        except Exception as exc:  # noqa: BLE001
            raise VectorDimensionError(
                "Could not query Chroma. If this collection was built with a "
                "different embedding model, rebuild it with the current local model."
            ) from exc
        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        dists = result.get("distances", [[]])[0]
        embs = result.get("embeddings", [[]])[0] or []

        hits: list[SearchHit] = []
        for i, (_id, doc, meta, dist) in enumerate(zip(ids, docs, metas, dists)):
            similarity = 1.0 - float(dist)
            emb = list(embs[i]) if i < len(embs) else None
            hits.append(
                SearchHit(
                    id=_id,
                    text=doc,
                    metadata=meta or {},
                    score=similarity,
                    embedding=emb,
                )
            )
        return hits

    def delete(self, ids: list[str] | None = None, where: dict | None = None) -> None:
        if ids:
            self._collection.delete(ids=ids)
        elif where:
            self._collection.delete(where=self._to_chroma_where(where))
        logger.info("event=vector_delete backend=chroma ids=%s where=%s", bool(ids), where)
