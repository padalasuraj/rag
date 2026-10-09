from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services import embedding_service, llm_service, ollama_client
from app.services.vectorstore import chroma_store


class FakeArray:
    def __init__(self, rows: list[list[float]]) -> None:
        self._rows = rows

    def astype(self, _dtype):
        return self

    def tolist(self) -> list[list[float]]:
        return self._rows


class FakeSentenceTransformer:
    def __init__(self, dimensions: int = 3) -> None:
        self.dimensions = dimensions
        self.calls: list[list[str]] = []

    def get_sentence_embedding_dimension(self) -> int:
        return self.dimensions

    def encode(self, texts, **_kwargs):
        self.calls.append(list(texts))
        return FakeArray([[1.0, 0.0, 0.0] for _ in texts])


def test_sentence_transformer_provider_batches_and_validates(monkeypatch):
    fake_model = FakeSentenceTransformer()
    monkeypatch.setattr(
        embedding_service,
        "settings",
        SimpleNamespace(
            embedding_model="test-embedding-model",
            embedding_dimensions=3,
            embedding_batch_size=2,
            embedding_provider="sentence_transformers",
        ),
    )
    monkeypatch.setattr(
        embedding_service,
        "_load_sentence_transformer",
        lambda _name: fake_model,
    )

    provider = embedding_service.SentenceTransformerEmbeddingProvider()
    vectors = provider.embed(["alpha", "beta", "gamma"])

    assert vectors == [[1.0, 0.0, 0.0]] * 3
    assert fake_model.calls == [["alpha", "beta"], ["gamma"]]


def test_sentence_transformer_provider_rejects_dimension_mismatch(monkeypatch):
    monkeypatch.setattr(
        embedding_service,
        "settings",
        SimpleNamespace(
            embedding_model="test-embedding-model",
            embedding_dimensions=3,
            embedding_batch_size=2,
            embedding_provider="sentence_transformers",
        ),
    )
    monkeypatch.setattr(
        embedding_service,
        "_load_sentence_transformer",
        lambda _name: FakeSentenceTransformer(dimensions=4),
    )

    with pytest.raises(embedding_service.EmbeddingError, match="dimension mismatch"):
        embedding_service.SentenceTransformerEmbeddingProvider()


def test_ollama_llm_complete_and_stream(monkeypatch):
    monkeypatch.setattr(
        llm_service,
        "settings",
        SimpleNamespace(
            llm_model="qwen3:8b",
            llm_temperature=0.1,
            llm_max_tokens=128,
            llm_provider="ollama",
        ),
    )
    monkeypatch.setattr(
        ollama_client,
        "post_json",
        lambda _path, _payload, model: {"message": {"content": f"done with {model}"}},
    )
    monkeypatch.setattr(
        ollama_client,
        "stream_json_lines",
        lambda _path, _payload, model: iter(
            [{"message": {"content": "hel"}}, {"message": {"content": "lo"}}, {"done": True}]
        ),
    )

    provider = llm_service.OllamaLLMProvider()

    assert provider.complete("system", "user") == "done with qwen3:8b"
    assert "".join(provider.stream("system", "user")) == "hello"


def test_ollama_provider_suppresses_think_blocks(monkeypatch):
    monkeypatch.setattr(
        llm_service,
        "settings",
        SimpleNamespace(
            llm_model="qwen3:8b",
            llm_temperature=0.1,
            llm_max_tokens=128,
            llm_provider="ollama",
        ),
    )
    monkeypatch.setattr(
        ollama_client,
        "post_json",
        lambda _path, _payload, model: {
            "message": {"content": "<think>private notes</think>Final answer [1]."}
        },
    )
    monkeypatch.setattr(
        ollama_client,
        "stream_json_lines",
        lambda _path, _payload, model: iter(
            [
                {"message": {"content": "<thi"}},
                {"message": {"content": "nk>private"}},
                {"message": {"content": " notes</think>Final "}},
                {"message": {"content": "answer [1]."}},
                {"done": True},
            ]
        ),
    )

    provider = llm_service.OllamaLLMProvider()

    assert provider.complete("system", "user") == "Final answer [1]."
    assert "".join(provider.stream("system", "user")) == "Final answer [1]."


def test_ollama_health_reports_missing_model(monkeypatch):
    monkeypatch.setattr(
        ollama_client,
        "get_json",
        lambda _path, model: {"models": [{"name": "other:latest"}]},
    )

    status = ollama_client.probe_ollama("qwen3:8b")

    assert status["status"] == "model_missing"
    assert "ollama pull qwen3:8b" in status["message"]


def test_chroma_dimension_guard_rejects_wrong_size(monkeypatch):
    monkeypatch.setattr(
        chroma_store,
        "settings",
        SimpleNamespace(embedding_dimensions=3),
    )

    with pytest.raises(chroma_store.VectorDimensionError, match="expected 3"):
        chroma_store.ChromaVectorStore._validate_vector_dimensions([[1.0, 2.0]])


def test_chroma_rejects_populated_collection_without_embedding_metadata(monkeypatch):
    monkeypatch.setattr(
        chroma_store,
        "settings",
        SimpleNamespace(
            chroma_collection_name="legacy_collection",
            embedding_provider="sentence_transformers",
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",
            embedding_dimensions=384,
        ),
    )

    store = chroma_store.ChromaVectorStore.__new__(chroma_store.ChromaVectorStore)
    store._collection = SimpleNamespace(metadata={}, count=lambda: 10)

    with pytest.raises(chroma_store.VectorDimensionError, match="no embedding provider metadata"):
        store._validate_collection_metadata()
