"""LLM client — per-request OpenAI-compatible API calls with provider config."""

import json
import logging

import httpx

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 5  # Prevent infinite loops


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
    """Non-streaming chat completion. Returns {'content': str, 'tool_calls': list | None}."""
    async with _create_client(provider) as client:
        response = await client.post(
            "/chat/completions",
            json=_build_body(provider, messages, temperature, tools),
        )
        response.raise_for_status()
        data = response.json()
        msg = data["choices"][0]["message"]
        return {
            "content": msg.get("content") or "",
            "tool_calls": msg.get("tool_calls"),
        }


async def chat_stream(provider: dict, messages: list[dict], temperature: float | None = None):
    """Streaming chat completion — yields token strings."""
    async with _create_client(provider) as client:
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
                    chunk = json.loads(data_str)
                    delta = chunk["choices"][0].get("delta", {})
                    if "content" in delta:
                        yield delta["content"]


# ── Agent loop with tool calling ───────────────────────────────────

async def run_agent(
    provider: dict,
    messages: list[dict],
    tools: list[dict],
    execute_tool,
    temperature: float | None = None,
) -> str:
    """Run the agent loop: call LLM, execute tools, repeat until final answer."""
    working_messages = list(messages)  # Copy to avoid mutating caller's list

    for _round in range(MAX_TOOL_ROUNDS):
        result = await chat(provider, working_messages, temperature, tools)

        if result["content"]:
            final_answer = result["content"]
        else:
            final_answer = ""

        if not result["tool_calls"]:
            return final_answer

        # Append assistant message with tool calls
        assistant_msg = {"role": "assistant", "content": final_answer or None}
        assistant_msg["tool_calls"] = result["tool_calls"]
        working_messages.append(assistant_msg)

        # Execute each tool call
        for tc in result["tool_calls"]:
            fn = tc["function"]
            tool_name = fn["name"]
            try:
                args = json.loads(fn["arguments"])
            except json.JSONDecodeError:
                args = {}
            logger.info("Agent tool call: %s(%s)", tool_name, args)

            tool_result = await execute_tool(tool_name, args)

            working_messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": tool_result,
            })

    return final_answer or "处理超时，请简化问题后重试。"


async def run_agent_stream(
    provider: dict,
    messages: list[dict],
    tools: list[dict],
    execute_tool,
    temperature: float | None = None,
):
    """Run agent loop (tools non-streaming), then stream the final answer."""
    working_messages = list(messages)

    for _round in range(MAX_TOOL_ROUNDS):
        result = await chat(provider, working_messages, temperature, tools)

        if result["content"]:
            final_answer = result["content"]
        else:
            final_answer = ""

        if not result["tool_calls"]:
            # Replay the final answer via streaming for consistent UX
            # Build messages that include the final assistant response
            final_messages = list(messages)
            final_messages.append({"role": "assistant", "content": final_answer})
            # Stream a fresh completion to get token-by-token output
            async for token in chat_stream(provider, final_messages, temperature):
                yield token
            return

        # Append assistant message with tool calls
        assistant_msg = {"role": "assistant", "content": final_answer or None}
        assistant_msg["tool_calls"] = result["tool_calls"]
        working_messages.append(assistant_msg)

        for tc in result["tool_calls"]:
            fn = tc["function"]
            tool_name = fn["name"]
            try:
                args = json.loads(fn["arguments"])
            except json.JSONDecodeError:
                args = {}
            logger.info("Agent stream tool call: %s(%s)", tool_name, args)

            tool_result = await execute_tool(tool_name, args)

            working_messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": tool_result,
            })

    # Max rounds reached — stream whatever we have
    async for token in chat_stream(provider, working_messages, temperature):
        yield token
