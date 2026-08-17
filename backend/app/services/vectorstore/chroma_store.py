"""ChromaDB implementation of VectorStore (the default backend).

Chroma is chosen as the default because it persists to local disk and needs no
external account or network service — so the whole app runs with `docker compose
up` and a single OpenAI key. For production scale, swap to Pinecone/pgvector via
the factory; nothing else changes.

We store precomputed embeddings (embedding_function=None) so the OpenAI
embedding provider stays the single source of truth for vectors, and we set the
collection distance to cosine. Chroma returns cosine *distance*
(1 - similarity), which we convert back to a similarity score.
"""

from __future__ import annotations

import logging

from app.config import settings
from app.services.vectorstore.base import SearchHit, VectorRecord

logger = logging.getLogger(__name__)


class ChromaVectorStore:
    def __init__(self) -> None:
        import chromadb

        self._client = chromadb.PersistentClient(path=settings.chroma_dir)
        # cosine space matches normalized embedding similarity.
        self._collection = self._client.get_or_create_collection(
            name="nexusrag_chunks",
            metadata={"hnsw:space": "cosine"},
            embedding_function=None,
        )

    def upsert(self, records: list[VectorRecord]) -> None:
        if not records:
            return
        self._collection.upsert(
            ids=[r.id for r in records],
            embeddings=[r.embedding for r in records],
            documents=[r.text for r in records],
            metadatas=[r.metadata for r in records],
        )
        logger.info("event=vector_upsert backend=chroma count=%d", len(records))

    @staticmethod
    def _to_chroma_where(where: dict | None) -> dict | None:
        """Translate a flat {field: value} equality filter to Chroma syntax.

        Chroma needs an explicit $and when more than one condition is present.
        """
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
        result = self._collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            where=self._to_chroma_where(where),
            include=["documents", "metadatas", "distances", "embeddings"],
        )
        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        dists = result.get("distances", [[]])[0]
        embs = result.get("embeddings", [[]])[0] or []

        hits: list[SearchHit] = []
        for i, (_id, doc, meta, dist) in enumerate(zip(ids, docs, metas, dists)):
            # cosine distance -> similarity
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
