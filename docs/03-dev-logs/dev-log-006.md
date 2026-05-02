# Dev Log 006 — 系统集成测试与全量修复

> **日期**: 2026-05-02
> **版本**: v1.6.0
> **类型**: 故障修复 + 架构对齐
> **会话**: 第 6 次 AI 编码会话

---

## 背景

系统经过 5 次开发迭代后，Tier 1-3 共 23 项功能已全部实现。但 Matter（事项管理）模块被迁移删除后，前端仍存在大量死链；后端多个 API 路由未注册；task 表被迁移删除后相关代码未适配。本次会话对系统进行全量测试排错，确保所有服务正常运行。

---

## 发现与修复（8 项）

### 1. Backend 无法启动 — `llm_service.py` 版本冲突

**现象**: 容器 `odms-backend` 反复重启，日志显示 `ImportError: cannot import name 'get_llm_service'`

**根因**: 服务器 `llm_service.py` 是旧版（模块级 `chat()` 函数），而 `rag_service.py` 和本地版本使用 `get_llm_service()` 工厂函数。

**修复**: 同步本地 `llm_service.py`（含 `LLMService` 类 + `get_llm_service()` 单例）和 `summarization_service.py` 到服务器。

### 2. `GET /api/v1/tasks` → 404 + 500

**现象**: 前端待办中心页调用 `/tasks` 返回 404，修复路由后返回 500 `relation "task" does not exist`

**根因**:
- `router.py` 未注册 tasks/dashboard 路由
- `task` 表已被 `remove_legacy_matter_workflow` 迁移删除
- 新系统使用 `task_instance` 表（`ProjectTask` 模型），但 `Task` 模型仍指向已删除的表

**修复**:
- `router.py`: 添加 `include_router(tasks.router)` 和 `include_router(dashboard.router)`
- `task.py`: 改为重导出 `ProjectTask as Task`（映射 `task_instance` 表）
- `models/__init__.py`: 移除重复的 `ProjectTask` 导入
- `tasks.py`: 完全重写，适配 `ProjectTask` 的字段（`template_id`, `creator_id`, `current_stage_order`），移除 `matter_id`/`assignee_id`/`priority`/`due_time` 等不存在的列
- 手动清理容器内 `.pyc` 缓存（`docker exec odms-backend find /app -name '*.pyc' -delete`）

### 3. `GET /api/v1/dashboard/*` → 404

**现象**: dashboard 全部 7 个子端点（overview/key-projects/risks/personal-stats 等）返回 404

**根因**: `router.py` 未注册 dashboard 路由；服务器 `dashboard.py` 仅有 28 行 stub（仅含 `personal-stats`）；本地 `dashboard.py` 大量引用已删除的 `Matter`/`MatterMember` 模型

**修复**: 完全重写 `dashboard.py`，对接新版 `DashboardService`（使用 `ProjectTask`/`TaskTemplate`，无 Matter 依赖），映射前端期望的端点：
- `/overview` → `get_overview(db)`
- `/key-projects` → `get_active_tasks(db)`
- `/risks` → `get_risk_alerts(db)`
- `/progress-chart` → `get_stage_funnel(db)` + `get_monthly_trend(db)`
- `/type-distribution` → `get_template_distribution(db)`
- `/personal-stats` → `get_personal_stats(db, user_id)`
- `/advanced` → 组合趋势 + 部门负载 + 分布

### 4. `GET /api/v1/ai/conversations` → 500

**现象**: AI 对话列表接口返回 `Internal Server Error`

**根因**: `list_conversations` 端点访问 `c.messages`（懒加载关系）时触发 SQLAlchemy `MissingGreenlet` 错误——在异步上下文中尝试 IO 操作

**修复**: 查询 `AIConversation` 时添加 `.options(selectinload(AIConversation.messages))` 预加载关联数据

### 5. WorkbenchView 无限加载

**现象**: 工作台页面骨架屏持续显示，`loading.value = false` 永不执行

**根因**: `onMounted` 中 `Promise.all` 包含 `matterStore.fetchMatters()`，该调用访问不存在的 `/api/v1/matters` 端点导致 reject，整个 `Promise.all` 失败

**修复**:
- 移除 `matterStore` 依赖
- 将 `Promise.all` 包装在 try/catch 中，单个 API 失败不影响页面渲染
- "我的事项"区域替换为"最近任务"（使用 `taskStore`）
- "快速操作"中"创建事项"改为"创建任务"（链接 `/task-mgmt`）
- 个人统计卡片适配新 API 字段（`status_distribution` 替代 `priority_distribution`）

### 6. 前端 7 处 Matter 死链

**现象**: 多处 `router.push('/matters/...')` 导航到不存在的路由

**涉及文件**:

| 文件 | 原链接 | 修复 |
|------|--------|------|
| `NotificationBell.vue` | `/matters/${item.related_matter_id}` | 移除点击导航 |
| `useShortcuts.ts` | `/matters` (Ctrl+N) | 改为 `/task-mgmt` |
| `SearchResultsView.vue` | `/matters/${item.id}` | 改为 `/task-mgmt` |
| `TaskCenterView.vue` | `/matters/${row.matter_id}` | 改为 `/task-mgmt` |
| `LeadershipDashboardView.vue` | `/matters/${row.matter_id}`（2处） | 改为 `/task-mgmt` |
| `DocumentCenterView.vue` | `mattersApi.getList(...)` | 添加 `.catch()` |
| `TaskDialog.vue` | `mattersApi.getList(...)` | 添加 `.catch()` |

### 7. Dashboard API 类型不匹配

**现象**: 前端 TypeScript 类型与后端新响应结构不一致

**修复**: 更新 `frontend/src/api/dashboard.ts` 所有接口：
- `DashboardOverview`: `total_matters` → `total_tasks`/`active_tasks`/`completed_tasks`/`pipeline_progress`/`overdue_stages`/`total_slots`/`filled_slots`
- `KeyProjectItem`: `matter_id`/`matter_no` → `task_id`/`template_name`/`current_stage`/`current_stage_order`/`creator_id`
- `RiskAlertItem`: `matter_id`/`matter_no` → `task_id`/`stage_name`
- `PersonalStats`: 新增 `total_tasks`，`priority_distribution` → `status_distribution`
- `AdvancedAnalytics`: `departments`/`priority_breakdown` → `department_workload`/`template_distribution`/`status_distribution`

### 8. 前端旧文件清理

**删除**:
- `frontend/src/views/matters/` 目录（`MatterDetailView.vue`, `MatterListView.vue`）
- `frontend/src/views/workflow/` 目录（`WorkflowTemplateEditView.vue`, `WorkflowTemplateListView.vue`）
- `frontend/src/api/workflow.ts`

**保留**:
- `frontend/src/api/matters.ts` — 仍被 `stores/matters.ts`、`TaskDialog.vue`、`DocumentCenterView.vue` 引用
- `backend/app/services/matter_service.py` — 仍被 `api/v1/matters.py` 引用
- `backend/app/services/workflow_service.py` — 仍被 workflow API 路由引用

---

## 修改文件清单

### 后端（8 文件）

| 文件 | 改动 |
|------|------|
| `backend/app/api/v1/router.py` | +tasks +dashboard 路由注册 |
| `backend/app/api/v1/tasks.py` | 完全重写，适配 `task_instance` 表 |
| `backend/app/api/v1/dashboard.py` | 完全重写，对接新 `DashboardService` |
| `backend/app/api/v1/ai.py` | +`selectinload` 修复 MissingGreenlet |
| `backend/app/models/task.py` | 改为 `ProjectTask` 别名 |
| `backend/app/models/__init__.py` | 移除重复 `ProjectTask` 导入 |
| `backend/app/services/llm_service.py` | 同步本地版本 |
| `backend/app/services/summarization_service.py` | 同步本地版本 |

### 前端（9 文件）

| 文件 | 改动 |
|------|------|
| `frontend/src/views/home/WorkbenchView.vue` | 移除 Matter 依赖，适配新 API |
| `frontend/src/api/dashboard.ts` | 更新全部 TypeScript 接口 |
| `frontend/src/components/notifications/NotificationBell.vue` | 移除 matter 导航 |
| `frontend/src/composables/useShortcuts.ts` | `/matters` → `/task-mgmt` |
| `frontend/src/views/search/SearchResultsView.vue` | `/matters/:id` → `/task-mgmt` |
| `frontend/src/views/tasks/TaskCenterView.vue` | `/matters/:id` → `/task-mgmt` |
| `frontend/src/views/tasks/TaskDialog.vue` | +`.catch()` 防护 |
| `frontend/src/views/documents/DocumentCenterView.vue` | +`.catch()` 防护 |
| `frontend/src/views/dashboard/LeadershipDashboardView.vue` | `/matters/:id` → `/task-mgmt` (2处) |

### 文档（2 文件）

| 文件 | 改动 |
|------|------|
| `docs/03-dev-logs/enhancement-plan.md` | Tier 3: 5/7 → 7/7, 新增 CAS/RAG 文件清单 |
| `docs/03-dev-logs/dev-log-006.md` | 本次会话记录（新建） |

---

## 验证结果

### API 全量测试（12/12 ✅）

```
✅ /api/v1/auth/login          → 200
✅ /api/v1/documents/          → 200
✅ /api/v1/tasks               → 200 (创建/更新/删除/批量完成)
✅ /api/v1/dashboard/overview       → 200
✅ /api/v1/dashboard/personal-stats → 200
✅ /api/v1/dashboard/key-projects   → 200
✅ /api/v1/dashboard/risks          → 200
✅ /api/v1/dashboard/advanced       → 200
✅ /api/v1/notifications/     → 200
✅ /api/v1/users/             → 200
✅ /api/v1/ai/conversations   → 200
✅ /api/v1/task-templates     → 200
✅ /api/v1/task-instances     → 200
```

### 容器状态

```
✅ odms-frontend      Up
✅ odms-backend       Up
✅ odms-celery-worker Up
✅ odms-celery-beat   Up
✅ odms-db            Up (3d)
✅ odms-redis         Up (3d)
✅ odms-minio         Up (3d)
```

### 前端

- 构建: 2483 modules, 0 errors
- 页面: HTTP 200
- 无 Matter 死链残留

---

## 技术债务

| 项目 | 严重度 | 说明 |
|------|--------|------|
| `LeadershipDashboardView` 数据适配 | 中 | 仪表盘视图仍使用旧字段名（`matter_id`/`matter_no`），需要完整 UI 重写以匹配新 API 响应结构 |
| `TaskCenterView` 数据适配 | 中 | 待办中心视图字段名需要更新（`matter_id`/`matter_title`/`priority` 等不再存在） |
| `PublicDashboardView` | 低 | 公开仪表盘调用未注册的 `/public/dashboard/*` 路由 |
| `stores/matters.ts` | 低 | Matter store 仍存在但后端无对应 API，已在调用处添加 `.catch()` |

---

## 经验总结

1. **迁移删除要同步代码** — 数据库迁移删除 `task` 表和 `Matter` 模型后，相关 API 代码和前端视图必须同步更新，否则积压为大量 404/500
2. **路由注册需集中管理** — `router.py` 是 API 入口，新增模块后必须注册，遗漏会导致"文件存在但端点 404"的隐蔽故障
3. **容器内 .pyc 缓存** — Docker volume 挂载时，`.pyc` 文件可能由 root 创建导致无法从宿主机删除，必须通过 `docker exec` 清理
4. **`Promise.all` 失败即全败** — 前端多个独立 API 调用不应放在同一个 `Promise.all` 中，单个失败会导致整个页面卡死
