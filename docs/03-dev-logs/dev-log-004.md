# 开发日志 #004 — AI 文档助手 (RAG) + 预览修复 + 安全配置外移

**日期**：2026-04-30
**阶段**：P1 安全加固 + P2 AI 智能处理 + Bug 修复
**产出**：7 个新服务/API + 5 项 bug 修复 + 94 种文件类型支持

## 一、P1 安全配置外移

### SMTP 凭证 → .env
- 修改 `backend/app/utils/email_sender.py`：从 `get_settings()` 读取 SMTP 配置，不再硬编码
- 新增 7 个 SMTP 配置项到 `Settings` 类和 `.env`

### JWT_SECRET_KEY → .env
- 从 `docker-compose.yml` 移除硬编码 `JWT_SECRET_KEY: change-me-in-production`
- JWT 密钥现在仅由 `.env` 管理

## 二、P2 AI 文档助手 (RAG)

### 技术选型

| 组件 | 方案 | 说明 |
|------|------|------|
| LLM | DeepSeek API (deepseek-chat) | OpenAI 兼容格式 |
| Embedding | fastembed + BGE-small-zh | ONNX Runtime，768维，~50MB |
| 向量存储 | pgvector | `<=>` 余弦距离，IVFFlat 索引 |
| 前端聊天 | Vue 3 + Element Plus | SSE 流式响应 |

### 新建文件（12个）

| 文件 | 说明 |
|------|------|
| `backend/app/models/ai.py` | DocumentChunk, AIConversation, AIMessage 模型 |
| `backend/app/services/embedding_service.py` | fastembed 封装，asyncio.to_thread 非阻塞 |
| `backend/app/services/llm_service.py` | DeepSeek API 客户端 (httpx + SSE streaming) |
| `backend/app/services/rag_service.py` | 分块(500字符/50重叠) → 向量检索 → RAG 问答 |
| `backend/app/services/summarization_service.py` | LLM 文档摘要 |
| `backend/app/api/v1/ai.py` | 7 个 API 端点（chat/stream/summarize/embed/conversations） |
| `backend/app/tasks/embedding_tasks.py` | Celery 后台任务：embedding + 自动摘要 |
| `backend/alembic/versions/enable_pgvector_and_ai_tables.py` | DDL 迁移：vector 扩展 + AI 表 |
| `frontend/src/api/ai.ts` | AI API TypeScript 封装 |
| `frontend/src/stores/ai.ts` | AI 聊天 Pinia 状态管理 |
| `frontend/src/views/ai/AIChatView.vue` | AI 助手聊天主界面 |
| `frontend/src/components/documents/DocumentRelationGraph.vue` | 文档关系图谱（ECharts 力导向图） |

### 修改文件（9个）

| 文件 | 变更 |
|------|------|
| `backend/app/config.py` | +9 个 AI 配置项 |
| `backend/app/models/document.py` | +embedding Vector(768), +chunks 关系 |
| `backend/app/api/v1/router.py` | 注册 ai 路由 |
| `backend/app/api/v1/documents.py` | +similar-vector 端点，上传触发 Celery 任务 |
| `backend/app/services/document_intelligence.py` | +find_similar_by_vector, +get_document_graph_data |
| `backend/app/tasks/celery_app.py` | 注册 embedding_tasks |
| `backend/requirements.txt` | +fastembed, +pgvector |
| `frontend/src/router/index.ts` | +/ai/chat 路由 |
| `frontend/src/components/layout/Sidebar.vue` | +AI 助手菜单项 |

### RAG 问答流程
```
用户提问 → embed(query) → pgvector <=> 检索 Top-K chunks
         → 拼接上下文 → DeepSeek chat/completions → SSE 流式回复
```

## 三、Bug 修复

### 1. 文档详情页进入弹"请求失败" (MissingGreenlet)
**根因**：`get_document_graph_data` 中 `source.tags` 未预加载，触发懒加载导致 `MissingGreenlet`
**修复**：查询时添加 `selectinload(Document.tags)` 预加载 (`document_intelligence.py:298`)

### 2. 文档 owner 无删除权限
**根因**：API 层 `check_permission(DOCUMENT_DELETE)` 硬拦截 + 前端无按钮
**修复**：
- 后端：移除 `check_permission`，服务层已检查 `owner_id / admin / dept_leader`
- 前端：`DocumentDetailView.vue` 新增红色删除按钮，`canDeleteCurrentDoc` computed

### 3. 文本提取仅支持 4 种文件类型
**根因**：`text_extractor.py` 仅支持 txt/docx/pdf/xlsx
**修复**：重写提取器，扩展至 **94 种类型**：
- 纯文本 89 种：md, csv, json, yaml, html, py, js, ts, java, go, rs, c, cpp, sql...
- 二进制 5 种：docx, pdf, xlsx, xls, pptx (新增 python-pptx 支持)
- API 端点改用 `is_supported()` 动态检查

### 4. "加载预览"点击无效
**根因**：三个问题叠加
- 后端返回 `preview_url`/`is_original`，前端读 `res.url`/`res.status` → 字段不匹配
- 上传时从未 dispatch `convert_to_pdf` Celery 任务
- Celery Worker 容器未安装 LibreOffice

**修复**：
- 统一响应格式为 `{url, status: "ready"}`
- upload complete 处理中 dispatch `convert_to_pdf.delay(doc_id, storage_path, file_type)`
- Dockerfile 加入 LibreOffice (core/writer/calc/impress)，使用阿里云 Debian 镜像源
- 重建全部 3 个后端镜像 (backend/worker/beat)

### 5. MinIO 预签名 URL 签名不匹配
**根因**：简单字符串替换 host (`minio:9000` → `10.10.50.205:9000`) 破坏签名
**修复**：创建独立 `_public_client`（配置 `MINIO_PUBLIC_ENDPOINT=10.10.50.205:9000`）直接生成签名 URL，签名与 URL 一致

### 6. Celery Worker 模型导入顺序错误
**根因**：`convert_to_pdf` 任务中 `from app.models.document import Document` 触发 `MatterType` → `Matter` → `User` 依赖链失败
**修复**：在任务函数内依次导入全部 9 个模型模块 (`user, role, department, matter, document, workflow, task, webhook, ai`)

## 四、部署相关

### Docker 兼容性
- docker-compose v1.29.2 + Docker 29.1.3 存在 `ContainerConfig` KeyError
- 创建 `deploy.sh` 脚本：docker stop → docker rm → docker-compose up -d
- 用法：`bash deploy.sh [backend|frontend|all]`

### 前端文件同步
- P2 前端文件曾因 scp 未同步导致构建失败
- 批量同步了 `ai.ts`, `AIChatView.vue`, `stores/ai.ts`, `router/index.ts`, `Sidebar.vue`

## 当前系统状态

| 组件 | 状态 |
|------|------|
| 后端容器 (7个) | 全部运行中 |
| pgvector 扩展 | 已启用，IVFFlat 索引已建 |
| LibreOffice | 7.4.7.2，已装于 backend/worker/beat |
| 前端 | 含 AI 聊天界面 + 文档删除按钮 + 预览 |
| 数据库 | 3 个 stale draft 文档已软删除 |
| HTML 预览 | LibreOffice → HTML，iframe srcdoc 内嵌展示 |

## 五、预览升级：LibreOffice HTML 转换 (2026-04-30)

### 背景
此前预览链路为：PDF 转换 → MinIO → 预签名 URL → 浏览器下载 PDF。两个问题：
1. 系统无 PDF 内嵌组件，浏览器只能强制下载
2. PDF 中文乱码（字体缺失）

后改为文本提取方案，但纯文本丢失了表格、加粗、标题等排版信息。

### 方案：LibreOffice → HTML → iframe srcdoc
- **保留格式**：HTML 保留了表格、粗体、斜体、标题、列表等 Word/Excel/PPT 排版
- **内嵌展示**：使用 `<iframe srcdoc>` 隔离样式，不污染页面也不被页面污染
- **三层回退**：HTML 预览 → 文本提取 → 不支持提示

### 变更文件（6个）

| 文件 | 变更 |
|------|------|
| `backend/app/tasks/preview_tasks.py` | `convert_to_pdf` → `convert_to_html`，`--convert-to html`，上传 `preview/{id}/preview.html` |
| `backend/app/models/document.py` | +`preview_html_path` 列 |
| `backend/alembic/versions/add_preview_html_path.py` | DDL 迁移：`ALTER TABLE document ADD COLUMN preview_html_path` |
| `backend/app/api/v1/documents.py` | `get_preview_text` 优先检查 HTML；上传时 dispatch `convert_to_html` |
| `frontend/src/api/documents.ts` | `PreviewText.format` 新增 `'html'` |
| `frontend/src/views/documents/DocumentDetailView.vue` | `<iframe srcdoc>` 展示 HTML 格式预览 |

### 预览优先级
```
get_preview_text(doc_id)
  ├── 1. preview_html_path 存在 → MinIO 下载 HTML → format: "html" → iframe srcdoc
  ├── 2. extracted_text 有缓存或支持提取 → format: "markdown"/"text" → pre/v-html
  └── 3. 不支持 → format: "text", has_content: false
```

## 验证命令

```bash
# 预览转换
curl http://10.10.50.205:8000/api/v1/documents/4/preview -H "Authorization: Bearer $TOKEN"

# AI 问答
curl -X POST http://10.10.50.205:8000/api/v1/ai/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"这份文档的主要内容是什么？"}'

# 向量相似文档
curl http://10.10.50.205:8000/api/v1/documents/4/similar-vector \
  -H "Authorization: Bearer $TOKEN"
```

---

*记录人：Claude Code*
