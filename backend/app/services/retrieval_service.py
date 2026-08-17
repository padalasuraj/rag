"""Retrieval — the read side of RAG.

Pipeline:
1. Embed the (contextualized) query.
2. Pull `retrieval_top_k` candidates from the vector store, scoped to the
   knowledge base and optionally to a source type (metadata filter).
3. Drop candidates below `similarity_threshold` — this is what lets the system
   honestly say "I couldn't find this" instead of answering from noise.
4. Rerank the survivors with Maximal Marginal Relevance (MMR) and keep the top
   `rerank_top_n`. MMR balances relevance to the query against diversity, so we
   don't send the LLM five near-duplicate chunks and miss a complementary one.

Why MMR over a cross-encoder reranker by default: it needs no extra model or
API call (it reuses the embeddings we already fetched), so it keeps the app
zero-dependency to run. A cross-encoder (e.g. bge-reranker) is a documented
drop-in upgrade at this exact step.
"""

from __future__ import annotations

import logging

from app.config import settings
from app.services import embedding_service
from app.services.vectorstore.base import SearchHit
from app.services.vectorstore.factory import get_vector_store

logger = logging.getLogger(__name__)


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def _mmr(
    query_vec: list[float],
    hits: list[SearchHit],
    top_n: int,
    lambda_mult: float,
) -> list[SearchHit]:
    """Greedy Maximal Marginal Relevance selection.

    score(candidate) = λ * sim(candidate, query)
                       - (1 - λ) * max sim(candidate, already_selected)
    """
    usable = [h for h in hits if h.embedding]
    if not usable:
        return hits[:top_n]

    selected: list[SearchHit] = []
    candidates = list(usable)

    while candidates and len(selected) < top_n:
        best_hit = None
        best_score = float("-inf")
        for cand in candidates:
            relevance = _cosine(query_vec, cand.embedding)  # type: ignore[arg-type]
            if selected:
                redundancy = max(
                    _cosine(cand.embedding, s.embedding)  # type: ignore[arg-type]
                    for s in selected
                )
            else:
                redundancy = 0.0
            mmr_score = lambda_mult * relevance - (1 - lambda_mult) * redundancy
            if mmr_score > best_score:
                best_score = mmr_score
                best_hit = cand
        assert best_hit is not None
        selected.append(best_hit)
        candidates.remove(best_hit)

    return selected


def retrieve(
    knowledge_base_id: str,
    query: str,
    *,
    source_type_filter: str = "all",
) -> list[SearchHit]:
    """Return the reranked, grounded set of chunks for a query."""
    query_vec = embedding_service.embed_query(query)

    where: dict = {"knowledge_base_id": knowledge_base_id}
    if source_type_filter and source_type_filter != "all":
        where["source_type"] = source_type_filter

    candidates = get_vector_store().query(
        embedding=query_vec, top_k=settings.retrieval_top_k, where=where
    )

    # Score threshold => honest "not found" behavior downstream.
    grounded = [h for h in candidates if h.score >= settings.similarity_threshold]
    if not grounded:
        logger.info(
            "event=retrieve grounded=0 kb=%s top_score=%.3f",
            knowledge_base_id,
            candidates[0].score if candidates else 0.0,
        )
        return []

    reranked = _mmr(query_vec, grounded, settings.rerank_top_n, settings.mmr_lambda)
    logger.info(
        "event=retrieve kb=%s candidates=%d grounded=%d used=%d",
        knowledge_base_id,
        len(candidates),
        len(grounded),
        len(reranked),
    )
    return reranked
