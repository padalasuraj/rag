"""Knowledge base CRUD endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.repositories import knowledge_base_repository as repo
from app.schemas import (
    KnowledgeBaseCreate,
    KnowledgeBaseOut,
    KnowledgeBaseUpdate,
)

router = APIRouter(prefix="/knowledge-bases", tags=["knowledge-bases"])


@router.post("", response_model=KnowledgeBaseOut, status_code=status.HTTP_201_CREATED)
def create_kb(payload: KnowledgeBaseCreate, db: Session = Depends(get_db)):
    kb = repo.create(db, payload.name, payload.description)
    return repo.to_out(db, kb)


@router.get("", response_model=list[KnowledgeBaseOut])
def list_kbs(db: Session = Depends(get_db)):
    return [repo.to_out(db, kb) for kb in repo.list_all(db)]


@router.get("/{kb_id}", response_model=KnowledgeBaseOut)
def get_kb(kb_id: str, db: Session = Depends(get_db)):
    kb = repo.get(db, kb_id)
    if kb is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Knowledge base not found.")
    return repo.to_out(db, kb)


@router.patch("/{kb_id}", response_model=KnowledgeBaseOut)
def update_kb(kb_id: str, payload: KnowledgeBaseUpdate, db: Session = Depends(get_db)):
    kb = repo.get(db, kb_id)
    if kb is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Knowledge base not found.")
    kb = repo.update(db, kb, payload.name, payload.description)
    return repo.to_out(db, kb)


@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_kb(kb_id: str, db: Session = Depends(get_db)):
    kb = repo.get(db, kb_id)
    if kb is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Knowledge base not found.")
    # Also purge this KB's vectors from the vector store.
    from app.services.vectorstore.factory import get_vector_store

    get_vector_store().delete(where={"knowledge_base_id": kb_id})
    repo.delete(db, kb)
    return None
