"""LLM client — per-request OpenAI-compatible API calls with provider config."""

import json
import logging

import httpx

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 5       # Prevent infinite loops
MAX_MESSAGES = 30         # Cap total messages to avoid unbounded arrays


def _create_client(provider: dict) -> httpx.AsyncClient:
    """Create an httpx client for the given provider config."""
    return httpx.AsyncClient(
        base_url=provider["api_base"],
        headers={
            "Authorization": f"Bearer {provider['api_key']}",
            "Content-Type": "application/json",
        },
        timeout=httpx.Timeout(120.0),
    )


def _trim_messages(messages: list[dict], max_count: int) -> list[dict]:
    """Trim messages array if it exceeds max_count, preserving system+user and recent context."""
    if len(messages) <= max_count:
        return messages
    # Always keep the system message and the last user message
    system_msg = messages[0] if messages and messages[0]["role"] == "system" else None
    user_msg = messages[-1] if messages and messages[-1]["role"] == "user" else None
    # Take the most recent messages, minus system and last user to avoid duplication
    trim_target = max_count - (1 if system_msg else 0) - (1 if user_msg else 0)
    trimmed = messages[-(trim_target + (1 if user_msg else 0)):]
    # Prepend system if it was present
    if system_msg and (not trimmed or trimmed[0]["role"] != "system"):
        trimmed.insert(0, system_msg)
    return trimmed


def _build_body(
    provider: dict,
    messages: list[dict],
    temperature: float | None = None,
    tools: list[dict] | None = None,
    stream: bool = False,
) -> dict:
    body: dict = {
        "model": provider["model"],
        "messages": messages,
        "temperature": temperature if temperature is not None else provider.get("temperature", 0.3),
        "max_tokens": provider.get("max_tokens", 4096),
    }
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    if stream:
        body["stream"] = True
    return body


async def chat(
    provider: dict,
    messages: list[dict],
    temperature: float | None = None,
    tools: list[dict] | None = None,
) -> dict:
    """Non-streaming chat completion. Returns {'content': str, 'tool_calls': list | None}.

    Raises ChatError with a user-friendly message on API failure.
    """
    async with _create_client(provider) as client:
        try:
            response = await client.post(
                "/chat/completions",
                json=_build_body(provider, messages, temperature, tools),
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error("LLM API HTTP error: %s — %s", e.response.status_code, e.response.text[:500])
            raise ChatError(f"AI 服务返回错误 (HTTP {e.response.status_code})，请稍后重试。") from e
        except httpx.RequestError as e:
            logger.error("LLM API request error: %s", e)
            raise ChatError("无法连接到 AI 服务，请检查网络或供应商配置。") from e

        data = response.json()
        msg = data["choices"][0]["message"]
        return {
            "content": msg.get("content") or "",
            "tool_calls": msg.get("tool_calls"),
        }


class ChatError(Exception):
    """User-facing error from LLM API calls."""


async def chat_stream(provider: dict, messages: list[dict], temperature: float | None = None):
    """Streaming chat completion — yields token strings.

    Raises ChatError on API failure.
    """
    async with _create_client(provider) as client:
        try:
            async with client.stream(
                "POST",
                "/chat/completions",
                json=_build_body(provider, messages, temperature, stream=True),
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]
        except httpx.HTTPStatusError as e:
            logger.error("LLM stream HTTP error: %s — %s", e.response.status_code, e.response.text[:500])
            raise ChatError(f"AI 服务返回错误 (HTTP {e.response.status_code})，请稍后重试。") from e
        except httpx.RequestError as e:
            logger.error("LLM stream request error: %s", e)
            raise ChatError("无法连接到 AI 服务，请检查网络或供应商配置。") from e


# ── Agent loop with tool calling ───────────────────────────────────

def _validate_tool_call(tc: dict) -> bool:
    """Check that a tool_call dict has the required structure."""
    return (
        isinstance(tc, dict)
        and isinstance(tc.get("id"), str)
        and isinstance(tc.get("function"), dict)
        and isinstance(tc["function"].get("name"), str)
        and isinstance(tc["function"].get("arguments"), str)
    )


async def run_agent(
    provider: dict,
    messages: list[dict],
    tools: list[dict],
    execute_tool,
    temperature: float | None = None,
) -> str:
    """Run the agent loop: call LLM, execute tools, repeat until final answer."""
    working_messages = list(messages)  # Copy to avoid mutating caller's list
    final_answer = ""

    for _round in range(MAX_TOOL_ROUNDS):
        # Trim messages if needed to avoid unbounded growth
        if len(working_messages) > MAX_MESSAGES:
            working_messages = _trim_messages(working_messages, MAX_MESSAGES)

        try:
            result = await chat(provider, working_messages, temperature, tools)
        except ChatError:
            # If a later round fails after we already have content, return what we have
            if final_answer:
                return final_answer
            raise

        if result["content"]:
            final_answer = result["content"]

        # --- Handle tool calls ---
        raw_tool_calls = result.get("tool_calls")
        valid_tool_calls = [tc for tc in (raw_tool_calls or []) if _validate_tool_call(tc)]

        if not valid_tool_calls:
            # No valid tool calls — return the final answer
            return final_answer or "抱歉，处理您的问题时遇到了问题，请重试。"

        # Append assistant message with tool calls
        assistant_msg: dict = {
            "role": "assistant",
            "content": final_answer or None,
            "tool_calls": valid_tool_calls,
        }
        working_messages.append(assistant_msg)

        # Execute each tool call
        for tc in valid_tool_calls:
            fn = tc["function"]
            tool_name = fn["name"]
            try:
                args = json.loads(fn["arguments"])
            except json.JSONDecodeError:
                logger.warning("Malformed tool arguments for %s: %s", tool_name, fn.get("arguments", "")[:200])
                args = {}

            logger.info("Agent tool call: %s(%s)", tool_name, args)

            try:
                tool_result = await execute_tool(tool_name, args)
            except Exception:
                logger.exception("Tool execution failed: %s(%s)", tool_name, args)
                tool_result = json.dumps(
                    {"error": f"工具 {tool_name} 执行失败，请尝试其他方式。"},
                    ensure_ascii=False,
                )

            working_messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": tool_result,
            })

    # Max rounds reached
    if final_answer:
        return final_answer
    # Try one last call without tools to get a plain answer
    try:
        fallback = await chat(provider, working_messages, temperature)
        return fallback["content"] or "处理超时，请简化问题后重试。"
    except Exception:
        return "处理超时，请简化问题后重试。"


async def run_agent_stream(
    provider: dict,
    messages: list[dict],
    tools: list[dict],
    execute_tool,
    temperature: float | None = None,
):
    """Run agent loop (tools non-streaming), then stream the final answer."""
    working_messages = list(messages)
    final_answer = ""
    chat_error_occurred = False

    for _round in range(MAX_TOOL_ROUNDS):
        # Trim messages if needed to avoid unbounded growth
        if len(working_messages) > MAX_MESSAGES:
            working_messages = _trim_messages(working_messages, MAX_MESSAGES)

        try:
            result = await chat(provider, working_messages, temperature, tools)
        except ChatError:
            chat_error_occurred = True
            # Fall through to stream what we have (or an error message)
            break

        if result["content"]:
            final_answer = result["content"]

        # --- Handle tool calls ---
        raw_tool_calls = result.get("tool_calls")
        valid_tool_calls = [tc for tc in (raw_tool_calls or []) if _validate_tool_call(tc)]

        if not valid_tool_calls:
            # No more tool calls — stream the final answer
            break

        # Append assistant message with tool calls
        assistant_msg: dict = {
            "role": "assistant",
            "content": final_answer or None,
            "tool_calls": valid_tool_calls,
        }
        working_messages.append(assistant_msg)

        for tc in valid_tool_calls:
            fn = tc["function"]
            tool_name = fn["name"]
            try:
                args = json.loads(fn["arguments"])
            except json.JSONDecodeError:
                logger.warning("Malformed tool arguments for %s: %s", tool_name, fn.get("arguments", "")[:200])
                args = {}

            logger.info("Agent stream tool call: %s(%s)", tool_name, args)

            try:
                tool_result = await execute_tool(tool_name, args)
            except Exception:
                logger.exception("Tool execution failed (stream): %s(%s)", tool_name, args)
                tool_result = json.dumps(
                    {"error": f"工具 {tool_name} 执行失败，请尝试其他方式。"},
                    ensure_ascii=False,
                )

            working_messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": tool_result,
            })

    if chat_error_occurred:
        # Yield the error as a stream token for the frontend to display
        yield "抱歉，AI 服务暂时不可用，请稍后重试。"
        return

    # Stream the final answer via a fresh completion for token-by-token output.
    # Use working_messages (with full tool-call context) so the LLM has all context.
    final_messages = list(working_messages)
    if final_answer:
        final_messages.append({"role": "assistant", "content": final_answer})

    try:
        async for token in chat_stream(provider, final_messages, temperature):
            yield token
    except Exception:
        logger.exception("Final stream failed")
        if final_answer:
            yield final_answer
        else:
            yield "抱歉，生成回答时出错。"
        return
