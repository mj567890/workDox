# 系统健康检查 — 汇总报告

**日期**: 2026-05-06
**Phase 2 完成**: 12 Agent 并行分析+修复
**代码变更**: 约 65 个文件修改，2 个文件新建，1 个文件删除

---

## 一、总体统计

| 维度 | 发现问题 | 已修复 | 待确认 |
|------|----------|--------|--------|
| 架构 | 11 | 2 | 9 |
| 后端质量 | 15 | 15 | 0 |
| 前端质量 | 10 | 9 | 1 |
| 安全 | 11 | 5 | 6 |
| 性能/数据库 | 8 | 6 | 2 |
| RAG+AI | 12 | 12 | 0 |
| 测试 | 2 缺口 | +23 新测试 | 2 |
| DevOps | 12 | 11 | 1 |
| Bug | 32 | 29 | 3 |
| 契约 | 8 | 3 | 5 |
| 死代码 | 13 | 7 | 6 |
| 依赖/配置 | 9 | 6 | 3 |
| **合计** | **~143** | **~105** | **~38** |

---

## 二、CRITICAL 修复清单（已修复）

### Agent 循环崩溃链 (A6)
- LLM HTTP 调用无异常处理 → 添加 ChatError + try/except
- 工具执行无异常处理 → 任何工具失败会崩溃整个循环 → 已包裹
- 流式模式下工具上下文丢失 → run_agent_stream 从原始 messages 重建，丢失工具调用历史 → 改为从 working_messages 重建
- tool_call 结构无校验 → 畸形 LLM 响应导致 KeyError → 添加 _validate_tool_call()
- 空关键词导致 tsquery SQL 错误 → 添加输入验证

### 并发竞态条件 (A9)
- 文档锁定 TOCTOU → SELECT FOR UPDATE
- 版本号冲突 → Document 行级锁
- 工作流节点状态竞态 → advance/rollback/skip_node 全部加锁
- Admin 无法解锁文档 → 权限检查修复
- 标签名重复 → unique=True + 迁移

### 契约断裂 (A10)
- Document LockStatus 接口前后端字段完全不一致 → 对齐
- POST/DELETE /lock 返回垃圾数据 → 返回完整 LockStatusOut

### API 安全 (A4)
- AI Provider API Key 明文暴露 → 掩码处理
- 预签名 URL TTL 过长(1h) → 降至 15min
- 文件上传仅检查扩展名 → 添加 magic bytes 校验

---

## 三、关键性能修复

| 问题 | 位置 | 影响 | 修复 |
|------|------|------|------|
| N+1 查询 | tasks list API | 每页 40 次额外查询 | 批量查询 template/creator |
| N+1 查询 | RAG ask/ask_stream | 每次 10+ 次额外查询 | _get_doc_names_batch() |
| N+1 查询 | task board | M×N 次额外查询 | _get_slot_versions_batch() |
| 无限分页 | task_templates, task_instances | 全表返回 | 添加分页参数 |
| 无缓存 | categories, tags | 每次请求查DB | Redis 600s 缓存 |

---

## 四、待确认的高风险事项

### P1 — 需要立即处理

1. **硬编码凭证** (A4): docker-compose.yml 中 DB/MinIO 密码明文 → 迁移到 .env
2. **JWT_SECRET_KEY 默认值** (A4): `"change-me-in-production"` → 生产环境必须覆盖
3. **python-jose + passlib 废弃** (A12): 两个安全库已停止维护 4-5 年 → 迁移到 PyJWT + bcrypt
4. **5 个后端路由模块未注册** (A1/A10): search/public_dashboard 已注册，matters/workflow_templates/workflow_nodes 是遗留死代码
5. **Alembic 缺少 4 个模型** (A1): DocumentReview, WebhookSubscription, DocumentChunk, AIConversation/AIMessage → autogenerate 可能删表
6. **11 个遗留 matter/workflow 文件** (A1/A10): 表已删除但代码残留，前端有引用会 404

### P2 — 应在下一迭代处理

7. **无频率限制** (A4): 登录端点可暴力破解 → 添加 slowapi
8. **v-html XSS 风险** (A4): 3 处使用但未净化 → DOMPurify
9. **Docker 以 root 运行** (A4/A8): 生产环境应降权
10. **20+ 缺失数据库索引** (A5): DDL 已生成在报告中，需在低峰期执行
11. **_check_document_access 权限静默失效** (A11): 从不拒绝未授权用户
12. **Markdown 表格渲染正则** (A3): 仅处理简单表格，嵌套/转义会断裂
13. **ECharts 内存泄漏** (A3): init() 从不 dispose()
14. **public_dashboard 端点刷新间隔** (A4): 每次刷新 = 一次数据库查询，无缓存

### P3 — 技术债务

15. 整个 `schemas/` 层与 API 隔离 — 10 个文件从未导入
16. 18 个 API 模块中 17 个直接使用 SQLAlchemy（无服务层）
17. 两个 webhook 调度器并存（dispatch.py vs webhook_dispatcher.py）
18. 无前端测试基础设施
19. 无 Celery 健康检查端点
20. 无请求日志中间件

---

## 五、新增测试

| 文件 | 测试数 | 覆盖 |
|------|--------|------|
| `backend/tests/test_search.py` | 11 | 全文搜索（关键词、过滤、分页、权限） |
| `backend/tests/test_ai.py` | 12 | 文本分块(7) + Agent循环(5) |
| 已有测试 | 60 | 认证、权限、文档、事项、审批 |
| **总计** | **83** | |

---

## 六、文件变更摘要

### 后端修改 (~45 files)
- `api/v1/router.py` — 注册 search + public_dashboard
- `api/v1/documents.py` — 5 处日志修复、LockStatus 返回、Redis 缓存、magic bytes 校验
- `api/v1/tasks.py` — N+1 批量查询修复
- `api/v1/task_templates.py` — 分页
- `api/v1/task_instances.py` — 分页
- `api/v1/system.py` — API Key 掩码
- `api/v1/auth.py` — 日志
- `api/v1/ws.py` — JWT 异常细化
- `api/v1/ai.py` — ChatError 503 处理
- `api/v1/users.py` — 未使用导入清理
- `api/v1/matters.py` — 未使用导入清理
- `services/llm_service.py` — Agent 循环 7 项修复 (ChatError, 工具异常, 消息限制, tool_call 校验, 流式上下文, etc.)
- `services/tool_service.py` — 4 项修复 (空关键词, 类型校验, 重复列, 描述完善)
- `services/rag_service.py` — 去重 80% 重复代码 + N+1 批量查询
- `services/embedding_service.py` — 维度注释 + 模型加载异常 + 降级 fallback
- `services/document_service.py` — FOR UPDATE 锁 + admin 解锁 + 未使用导入
- `services/workflow_service.py` — 3 个节点操作的 FOR UPDATE
- `services/task_management_service.py` — N+1 批量查询 + 分页
- `services/ai_config.py` — 日志
- `services/auth_service.py` — 日志
- `services/archive_service.py` — 日志
- `services/document_preview_service.py` — 日志
- `services/summarization_service.py` — 日志
- `services/cas_service.py` — 未使用导入
- `services/oauth2_service.py` — 重复导入
- `core/storage.py` — 预签名 TTL 从 3600→900
- `core/ws_manager.py` — 异常细化
- `models/document.py` — Tag.name unique=True
- `utils/file_utils.py` — magic bytes 校验
- `utils/dispatch.py` — 异常细化
- `utils/email_sender.py` — print→logger
- `tasks/embedding_tasks.py` — 连接池泄漏修复
- `schemas/auth.py` — 字段长度校验
- `schemas/user.py` — 字段长度校验
- `alembic/env.py` — WebhookSubscription 导入
- `alembic/versions/add_tag_name_unique.py` — 新建迁移

### 前端修改 (~16 files)
- `views/documents/DocumentDetailView.vue` — LockStatus 字段对齐 (4处)
- `views/tasks/TaskBoardView.vue` — 5 个函数添加错误处理
- `views/tasks/TaskCenterView.vue` — 2 个函数添加错误处理
- `views/tasks/TaskTemplateEditView.vue` — 5 个函数添加错误处理
- `views/tasks/TaskListView.vue` — 错误处理 + 空状态
- `views/audit/AuditLogView.vue` — 搜索修复 + 空状态
- `views/admin/UserManagementView.vue` — 错误处理 + 空状态 + maxlength
- `views/admin/DepartmentManagementView.vue` — 空状态 + maxlength
- `views/admin/DocumentCategoryManagementView.vue` — 空状态 + maxlength
- `views/admin/RoleManagementView.vue` — 空状态 + maxlength
- `views/admin/TagManagementView.vue` — 空状态 + maxlength
- `views/admin/AIConfigView.vue` — toggleProvider 回滚
- `views/ai/AIChatView.vue` — onMounted 错误处理
- `views/profile/WebhookManagementView.vue` — 空状态
- `api/documents.ts` — LockStatus 接口对齐
- `api/index.ts` — AbortController 信号传递
- `composables/useAuth.ts` — 删除（死代码）

### DevOps 修改 (~6 files)
- `docker-compose.yml` — 健康检查 + 资源限制 + depends_on 条件 + 镜像版本固定
- `frontend/nginx.conf` — gzip + 缓存 + 安全头 + 代理超时
- `deploy.sh` — 前置检查 + 错误处理 + 健康等待
- `backend/.env.example` — 21 个缺失变量
- `backend/.dockerignore` — 新建
- `frontend/.dockerignore` — 新建
- `backend/Dockerfile` — 基础镜像固定
- `frontend/Dockerfile` — 基础镜像固定
- `backend/requirements.txt` — redis 版本固定

### 新建文件
- `backend/tests/test_search.py` — 11 个搜索测试
- `backend/tests/test_ai.py` — 12 个 AI 测试
- `backend/alembic/versions/add_tag_name_unique.py` — 标签唯一约束迁移
- `backend/.env.example` — 环境变量文档
- `backend/.dockerignore`
- `frontend/.dockerignore`

### 删除文件
- `frontend/src/composables/useAuth.ts` — 从未使用

---

## 七、下一步

1. **确认 P1 事项** — 特别是 docker-compose 凭证迁移、废弃库替换、遗留代码清理
2. **执行 Phase 4** — 对 P2 事项进行自动修复（频率限制、v-html 净化、ECharts 内存泄漏等）
3. **同步到服务器** — 变更已就绪，确认后推送到服务器验证
4. **运行测试** — 83 个测试需要在服务器上执行验证

---

*报告生成: Claude Code Orchestrator | 2026-05-06*
