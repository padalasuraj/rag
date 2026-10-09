# NexusRAG

## Online Deployment Status

The cloud migration is in progress. There is no verified live deployment yet.
The web interface and API are packaged together in the root `Dockerfile`, and
`VECTOR_STORE=sql` stores vectors and original PDFs in the database so uploads
survive hosting restarts when `DATABASE_URL` points to managed PostgreSQL.
Browser workspaces are isolated with an HTTP-only cookie. Keep that cookie to
return to the same workspace; this is not account-based, cross-device login.

Planned free-tier services are Render for hosting, Neon for PostgreSQL, and a
hosted AI provider for generation and embeddings. Provider selection requires
approval because uploaded passages and questions leave the application server.
Hosted AI credentials and hosting-account access have not been configured.
The existing local AI providers remain available until that selection is made.

`deployment/render.yaml.example` is a deployment draft, not a working launch
button. Do not deploy it until the hosted AI provider is implemented and the
runtime secrets are configured. No local installations are required for the
intended online application.

GitHub Actions checks the backend tests, frontend build, and container build.
The cloud dependency set avoids local AI model packages. SQL vector search is
intended for small workspaces, and limits each source to 1,000 chunks; it uses
exact cosine search with the existing threshold and MMR reranking.

Free hosting has limits: Render can sleep after inactivity, Neon has storage
and compute allowances, and AI APIs impose quotas. Free plans do not guarantee
an always-awake service. YouTube extraction requires accessible captions;
scanned PDFs without a text layer require OCR, which is not implemented.

Service references: [Render](https://render.com/docs/free),
[Neon](https://neon.com/pricing),
[Gemini pricing and data use](https://ai.google.dev/gemini-api/docs/pricing).

NexusRAG is a full-stack Retrieval-Augmented Generation app for PDFs, YouTube
transcripts, and pasted text. It runs locally with FastAPI, React, ChromaDB,
SQLite, Ollama for chat generation, and Sentence Transformers for embeddings.

The assistant answers only from retrieved source passages, streams responses over
Server-Sent Events, and attaches citations back to the original PDF page,
YouTube timestamp, or text snippet.

## Features

- Local chat model through Ollama, defaulting to `qwen3:8b`.
- Local embeddings through `sentence-transformers/all-MiniLM-L6-v2`.
- ChromaDB vector storage with provider/model-specific collection names.
- SQLite metadata storage by default.
- PDF, YouTube, and text ingestion with cleaning, chunking, and citation metadata.
- Similarity thresholding plus MMR reranking before generation.
- Grounded chat, contextual follow-up question rewriting, streaming, summaries,
  quiz generation, and retrieval analytics.
- Tests use mock providers and an in-memory vector store, so they do not require
  Ollama or external services.

## Architecture

```text
React frontend
  -> FastAPI backend
  -> local Ollama LLM
  -> local Sentence Transformer embeddings
  -> ChromaDB
  -> SQLite
```

The core RAG flow is unchanged:

```text
Document ingestion
  -> text extraction
  -> cleaning
  -> chunking
  -> local embeddings
  -> ChromaDB
  -> similarity retrieval
  -> threshold filtering
  -> MMR reranking
  -> context construction
  -> local LLM
  -> grounded answer
  -> citations
```

## Local Setup On Windows

Install Python 3.11+, Node.js 18+, and Ollama for Windows:

```powershell
winget install Ollama.Ollama
```

Or download Ollama from:

```text
https://ollama.com/download
```

Pull the default local chat model:

```powershell
ollama pull qwen3:8b
```

Verify the model works:

```powershell
ollama run qwen3:8b
```

Verify the Ollama server is running:

```powershell
Invoke-RestMethod http://localhost:11434/api/tags
```

If your laptop has limited RAM, choose a smaller Ollama model and update
`LLM_MODEL` in `backend/.env`, for example:

```env
LLM_MODEL=qwen3:4b
```

## Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

The API runs at:

```text
http://localhost:8000
```

API docs are available at:

```text
http://localhost:8000/docs
```

The health endpoint reports the local AI provider and whether the configured
Ollama model is installed:

```text
http://localhost:8000/api/health
```

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

## Environment

Copy `backend/.env.example` to `backend/.env`. The default local configuration is:

```env
LLM_PROVIDER=ollama
LLM_MODEL=qwen3:8b
OLLAMA_BASE_URL=http://localhost:11434

EMBEDDING_PROVIDER=sentence_transformers
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSIONS=384

VECTOR_STORE=chroma
DATABASE_URL=sqlite:///./nexusrag.db

CHUNK_SIZE=900
CHUNK_OVERLAP=150

RETRIEVAL_TOP_K=12
RERANK_TOP_N=5
SIMILARITY_THRESHOLD=0.18
MMR_LAMBDA=0.6
```

`sentence-transformers/all-MiniLM-L6-v2` is downloaded the first time the
embedding provider is loaded if it is not already cached. After Ollama and the
embedding model are installed locally, AI features run on your computer.

Changing embedding models changes vector dimensions. NexusRAG uses a generated
Chroma collection name that includes the embedding provider, model, and
dimension so older indexes are not mixed with new local embeddings. If you set
`CHROMA_COLLECTION` manually and change embedding models, rebuild that
collection.

## Docker

The backend image does not install or run Ollama. Run Ollama separately on the
host or as its own service.

For the common Windows host-Ollama workflow, set this in `backend/.env` before
starting Docker:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

Then run:

```powershell
docker compose up --build
```

Open:

```text
http://localhost:8080
```

## Testing

Backend tests use mock AI providers and do not need Ollama:

```powershell
cd backend
pytest
```

## Project Structure

```text
backend/app/services/llm_service.py          Ollama LLM provider
backend/app/services/embedding_service.py    Sentence Transformers provider
backend/app/services/rag_service.py          grounded answer orchestration
backend/app/services/retrieval_service.py    retrieval, thresholding, MMR
backend/app/services/ingestion_service.py    source ingestion and indexing
backend/app/services/vectorstore/            Chroma, Pinecone, test store
frontend/src/                                React app
```

## Troubleshooting

If `/api/health` says the local AI provider is unavailable, start Ollama and try
again.

If `/api/health` says the model is missing, run:

```powershell
ollama pull qwen3:8b
```

If generation fails because there is not enough RAM, use a smaller local model
and set `LLM_MODEL` accordingly.

If embeddings fail to load, reinstall backend dependencies:

```powershell
pip install -r requirements.txt
```

## License

MIT. See [LICENSE](./LICENSE).
