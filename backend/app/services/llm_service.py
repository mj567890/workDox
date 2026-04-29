"""LLM service for DeepSeek API (OpenAI-compatible).

Provides async chat completion and SSE streaming interfaces.
"""

import logging

import httpx
from app.config import get_settings

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        settings = get_settings()
        self._api_key = settings.DEEPSEEK_API_KEY
        self._base_url = settings.DEEPSEEK_API_BASE
        self._model = settings.DEEPSEEK_MODEL
        self._max_tokens = settings.DEEPSEEK_MAX_TOKENS
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(120.0),
            )
        return self._client

    async def chat(
        self, messages: list[dict], temperature: float = 0.3
    ) -> str:
        """Send messages to DeepSeek and return the assistant's response."""
        client = await self._get_client()
        response = await client.post(
            "/chat/completions",
            json={
                "model": self._model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": self._max_tokens,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def chat_stream(self, messages: list[dict], temperature: float = 0.3):
        """Stream response from DeepSeek as SSE text chunks."""
        client = await self._get_client()
        async with client.stream(
            "POST",
            "/chat/completions",
            json={
                "model": self._model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": self._max_tokens,
                "stream": True,
            },
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    import json

                    chunk = json.loads(data_str)
                    delta = chunk["choices"][0].get("delta", {})
                    if "content" in delta:
                        yield delta["content"]

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None


_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
