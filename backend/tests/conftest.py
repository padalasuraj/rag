"""Test configuration.

The whole point: exercise the real RAG pipeline (chunking -> embed -> vector
store -> retrieve -> rerank -> answer) with ZERO external dependencies by
injecting deterministic mock providers and an in-memory vector store through the
same DI hooks the app exposes.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from collections.abc import Iterator

import pytest

# Configure the environment BEFORE importing the app so Settings pick it up.
_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.close(_db_fd)
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"
os.environ["OPENAI_API_KEY"] = "test-key-not-used"
os.environ["STORAGE_DIR"] = tempfile.mkdtemp()
os.environ["CHROMA_DIR"] = tempfile.mkdtemp()

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services import embedding_service, llm_service  # noqa: E402
from app.services.vectorstore.factory import (  # noqa: E402
    InMemoryVectorStore,
    set_vector_store,
)

_EMB_DIM = 64


class MockEmbeddingProvider:
    """Deterministic bag-of-words embedding: shared words => high similarity."""

    dimensions = _EMB_DIM

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    @staticmethod
    def _vec(text: str) -> list[float]:
        v = [0.0] * _EMB_DIM
        for tok in text.lower().split():
            bucket = int(hashlib.md5(tok.encode()).hexdigest(), 16) % _EMB_DIM
            v[bucket] += 1.0
        norm = sum(x * x for x in v) ** 0.5 or 1.0
        return [x / norm for x in v]


class MockLLMProvider:
    def complete(self, system, user, *, temperature=None, json_mode=False) -> str:
        s = system.lower()
        if "quiz" in s:
            return (
                '{"questions": [{"question": "What is tested?",'
                '"options": [{"label":"A","text":"a"},{"label":"B","text":"b"},'
                '{"label":"C","text":"c"},{"label":"D","text":"d"}],'
                '"correct_label": "A", "explanation": "Because.",'
                '"passage_index": 1}]}'
            )
        if "follow-up" in s:
            return '["What next?", "Why?", "How?"]'
        if "standalone search query" in s:
            return user.split("Latest question:")[-1].strip()
        return "This is a grounded answer derived from the passages [1]."

    def stream(self, system, user, *, temperature=None) -> Iterator[str]:
        for token in ["This ", "is ", "a ", "grounded ", "answer ", "[1]"]:
            yield token


@pytest.fixture(autouse=True)
def _inject_providers():
    embedding_service.set_embedding_provider(MockEmbeddingProvider())
    llm_service.set_llm_provider(MockLLMProvider())
    set_vector_store(InMemoryVectorStore())
    yield


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def kb_id(client: TestClient) -> str:
    resp = client.post(
        "/api/knowledge-bases",
        json={"name": "Test KB", "description": "for tests"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]
