from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    classification: Literal["synthetic", "public"]
    byte_size: int
    sha256: str
    status: str
    page_count: int
    chunk_count: int
    error_message: str | None
    created_at: datetime


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]


class Citation(BaseModel):
    number: int
    document_id: str
    filename: str
    chunk_id: int
    page_number: int | None
    excerpt: str
    rank: float


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    session_id: UUID | None = None
    document_ids: list[UUID] = Field(default_factory=list, max_length=20)


class AgentTraceStep(BaseModel):
    step: int
    type: Literal["tool", "answer", "fallback"]
    tool_name: str | None
    summary: str
    tool_input: dict[str, Any] = Field(default_factory=dict)
    result_count: int = 0
    error_type: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    citations: list[Citation]
    grounded: bool
    response_mode: Literal[
        "agentic_rag_v1",
        "openrouter_nemotron_grounded_v1",
        "extractive_grounded_v1",
    ]
    model: str | None
    agent_trace: list[AgentTraceStep] = Field(default_factory=list)


class ChatMessageResponse(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    citations: list[Citation]
    response_mode: str | None = None
    model: str | None = None
    agent_trace: list[AgentTraceStep] = Field(default_factory=list)
    created_at: datetime


class ChatSessionResponse(BaseModel):
    id: str
    title: str
    messages: list[ChatMessageResponse]
