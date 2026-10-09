"""Durable, filtered cosine search for small free-tier workspaces."""

import heapq
from sqlalchemy import delete, select

from app.config import settings
from app.db import SessionLocal
from app.models import StoredVector
from app.services.vectorstore.base import SearchHit
from app.services.vectorstore.chroma_store import VectorDimensionError
from app.services.vectorstore.factory import InMemoryVectorStore


class SQLVectorStore:
    @property
    def collection(self):
        return f"{settings.embedding_provider}:{settings.embedding_model}:{settings.embedding_dimensions}"

    def upsert(self, records):
        with SessionLocal() as db:
            self.upsert_in_session(db, records)
            db.commit()

    def upsert_in_session(self, db, records):
        for record in records:
            if len(record.embedding) != settings.embedding_dimensions:
                raise VectorDimensionError("Embedding dimensions do not match the configured model.")
            db.merge(StoredVector(
                id=record.id, collection=self.collection,
                knowledge_base_id=record.metadata["knowledge_base_id"],
                source_id=record.metadata["source_id"], embedding=record.embedding,
                text=record.text, meta=record.metadata,
            ))

    def query(self, embedding, top_k, where=None):
        if len(embedding) != settings.embedding_dimensions:
            raise VectorDimensionError("Query embedding dimensions do not match the configured model.")
        if not where or not where.get("knowledge_base_id"):
            raise ValueError("Vector searches must be scoped to a knowledge base.")
        stmt = select(StoredVector).where(
            StoredVector.collection == self.collection,
            StoredVector.knowledge_base_id == where["knowledge_base_id"],
        )
        with SessionLocal() as db:
            hits = (SearchHit(
                id=row.id, text=row.text, metadata=row.meta, embedding=row.embedding,
                score=InMemoryVectorStore._cosine(embedding, row.embedding),
            ) for row in db.execute(stmt.execution_options(yield_per=100)).scalars()
                if all(row.meta.get(k) == v for k, v in where.items()))
            return heapq.nlargest(top_k, hits, key=lambda hit: hit.score)

    def delete(self, ids=None, where=None):
        stmt = delete(StoredVector)
        if ids:
            stmt = stmt.where(StoredVector.id.in_(ids))
        elif where and where.get("source_id"):
            stmt = stmt.where(StoredVector.source_id == where["source_id"])
        elif where and where.get("knowledge_base_id"):
            stmt = stmt.where(StoredVector.knowledge_base_id == where["knowledge_base_id"])
        else:
            return
        with SessionLocal() as db:
            db.execute(stmt)
            db.commit()
