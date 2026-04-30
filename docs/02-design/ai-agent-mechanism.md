# AI Agent 工具调用机制设计文档

**版本**：v1.0
**日期**：2026-04-30
**状态**：已实现

---

## 一、概述

WorkDox AI 助手不仅支持基于文档内容的 RAG 问答，还具备 **Agent 自主工具调用**能力——AI 能根据用户意图，自动选择合适的工具（搜索文档、列出文件、查统计等），执行后整合结果自然回复。

核心思路：**让 LLM 从被动接收上下文升级为主动获取信息**。

---

## 二、架构全景

```
用户输入 "库里有多少文档？"
    │
    ├─ 1. 向量检索（异步，自动完成）
    │     用户 query → fastembed → 512 维向量
    │     → pgvector <=> 余弦距离搜索 → Top-K 相关文档片段
    │     结果嵌入系统提示词，作为背景知识
    │
    ├─ 2. 构建消息
    │     系统提示词 = 工具列表 + 向量检索结果 + 行为规则
    │     + 文档库概况（名称、数量、类型）
    │     + 用户问题
    │
    └─ 3. Agent 循环（最多 5 轮）
         LLM 分析意图
         ├─ 需要工具 → 调用 execute_tool() → 结果追加到对话 → 回到 LLM
         └─ 不需要工具 → 返回最终回答
```

---

## 三、核心组件

### 3.1 多供应商支持

**数据模型** — `ai_providers` 表：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| name | string(100) | 显示名称，如 "DeepSeek V3" |
| provider_type | string(50) | deepseek / qwen / openai / custom |
| api_base | string(500) | API 端点 |
| api_key | string(500) | 密钥 |
| model | string(100) | 模型名，如 deepseek-chat |
| max_tokens | int | 最大输出 token |
| temperature | float | 生成温度 |
| is_enabled | bool | 是否启用 |
| sort_order | int | 排序 |

**LLM 客户端** — `llm_service.py`：

从全局单例重构为无状态函数，每次请求根据 `provider` dict 创建临时 `httpx.AsyncClient`：

```python
def _create_client(provider: dict) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=provider["api_base"],
        headers={
            "Authorization": f"Bearer {provider['api_key']}",
            "Content-Type": "application/json",
        },
        timeout=httpx.Timeout(120.0),
    )
```

三个核心函数：
- `chat(provider, messages, tools)` — 非流式调用，返回 `{content, tool_calls}`
- `chat_stream(provider, messages)` — 流式调用，yield token
- `run_agent(provider, messages, tools, executor)` — Agent 循环
- `run_agent_stream(provider, messages, tools, executor)` — 流式 Agent

### 3.2 工具系统

文件：`tool_service.py`

每个工具有两部分：

**① JSON Schema（Function Calling 格式）** — 告诉 LLM 工具签名：

```python
{
    "type": "function",
    "function": {
        "name": "search_documents",
        "description": "在文档库中搜索文档。按关键词匹配名称和描述。",
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "搜索关键词"},
                "file_type": {"type": "string", "description": "可选的文件类型过滤"},
            },
            "required": ["keyword"],
        },
    },
}
```

**② 执行函数** — 查数据库：

```python
async def _search_documents(db, args):
    keyword = args["keyword"]
    sql = text(
        "SELECT id, original_name, file_type, status, description "
        "FROM document WHERE is_deleted = false "
        "AND to_tsvector('simple', coalesce(original_name, '') || ' ' "
        "|| coalesce(description, '')) @@ to_tsquery('simple', :q) "
        "ORDER BY id LIMIT 20"
    )
    result = await db.execute(sql, {"q": " | ".join(keyword.split())})
    rows = result.fetchall()
    return json.dumps({"found": len(rows), "documents": [...]})
```

**已实现的 4 个工具：**

| 工具 | 功能 | 数据源 | 典型触发 |
|------|------|--------|----------|
| `search_documents` | 全文搜索文档名称和描述 | PostgreSQL `tsvector` GIN 索引 | "找一下关于XX的文档" |
| `list_all_documents` | 列出所有文档（支持分页、状态筛选） | `document` 表 | "有哪些文档" |
| `get_document_detail` | 获取单文档完整信息（含标签、分类、版本） | 多表 JOIN | "文档 #4 的详细信息" |
| `get_library_overview` | 文档库聚合统计 | `GROUP BY` 查询 | "库里有多少文档" |

### 3.3 Agent 循环

文件：`llm_service.py` → `run_agent()`

最核心的 30 行逻辑：

```python
async def run_agent(provider, messages, tools, execute_tool):
    working_messages = list(messages)  # 不污染调用方

    for round in range(MAX_TOOL_ROUNDS):  # 最多 5 轮
        # 1. 调用 LLM，传入工具列表
        result = await chat(provider, working_messages, tools=tools)

        # 2. 如果没有工具调用，返回文本
        if not result["tool_calls"]:
            return result["content"]

        # 3. 追加 assistant 消息（含 tool_calls）
        assistant_msg = {"role": "assistant", "content": result["content"] or None}
        assistant_msg["tool_calls"] = result["tool_calls"]
        working_messages.append(assistant_msg)

        # 4. 执行每个工具，追加结果
        for tc in result["tool_calls"]:
            args = json.loads(tc["function"]["arguments"])
            tool_result = await execute_tool(tc["function"]["name"], args)
            working_messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": tool_result,
            })

    return result.get("content") or "处理超时"
```

**流式版本** `run_agent_stream()`：
- 工具调用阶段走非流式（工具调用本身很快）
- 最终回答阶段走流式，逐 token 返回给前端

### 3.4 提示词设计

这是整个机制最容易出问题的地方。经过三轮迭代，最终方案如下：

**向量检索结果注入系统提示词**（不是用户消息），确保工具调用后仍可见：

```
System Prompt:
  ┌──────────────────────────────────────────┐
  │ 你是 WorkDox 文档管理助手。              │
  │                                          │
  │ 工具有（注意：只返回元数据，不含正文）： │
  │   - search_documents: 搜索文档           │
  │   - list_all_documents: 列出文档         │
  │   - get_document_detail: 文档详情        │
  │   - get_library_overview: 库统计         │
  │                                          │
  │ 以下是从文档中检索到的相关内容：         │
  │ [文档: Markdown_大纲.md] 课程制作包含... │
  │ [文档: StudyStudio_课程制作全流程.pptx]..│
  │                                          │
  │ 处理规则：                               │
  │ 1. 内容类问题 → 直接用上面的检索内容    │
  │ 2. 搜索/查找类问题 → 用 search_documents│
  │ 3. 统计/列表类问题 → 用 overview/list   │
  │ 4. 不要编造信息                         │
  │ 5. 使用中文回答                         │
  └──────────────────────────────────────────┘

User Prompt:
  文档库概况：共有 2 个文档...
  用户问题：课程制作有哪些阶段？
```

**关键设计决策：**

| 问题 | 错误方案 | 正确方案 |
|------|----------|----------|
| 向量上下文放哪里 | 放用户消息 → 工具调用后"被冲走" | 放系统提示词 → 始终可见 |
| 工具能力描述 | 不注明数据范围 → AI 用工具查正文 | 标注"仅返回元数据" → 不会误用 |
| 意图分类 | 模糊规则 → AI 随机选择 | 三条明确规则 → 内容/搜索/统计分流 |

---

## 四、意图分流逻辑

```
用户输入
    │
    ▼
LLM 分析意图（基于系统提示词中的规则）
    │
    ├─ "XX 是什么" / "XX 有哪些步骤"
    │   → 内容类 → 直接使用系统提示词中的向量检索结果
    │   → 不调用工具
    │   → 例："课程制作有哪些阶段？"
    │
    ├─ "找一下关于 XX 的文档" / "有没有 XX"
    │   → 搜索类 → 调用 search_documents("XX")
    │   → 返回匹配的文档列表 → LLM 格式化输出
    │   → 例："有没有关于大纲的文档？"
    │
    ├─ "有多少文档" / "统计一下"
    │   → 统计类 → 调用 get_library_overview
    │   → 返回聚合数据 → LLM 格式化输出
    │   → 例："库里有多少文档？"
    │
    └─ "文档 #4 的详细信息"
        → 详情类 → 调用 get_document_detail(4)
        → 返回完整元数据 → LLM 格式化输出
        → 例："文档 #4 是什么？"
```

---

## 五、数据流详解（以聊天为例）

### 非流式：`POST /api/v1/ai/chat`

```
RAGService.ask()
  │
  ├─ 1. embed_single(query) → 512 维向量
  ├─ 2. search_similar_chunks(vector, top_k=5) → pgvector <=> 余弦距离
  │     返回：[{chunk_id, document_id, chunk_text, similarity}, ...]
  │
  ├─ 3. _get_library_summary() → "文档库共有 2 个文档：\n  [4] StudyStudio_课程制作全流程.pptx..."
  │
  ├─ 4. 构建 messages:
  │     system: 工具列表 + 向量上下文 + 规则
  │     user: 文档库概况 + 用户问题
  │
  ├─ 5. llm_service.run_agent(provider, messages, TOOLS, execute_tool)
  │     │
  │     └─ Agent 循环:
  │         ├─ LLM 决定: use tool? 或 answer?
  │         ├─ use tool → execute_tool(db, name, args) → 结果追加到对话 → 回到 LLM
  │         └─ answer → 返回文本
  │
  └─ 6. 返回 {"answer": "...", "sources": [...], "conversation_id": ...}
```

### 流式：`POST /api/v1/ai/chat/stream`

```
同非流式步骤 1-4

步骤 5: llm_service.run_agent_stream(provider, messages, TOOLS, execute_tool)
  ├─ 工具调用阶段：非流式（同 run_agent）
  ├─ 最终回答阶段：流式 chat_stream()
  └─ 逐 token 通过 SSE 推送:
      data: {"type": "sources", "data": [...]}
      data: {"type": "token", "content": "课"}
      data: {"type": "token", "content": "程"}
      ...
      data: {"type": "done", "conversation_id": 6}
```

---

## 六、向量检索

### 嵌入模型

- 模型：`BAAI/bge-small-zh-v1.5`（via fastembed / ONNX Runtime）
- 维度：512
- 运行方式：线程池中同步调用，`asyncio.to_thread` 不阻塞事件循环

### 文本分块

```python
RAGService.chunk_text(text, chunk_size=500, overlap=50)
# 按句子边界分割，相邻块 50 字符重叠
# 避免关键信息被切断
```

### 存储与检索

- 存储：`document_chunk` 表，`Vector(512)` 列，pgvector 扩展
- 检索：余弦距离 `<=>` 运算符，`CAST(:embedding AS vector)` 转换
- 全文搜索：`tsvector('simple')` + GIN 索引，用于工具 `search_documents`

---

## 七、文件清单

```
backend/app/
├── services/
│   ├── tool_service.py        # 工具定义 + 执行（4 个工具）
│   ├── llm_service.py         # LLM 客户端 + Agent 循环
│   ├── rag_service.py         # RAG 服务（分块、嵌入、Agent 问答）
│   ├── ai_config.py           # 供应商配置 CRUD
│   ├── embedding_service.py   # fastembed 封装
│   └── summarization_service.py  # 文档摘要
├── models/
│   ├── ai_provider.py         # AI 供应商模型
│   ├── ai.py                  # DocumentChunk / AIConversation / AIMessage
│   └── document.py            # Document（含 embedding 列）
└── api/v1/
    ├── ai.py                  # AI 聊天 API（chat / stream / providers / conversations）
    └── system.py              # 供应商 CRUD + AI 配置

frontend/src/
├── views/
│   ├── ai/AIChatView.vue      # AI 对话页（含供应商选择器）
│   └── admin/AIConfigView.vue # AI 配置管理（供应商表格 + RAG 参数）
├── stores/ai.ts               # AI 状态管理
└── api/
    ├── ai.ts                  # AI API 类型定义
    └── system.ts              # 供应商 CRUD API
```

---

## 八、扩展指南

### 添加新工具

1. 在 `tool_service.py` 的 `TOOLS` 列表中添加 JSON Schema
2. 在 `execute_tool()` 中添加分支和实现函数
3. 在系统提示词中补充工具描述

示例——添加"统计某个用户的上传量"工具：

```python
# 1. Schema
{
    "type": "function",
    "function": {
        "name": "get_user_upload_stats",
        "description": "获取指定用户的上传统计",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "integer", "description": "用户ID"},
            },
            "required": ["user_id"],
        },
    },
}

# 2. 执行函数
async def _get_user_upload_stats(db, args):
    sql = text("SELECT count(*), sum(file_size) FROM document WHERE owner_id = :uid")
    result = await db.execute(sql, {"uid": args["user_id"]})
    row = result.fetchone()
    return json.dumps({"count": row[0], "total_size": row[1]})

# 3. 注册到 execute_tool()
if tool_name == "get_user_upload_stats":
    return await _get_user_upload_stats(db, arguments)
```

### 添加新 AI 供应商

1. 确认供应商支持 OpenAI-compatible API（`/chat/completions` 端点 + Function Calling）
2. 在管理后台「AI 配置管理」页面添加供应商
3. 填入 API 地址、密钥、模型名
4. 启用后即可在 AI 助手下拉框中选择

---

## 九、设计决策记录

| 决策 | 选项 | 选择 | 原因 |
|------|------|------|------|
| LLM 客户端模式 | 单例 vs 无状态 | 无状态 | 多供应商需动态切换 |
| 工具调用协议 | 自定义 vs OpenAI Function Calling | OpenAI 兼容 | 主流供应商都支持 |
| 向量上下文位置 | 用户消息 vs 系统提示词 | 系统提示词 | 工具调用后不会被冲走 |
| Agent 最大轮数 | 3 / 5 / 无限 | 5 | 兼顾灵活性和安全性 |
| 流式策略 | 全程流式 vs 工具非流式+回答流式 | 混合 | 工具调用快且不流式，回答流式体验好 |
| 全文搜索 | tsvector vs ILIKE | tsvector + GIN | 毫秒级响应，支持中文分词 |

---

*记录人：Claude Code*
