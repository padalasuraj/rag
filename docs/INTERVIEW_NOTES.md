# NexusRAG — Design Notes & Interview Talking Points

This document is the "why" behind the code. It's written for two audiences: an
interviewer skimming for engineering judgment, and future-me who needs to defend
every decision in a system-design conversation.

---

## 1. The one-sentence pitch

> NexusRAG is a full-stack RAG platform where every answer is grounded in the
> user's own sources and cites the exact page or timestamp it came from — and it
> says "I don't know" instead of hallucinating when the sources don't cover the
> question.

If I can only make one point, it's that last clause. **Honest grounding is the
hard part of RAG**, and most demos skip it. The threshold + code-built citations
+ not-found fallback are the features I'd defend hardest.

---

## 2. Decisions & tradeoffs

### 2.1 No LangChain — the OpenAI SDK used directly

**Decision:** implement chunking, retrieval, reranking, and prompting myself
instead of pulling in LangChain/LlamaIndex.

**Why:** for a portfolio project the goal is to *demonstrate* that I understand
the pipeline, not hide it behind a framework. Direct implementation also means
fewer version-churn dependencies, smaller install, and full control over the
prompt and citation construction. In a real product with a large team I'd
reconsider — a framework buys ecosystem integrations — but here the transparency
is the point.

**Tradeoff:** I re-implement things a framework gives free (splitters, retriever
interfaces). Accepted, because each is small and well-understood.

### 2.2 Citations are computed in code, not asked of the model

**Decision:** the model is told to reference sources as `[1]`, `[2]`, … but the
*citation objects* (title, page, timestamp, snippet, score) are assembled in
Python from the retrieved chunks' metadata and returned alongside the answer.

**Why:** if you ask the LLM to emit citation metadata, it will happily invent
plausible-looking page numbers. By binding citations to the actual retrieved
chunks, a citation **cannot** point at something that wasn't in the context.
This is the single most important trust decision in the app.

### 2.3 Grounding via prompt + threshold, not fine-tuning

**Decision:** a strict system prompt ("answer only from the context; if it's not
there, say so") plus a similarity threshold that discards weak retrievals before
they ever reach the model.

**Why:** the threshold is the real safety net. A good prompt reduces
hallucination; a hard retrieval floor makes "not found" a *structural* outcome
rather than something we hope the model chooses. If the best chunk's score is
below `SIMILARITY_THRESHOLD`, we short-circuit and return the honest fallback
without spending a generation call.

**Tradeoff:** the threshold needs tuning per embedding model. It's an env var for
exactly that reason, and analytics surface the grounded-answer rate so it's
observable.

### 2.4 MMR reranking, reusing embeddings

**Decision:** fetch `top_k` (12) candidates, then rerank down to `top_n` (5) with
Maximal Marginal Relevance.

**Why:** naive top-k often returns five paraphrases of the same passage, which
wastes context and biases the answer. MMR trades a little relevance for diversity
so the model sees complementary evidence. I reuse the embeddings already returned
by the vector query to compute pairwise similarity, so reranking costs **zero
extra API calls** — a deliberate cost/latency choice.

### 2.5 Query contextualization for follow-ups

**Decision:** when there are ≥2 prior turns, rewrite the incoming question into a
standalone query before retrieval.

**Why:** "what about the second one?" has no useful embedding on its own.
Rewriting it against history ("what are the drawbacks of the second approach the
document lists?") is what makes multi-turn retrieval actually work. It's one
cheap LLM call and it's the difference between a demo and a usable assistant.

### 2.6 Provider abstractions (vector store, LLM, embeddings)

**Decision:** each external dependency sits behind a small `Protocol`, with a
factory selecting the implementation from config. Chroma/Pinecone, SQLite/
Postgres, and the OpenAI clients are all swappable.

**Why:** it keeps the core logic testable (I inject mock providers + an in-memory
vector store in tests, so the suite runs with no key and no network) and it makes
the "how would you productionize this" answer concrete: flip two env vars.

### 2.7 SQLite + local Chroma by default

**Decision:** default to zero-infrastructure storage.

**Why:** a reviewer should be able to `pip install`, add one key, and have a
working system in two minutes. The abstractions above mean this is a *default*,
not a ceiling — Postgres + Pinecone is an env change, not a rewrite.

### 2.8 Background ingestion + status polling

**Decision:** ingestion runs in a FastAPI background task; the source row moves
`pending → processing → completed/failed`; the UI polls until done.

**Why:** embedding a long PDF takes seconds-to-minutes; blocking the request
would be a terrible UX and risk timeouts. Polling is the simplest correct answer
at this scale. **This is also my headline scaling seam** (see §4).

### 2.9 SSE for streaming (not WebSockets)

**Decision:** stream tokens over Server-Sent Events.

**Why:** the data flow is one-directional (server → client) and request-scoped.
SSE is simpler than WebSockets for that shape, works over plain HTTP, and needs
only a small nginx tweak (`proxy_buffering off`). WebSockets would be over-
engineering here.

---

## 3. Likely interview questions (and my answers)

**Q: How do you stop the model from hallucinating?**
Three layers: (1) a hard similarity threshold discards weak retrievals before
generation; (2) a strict grounding prompt; (3) citations are built from real
retrieved metadata in code, so a citation can't reference something outside the
context. If nothing clears the threshold, we return a fixed not-found message and
never call the model.

**Q: Why chunk overlap, and how did you pick the size?**
Overlap prevents a concept from being severed at a chunk boundary and lost to
retrieval. ~900 chars with ~150 overlap balances retrieval granularity against
context bloat for `gpt-4o-mini`; both are env-tunable. I split on sentence
boundaries where possible so chunks read coherently.

**Q: What's your retrieval quality strategy?**
Cosine similarity for candidates, a score floor for precision, MMR for diversity.
I log per-answer relevance and grounded-rate to `QueryLog` so quality is
measurable, not vibes. Next step would be hybrid (BM25 + dense) retrieval and a
cross-encoder reranker.

**Q: How would this scale to 10k users / millions of documents?**
See §4 — the short version: move ingestion to a Celery/Redis worker pool, swap
Chroma→Pinecone and SQLite→Postgres (both one env var), make the API stateless
behind a load balancer, and add per-tenant isolation via a namespace/metadata
filter on the vector store.

**Q: Where's the state? Is the API stateless?**
The API is effectively stateless already — all durable state lives in the
metadata DB and the vector store. Conversational "memory" is just persisted chat
rows re-read per request, not in-process state. That's what makes horizontal
scaling a config change rather than a refactor.

**Q: How do citations to timestamps/pages actually work?**
Each chunk stores its origin metadata at ingestion time (PDF page or transcript
start-seconds). At answer time those travel with the retrieved chunk into the
citation object, and the frontend builds a deep link — `file#page=N` for PDFs,
`youtube.com/watch?v=…&t=Ns` for video.

**Q: What did you deliberately *not* build, and why?**
Auth/multi-tenancy, an in-app PDF viewer with highlight spans, and a durable job
queue. Each is a known extension point (§5 of the README). I scoped to a
single-user, locally-runnable system that demonstrates the RAG engineering
clearly, and documented the seams rather than half-building them.

---

## 4. Scaling story (the whiteboard version)

```
                    ┌────────────┐
   users ─────────► │   nginx /  │
                    │    LB      │
                    └─────┬──────┘
                          │ (stateless)
                ┌─────────┴─────────┐
                │  FastAPI replicas │
                └───┬───────────┬───┘
        enqueue job │           │ read/write
                    ▼           ▼
              ┌──────────┐  ┌───────────┐   ┌──────────────┐
              │  Redis   │  │ Postgres  │   │  Pinecone    │
              │  queue   │  │ metadata  │   │ vector store │
              └────┬─────┘  └───────────┘   └──────────────┘
                   │ consume
              ┌────▼──────────┐
              │ Celery workers│  (extract · chunk · embed · upsert)
              └───────────────┘
```

Key moves, each already accounted for in the design:

1. **Ingestion → worker pool.** Today's background task becomes a Celery job on
   Redis. Ingestion is independently scalable and survives API restarts. The
   `pending/processing` status model already assumes async completion, so the
   API and UI don't change.
2. **Vector store → Pinecone** (`VECTOR_STORE=pinecone`). Managed ANN over
   millions of vectors; per-tenant isolation via namespaces.
3. **Metadata → Postgres** (`DATABASE_URL=postgresql+psycopg://…`). SQLAlchemy
   means no query changes.
4. **API replicas behind a load balancer.** Stateless, so this is pure
   horizontal scale.
5. **Cost/latency controls.** Embedding is batched; MMR reuses fetched vectors;
   the threshold avoids generation calls on unanswerable queries; responses
   stream so perceived latency is low.

---

## 5. What I'd measure in production

- **Grounded-answer rate** — already tracked; the core trust metric.
- **Retrieval relevance** (mean similarity of used chunks) — already tracked.
- **Faithfulness / answer-relevance** via an eval harness (LLM-as-judge on a
  labelled set) — the biggest missing piece and my next build.
- **p95 ingestion time** and **p95 answer latency** — SLOs for the two pipelines.

---

## 6. Thirty-second demo script

1. Create a knowledge base; drop in a technical PDF **and** a related YouTube
   talk. Watch them index (status pills go Ready).
2. Ask a factual question → answer streams in, with a citation. Click it →
   the PDF opens at the exact page (or the video jumps to the timestamp).
3. Ask a follow-up ("and what about the trade-offs?") → contextualization makes
   retrieval still work.
4. Ask something off-topic → the assistant honestly says it isn't in the
   sources. **This is the moment that sells the project.**
5. Open **Study** → generate a quiz from the sources; every answer has an
   explanation + citation. Open **Analytics** → grounded rate, relevance,
   most-queried sources.
