"""Cloud persistence and cross-workspace authorization regressions."""

import uuid

import fitz
from fastapi.testclient import TestClient

from app.config import settings
from app.db import SessionLocal
from app.main import app
from app.models import StoredFile, StoredVector
from app.services.vectorstore.base import VectorRecord
from app.services.vectorstore.factory import set_vector_store
from app.services.vectorstore.sql_store import SQLVectorStore


def test_other_browser_cannot_access_workspace(client, kb_id):
    source = client.post("/api/sources/text", json={
        "knowledge_base_id": kb_id, "title": "Private notes", "content": "Private source content."
    }).json()
    with TestClient(app) as visitor:
        assert visitor.get("/api/knowledge-bases").json() == []
        for method, path, payload in [
            ("GET", f"/api/knowledge-bases/{kb_id}", None),
            ("DELETE", f"/api/knowledge-bases/{kb_id}", None),
            ("GET", f"/api/sources/{source['id']}", None),
            ("DELETE", f"/api/sources/{source['id']}", None),
            ("GET", f"/api/analytics/{kb_id}", None),
            ("GET", f"/api/chat/{kb_id}/history", None),
            ("POST", "/api/chat", {"knowledge_base_id": kb_id, "question": "Private?"}),
            ("POST", "/api/summarize", {"source_id": source["id"]}),
            ("POST", "/api/quiz", {"knowledge_base_id": kb_id}),
        ]:
            assert visitor.request(method, path, json=payload).status_code == 404
    assert client.get(f"/api/sources/{source['id']}").status_code == 200


def test_pdf_persists_reindexes_and_deletes(client, kb_id):
    document = fitz.open()
    document.new_page().insert_text((72, 72), "Semantic search finds related document passages.")
    data = document.tobytes()
    document.close()
    source = client.post("/api/sources/pdf", data={"knowledge_base_id": kb_id},
                         files={"file": ("notes.pdf", data, "application/pdf")}).json()
    assert client.get(f"/api/sources/{source['id']}").json()["status"] == "completed"
    with SessionLocal() as db:
        assert db.get(StoredFile, source["id"]).content == data
    assert client.get(f"/api/sources/{source['id']}/file").content == data
    with TestClient(app) as visitor:
        assert visitor.get(f"/api/sources/{source['id']}/file").status_code == 404
    assert client.post(f"/api/sources/{source['id']}/reindex").status_code == 202
    assert client.get(f"/api/sources/{source['id']}").json()["status"] == "completed"
    assert client.delete(f"/api/knowledge-bases/{kb_id}").status_code == 204
    with SessionLocal() as db:
        assert db.get(StoredFile, source["id"]) is None


def test_sql_vectors_survive_new_store_and_filter(client, monkeypatch):
    monkeypatch.setattr(settings, "embedding_dimensions", 2)
    kb = uuid.uuid4().hex
    source = uuid.uuid4().hex
    rid = uuid.uuid4().hex
    SQLVectorStore().upsert([VectorRecord(rid, [1.0, 0.0], "Persistent passage", {
        "knowledge_base_id": kb, "source_id": source, "source_type": "text",
    })])
    store = SQLVectorStore()
    hits = store.query([1.0, 0.0], 5, {"knowledge_base_id": kb})
    assert hits[0].id == rid and hits[0].score == 1
    assert store.query([1.0, 0.0], 5, {"knowledge_base_id": "other"}) == []
    assert store.query([1.0, 0.0], 5, {"knowledge_base_id": kb, "source_type": "pdf"}) == []
    monkeypatch.setattr(settings, "embedding_model", "different-model")
    assert store.query([1.0, 0.0], 5, {"knowledge_base_id": kb}) == []
    store.delete(where={"source_id": source})
    with SessionLocal() as db:
        assert db.get(StoredVector, rid) is None


def test_sql_ingestion_commits_chunks_and_vectors_together(client, kb_id, monkeypatch):
    monkeypatch.setattr(settings, "embedding_dimensions", 64)
    set_vector_store(SQLVectorStore())
    source = client.post("/api/sources/text", json={"knowledge_base_id": kb_id,
        "title": "Durable notes", "content": "Embeddings enable semantic retrieval and citation search."}).json()
    assert client.get(f"/api/sources/{source['id']}").json()["status"] == "completed"
    response = client.post("/api/chat", json={"knowledge_base_id": kb_id,
        "question": "What do embeddings enable?", "stream": False})
    assert response.status_code == 200 and response.json()["citations"]
