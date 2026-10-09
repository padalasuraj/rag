# NexusRAG Design Notes

This document explains the engineering choices behind NexusRAG.

## One-Sentence Pitch

NexusRAG is a local-first RAG platform where every answer is grounded in the
user's own sources, cites the exact page or timestamp it came from, and says it
does not know when retrieval cannot support an answer.

## Key Decisions

### Local AI Providers

The app uses Ollama for chat generation and Sentence Transformers for
embeddings. This keeps generation and embeddings on the developer machine after
the required models have been installed.

The current defaults are:

```text
LLM_MODEL=qwen3:8b
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### No LangChain

Chunking, retrieval, MMR reranking, prompt construction, citations, and provider
selection are implemented directly. This keeps the project lightweight and makes
the RAG pipeline easy to inspect in an interview or during debugging.

### Citations Are Computed In Code

The model only sees numbered passages like `[1]` and `[2]`. Citation objects are
assembled from the retrieved chunks' database metadata, so a citation cannot
point to a source that was not retrieved.

### Grounding Uses Prompting Plus A Retrieval Threshold

The system prompt requires answers to use only provided context, but the
similarity threshold is the stronger guardrail. If no retrieved chunk clears
`SIMILARITY_THRESHOLD`, NexusRAG returns the fixed not-found response without
calling the model.

### MMR Reranking

The retriever fetches `RETRIEVAL_TOP_K` candidates, filters by score, and uses
Maximal Marginal Relevance to keep `RERANK_TOP_N` diverse passages. MMR reuses
the embeddings returned by the vector store.

### Query Contextualization

Follow-up questions are rewritten into standalone retrieval queries using the
local chat model. The rewrite only improves retrieval; final answers remain
grounded in the selected knowledge base.

### Provider Abstractions

The LLM, embedding model, and vector store sit behind small protocols or factory
functions. Tests inject mock providers and an in-memory vector store through the
same hooks the app uses at runtime.

### Local Storage Defaults

SQLite stores metadata and ChromaDB stores vectors. The default Chroma collection
name includes the embedding provider, model, and dimensions so old indexes are
not silently mixed with vectors from a different model.

## Scaling Story

For production-scale use:

1. Move ingestion from FastAPI background tasks to a durable worker queue.
2. Use Postgres for metadata.
3. Use a managed or separately hosted vector database when local Chroma is not
   enough.
4. Run multiple stateless FastAPI replicas behind a load balancer.
5. Keep the provider interfaces so model/runtime choices remain replaceable.

## What To Measure

- Grounded answer rate.
- Average retrieval score.
- p95 ingestion time.
- p95 answer latency.
- Faithfulness and answer relevance on a labeled evaluation set.

## Demo Script

1. Start Ollama and pull `qwen3:8b`.
2. Start the FastAPI backend and React frontend.
3. Create a knowledge base and upload a PDF or paste text.
4. Ask a source-covered question and show streamed citations.
5. Ask an off-topic question and show the not-found behavior.
6. Ask a follow-up and show contextual retrieval.
7. Generate a quiz and a summary from the same source.
