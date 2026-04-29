"""AI document summarization service using DeepSeek LLM."""

import logging

from app.services.llm_service import get_llm_service

logger = logging.getLogger(__name__)


class SummarizationService:
    async def summarize(self, text: str, doc_name: str = "") -> str:
        """Generate an AI summary of document text."""
        if not text or len(text.strip()) < 100:
            return text or ""

        llm = get_llm_service()
        truncated = text[:8000]  # Keep within token limits

        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个专业的文档摘要助手。请用中文生成简洁、准确的摘要。\n"
                    "要求：\n"
                    "1. 提取文档的核心主题和关键信息\n"
                    "2. 保持客观，不要添加个人观点\n"
                    "3. 摘要长度控制在200-500字\n"
                    "4. 如果文档包含数据、日期、名称等关键信息，请保留"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"请为以下文档生成摘要：\n\n"
                    f"文档名称：{doc_name}\n\n"
                    f"文档内容：\n{truncated}"
                ),
            },
        ]

        summary = await llm.chat(messages, temperature=0.2)
        logger.info("Generated summary for '%s' (%d chars input, %d chars output)",
                     doc_name, len(text), len(summary))
        return summary.strip()

    async def summarize_document(
        self, doc_text: str, doc_name: str = ""
    ) -> str:
        """Public interface for document summarization."""
        return await self.summarize(doc_text, doc_name)
