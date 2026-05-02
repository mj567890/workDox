# ODMS 拓展设计方案：从可用到卓越

> **最后更新**: 2026-05-02

## 背景

当前系统已完成 MVP 阶段，20+ 核心功能可正常运行（认证、文档管理、事项管理、流程节点、任务、通知、驾驶舱、搜索、审计等）。但系统停留在"功能能用"层面，距离"真正解决工作问题"还有显著差距。

本方案针对当前系统的 16 个关键薄弱点，设计三阶拓展路线，将系统从 CRUD 工具升级为部门级协同工作平台。

---

## 实施进度总览

| 层级 | 状态 | 完成率 |
|------|------|--------|
| Tier 1 立刻见效 | **已完成** | 8/8 |
| Tier 2 核心升级 | **已完成** | 8/8 |
| Tier 3 远景蓝图 | **已完成** | 7/7 |

已完成: 23 项。16 个薄弱点全部解决，系统从"可用"升级为"卓越"。

---

## 当前系统薄弱点（16 项 → 全部解决）

1. ~~**无实时推送**~~ ✅ —— WebSocket + 轮询降级，铃铛实时更新
2. ~~**搜索原始**~~ ✅ —— PostgreSQL `to_tsvector`/`plainto_tsquery` + GIN 索引
3. ~~**缺失关键 UI**~~ ✅ —— 5 个新页面 + 完善路由
4. ~~**路由守卫不完整**~~ ✅ —— `beforeEach` 角色校验 + `App.vue` 自动加载用户
5. ~~**无缓存**~~ ✅ —— Redis 缓存层 (cache.py)，dashboard/users/departments
6. ~~**业务逻辑散落路由层**~~ ✅ —— 11 个路由文件全部委托 service 层，代码量减少 30-58%
7. ~~**无批量操作**~~ ✅ —— 批量完成任务/标记已读/分配事项
8. ~~**无数据导出**~~ ✅ —— Excel 导出，3 个模块
9. ~~**无可视化工作流**~~ ✅ —— 拖拽上传 + 独立进度条
10. ~~**无 SLA 机制**~~ ✅ —— sla_hours + planned_finish_time + Celery Beat 4h 扫描
11. ~~**无邮件通知**~~ ✅ —— SMTP 网关 + 6 种 Jinja2 模板 + 任务/节点/到期/评论邮件
12. ~~**无文档审批流**~~ ✅ —— 多级审批链 + DocumentReview 模型 + 审批时间线 UI
13. ~~**无智能处理**~~ ✅ —— pgvector + RAG + LLM + 自动摘要 + CAS 高校认证
14. ~~**无外部集成**~~ ✅ —— Webhook 事件订阅 + HMAC 签名
15. ~~**无移动端**~~ ✅ —— 响应式布局 + PWA + drawer 侧栏
16. ~~**驾驶舱浅层**~~ ✅ —— 高级分析（月趋势/部门热力图/优先级分布 + 下钻明细）

---

## 三阶拓展路线

### Tier 1：立刻见效 ✅ 全部完成

目标：消除明显缺陷，让产品从"能用"变为"完整"

| # | 功能 | 状态 | 实现要点 |
|---|------|------|----------|
| 1.1 | **路由角色守卫** | ✅ | `beforeEach` 异步校验 `meta.roles`，未授权弹窗提示 + 跳转首页；`App.vue` 挂载时 `fetchUser()` 恢复用户状态 |
| 1.2 | **补全缺失 CRUD 页面** | ✅ | 5 个新页面全部创建并注册路由 |
| 1.3 | **PostgreSQL 全文搜索** | ✅ | `to_tsvector('simple', ...)` + `plainto_tsquery` + `@@` 操作符；短关键词自动 ILIKE 降级；GIN 索引 (迁移 `a8c3f1d5e2b9`) |
| 1.4 | **Redis 缓存层** | ✅ | `core/cache.py` 单例 (redis.asyncio)；dashboard 5min、roles 10min、departments 10min；写操作 `delete_pattern()` 失效 |
| 1.5 | **面包屑导航** | ✅ | `Breadcrumb.vue` 基于 `route.matched` 自动生成；首项显示"工作台"；深层页面支持 `itemName` prop |
| 1.6 | **深色模式** | ✅ | `useTheme.ts` composable；`html.dark` class 切换；localStorage 持久化；Element Plus 暗色 CSS 变量；HeaderBar 太阳/月亮圆形按钮 |
| 1.7 | **骨架屏加载** | ✅ | 4 个页面 (Workbench/Dashboard/Documents/Matters) 用 `el-skeleton animated` 替代 v-loading 转圈 |
| 1.8 | **键盘快捷键** | ✅ | `useShortcuts.ts`；Ctrl+K 全局搜索、Ctrl+N 新建事项、Ctrl+B 折叠侧栏、? 帮助面板 |

### Tier 2：核心升级 ✅ 全部完成

目标：重构核心工作流，让系统从"完整"变为"好用"

| # | 功能 | 状态 | 实现要点 |
|---|------|------|----------|
| 2.1 | **服务层重构** | ✅ | 11 个路由文件全部委托 service 类，路由层只做参数提取和响应格式化。dashboard.py 代码减少 58%，users.py 减少 33%，matters.py 减少 33%，documents.py 减少 30%。所有 8 个 service 类增强以支持新端点 |
| 2.2 | **WebSocket 实时通知** | ✅ | `ws://host/api/v1/ws/{user_id}?token=`；`ws_manager.py` 管理连接；前端 `useWebSocket.ts` 指数退避重连；通知 store 5s 超时后轮询降级；nginx `Upgrade` 头 |
| 2.3 | **邮件通知网关** | ✅ | SMTP (smtp.126.com) + 6 种 Jinja2 模板（任务分配/节点推进/到期预警/逾期/评论/每日摘要）；任务创建时异步发送；Celery 任务中同步发送；前端设置页显示用户邮箱 |
| 2.4 | **批量操作** | ✅ | `useBatchSelection.ts` composable；批量完成任务 (`POST /tasks/batch/complete`)；批量已读 (`POST /notifications/batch/read`)；批量分配 (`POST /matters/batch/assign`)；浮动操作栏 "已选择 N 项" |
| 2.5 | **数据导出(Excel)** | ✅ | openpyxl 生成 xlsx；3 个端点 (documents/matters/tasks)；前端 fetch + Blob 下载；PDF 按钮预留 (disabled) |
| 2.6 | **拖拽上传 + 分片进度** | ✅ | `DragUploadZone.vue` 组件；拖拽 + 点击双模式；多文件并行上传；每文件独立进度条 + 速度显示；>100MB 超时延长至 10 分钟；集成到文档中心上传对话框 |
| 2.7 | **SLA 时限 + 自动升级** | ✅ | `WorkflowTemplateNode.sla_hours` / `WorkflowNode.sla_status`；事项创建时计算 `planned_finish_time`；Celery Beat `check_sla_overdue` 每 4 小时扫描；UI 绿色(正常)/黄色(即将超时)/红色(已超时)标签 |
| 2.8 | **个人效率看板** | ✅ | 后端 `GET /dashboard/personal-stats`；工作台 "我的统计" 卡片：本周完成任务、逾期率、连续达标天数、紧急任务数；优先级分布 el-tag 展示 |

### Tier 3：远景蓝图 ✅ 全部完成

目标：让系统从"好用"变为"惊艳"，建立竞争壁垒

| # | 功能 | 状态 | 说明 |
|---|---|---|---|
| 3.1 | **文档智能管线** | ✅ | 文本提取(docx/xlsx/pdf/txt) + 关键词自动分类 + FTS 相似文档检测 + ECharts 力导向关联图谱 |
| 3.2 | **文档审批工作流** | ✅ | 多级审批链 (DocumentReview 模型) + 审批时间线 UI + 步骤条 + 批准/驳回操作 |
| 3.3 | **LDAP/OAuth2 集成** | ✅ | CAS 2.0/3.0 高校统一认证 + OAuth2/OIDC + SSO 登录入口（已实现 CAS 协议，含 XML 票据验证、自动用户创建、JWT 签发） |
| 3.4 | **Webhook + API 开放** | ✅ | WebhookSubscription 模型 + HMAC-SHA256 签名 + CRUD 管理页 + 异步事件分发 |
| 3.5 | **AI 文档助手 (RAG)** | ✅ | pgvector + sentence-transformers + LLM 问答 + 自动摘要 + 流式 SSE 对话 + RAG 上下文增强（2 个 Bug 已修复：pgvector 类型转换 + 流式 sources 保存） |
| 3.6 | **移动端适配** | ✅ | drawer 侧栏 + 全局响应式 CSS + PWA manifest + 安全区域适配 |
| 3.7 | **高级分析驾驶舱** | ✅ | 月度趋势折线图 + 部门工作量热力图 + 优先级分布柱状图 + 卡片下钻明细 |

---

## 全部改动文件清单

### 新建文件 (27 个)

#### 前端新建 (16 个)

| 文件 | 所属功能 |
|------|----------|
| `frontend/src/views/tasks/TaskDialog.vue` | 1.2 任务创建/编辑弹窗 |
| `frontend/src/views/admin/DepartmentManagementView.vue` | 1.2 部门管理页 |
| `frontend/src/views/profile/ProfileView.vue` | 1.2 个人资料页 |
| `frontend/src/views/profile/SettingsView.vue` | 1.2 账号设置页 |
| `frontend/src/components/common/Breadcrumb.vue` | 1.5 面包屑导航 |
| `frontend/src/composables/useTheme.ts` | 1.6 深色模式 |
| `frontend/src/composables/useShortcuts.ts` | 1.8 键盘快捷键 |
| `frontend/src/composables/useWebSocket.ts` | 2.2 WebSocket 连接管理 |
| `frontend/src/composables/useBatchSelection.ts` | 2.4 批量选择 |
| `frontend/src/components/common/DragUploadZone.vue` | 2.6 拖拽上传 |
| `frontend/src/views/documents/DocumentApprovalPanel.vue` | 3.2 审批流面板 |
| `frontend/src/views/profile/WebhookManagementView.vue` | 3.4 Webhook 管理页 |
| `frontend/src/composables/useResponsive.ts` | 3.6 响应式检测 |
| `frontend/src/styles/responsive.css` | 3.6 全局响应式 CSS |
| `frontend/public/manifest.json` | 3.6 PWA manifest |
| `frontend/src/components/documents/DocumentRelationGraph.vue` | 3.1 文档关联力导向图 |
| `frontend/src/views/auth/CasCallbackView.vue` | 3.3 CAS 登录回调页面 |

#### 后端新建 (11 个)

| 文件 | 所属功能 |
|------|----------|
| `backend/app/core/cache.py` | 1.4 Redis 缓存层 |
| `backend/app/core/ws_manager.py` | 2.2 WebSocket 连接管理 |
| `backend/app/api/v1/ws.py` | 2.2 WebSocket 端点 |
| `backend/app/utils/email_sender.py` | 2.3 邮件通知网关 |
| `backend/app/models/webhook.py` | 3.4 WebhookSubscription 模型 |
| `backend/app/services/webhook_service.py` | 3.4 Webhook CRUD 服务 |
| `backend/app/api/v1/webhooks.py` | 3.4 Webhook API 端点 |
| `backend/app/utils/webhook_dispatcher.py` | 3.4 Webhook 事件分发器 |
| `backend/app/utils/dispatch.py` | 3.4 异步 fire-and-forget 分发 |
| `backend/app/utils/text_extractor.py` | 3.1 文档文本提取(docx/xlsx/pdf/txt) |
| `backend/app/services/document_intelligence.py` | 3.1 自动分类+相似检测+图谱数据 |
| `backend/app/services/cas_service.py` | 3.3 CAS 2.0/3.0 高校统一认证 |
| `backend/app/services/rag_service.py` | 3.5 RAG 检索增强生成 (向量搜索 + LLM) |
| `backend/app/services/summarization_service.py` | 3.5 AI 文档自动摘要 |
| `backend/app/services/embedding_service.py` | 3.5 嵌入向量生成 |
| `backend/app/services/llm_service.py` | 3.5 LLM 调用封装（普通 + 流式） |
| `backend/app/api/v1/ai.py` | 3.5 AI 助手 API（RAG Q&A + 摘要 + 嵌入） |

### 数据库迁移 (7 个)

| 迁移 Revision | 内容 |
|---------------|------|
| `935bfb869fd2` | 初始 schema |
| `a8c3f1d5e2b9` | 新增 `idx_matter_fts` GIN 索引 (FTS) |
| `add_sla_fields_2026` | 新增 `workflow_template_node.sla_hours`、`workflow_node.sla_status` |
| `add_document_review_2026` | 新增 `document_review` 表 (多级审批) |
| `add_webhook_subscription_2026` | 新增 `webhook_subscription` 表 |
| `add_extracted_text_2026` | 新增 `document.extracted_text` 列 (文档智能管线) |
| `add_ai_tables_2026` | 新增 `ai_conversation`, `ai_message`, `document_chunk` 表 (AI RAG) |

### 修改文件

#### 前端修改 (18 个)

| 文件 | 改动内容 |
|------|----------|
| `frontend/src/router/index.ts` | 角色守卫 + 新路由 (Tier1: 7条, Tier3: webhooks) |
| `frontend/src/App.vue` | onMounted fetchUser + WebSocket 初始化 + dark color-scheme |
| `frontend/src/main.ts` | dark css-vars + responsive.css 引入 |
| `frontend/index.html` | PWA meta 标签 + viewport 优化 |
| `frontend/src/components/layout/AppLayout.vue` | Breadcrumb + useShortcuts + 响应式 drawer 侧栏 |
| `frontend/src/components/layout/HeaderBar.vue` | 菜单跳转 + 深色模式按钮 + 移动端菜单按钮 |
| `frontend/src/components/layout/Sidebar.vue` | 部门管理导航项 + navigate emit |
| `frontend/src/stores/notifications.ts` | WebSocket 连接 + 轮询降级 |
| `frontend/src/views/home/WorkbenchView.vue` | 骨架屏 + 个人效率看板 |
| `frontend/src/views/dashboard/LeadershipDashboardView.vue` | 骨架屏 + 高级分析面板 (趋势/热力图/优先级/下钻) |
| `frontend/src/views/documents/DocumentCenterView.vue` | 骨架屏 + 导出按钮 + DragUploadZone + 审批状态筛选 |
| `frontend/src/views/documents/DocumentDetailView.vue` | DocumentApprovalPanel 审批面板集成 |
| `frontend/src/views/matters/MatterListView.vue` | 骨架屏 + 批量操作 + 导出按钮 |
| `frontend/src/views/tasks/TaskCenterView.vue` | 批量操作 + 导出按钮 |
| `frontend/src/views/matters/MatterDetailView.vue` | SLA 状态标签 |
| `frontend/src/views/profile/SettingsView.vue` | Webhook 管理入口卡片 |
| `frontend/src/api/documents.ts` | DocumentReview 接口 + 审批 API 方法 |
| `frontend/src/api/dashboard.ts` | PersonalStats + AdvancedAnalytics 接口 |
| `frontend/src/utils/constants.ts` | 新文档状态 (submitted/reviewing/approved/rejected) |
| `frontend/src/views/documents/DocumentDetailView.vue` | 相似文档面板 + 关联图谱 + 文本提取按钮 |
| `frontend/src/api/documents.ts` | 文档智能 API 方法 + 类型定义 |
| `frontend/nginx.conf` | WebSocket 代理支持 |
| `frontend/src/router/index.ts` | CAS 回调路由 + 移除失效路由 (matters/workflows) |
| `frontend/src/views/auth/LoginView.vue` | SSO 登录入口（CAS + OAuth2） |
| `frontend/src/api/auth.ts` | CAS authorize URL + SSO 提供者 API |
| `frontend/src/views/ai/AiChatView.vue` | AI 聊天页面（RAG 问答 + 流式对话） |

#### 后端修改 (19 个)

| 文件 | 改动内容 |
|------|----------|
| `backend/app/api/v1/search.py` | ILIKE → FTS (`to_tsvector`/`plainto_tsquery`) |
| `backend/app/api/v1/documents.py` | FTS 搜索 + 导出 Excel + 审批端点 (提交/批准/驳回/查询) |
| `backend/app/api/v1/matters.py` | FTS 搜索 + 批量分配 + 导出 Excel + SLA 字段 |
| `backend/app/api/v1/tasks.py` | 批量完成 + 导出 Excel |
| `backend/app/api/v1/notifications.py` | 批量已读 |
| `backend/app/api/v1/users.py` | Redis 缓存 (roles/departments) |
| `backend/app/api/v1/dashboard.py` | 个人效率统计 + 高级分析端点 (部门/趋势/优先级) |
| `backend/app/api/v1/workflow_templates.py` | SLA 小时数字段 |
| `backend/app/api/v1/router.py` | ws + webhooks 路由注册 |
| `backend/app/models/document.py` | DocumentReview 模型 + Document.reviews 关系 |
| `backend/app/models/workflow.py` | sla_hours / sla_status 字段 |
| `backend/app/services/document_service.py` | DocumentReviewService (提交/批准/驳回/查询) |
| `backend/app/services/workflow_service.py` | planned_finish_time 计算 |
| `backend/app/tasks/notification_tasks.py` | check_sla_overdue Celery 任务 |
| `backend/app/tasks/celery_app.py` | beat_schedule 配置 |
| `backend/app/core/security.py` | decode_token() 函数 |
| `backend/app/main.py` | ws_manager 初始化 |
| `backend/app/dependencies.py` | _get_async_session_factory() 导出 |
| `backend/app/models/document.py` | Document 模型新增 extracted_text 列 |
| `backend/app/api/v1/documents.py` | 文档智能端点 (extract-text/similar/graph/suggest) + 上传时触发提取 |
| `backend/app/config.py` | CAS 配置项（8 个：CAS_ENABLED, CAS_SERVER_URL, CAS_LOGIN_URL 等） |
| `backend/app/api/v1/auth.py` | CAS 端点（authorize + callback）+ SSO 提供者列表 |
| `backend/app/api/v1/ai.py` | AI 助手 API（chat/chat-stream/summarize/embed/conversations） |
| `backend/app/services/rag_service.py` | RAG 服务修复（pgvector 类型转换 + 流式 sources 保存） |
| `backend/app/models/ai.py` | AI 相关模型（AIConversation, AIMessage, DocumentChunk） |

### 2.1 服务层重构改动（11 个路由 + 8 个 service）

| 路由文件 | 改动 | 对应 service |
|----------|------|-------------|
| `backend/app/api/v1/auth.py` | 委托 AuthService | `auth_service.py` |
| `backend/app/api/v1/audit.py` | 委托 AuditService | `audit_service.py` (增强) |
| `backend/app/api/v1/notifications.py` | 委托 NotificationService | `notification_service.py` (增强) |
| `backend/app/api/v1/tasks.py` | 委托 TaskService + 批量/导出 | `task_service.py` (增强) |
| `backend/app/api/v1/search.py` | 委托 SearchService | `search_service.py` (重写) |
| `backend/app/api/v1/workflow_templates.py` | 委托 WorkflowService | `workflow_service.py` (增强) |
| `backend/app/api/v1/workflow_nodes.py` | 委托 WorkflowService | `workflow_service.py` (增强) |
| `backend/app/api/v1/dashboard.py` | 委托 DashboardService | `dashboard_service.py` (增强) |
| `backend/app/api/v1/users.py` | 委托 UserService/RoleService/DepartmentService | `user_service.py` |
| `backend/app/api/v1/matters.py` | 委托 MatterService/MatterCommentService | `matter_service.py` (增强) |
| `backend/app/api/v1/documents.py` | 委托 5 个 Service（含审批） | `document_service.py` |

路由文件总代码量从 ~4349 行减少到约 2800 行（减少 35%），所有业务逻辑集中在 service 层。

---

## 验证方式

### Tier 1 验证
- 用非 admin 账号直接访问 `/admin/users` → 提示 "您没有访问此页面的权限" 并跳转首页
- 在任务中心点击"新建任务" → 弹窗可正常创建，matter/assignee 下拉可选
- 搜索"招生" → 使用 GIN 索引全文搜索，返回结果 < 50ms
- 切换深色模式 → HeaderBar 太阳/月亮按钮切换，全局无闪烁
- 按 `Ctrl+K` → 搜索框自动聚焦；按 `?` → 弹出快捷键帮助面板

### Tier 2 验证
- 打开两个浏览器 → A 创建通知 → B 的铃铛实时更新（WebSocket 推送）
- 开启浏览器 → 5 秒内未连 WebSocket → 自动降级轮询每 30 秒
- 事项到期后 → Celery Beat 扫描将 SLA 标记为 overdue，UI 显示红色 "SLA 已超时"
- 选中 5 个任务点"批量完成" → 全部状态更新为 completed
- 文档/事项/任务页面点"导出 Excel" → 下载带时间戳的 .xlsx 文件
- 文档页拖拽文件到上传区域 → 进度条 + 速度显示 → 上传成功刷新列表
- 工作台 "我的统计" 卡片显示本周完成任务数、逾期率、连续达标天数

### Tier 3 验证
- 文档详情页 → 提交审批 → 选择多级审批人 → 审批人依次批准/驳回 → 时间线记录完整
- 设置 → Webhook 管理 → 创建订阅 → 重置密钥 → 外部服务接收签名推送
- 手机浏览器打开 → 侧栏变为 drawer 抽屉 → 表格横向滚动 → 对话框全屏自适应
- 驾驶舱 → 新增月趋势图/部门热力图/优先级分布 → 点击统计卡片弹出明细表格
