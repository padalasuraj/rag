"""Pydantic v2 schemas — the API's public contract.

Keeping request/response models separate from ORM models means the database
shape can change without breaking clients, and validation happens at the edge.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# --------------------------------------------------------------------------- #
# Knowledge bases
# --------------------------------------------------------------------------- #


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class SourceCounts(BaseModel):
    total: int = 0
    pdf: int = 0
    youtube: int = 0
    text: int = 0


class KnowledgeBaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    is_demo: bool
    created_at: datetime
    updated_at: datetime
    source_counts: SourceCounts = SourceCounts()
    chunk_count: int = 0


# --------------------------------------------------------------------------- #
# Sources
# --------------------------------------------------------------------------- #


class YouTubeSourceCreate(BaseModel):
    knowledge_base_id: str
    url: str

    @field_validator("url")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class TextSourceCreate(BaseModel):
    knowledge_base_id: str
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1)


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    knowledge_base_id: str
    source_type: str
    title: str
    status: str
    error: str | None = None
    num_chunks: int
    meta: dict
    created_at: datetime
    updated_at: datetime


# --------------------------------------------------------------------------- #
# Chat + retrieval
# --------------------------------------------------------------------------- #


class Citation(BaseModel):
    index: int  # the [n] marker used in the answer
    source_id: str
    chunk_id: str
    source_type: Literal["pdf", "youtube", "text"]
    title: str
    snippet: str
    score: float
    page: int | None = None
    start_seconds: float | None = None
    section: str | None = None
    url: str | None = None  # deep link (YouTube ?t= or PDF #page=)


class ChatRequest(BaseModel):
    knowledge_base_id: str
    question: str = Field(min_length=1, max_length=4000)
    source_type_filter: Literal["all", "pdf", "youtube", "text"] = "all"
    stream: bool = True


class ChatResponse(BaseModel):
    answer: str
    grounded: bool
    citations: list[Citation]
    related_questions: list[str] = []
    latency_ms: float


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    content: str
    citations: list
    created_at: datetime


# --------------------------------------------------------------------------- #
# AI features
# --------------------------------------------------------------------------- #


class SummarizeRequest(BaseModel):
    source_id: str
    mode: Literal["summary", "key_points", "eli5"] = "summary"


class SummarizeResponse(BaseModel):
    mode: str
    result: str


class QuizRequest(BaseModel):
    knowledge_base_id: str
    source_id: str | None = None
    num_questions: int = Field(default=5, ge=1, le=15)


class QuizOption(BaseModel):
    label: str  # "A" | "B" | "C" | "D"
    text: str


class QuizQuestion(BaseModel):
    question: str
    options: list[QuizOption]
    correct_label: str
    explanation: str
    citation: Citation | None = None


class QuizResponse(BaseModel):
    questions: list[QuizQuestion]


# --------------------------------------------------------------------------- #
# Analytics
# --------------------------------------------------------------------------- #


class SourceUsage(BaseModel):
    source_id: str
    title: str
    source_type: str
    query_hits: int


class AnalyticsResponse(BaseModel):
    knowledge_base_id: str
    total_sources: int
    total_chunks: int
    questions_asked: int
    grounded_answer_rate: float
    avg_retrieval_score: float
    avg_latency_ms: float
    most_queried_sources: list[SourceUsage]


class HealthResponse(BaseModel):
    status: str
    app: str
    environment: str
    vector_store: str
    llm_provider: str
    llm_model: str
    embedding_provider: str
    embedding_model: str
    ai_provider: str
    ai_status: str
    ai_message: str


__all__ = [name for name in dir() if name[0].isupper()]
