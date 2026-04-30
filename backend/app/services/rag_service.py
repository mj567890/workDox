"""RAG service: document chunking, vector search, and retrieval-augmented generation."""

import re
import logging

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import DocumentChunk
from app.models.document import Document
from app.services.embedding_service import get_embedding_service
from app.services import llm_service
from app.services.ai_config import get_rag_params
from app.services.tool_service import TOOLS, execute_tool

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

        rag_params = await get_rag_params(db)
        chunks = self.chunk_text(
            extracted_text,
            chunk_size=rag_params["chunk_size"],
            overlap=rag_params["chunk_overlap"],
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
        emb_str = "[" + ",".join(str(v) for v in full_embedding) + "]"
        await db.execute(
            text("UPDATE document SET embedding = CAST(:emb AS vector) WHERE id = :did"),
            {"emb": emb_str, "did": doc_id},
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
        # Convert embedding list to pgvector-compatible string format
        emb_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        conditions = []
        params: dict = {"embedding": emb_str, "k": top_k}

        if document_ids:
            conditions.append("dc.document_id = ANY(:doc_ids)")
            params["doc_ids"] = document_ids

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        sql = text(
            f"""
            SELECT dc.id, dc.document_id, dc.chunk_text, dc.chunk_index,
                   1 - (dc.embedding <=> CAST(:embedding AS vector)) AS similarity
            FROM document_chunk dc
            WHERE {where_clause}
            ORDER BY dc.embedding <=> CAST(:embedding AS vector)
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

    async def _get_library_summary(self, db: AsyncSession) -> str:
        """Build a summary of the document library so the AI knows what it manages."""
        result = await db.execute(
            select(
                Document.id, Document.original_name, Document.file_type,
                Document.status,
            ).where(Document.is_deleted == False).order_by(Document.id)
        )
        docs = result.all()
        if not docs:
            return "文档库中暂无文档。"

        total = len(docs)
        lines = [f"文档库共有 {total} 个文档："]
        for d in docs:
            lines.append(f"  [{d[0]}] {d[1]}（{d[2]}, 状态: {d[3]}）")
        return "\n".join(lines)

    # ── RAG Q&A ───────────────────────────────────────────────────

    async def ask(
        self,
        db: AsyncSession,
        query: str,
        provider: dict,
        document_ids: list[int] | None = None,
        chat_history: list[dict] | None = None,
    ) -> dict:
        """Agent RAG pipeline: vector search context + tools → LLM answer."""
        emb_service = get_embedding_service()
        rag_params = await get_rag_params(db)

        # 1. Embed query
        query_embedding = await emb_service.embed_single(query)

        # 2. Vector search
        chunks = await self.search_similar_chunks(
            db,
            query_embedding,
            top_k=rag_params["top_k"],
            document_ids=document_ids,
        )

        # 3. Build messages with library context + vector results + tools
        library_summary = await self._get_library_summary(db)

        # Build vector context for system prompt
        vector_context = ""
        if chunks:
            context_parts = []
            for c in chunks:
                doc_name = await self._get_doc_name(db, c["document_id"])
                context_parts.append(f"[文档: {doc_name}] {c['chunk_text']}")
            vector_context = "\n\n---\n\n".join(context_parts)

        system_prompt = (
            "你是一个专业的文档管理助手（WorkDox）。你可以访问文档库并提供帮助。\n"
            "\n"
            "你有以下工具可用（注意：工具只返回文档元数据——名称、类型、状态等，不含正文内容）：\n"
            "- search_documents: 按关键词搜索文档（匹配名称和描述）\n"
            "- list_all_documents: 列出文档库中的文档\n"
            "- get_document_detail: 查看指定文档的详细信息（不含正文）\n"
            "- get_library_overview: 获取文档库整体统计概况\n"
        )
        if vector_context:
            system_prompt += (
                "\n"
                "以下是从文档中检索到的相关内容（用于回答内容类问题）：\n"
                f"{vector_context}\n"
                "\n"
                "处理规则：\n"
                "1. 内容类问题（如'XX是什么'、'XX有哪些步骤'）→ 直接根据上面的检索内容回答，不要调用工具\n"
                "2. 搜索/查找类问题（如'找一下关于XX的文档'）→ 使用 search_documents 工具\n"
                "3. 统计/列表类问题（如'有多少文档'、'列出所有文档'）→ 使用 get_library_overview 或 list_all_documents\n"
                "4. 仅根据实际数据回答，不要编造信息\n"
                "5. 使用中文回答"
            )
        else:
            system_prompt += (
                "\n"
                "处理规则：\n"
                "1. 搜索/查找类问题（如'找一下关于XX的文档'）→ 使用 search_documents 工具\n"
                "2. 统计/列表类问题（如'有多少文档'、'列出所有文档'）→ 使用 get_library_overview 或 list_all_documents\n"
                "3. 仅根据实际数据回答，不要编造信息\n"
                "4. 使用中文回答"
            )

        user_prompt = f"{library_summary}\n\n用户问题：{query}"

        messages = [{"role": "system", "content": system_prompt}]
        if chat_history:
            messages.extend(chat_history)
        messages.append({"role": "user", "content": user_prompt})

        # 4. Run agent loop with tools
        async def exec_tool(name: str, args: dict) -> str:
            return await execute_tool(db, name, args)

        answer = await llm_service.run_agent(provider, messages, TOOLS, exec_tool)

        # 5. Format sources from vector search
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
        provider: dict,
        document_ids: list[int] | None = None,
        chat_history: list[dict] | None = None,
    ):
        """Streaming agent RAG Q&A — yields SSE chunks."""
        emb_service = get_embedding_service()
        rag_params = await get_rag_params(db)

        # 1. Embed query
        query_embedding = await emb_service.embed_single(query)

        # 2. Vector search
        chunks = await self.search_similar_chunks(
            db,
            query_embedding,
            top_k=rag_params["top_k"],
            document_ids=document_ids,
        )

        # 3. Build messages with library context + vector results + tools
        library_summary = await self._get_library_summary(db)

        # Build vector context for system prompt
        vector_context = ""
        if chunks:
            context_parts = []
            for c in chunks:
                doc_name = await self._get_doc_name(db, c["document_id"])
                context_parts.append(f"[文档: {doc_name}] {c['chunk_text']}")
            vector_context = "\n\n---\n\n".join(context_parts)

        system_prompt = (
            "你是一个专业的文档管理助手（WorkDox）。你可以访问文档库并提供帮助。\n"
            "\n"
            "你有以下工具可用（注意：工具只返回文档元数据——名称、类型、状态等，不含正文内容）：\n"
            "- search_documents: 按关键词搜索文档（匹配名称和描述）\n"
            "- list_all_documents: 列出文档库中的文档\n"
            "- get_document_detail: 查看指定文档的详细信息（不含正文）\n"
            "- get_library_overview: 获取文档库整体统计概况\n"
        )
        if vector_context:
            system_prompt += (
                "\n"
                "以下是从文档中检索到的相关内容（用于回答内容类问题）：\n"
                f"{vector_context}\n"
                "\n"
                "处理规则：\n"
                "1. 内容类问题（如'XX是什么'、'XX有哪些步骤'）→ 直接根据上面的检索内容回答，不要调用工具\n"
                "2. 搜索/查找类问题（如'找一下关于XX的文档'）→ 使用 search_documents 工具\n"
                "3. 统计/列表类问题（如'有多少文档'、'列出所有文档'）→ 使用 get_library_overview 或 list_all_documents\n"
                "4. 仅根据实际数据回答，不要编造信息\n"
                "5. 使用中文回答"
            )
        else:
            system_prompt += (
                "\n"
                "处理规则：\n"
                "1. 搜索/查找类问题（如'找一下关于XX的文档'）→ 使用 search_documents 工具\n"
                "2. 统计/列表类问题（如'有多少文档'、'列出所有文档'）→ 使用 get_library_overview 或 list_all_documents\n"
                "3. 仅根据实际数据回答，不要编造信息\n"
                "4. 使用中文回答"
            )

        user_prompt = f"{library_summary}\n\n用户问题：{query}"

        messages = [{"role": "system", "content": system_prompt}]
        if chat_history:
            messages.extend(chat_history)
        messages.append({"role": "user", "content": user_prompt})

        # 4. Yield sources first, then stream agent answer
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

        async def exec_tool(name: str, args: dict) -> str:
            return await execute_tool(db, name, args)

        async for token in llm_service.run_agent_stream(provider, messages, TOOLS, exec_tool):
            yield {"type": "token", "content": token}

        yield {"type": "done"}
