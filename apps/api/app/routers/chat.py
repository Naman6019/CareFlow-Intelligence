import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.db.models import ChatMessage, ChatSession, Document
from app.document_agent.agent import (
    AgentRunError,
    CareFlowDocumentAgent,
)
from app.document_agent.retrieval import (
    DocumentSearchTool,
    build_grounded_answer,
)
from app.schemas.documents import (
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    ChatSessionResponse,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])
search_tool = DocumentSearchTool()
document_agent = CareFlowDocumentAgent(settings)
logger = logging.getLogger(__name__)


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    session: AsyncSession = Depends(get_session),
) -> ChatResponse:
    document_ids = [str(document_id) for document_id in request.document_ids]
    if document_ids:
        ready_ids = set(
            await session.scalars(
                select(Document.id).where(
                    Document.id.in_(document_ids),
                    Document.status == "ready",
                )
            )
        )
        if len(ready_ids) != len(set(document_ids)):
            raise HTTPException(
                status_code=400,
                detail="One or more selected documents are unavailable.",
            )

    if request.session_id is not None:
        chat_session = await session.get(ChatSession, str(request.session_id))
        if chat_session is None:
            raise HTTPException(status_code=404, detail="Chat session not found.")
    else:
        chat_session = ChatSession(
            id=str(uuid4()),
            title=request.question.strip()[:120],
        )
        session.add(chat_session)
        await session.flush()

    session.add(
        ChatMessage(
            id=str(uuid4()),
            session_id=chat_session.id,
            role="user",
            content=request.question.strip(),
            citations=[],
            message_metadata={},
        )
    )

    response_mode = "extractive_grounded_v1"
    model = None
    provider_status = "not_configured"
    agent_trace = []
    retrieved_chunks = 0
    if settings.openrouter_enabled:
        try:
            agent_result = await document_agent.run(
                session,
                request.question,
                document_ids,
            )
            answer = agent_result.answer
            citations = agent_result.citations
            model = agent_result.model
            agent_trace = agent_result.trace
            retrieved_chunks = agent_result.retrieved_chunks
            response_mode = "agentic_rag_v1"
            provider_status = "success"
        except AgentRunError as exc:
            logger.warning("Document agent fallback: %s", exc)
            results = await search_tool.run(
                session,
                request.question,
                document_ids,
                limit=5,
            )
            answer, citations = build_grounded_answer(
                request.question,
                results,
            )
            retrieved_chunks = len(results)
            agent_trace = [
                {
                    "step": 1,
                    "type": "fallback",
                    "tool_name": None,
                    "summary": (
                        "The agent could not complete its bounded tool loop, "
                        "so deterministic document retrieval answered instead."
                    ),
                    "tool_input": {},
                    "result_count": len(results),
                    "error_type": "agent_error",
                }
            ]
            provider_status = "fallback"
    else:
        results = await search_tool.run(
            session,
            request.question,
            document_ids,
            limit=5,
        )
        answer, citations = build_grounded_answer(
            request.question,
            results,
        )
        retrieved_chunks = len(results)
        if not results:
            provider_status = "no_evidence"

    session.add(
        ChatMessage(
            id=str(uuid4()),
            session_id=chat_session.id,
            role="assistant",
            content=answer,
            citations=citations,
            message_metadata={
                "grounded": bool(citations),
                "response_mode": response_mode,
                "model": model,
                "provider_status": provider_status,
                "retrieved_chunks": retrieved_chunks,
                "agent_trace": agent_trace,
            },
        )
    )
    await session.commit()

    return ChatResponse(
        session_id=chat_session.id,
        answer=answer,
        citations=citations,
        grounded=bool(citations),
        response_mode=response_mode,
        model=model,
        agent_trace=agent_trace,
    )


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session(
    session_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ChatSessionResponse:
    chat_session = await session.get(ChatSession, str(session_id))
    if chat_session is None:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    messages = (
        await session.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == chat_session.id)
            .order_by(ChatMessage.created_at, ChatMessage.id)
        )
    ).all()
    return ChatSessionResponse(
        id=chat_session.id,
        title=chat_session.title,
        messages=[
            ChatMessageResponse(
                id=message.id,
                role=message.role,
                content=message.content,
                citations=message.citations,
                response_mode=message.message_metadata.get("response_mode"),
                model=message.message_metadata.get("model"),
                agent_trace=message.message_metadata.get("agent_trace", []),
                created_at=message.created_at,
            )
            for message in messages
        ],
    )
