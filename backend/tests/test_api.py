"""API + pipeline integration tests (no external services).

Because FastAPI's TestClient runs BackgroundTasks synchronously after the
response, a source is fully ingested by the time the POST returns.
"""

from __future__ import annotations

import json


def _add_text_source(client, kb_id, title, content):
    resp = client.post(
        "/api/sources/text",
        json={"knowledge_base_id": kb_id, "title": title, "content": content},
    )
    assert resp.status_code == 202, resp.text
    return resp.json()


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["vector_store"] in {"chroma", "pinecone"}
    assert body["llm_provider"] == "ollama"
    assert body["embedding_provider"] == "sentence_transformers"
    assert body["ai_status"] == "connected"


def test_knowledge_base_crud(client):
    created = client.post("/api/knowledge-bases", json={"name": "ML Course"})
    assert created.status_code == 201
    kb = created.json()

    listed = client.get("/api/knowledge-bases")
    assert any(k["id"] == kb["id"] for k in listed.json())

    patched = client.patch(
        f"/api/knowledge-bases/{kb['id']}", json={"name": "ML Course v2"}
    )
    assert patched.json()["name"] == "ML Course v2"

    deleted = client.delete(f"/api/knowledge-bases/{kb['id']}")
    assert deleted.status_code == 204
    assert client.get(f"/api/knowledge-bases/{kb['id']}").status_code == 404


def test_text_ingestion_completes_and_counts(client, kb_id):
    source = _add_text_source(
        client,
        kb_id,
        "Regression Notes",
        "Logistic regression predicts probabilities using the sigmoid function. "
        "It is a linear classifier used for binary classification problems. " * 5,
    )
    # Background ingestion has already run.
    fetched = client.get(f"/api/sources/{source['id']}").json()
    assert fetched["status"] == "completed"
    assert fetched["num_chunks"] >= 1

    kb = client.get(f"/api/knowledge-bases/{kb_id}").json()
    assert kb["source_counts"]["text"] == 1
    assert kb["chunk_count"] >= 1


def test_text_reindex_does_not_mutate_source(client, kb_id):
    source = _add_text_source(
        client,
        kb_id,
        "DBMS Notes",
        "Database management systems organize data and support transactions. " * 5,
    )
    before = client.get(f"/api/sources/{source['id']}").json()

    resp = client.post(f"/api/sources/{source['id']}/reindex")

    assert resp.status_code == 409
    after = client.get(f"/api/sources/{source['id']}").json()
    assert after["status"] == before["status"] == "completed"
    assert after["num_chunks"] == before["num_chunks"]
    assert after["error"] is None


def test_chat_grounded_answer_with_citations(client, kb_id):
    _add_text_source(
        client,
        kb_id,
        "Regression Notes",
        "Logistic regression predicts probabilities using the sigmoid function "
        "for binary classification.",
    )
    resp = client.post(
        "/api/chat",
        json={
            "knowledge_base_id": kb_id,
            "question": "What does logistic regression predict using the sigmoid function?",
            "stream": False,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["grounded"] is True
    assert len(body["citations"]) >= 1
    assert body["citations"][0]["source_type"] == "text"


def test_chat_not_found_on_empty_kb(client, kb_id):
    resp = client.post(
        "/api/chat",
        json={
            "knowledge_base_id": kb_id,
            "question": "What is quantum chromodynamics?",
            "stream": False,
        },
    )
    body = resp.json()
    assert body["grounded"] is False
    assert body["citations"] == []
    assert "couldn't find" in body["answer"].lower()


def test_chat_streaming_emits_sse_events(client, kb_id):
    _add_text_source(
        client, kb_id, "Notes", "Embeddings map text to vectors for semantic search."
    )
    resp = client.post(
        "/api/chat",
        json={
            "knowledge_base_id": kb_id,
            "question": "What do embeddings map text to?",
            "stream": True,
        },
    )
    assert resp.status_code == 200
    text = resp.text
    assert "data:" in text
    # Parse event types out of the SSE stream.
    types = []
    for line in text.splitlines():
        if line.startswith("data:"):
            types.append(json.loads(line[len("data:"):].strip())["type"])
    assert "citations" in types
    assert "token" in types
    assert "done" in types


def test_quiz_generation(client, kb_id):
    source = _add_text_source(
        client,
        kb_id,
        "Overfitting Notes",
        "Overfitting happens when a model learns noise in the training data and "
        "fails to generalize to new data.",
    )
    resp = client.post(
        "/api/quiz",
        json={"knowledge_base_id": kb_id, "source_id": source["id"], "num_questions": 1},
    )
    assert resp.status_code == 200
    questions = resp.json()["questions"]
    assert len(questions) == 1
    assert len(questions[0]["options"]) == 4
    assert questions[0]["correct_label"] in {"A", "B", "C", "D"}


def test_analytics_after_a_question(client, kb_id):
    _add_text_source(
        client, kb_id, "Notes", "Vector databases store embeddings for fast retrieval."
    )
    client.post(
        "/api/chat",
        json={
            "knowledge_base_id": kb_id,
            "question": "What do vector databases store?",
            "stream": False,
        },
    )
    resp = client.get(f"/api/analytics/{kb_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_sources"] == 1
    assert body["questions_asked"] >= 1
