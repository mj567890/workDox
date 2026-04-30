# 开发日志 #006 — AI 多供应商 + Agent 工具调用机制

**日期**：2026-04-30
**阶段**：AI 助手能力升级
**产出**：多供应商支持 + Agent 自主工具调用 + 文档库感知

## 一、AI 多供应商支持

### 背景
此前 AI 配置只支持单个供应商，API Key 等参数以 key-value 存于 `system_config` 表，切换模型需要修改配置。

### 方案
新建 `ai_providers` 表，支持配置多个 AI 供应商，用户可在聊天时自由选择。

### 数据模型

| 表 | 字段 | 说明 |
|------|------|------|
| `ai_providers` | id, name, provider_type, api_base, api_key, model, max_tokens, temperature, is_enabled, sort_order | 供应商配置 |

### 后端 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST | `/system/ai-providers` | 供应商列表 / 创建 |
| PUT/DELETE | `/system/ai-providers/{id}` | 供应商编辑 / 删除 |
| GET | `/system/ai-config` | RAG 参数（保留） |
| PUT | `/system/ai-config` | 更新 RAG 参数 + 默认供应商 |

### LLM 服务重构

- 移除单例模式，改为每次请求根据 `provider` dict 创建临时 `httpx.AsyncClient`
- `chat()` 和 `chat_stream()` 接受 `provider` 参数
- 新增 `run_agent()` 和 `run_agent_stream()` — Agent 循环

### 变更文件

| 文件 | 变更 |
|------|------|
| `backend/app/models/ai_provider.py` | **新建** — AIProvider 模型 |
| `backend/app/services/llm_service.py` | 重构为无状态函数，新增 Agent 循环 |
| `backend/app/services/ai_config.py` | 新增 `get_provider_config()`、`get_default_provider()`、`list_providers()` |
| `backend/app/api/v1/ai.py` | ChatRequest 加 `provider_id`，新增 `GET /ai/providers` |
| `backend/app/api/v1/system.py` | 供应商 CRUD，AI 配置简化为 RAG + 默认供应商 |
| `frontend/src/views/admin/AIConfigView.vue` | 重写：供应商表格 + RAG 面板 |
| `frontend/src/views/ai/AIChatView.vue` | 顶部工具栏加供应商选择器 |
| `frontend/src/stores/ai.ts` | 新增 `providers`、`selectedProviderId`、`fetchProviders()` |

## 二、Agent 工具调用机制

### 背景
此前 AI 只能走 RAG 管道：嵌入查询 → 向量检索 → 灌入上下文 → 回答。用户无法搜索文档、无法查询库统计、无法获取文档详情。

### 方案
实现 OpenAI-compatible Function Calling，AI 自主决定何时调用工具。

### 工具清单

| 工具 | 功能 | 使用场景 |
|------|------|----------|
| `search_documents` | 按关键词全文搜索文档（名称+描述） | "找一下关于XX的文档" |
| `list_all_documents` | 列出所有文档 | "有哪些文档" |
| `get_document_detail` | 获取文档详细信息（含标签、版本） | "文档#4的详细信息" |
| `get_library_overview` | 获取文档库统计概况 | "库里有多少文档" |

### 核心逻辑

```
用户提问
  → 向量检索（注入系统提示词，作为背景知识）
  → LLM 分析意图
      ├─ 内容问答 → 直接用检索内容回答
      ├─ 搜索/查找 → 调用 search_documents 工具
      ├─ 统计/列表 → 调用 get_library_overview / list_all_documents
      └─ 文档详情 → 调用 get_document_detail 工具
  → 工具结果返回 → LLM 整合 → 自然语言回复
```

最大 5 轮工具调用循环，防止死循环。

### 提示词关键设计

- **向量检索结果注入系统提示词**（非用户消息），确保工具调用后仍可见
- **工具标注"仅返回元数据"**，防止 AI 对内容类问题误用工具
- **明确的内容/搜索/统计分类规则**，引导 AI 选择合适的模式

### 变更文件

| 文件 | 变更 |
|------|------|
| `backend/app/services/tool_service.py` | **新建** — 4 个工具定义 + 执行逻辑 |
| `backend/app/services/llm_service.py` | 新增 `run_agent()`、`run_agent_stream()` |
| `backend/app/services/rag_service.py` | `ask()`/`ask_stream()` 改为 Agent 模式 |
| `backend/app/services/summarization_service.py` | 适配 `chat()` 返回值变更 |

## 三、问题排查记录

| 问题 | 根因 | 修复 |
|------|------|------|
| AI 一直拒绝回答 | 没有文档时提示词强制 "仅根据文档回答" | 区分 RAG 模式 / 通用模式 |
| 向量检索返回 0 结果 | Vector 维度 768 与模型 512 不匹配 | 改 `Vector(512)` + 重新嵌入 |
| `get_conversation_messages` 报错 | 异步下懒加载 `messages` 关系失败 | 改用 GROUP BY + COUNT 子查询 |
| pgvector 查询报 "expected str, got list" | asyncpg 不接受 Python list 参数 | 转为字符串 + `CAST(:emb AS vector)` |
| AI 忽略向量上下文选择工具 | 提示词优先级不明确 | 向量上下文注入系统提示词 |

## 四、当前系统状态

| 组件 | 状态 |
|------|------|
| 后端容器 (7个) | 全部运行中 |
| AI 供应商 | 可配置多个，前端下拉切换 |
| Agent 工具调用 | 正常工作（内容问答 / 搜索 / 统计） |
| 向量检索 | pgvector 512 维，2 个文档已嵌入 |
| GitHub | 待推送 |

---

*记录人：Claude Code*
