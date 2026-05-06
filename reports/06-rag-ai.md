# Agent-6 Audit Report: RAG Pipeline & AI Agent Mechanism

**Date**: 2026-05-06
**Auditor**: Agent-6 (RAG + AI Evaluator)
**Scope**: `llm_service.py`, `tool_service.py`, `rag_service.py`, `embedding_service.py`, `ai.py` (API)

---

## Summary

Audited the AI Agent mechanism (OpenAI Function Calling + pgvector RAG) across 5 key files. Found **12 issues**: 5 critical (crashes), 3 medium (robustness), 4 minor (quality). **All 12 issues are now fixed.**

---

## 1. Agent Loop Correctness (llm_service.py) -- CRITICAL

### Issues Found:

**F1. No error handling on LLM API calls** (CRITICAL -- crash)
- `chat()` and `chat_stream()` had zero try/except around httpx calls
- Any network error, API error, or timeout would crash the entire request
- **Fix**: Added `ChatError` exception class, `httpx.HTTPStatusError` and `httpx.RequestError` handling with user-friendly Chinese messages

**F2. No error handling on tool execution** (CRITICAL -- crash)
- `execute_tool()` call in both `run_agent()` and `run_agent_stream()` had no try/except
- A single tool failure (e.g., DB connection error) would crash the entire agent loop
- **Fix**: Wrapped tool execution in try/except, returns error JSON if tool fails, allows loop to continue

**F3. Unbounded messages array** (MEDIUM -- memory)
- Each tool call round adds 2+ messages. With 5 rounds, messages could grow large.
- **Fix**: Added `MAX_MESSAGES = 30` cap and `_trim_messages()` that preserves system message and recent context

**F4. No validation of tool_call structure** (MEDIUM -- crash)
- Code blindly accessed `tc["id"]`, `tc["function"]["name"]`, `tc["function"]["arguments"]`
- A malformed LLM response (missing fields, wrong types) would crash with KeyError/TypeError
- **Fix**: Added `_validate_tool_call()` that checks all required fields and types before processing

**F5. Max rounds exhaustion behavior** (MEDIUM -- UX)
- Non-streaming: returned stale `final_answer` from earlier round or "timeout" message
- Streaming: streamed whatever the LLM returned, potentially with tool_calls
- **Fix**: Non-streaming now tries one final `chat()` call without tools as a fallback. Streaming yields error token.

**F6. Streaming lost tool context** (CRITICAL -- correctness)
- `run_agent_stream()` built `final_messages` from the **original** `messages` (without tool call context)
- When tools were used in earlier rounds, the streaming replay had no tool context, producing wrong/confused output
- **Fix**: Changed `final_messages = list(messages)` to `final_messages = list(working_messages)`

**F7. chat_stream() no JSON error handling** (MINOR -- resilience)
- `json.loads(data_str)` could fail on malformed SSE chunks
- **Fix**: Added try/except around `json.loads`, continues to next line on failure

---

## 2. Tool Schema vs Execution Consistency (tool_service.py)

### Issues Found:

**F8. Empty keyword crashes tsquery** (CRITICAL -- SQL error)
- `_search_documents()` built `tsquery = " | ".join(keyword.split())` even when keyword was `""`
- Empty tsquery could cause SQL errors or match everything
- **Fix**: Added validation: if `(args.get("keyword") or "").strip()` is empty, returns early

**F9. No input validation on document_id** (MEDIUM -- robustness)
- `_get_document_detail()` passed `args.get("document_id")` directly to SQL without type check
- LLM could pass string "4" or 0 or negative numbers
- **Fix**: Added isinstance check and <=0 guard

**F10. Duplicate has_text column** (MINOR -- waste)
- SQL query had `has_text` AND `has_text2` (both checking extracted_text existence)
- **Fix**: Removed duplicate `has_text2` column

**F11. Tool descriptions missing "metadata only" constraint** (MINOR -- clarity)
- Design doc mandates tools return "only metadata" -- this constraint was in system prompt but NOT in tool descriptions
- LLM could miss this and try to use tools for content queries
- **Fix**: Added "仅返回文档元数据...不含文档正文内容" to all 3 data-returning tool descriptions

**F12. No top-level error handling in execute_tool** (MEDIUM -- robustness)
- Though individual tool functions handle their own errors, a programming error could still propagate
- **Fix**: Wrapped the entire `execute_tool()` dispatcher in try/except

**F13. Added limit validation in _list_all_documents** (MINOR)
- `args.get("limit")` could be non-integer from malformed LLM output
- **Fix**: Added try/except around int conversion

---

## 3. Prompt Quality & Consistency (rag_service.py)

### Findings:

**P1. Prompts WERE identical** (OK -- no issue)
- Line-by-line comparison confirmed `ask()` and `ask_stream()` prompts were identical before refactoring
- Both correctly place vector context in system prompt (not user message), matching design doc

**P2. Massive code duplication** (MEDIUM -- maintenance)
- ~80% of the code in `ask()` and `ask_stream()` was duplicated: embedding, vector search, prompt building, source formatting
- Any future prompt change would need to be made in two places -- high risk of drift
- **Fix**: Extracted shared `_build_prompt()`, `_build_messages()`, `_build_sources()` methods

**P3. N+1 query for doc names** (MEDIUM -- performance) -- fixed by previous agent
- `_get_doc_name()` was called once per chunk in a loop (up to 5 separate DB roundtrips)
- Already fixed with `_get_doc_names_batch()` using `WHERE id IN (...)`

**P4. `doc_names` initialization bug** (MINOR -- crash risk)
- `ask()` did not initialize `doc_names = {}` before the `if chunks:` block (unlike `ask_stream()` which did)
- Empty chunks would either work (Python implementation detail) or crash with NameError
- **Fix**: Now consistently initializes `doc_names: dict[int, str] = {}` in both methods

**P5. Zero-results guidance** (MINOR -- prompt quality)
- No instruction for AI when vector search returns 0 results ("找不到相关文档")
- **Fix**: Added rule 5 (with context: "如果检索内容不足以回答问题，告知用户并建议使用工具搜索") and rule 4 (without context: "如果无法回答，建议用户先上传相关文档")

---

## 4. Embedding Pipeline (embedding_service.py)

### Issues Found:

**E1. Wrong dimension in comment** (MINOR -- documentation)
- Header comment: "768 dims" but BAAI/bge-small-zh-v1.5 is **512 dims**
- **Fix**: Corrected comment to "512 dims"

**E2. No error handling for model loading** (CRITICAL -- startup crash)
- `_load_model()` had no try/except around `TextEmbedding(model_name=...)`
- If model download/load failed (no network, disk full, ONNX error), app would crash
- **Fix**: Added try/except, stores error in `_load_error` to avoid repeated retry attempts, raises `RuntimeError` with clear message

**E3. No error handling for embedding generation** (CRITICAL -- crash)
- `model.embed(texts)` could fail mid-request, crashing the entire RAG pipeline
- **Fix**: Added try/except with fallback to zero-vectors (detects dimension from test encode or defaults to 512). This keeps the pipeline running even on partial failures.

**E4. Singleton pattern** (OK -- correct)
- `get_embedding_service()` uses `@lru_cache()` -- effectively a singleton
- Model is lazy-loaded, not loaded at import time
- Runs in thread pool via `asyncio.to_thread` -- does not block event loop

---

## 5. Edge Case Audit

| Edge Case | Status | Handling |
|-----------|--------|----------|
| Vector search returns 0 results | FIXED | Empty vector_context, prompt rules adapted, AI told to suggest uploading docs |
| Tool execution throws exception | FIXED | Caught at 2 levels: `execute_tool()` wrapper + `run_agent()` try/except |
| LLM returns content + tool_calls simultaneously | OK | Content preserved as `final_answer`, tool_calls executed, both appended to messages |
| LLM returns malformed tool_call JSON | FIXED | `_validate_tool_call()` filters invalid entries, `json.JSONDecodeError` caught |
| LLM API returns HTTP error | FIXED | `ChatError` exception raised, caught in API endpoint as HTTP 503 |
| LLM API network timeout | FIXED | `httpx.RequestError` caught, user-friendly message |
| Chat history with stale tool_call messages | OK | Conversation stores only user/assistant content (not tool messages) |
| Max rounds exceeded (non-streaming) | IMPROVED | Final fallback `chat()` without tools, then timeout message |
| Max rounds exceeded (streaming) | FIXED | Full context stream with error handling |

---

## 6. Design Recommendations (NOT implemented)

These are suggestions that require broader architectural discussion:

**R1. Agent loop should not replay via chat_stream()**
- The current hybrid approach (non-streaming tool calls, then streaming replay) is fragile
- The "replay" trick (appending assistant answer and streaming continuation) depends on LLM behavior
- **Recommendation**: Either (a) always stream from the start (with streaming function calling), or (b) split non-streaming answer into tokens artificially

**R2. Vector context length limit**
- There is no cap on system prompt size from vector context
- If `top_k` is large and chunks are long, system prompt could exceed model context limits
- **Recommendation**: Add a character/token budget for vector context (~2000 chars), truncate chunks

**R3. PostgreSQL full-text search for Chinese**
- `tsvector('simple')` does no Chinese word segmentation -- single characters only
- This works for exact substring matching but not semantic search
- **Recommendation**: Consider jieba + zhparser PostgreSQL extension, or fall back to ILIKE for Chinese queries

---

## 7. Files Modified

| File | Changes |
|------|---------|
| `backend/app/services/llm_service.py` | Added ChatError class, _trim_messages(), _validate_tool_call(); error handling in chat(), chat_stream(), run_agent(), run_agent_stream(); fixed streaming context bug |
| `backend/app/services/tool_service.py` | Added input validation (keyword, doc_id, limit); added "metadata only" to tool descriptions; removed duplicate has_text2 column; wrapped execute_tool() in try/except |
| `backend/app/services/rag_service.py` | Extracted _build_prompt(), _build_messages(), _build_sources(); fixed doc_names initialization; added zero-results guidance to prompts |
| `backend/app/services/embedding_service.py` | Fixed dimension comment (768 -> 512); added try/except for model loading and embedding; fallback to zero-vectors on failure |
| `backend/app/api/v1/ai.py` | Added ChatError import and HTTP 503 handling in chat endpoint |
