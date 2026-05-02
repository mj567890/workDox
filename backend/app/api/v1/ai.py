"""AI Assistant API routes — RAG Q&A, summarization, embeddings, conversations."""

import json
import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.models.ai import AIConversation, AIMessage
from app.services.rag_service import RAGService
from app.services.summarization_service import SummarizationService

router = APIRouter()
rag_service = RAGService()
summarization_service = SummarizationService()
logger = logging.getLogger(__name__)


# ── Schemas ──────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    document_ids: list[int] | None = None
    conversation_id: int | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict]
    conversation_id: int


class SummarizeRequest(BaseModel):
    document_id: int


class SummarizeResponse(BaseModel):
    document_id: int
    summary: str


class ConversationOut(BaseModel):
    id: int
    title: str
    document_id: int | None
    message_count: int
    created_at: str | None
    updated_at: str | None


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    sources: list[dict] | None
    created_at: str | None


# ── Helpers ──────────────────────────────────────────────────────

async def _get_or_create_conversation(
    db: AsyncSession,
    user_id: int,
    data: ChatRequest,
) -> AIConversation:
    if data.conversation_id:
        result = await db.execute(
            select(AIConversation).where(
                AIConversation.id == data.conversation_id,
                AIConversation.user_id == user_id,
            )
        )
        conv = result.scalars().first()
        if conv:
            return conv
    conv = AIConversation(
        user_id=user_id,
        document_id=data.document_ids[0] if data.document_ids else None,
    )
    db.add(conv)
    await db.flush()
    return conv


# ── Routes ───────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """RAG Q&A — ask questions about documents."""
    chat_history = None
    if data.conversation_id:
        result = await db.execute(
            select(AIMessage)
            .where(AIMessage.conversation_id == data.conversation_id)
            .order_by(AIMessage.created_at)
            .limit(20)
        )
        messages = result.scalars().all()
        chat_history = [
            {"role": m.role, "content": m.content} for m in messages
        ]

    result = await rag_service.ask(
        db,
        data.query,
        document_ids=data.document_ids,
        chat_history=chat_history,
    )

    conv = await _get_or_create_conversation(db, current_user.id, data)
    db.add(
        AIMessage(conversation_id=conv.id, role="user", content=data.query)
    )
    db.add(
        AIMessage(
            conversation_id=conv.id,
            role="assistant",
            content=result["answer"],
            sources=json.dumps(result["sources"], ensure_ascii=False),
        )
    )
    if conv.title == "New Chat":
        conv.title = data.query[:50]
    await db.commit()

    return ChatResponse(
        answer=result["answer"],
        sources=result["sources"],
        conversation_id=conv.id,
    )


@router.post("/chat/stream")
async def chat_stream(
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Streaming RAG Q&A — SSE response."""
    chat_history = None
    if data.conversation_id:
        result = await db.execute(
            select(AIMessage)
            .where(AIMessage.conversation_id == data.conversation_id)
            .order_by(AIMessage.created_at)
            .limit(20)
        )
        messages = result.scalars().all()
        chat_history = [
            {"role": m.role, "content": m.content} for m in messages
        ]

    async def event_stream():
        full_answer = ""
        sources_data = []
        try:
            async for chunk in rag_service.ask_stream(
                db, data.query,
                document_ids=data.document_ids,
                chat_history=chat_history,
            ):
                if chunk["type"] == "sources":
                    sources_data = chunk["data"]
                    yield f"data: {json.dumps({'type': 'sources', 'data': sources_data}, ensure_ascii=False)}\n\n"
                elif chunk["type"] == "token":
                    full_answer += chunk["content"]
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk['content']}, ensure_ascii=False)}\n\n"
                elif chunk["type"] == "done":
                    pass

            # Save conversation after streaming completes
            conv = await _get_or_create_conversation(db, current_user.id, data)
            db.add(AIMessage(conversation_id=conv.id, role="user", content=data.query))
            db.add(AIMessage(
                conversation_id=conv.id, role="assistant",
                content=full_answer,
                sources=json.dumps(sources_data, ensure_ascii=False),
            ))
            if conv.title == "New Chat":
                conv.title = data.query[:50]
            await db.commit()

            yield f"data: {json.dumps({'type': 'done', 'conversation_id': conv.id})}\n\n"
        except Exception:
            logger.exception("Streaming chat error")
            yield f"data: {json.dumps({'type': 'error', 'content': '生成回答时出错'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_document(
    data: SummarizeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate AI summary for a document."""
    from app.models.document import Document

    result = await db.execute(
        select(Document).where(
            Document.id == data.document_id, Document.is_deleted == False
        )
    )
    doc = result.scalars().first()
    if not doc:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("Document not found")

    if not doc.extracted_text:
        from app.core.exceptions import ValidationException
        raise ValidationException(
            "Document has no extracted text. Extract text first."
        )

    summary = await summarization_service.summarize_document(
        doc.extracted_text, doc.original_name
    )
    return SummarizeResponse(document_id=data.document_id, summary=summary)


@router.post("/documents/{doc_id}/embed")
async def embed_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate and store embeddings for a document."""
    count = await rag_service.embed_and_store_document(db, doc_id)
    return {"document_id": doc_id, "chunks_created": count}


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List AI chat conversations for current user."""
    result = await db.execute(
        select(AIConversation)
        .options(selectinload(AIConversation.messages))
        .where(AIConversation.user_id == current_user.id)
        .order_by(AIConversation.updated_at.desc())
        .limit(50)
    )
    convs = result.scalars().all()
    return [
        ConversationOut(
            id=c.id,
            title=c.title,
            document_id=c.document_id,
            message_count=len(c.messages) if c.messages else 0,
            created_at=c.created_at.isoformat() if c.created_at else None,
            updated_at=c.updated_at.isoformat() if c.updated_at else None,
        )
        for c in convs
    ]


@router.get("/conversations/{conv_id}", response_model=list[MessageOut])
async def get_conversation_messages(
    conv_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get messages for a conversation."""
    # Verify ownership
    result = await db.execute(
        select(AIConversation).where(
            AIConversation.id == conv_id,
            AIConversation.user_id == current_user.id,
        )
    )
    if not result.scalars().first():
        from app.core.exceptions import NotFoundException
        raise NotFoundException("Conversation not found")

    result = await db.execute(
        select(AIMessage)
        .where(AIMessage.conversation_id == conv_id)
        .order_by(AIMessage.created_at)
    )
    messages = result.scalars().all()
    return [
        MessageOut(
            id=m.id,
            role=m.role,
            content=m.content,
            sources=json.loads(m.sources) if m.sources else None,
            created_at=m.created_at.isoformat() if m.created_at else None,
        )
        for m in messages
    ]


@router.delete("/conversations/{conv_id}")
async def delete_conversation(
    conv_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation and its messages."""
    result = await db.execute(
        select(AIConversation).where(
            AIConversation.id == conv_id,
            AIConversation.user_id == current_user.id,
        )
    )
    if not result.scalars().first():
        from app.core.exceptions import NotFoundException
        raise NotFoundException("Conversation not found")

    await db.execute(
        delete(AIMessage).where(AIMessage.conversation_id == conv_id)
    )
    await db.execute(
        delete(AIConversation).where(AIConversation.id == conv_id)
    )
    await db.commit()
    return {"status": "deleted"}
