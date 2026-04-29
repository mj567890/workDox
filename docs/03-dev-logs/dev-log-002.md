# 开发日志 #002 — Phase 1-4 全栈代码实现

**日期**：2026-04-28
**阶段**：全栈开发 — 从零搭建完整项目代码
**产出**：138 个文件，后端 12 个 API 路由模块 + 10 个 Service + 18 张数据表，前端 12 个页面 + 8 个组件 + 6 个 Store + 9 个 API 模块

## 完成内容

### 1. 项目脚手架与基础设施

**Docker 编排** (`docker-compose.yml`):
- PostgreSQL 15 (pgvector) — 数据库
- Redis 7 — 缓存 + Celery 消息队列
- MinIO — S3 兼容对象存储
- FastAPI 后端 + Celery Worker + Celery Beat
- Vue 3 前端 (Nginx)

**后端配置** (`backend/`):
- `app/config.py` — Pydantic Settings 集中管理所有环境变量
- `app/main.py` — FastAPI 入口，CORS 中间件，路由挂载
- `app/dependencies.py` — 依赖注入：`get_db`、`get_current_user`、`check_permission`
- `alembic/` — 数据库迁移配置（env.py + alembic.ini）
- `Dockerfile` — 含 LibreOffice 用于文档转换

**前端配置** (`frontend/`):
- `vite.config.ts` — Vite + Element Plus 自动导入
- `tsconfig.json` — TypeScript 严格模式
- `package.json` — Vue 3.4, Element Plus 2.6, ECharts 5.5, PDF.js 4.0

### 2. 数据库模型（18 张表）

| 模型文件 | 表 |
|---|---|
| `models/base.py` | Base, TimestampMixin |
| `models/department.py` | department |
| `models/user.py` | user, user_role |
| `models/role.py` | role |
| `models/document.py` | matter_type, document_category, tag, document, document_version, document_tag, document_edit_lock, cross_matter_reference |
| `models/matter.py` | matter, matter_member, matter_comment |
| `models/workflow.py` | workflow_template, workflow_template_node, workflow_node |
| `models/task.py` | task, notification, operation_log |

关键设计：
- PostgreSQL GIN 全文检索索引（`to_tsvector`）
- 复合索引：matter(status), matter(due_date, status), operation_log(user_id, created_at)
- 非破坏式版本管理（DocumentVersion 独立表）
- 编辑锁定（DocumentEditLock 一对一层级）

### 3. 核心基础设施

| 文件 | 功能 |
|---|---|
| `core/security.py` | JWT 签发/校验（python-jose），密码哈希（bcrypt） |
| `core/permissions.py` | 4 种角色码 + 细粒度权限枚举 + 角色-权限映射 |
| `core/exceptions.py` | 自定义异常：NotFound, Forbidden, Unauthorized, Conflict, DocumentLocked, VersionConflict |
| `core/storage.py` | MinIO 客户端封装：上传/下载/预签名URL/删除 |
| `core/pagination.py` | 通用分页参数 + 响应模型 |
| `utils/file_utils.py` | MIME 检测、安全文件名、SHA256、存储路径生成 |
| `utils/text_extraction.py` | docx/xlsx/pdf/txt 文本提取（python-docx/openpyxl/pdfplumber） |

### 4. 业务逻辑层（10 个 Service）

| Service | 核心方法 |
|---|---|
| `auth_service.py` | authenticate, get_current_user_info |
| `user_service.py` | User CRUD + 角色管理 + 部门树 |
| `document_service.py` | 文档 CRUD + 上传 + 分类/标签管理；DocumentVersionService（版本上传/设为正式版/冲突检测）；DocumentLockService（锁定/解锁/过期清理）；CrossReferenceService（跨事项引用） |
| `document_preview_service.py` | 获取预览URL（缓存/直接/触发转换） |
| `archive_service.py` | 压缩包解压提取触发 |
| `matter_service.py` | 事项 CRUD + 编号生成 + 成员管理 + 进度计算；MatterCommentService |
| `workflow_service.py` | 模板 CRUD + 节点实例化 + 推进/退回/跳过；WorkflowValidationService（必需文档校验） |
| `task_service.py` | 任务 CRUD |
| `notification_service.py` | 通知 CRUD + 已读/未读管理 |
| `search_service.py` | PostgreSQL 全文搜索 |
| `dashboard_service.py` | 总览统计 + 重点项目 + 风险预警 + 进度图表 + 类型分布 |
| `audit_service.py` | 操作日志写入 + 查询 |

### 5. API 路由层（12 个路由模块，~50 个端点）

| 路由文件 | 端点 |
|---|---|
| `auth.py` | POST /login, POST /logout, GET /me |
| `users.py` | GET/POST /users, GET/PUT/DELETE /users/{id}, PUT password, Roles CRUD, Departments CRUD + tree |
| `documents.py` | GET/POST/DELETE documents, POST upload (chunk支持), GET download/preview/versions, POST versions, PUT official, lock/unlock, references, categories, tags |
| `matters.py` | GET/POST matters, GET/PUT/DELETE /{id}, status, members, comments, documents |
| `workflow_templates.py` | GET/POST templates, GET/PUT/DELETE /{id} |
| `workflow_nodes.py` | GET nodes, PUT advance/rollback/skip, GET validate |
| `tasks.py` | GET/POST tasks, GET/PUT/DELETE /{id} |
| `notifications.py` | GET notifications, unread-count, PUT read/read-all |
| `search.py` | GET search (全文检索) |
| `dashboard.py` | GET overview, key-projects, risks, progress-chart, type-distribution |
| `audit.py` | GET audit-logs (管理员/部门领导) |

### 6. Celery 异步任务（4 个任务模块）

| 任务文件 | 任务 |
|---|---|
| `preview_tasks.py` | `convert_to_pdf` — LibreOffice headless 转换 Office -> PDF，上传到 MinIO preview/ 目录（最大重试 3 次） |
| `archive_tasks.py` | `extract_archive` — 解压 zip（支持 rar/7z 需要 patool），遍历文件，自动创建 Document + DocumentVersion |
| `search_tasks.py` | `update_search_index` — 提取文本更新搜索索引；`rebuild_search_index` — 全量重建 |
| `notification_tasks.py` | `send_notification` / `send_bulk_notification` — 创建通知记录；`check_due_matters` — 到期/逾期检测（Celery Beat 定时）；`check_stalled_matters` — 7天无进展检测 |

### 7. 前端核心

**状态管理 (Pinia Stores)**:
| Store | 职责 |
|---|---|
| `auth.ts` | Token、用户信息、角色判断、登录/登出 |
| `documents.ts` | 文档列表、版本、分类、标签、锁定状态 |
| `matters.ts` | 事项列表、详情、讨论 |
| `tasks.ts` | 待办列表、状态更新 |
| `notifications.ts` | 通知列表、未读数、已读标记 |
| `dashboard.ts` | 驾驶舱数据全量加载 |

**API 封装** (`api/`):
- Axios 实例（baseURL, JWT 拦截器, 401/403/404/409 错误处理）
- 9 个类型化 API 模块（auth, documents, matters, tasks, workflow, notifications, dashboard, search, audit, users）

**组合函数** (`composables/`):
- `useAuth` — 响应式用户认证状态
- `usePagination` — 分页参数管理
- `useFileUpload` — 文件上传 + 进度跟踪
- `usePermission` — 操作权限判断（编辑/删除/锁定/设为正式版等）

**工具函数** (`utils/`):
- `constants.ts` — 状态/优先级/节点/文件类型的颜色和标签映射
- `format.ts` — 日期/文件大小/百分比格式化
- `download.ts` — 文件下载（URL 和 Blob）

### 8. 前端页面（12 个页面）

| 页面 | 路由 | 核心功能 |
|---|---|---|
| `LoginView` | `/login` | 用户名密码登录表单 |
| `WorkbenchView` | `/` | 个人工作台：待办列表 + 我的事项 + 通知 + 快捷操作 |
| `DocumentCenterView` | `/documents` | 文档中心：分类树 + 标签筛选 + 状态/类型过滤 + 拖拽上传对话框 |
| `DocumentDetailView` | `/documents/:id` | 文档详情：信息描述 + 预览（PDF.js iframe）+ 版本历史时间线 + 锁定/下载/上传新版本 |
| `MatterListView` | `/matters` | 事项列表：筛选 + 创建对话框（含事项类型/负责人/协作人/流程模板/重点工作） |
| `MatterDetailView` | `/matters/:id` | 事项工作台（核心页面）：信息 + 进度 + 流程节点卡片 + 文档列表 + 讨论区 + 成员管理 |
| `WorkflowTemplateListView` | `/workflow/templates` | 流程模板管理：CRUD + 节点配置 + 模板详情时间线 |
| `TaskCenterView` | `/tasks` | 待办中心：状态/优先级筛选 + 开始/完成操作 |
| `LeadershipDashboardView` | `/dashboard` | 领导驾驶舱：4 个指标卡片 + 重点工作看板 + 风险预警列表 + ECharts 进度柱状图 + 类型饼图 |
| `SearchResultsView` | `/search` | 搜索结果：范围切换（全部/文档/事项）+ 高亮显示 |
| `UserManagementView` | `/admin/users` | 用户管理：CRUD + 部门/角色筛选 |
| `RoleManagementView` | `/admin/roles` | 角色管理：CRUD |
| `AuditLogView` | `/audit` | 操作日志：类型/日期范围筛选 |

### 9. 前端组件（8 个可复用组件）

| 组件 | 用途 |
|---|---|
| `layout/AppLayout` | 侧边栏 + 顶部栏 + 主内容区布局 |
| `layout/Sidebar` | 菜单导航（含角色可见性控制、折叠动画） |
| `layout/HeaderBar` | 顶部栏（折叠按钮 + 全局搜索 + 通知铃铛 + 用户下拉菜单） |
| `common/FileTypeIcon` | 文件类型图标（Word/Excel/PDF/图片/压缩包） |
| `common/StatusTag` | 统一状态标签（文档/事项/任务/节点） |
| `common/ConfirmDialog` | 通用确认对话框 |
| `common/UserAvatar` | 用户头像 |
| `search/GlobalSearchBar` | 全局搜索输入框 |
| `notifications/NotificationBell` | 通知铃铛（未读角标 + 弹出面板 + 标记已读） |

## 关键技术实现

- **文档预览流程**：前端请求 → 后端检查 PDF 缓存 → Celery LibreOffice 转换 → MinIO 存储 → PDF.js 渲染
- **编辑锁定**：用户点击锁定 → 记录锁定信息（24小时过期）→ 上传新版本自动解锁 → 冲突检测（中间有新版本时提示）
- **必需文档校验**：JSON 规则格式（category + min_count / tag + min_count）→ 节点完成前动态评估
- **全文搜索**：PostgreSQL GIN 索引 + `to_tsvector` + `ts_headline` 高亮
- **分片上传**：支持 init → chunk → complete 流程，5MB 分片大小
- **软删除**：文档和事项均使用软删除（is_deleted / status 标记）

## 产出文件统计

```
后端文件:  60 个 Python 文件
  - models/      8 个（18 张表）
  - schemas/     10 个（所有请求/响应模型）
  - services/    10 个（业务逻辑）
  - api/v1/      12 个（路由端点）
  - tasks/       4 个（Celery 异步任务）
  - core/        5 个（基础设施）
  - utils/       2 个（工具函数）
  - config/      3 个（配置、依赖注入、主入口）

前端文件:  40 个 TypeScript/Vue 文件
  - views/       12 个页面
  - components/  8 个组件
  - stores/      6 个状态管理
  - api/         9 个 API 模块
  - composables/ 4 个组合函数
  - utils/       3 个工具函数

基础设施:  12 个配置文件
  - docker-compose.yml, Dockerfile × 2
  - alembic.ini, alembic/env.py
  - nginx.conf, vite.config.ts, tsconfig.json × 2
  - package.json, requirements.txt, .env

总计: 138 个文件
```

## 后续待办

- [ ] 数据库首次迁移（`alembic revision --autogenerate && alembic upgrade head`）
- [ ] 种子数据（预置角色、文档分类、示例用户）
- [ ] 单元测试（pytest 覆盖 service 层）
- [ ] API 集成测试（httpx 覆盖路由）
- [ ] WebSocket 实时通知（当前为轮询模式）
- [ ] OnlyOffice 在线编辑集成（Phase 2+ 扩展）
- [ ] 文档版本 Diff 对比（后续扩展）

---

*记录人：Claude Code*
