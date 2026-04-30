"""AI document summarization service."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.services import llm_service

logger = logging.getLogger(__name__)


def _get_provider_from_env() -> dict:
    """Get provider config from environment variables (no DB dependency)."""
    settings = get_settings()
    return {
        "api_key": settings.DEEPSEEK_API_KEY,
        "api_base": settings.DEEPSEEK_API_BASE,
        "model": settings.DEEPSEEK_MODEL,
        "max_tokens": settings.DEEPSEEK_MAX_TOKENS,
        "temperature": 0.3,
    }


class SummarizationService:
    async def _get_provider(self, db: AsyncSession | None) -> dict:
        """Get provider from DB if session available, otherwise from env."""
        if db is not None:
            try:
                from app.services.ai_config import get_default_provider
                return await get_default_provider(db)
            except Exception:
                pass
        return _get_provider_from_env()

    async def summarize(self, text: str, db: AsyncSession | None = None, doc_name: str = "") -> str:
        """Generate an AI summary of document text."""
        if not text or len(text.strip()) < 100:
            return text or ""

        provider = await self._get_provider(db)
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

        result = await llm_service.chat(provider, messages, temperature=0.2)
        summary = result["content"]
        logger.info("Generated summary for '%s' (%d chars input, %d chars output)",
                     doc_name, len(text), len(summary))
        return summary.strip()

    async def summarize_document(
        self, doc_text: str, db: AsyncSession | None = None, doc_name: str = ""
    ) -> str:
        """Public interface for document summarization. db is optional (falls back to env vars)."""
        return await self.summarize(doc_text, db, doc_name)
