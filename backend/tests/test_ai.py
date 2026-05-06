"""Tests for AI pipeline: chunking, agent loop, and provider config.

Tests are at the unit level (no external LLM/ONNX required).
We mock httpx for llm_service tests.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestChunking:
    """Test RAGService.chunk_text — pure text splitting logic."""

    def test_empty_text(self):
        from app.services.rag_service import RAGService

        chunks = RAGService.chunk_text("")
        assert chunks == []

    def test_single_short_text(self):
        from app.services.rag_service import RAGService

        text = "这是一段简短的测试文本。"
        chunks = RAGService.chunk_text(text, chunk_size=500, overlap=50)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_with_sentence_boundary(self):
        from app.services.rag_service import RAGService

        text = "第一句话。第二句话。第三句话。"
        chunks = RAGService.chunk_text(text, chunk_size=5, overlap=0)
        # With chunk_size=5, each sentence exceeds the limit
        # The function tries to fit, the first sentence "第一句话。" is 5 chars
        assert len(chunks) >= 2  # Should split into multiple chunks

    def test_overlap_between_chunks(self):
        from app.services.rag_service import RAGService

        text = "AAAA。BBBB。CCCC。DDDD。"  # Each "AAAA。" is 5 chars
        chunks = RAGService.chunk_text(text, chunk_size=5, overlap=2)
        assert len(chunks) >= 1
        # Overlap means some content from end of chunk N appears at start of chunk N+1

    def test_long_continuous_text(self):
        from app.services.rag_service import RAGService

        text = "这是一个很长的文本内容，没有任何句号或者其他分隔符来测试连续文本的分割效果。" * 20
        chunks = RAGService.chunk_text(text, chunk_size=100, overlap=20)
        assert len(chunks) > 1
        # Each chunk should be <= chunk_size (within reason)
        for c in chunks:
            assert len(c) <= 100 + 50  # Allow some slack for sentence boundaries

    def test_chunk_size_parameter_respected(self):
        from app.services.rag_service import RAGService

        text = "Sentence one. Sentence two. Sentence three." * 10
        chunks = RAGService.chunk_text(text, chunk_size=200, overlap=30)
        # No chunk should grossly exceed chunk_size
        for c in chunks:
            assert len(c) < 300  # generous margin for sentence boundary

    def test_chinese_text_chunking(self):
        from app.services.rag_service import RAGService

        text = (
            "根据公司年度工作安排，现将2026年春季招生工作有关事项通知如下："
            "一、招生计划。本年度计划招收新生500名。"
            "二、报名条件。具有高中及以上学历。"
            "三、考试安排。定于2026年3月15日进行统一考试。"
        )
        chunks = RAGService.chunk_text(text, chunk_size=80, overlap=20)
        assert len(chunks) >= 1
        # All chunks should contain some content
        for c in chunks:
            assert len(c.strip()) > 0


class TestAgentLoop:
    """Test llm_service.run_agent with mocked LLM responses."""

    @pytest.fixture
    def provider(self):
        return {
            "api_key": "test-key",
            "api_base": "https://test.api.example.com",
            "model": "test-model",
            "max_tokens": 1024,
            "temperature": 0.3,
        }

    @pytest.fixture
    def messages(self):
        return [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
        ]

    @pytest.mark.asyncio
    async def test_simple_answer_no_tools(self, provider, messages):
        """When LLM returns content with no tool_calls, return it directly."""
        from app.services import llm_service

        mock_response = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "Hello! How can I help you?",
                }
            }]
        }

        with patch.object(llm_service, "chat", new=AsyncMock(return_value={
            "content": "Hello! How can I help you?",
            "tool_calls": None,
        })):
            result = await llm_service.run_agent(
                provider, messages, tools=[], execute_tool=AsyncMock()
            )
            assert result == "Hello! How can I help you?"

    @pytest.mark.asyncio
    async def test_tool_calling_single_round(self, provider, messages):
        """Agent should execute tool call and feed result back to LLM."""
        from app.services import llm_service

        tool_executed = []

        async def my_execute_tool(name, args):
            tool_executed.append((name, args))
            return json.dumps({"found": True, "count": 3})

        # First call: LLM responds with a tool_call
        # Second call: LLM gives final answer
        chat_responses = [
            {
                "content": "",
                "tool_calls": [{
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "search_documents",
                        "arguments": json.dumps({"keyword": "招生"}),
                    },
                }],
            },
            {
                "content": "找到了3个相关文档。",
                "tool_calls": None,
            },
        ]
        mock_chat = AsyncMock(side_effect=chat_responses)

        with patch.object(llm_service, "chat", new=mock_chat):
            result = await llm_service.run_agent(
                provider, messages,
                tools=[{"type": "function", "function": {"name": "search_documents"}}],
                execute_tool=my_execute_tool,
            )

        assert tool_executed == [("search_documents", {"keyword": "招生"})]
        assert result == "找到了3个相关文档。"

    @pytest.mark.asyncio
    async def test_tool_calling_json_parse_error(self, provider, messages):
        """Invalid JSON in tool arguments should be caught gracefully."""
        from app.services import llm_service

        chat_responses = [
            {
                "content": "",
                "tool_calls": [{
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "search_documents",
                        "arguments": "not valid json {{{",
                    },
                }],
            },
            {
                "content": "执行完毕。",
                "tool_calls": None,
            },
        ]
        mock_chat = AsyncMock(side_effect=chat_responses)

        with patch.object(llm_service, "chat", new=mock_chat):
            result = await llm_service.run_agent(
                provider, messages,
                tools=[{"type": "function", "function": {"name": "search_documents"}}],
                execute_tool=AsyncMock(return_value="ok"),
            )

        assert result == "执行完毕。"

    @pytest.mark.asyncio
    async def test_max_rounds_protection(self, provider, messages):
        """Agent should stop after MAX_TOOL_ROUNDS to prevent infinite loops."""
        from app.services import llm_service

        # Simulate LLM that always calls tools
        chat_response = {
            "content": "",
            "tool_calls": [{
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "search_documents",
                    "arguments": json.dumps({"keyword": "test"}),
                },
            }],
        }

        with patch.object(llm_service, "chat", new=AsyncMock(return_value=chat_response)):
            result = await llm_service.run_agent(
                provider, messages,
                tools=[{"type": "function", "function": {"name": "search_documents"}}],
                execute_tool=AsyncMock(return_value="[]"),
            )

        # Should return timeout message after max rounds
        assert "超时" in result or "处理超时" in result

    @pytest.mark.asyncio
    async def test_chat_http_error(self, provider, messages):
        """HTTP errors from LLM provider should propagate."""
        import httpx
        from app.services import llm_service

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )

        with patch.object(llm_service, "_create_client", return_value=mock_client):
            mock_client.post = AsyncMock(return_value=mock_response)
            with pytest.raises(httpx.HTTPStatusError):
                await llm_service.chat(provider, messages)


class TestProviderConfig:
    """Test AI provider configuration retrieval."""

    @pytest.mark.asyncio
    async def test_get_provider_not_found(self, db_session):
        """Requesting a non-existent provider should raise ValueError."""
        from app.services.ai_config import get_provider_config

        with pytest.raises(ValueError, match="not found or disabled"):
            await get_provider_config(db_session, provider_id=99999)
