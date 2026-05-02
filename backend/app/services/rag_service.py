"""RAG service: document chunking, vector search, and retrieval-augmented generation."""

import re
import logging

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import DocumentChunk
from app.models.document import Document
from app.config import get_settings
from app.services.embedding_service import get_embedding_service
from app.services.llm_service import get_llm_service

logger = logging.getLogger(__name__)


class RAGService:
    # ── Chunking ──────────────────────────────────────────────────

    @staticmethod
    def chunk_text(
        text: str, chunk_size: int = 500, overlap: int = 50
    ) -> list[str]:
        """Split text into overlapping chunks, respecting sentence boundaries."""
        sentences = re.split(r"(?<=[。！？.!?\n])\s*", text)
        chunks: list[str] = []
        current = ""
        for sent in sentences:
            if len(current) + len(sent) <= chunk_size:
                current += sent
            else:
                if current:
                    chunks.append(current.strip())
                if overlap > 0 and chunks:
                    current = current[-overlap:] + sent
                else:
                    current = sent
        if current.strip():
            chunks.append(current.strip())
        return chunks

    # ── Embedding & Storage ───────────────────────────────────────

    async def embed_and_store_document(
        self, db: AsyncSession, doc_id: int
    ) -> int:
        """Chunk document text, generate embeddings, store in document_chunk table."""
        result = await db.execute(
            select(Document.extracted_text).where(Document.id == doc_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return 0
        extracted_text = row

        settings = get_settings()
        chunks = self.chunk_text(
            extracted_text,
            chunk_size=settings.RAG_CHUNK_SIZE,
            overlap=settings.RAG_CHUNK_OVERLAP,
        )
        if not chunks:
            return 0

        emb_service = get_embedding_service()
        embeddings = await emb_service.embed(chunks)

        # Delete old chunks
        await db.execute(
            text("DELETE FROM document_chunk WHERE document_id = :did"),
            {"did": doc_id},
        )

        # Store new chunks
        for i, (chunk_text, emb) in enumerate(zip(chunks, embeddings)):
            db.add(
                DocumentChunk(
                    document_id=doc_id,
                    chunk_index=i,
                    chunk_text=chunk_text,
                    embedding=emb,
                    token_count=len(chunk_text),
                )
            )

        # Store full-document embedding (first 2000 chars)
        full_text = extracted_text[:2000]
        full_embedding = await emb_service.embed_single(full_text)
        from sqlalchemy import update
        await db.execute(
            update(Document).where(Document.id == doc_id).values(embedding=full_embedding)
        )

        await db.commit()
        logger.info(
            "Embedded document %d: %d chunks stored", doc_id, len(chunks)
        )
        return len(chunks)

    # ── Vector Search ─────────────────────────────────────────────

    async def search_similar_chunks(
        self,
        db: AsyncSession,
        query_embedding: list[float],
        top_k: int = 5,
        document_ids: list[int] | None = None,
    ) -> list[dict]:
        """Find top-k most similar chunks by cosine distance."""
        conditions = []
        params: dict = {"embedding": query_embedding, "k": top_k}

        if document_ids:
            conditions.append("dc.document_id = ANY(:doc_ids)")
            params["doc_ids"] = document_ids

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        sql = text(
            f"""
            SELECT dc.id, dc.document_id, dc.chunk_text, dc.chunk_index,
                   1 - (dc.embedding <=> :embedding) AS similarity
            FROM document_chunk dc
            WHERE {where_clause}
            ORDER BY dc.embedding <=> :embedding
            LIMIT :k
        """
        )

        result = await db.execute(sql, params)
        return [
            {
                "chunk_id": row[0],
                "document_id": row[1],
                "chunk_text": row[2],
                "chunk_index": row[3],
                "similarity": round(float(row[4]), 4),
            }
            for row in result.all()
        ]

    # ── Helper ────────────────────────────────────────────────────

    async def _get_doc_name(self, db: AsyncSession, doc_id: int) -> str:
        result = await db.execute(
            select(Document.original_name).where(Document.id == doc_id)
        )
        row = result.scalar_one_or_none()
        return row if row else f"文档#{doc_id}"

    # ── RAG Q&A ───────────────────────────────────────────────────

    async def ask(
        self,
        db: AsyncSession,
        query: str,
        document_ids: list[int] | None = None,
        chat_history: list[dict] | None = None,
    ) -> dict:
        """Full RAG pipeline: embed query → vector search → context → LLM answer."""
        emb_service = get_embedding_service()
        llm_service = get_llm_service()
        settings = get_settings()

        # 1. Embed query
        query_embedding = await emb_service.embed_single(query)

        # 2. Vector search
        chunks = await self.search_similar_chunks(
            db,
            query_embedding,
            top_k=settings.RAG_TOP_K,
            document_ids=document_ids,
        )

        # 3. Build context
        context_parts = []
        for c in chunks:
            doc_name = await self._get_doc_name(db, c["document_id"])
            context_parts.append(f"[文档: {doc_name}] {c['chunk_text']}")
        context = "\n\n---\n\n".join(context_parts) if context_parts else "(无相关文档内容)"

        # 4. Build prompt
        system_prompt = (
            "你是一个专业的文档管理助手。请根据提供的文档内容回答用户问题。\n"
            "规则：\n"
            "1. 仅根据提供的文档片段回答，不要编造信息。\n"
            "2. 如果文档内容不足以回答问题，请明确说明。\n"
            "3. 回答时注明信息来源（文档名称）。\n"
            "4. 使用中文回答。"
        )

        user_prompt = f"文档内容：\n{context}\n\n用户问题：{query}\n\n请回答："

        messages = [{"role": "system", "content": system_prompt}]
        if chat_history:
            messages.extend(chat_history)
        messages.append({"role": "user", "content": user_prompt})

        # 5. Call LLM
        answer = await llm_service.chat(messages, temperature=0.3)

        # 6. Format sources
        sources = [
            {
                "document_id": c["document_id"],
                "document_name": await self._get_doc_name(db, c["document_id"]),
                "chunk_index": c["chunk_index"],
                "similarity": c["similarity"],
                "text_snippet": c["chunk_text"][:200],
            }
            for c in chunks
        ]

        return {"answer": answer, "sources": sources}

    async def ask_stream(
        self,
        db: AsyncSession,
        query: str,
        document_ids: list[int] | None = None,
        chat_history: list[dict] | None = None,
    ):
        """Streaming RAG Q&A — yields SSE chunks."""
        emb_service = get_embedding_service()
        llm_service = get_llm_service()
        settings = get_settings()

        # 1. Embed query
        query_embedding = await emb_service.embed_single(query)

        # 2. Vector search
        chunks = await self.search_similar_chunks(
            db,
            query_embedding,
            top_k=settings.RAG_TOP_K,
            document_ids=document_ids,
        )

        # 3. Build context
        context_parts = []
        for c in chunks:
            doc_name = await self._get_doc_name(db, c["document_id"])
            context_parts.append(f"[文档: {doc_name}] {c['chunk_text']}")
        context = "\n\n---\n\n".join(context_parts) if context_parts else "(无相关文档内容)"

        # 4. Build prompt
        system_prompt = (
            "你是一个专业的文档管理助手。请根据提供的文档内容回答用户问题。\n"
            "规则：\n"
            "1. 仅根据提供的文档片段回答，不要编造信息。\n"
            "2. 如果文档内容不足以回答问题，请明确说明。\n"
            "3. 回答时注明信息来源（文档名称）。\n"
            "4. 使用中文回答。"
        )

        user_prompt = f"文档内容：\n{context}\n\n用户问题：{query}\n\n请回答："

        messages = [{"role": "system", "content": system_prompt}]
        if chat_history:
            messages.extend(chat_history)
        messages.append({"role": "user", "content": user_prompt})

        # 5. Yield sources first, then stream tokens
        sources = [
            {
                "document_id": c["document_id"],
                "document_name": await self._get_doc_name(db, c["document_id"]),
                "chunk_index": c["chunk_index"],
                "similarity": c["similarity"],
                "text_snippet": c["chunk_text"][:200],
            }
            for c in chunks
        ]

        yield {"type": "sources", "data": sources}

        async for token in llm_service.chat_stream(messages, temperature=0.3):
            yield {"type": "token", "content": token}

        yield {"type": "done"}
