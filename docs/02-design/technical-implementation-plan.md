# 在线工作文档管理系统 - 技术实现计划

## 背景

为高职院校业务部门建设一个以"业务事项"为中心、以"文档"为核心资产、以"流程节点"为推进机制、以"领导驾驶舱"为管理视角的部门级工作文档协同平台。

当前状态：需求文档已完成，无任何代码，需要从零搭建。

## 技术栈

| 层次 | 选型 | 理由 |
|---|---|---|
| 后端框架 | Python FastAPI | 开发效率高、异步支持好、文档处理生态强 |
| 前端框架 | Vue 3 + TypeScript + Element Plus | 国内生态成熟、企业级组件库 |
| 数据库 | PostgreSQL 15 | 自带全文检索、JSON支持、可靠性高 |
| 文件存储 | MinIO | S3兼容、开源、后期可迁云 |
| 文档预览 | LibreOffice 转 PDF + PDF.js | 开源免费、无需商业许可 |
| 异步任务 | Celery + Redis | 处理文档转换、解压、搜索索引 |
| 认证 | JWT + RBAC | 无状态、角色权限清晰 |

## 核心设计决策

### 1. 文档组织方式：属性化，非文件夹化
- 文档通过"所属事项 + 文档分类 + 标签"三维定位
- 不设用户手动创建文件夹
- 左侧分类树是系统自动聚合的视图，不是物理目录

### 2. 版本管理：非破坏式 + 明确正式版
- 每次上传生成新版本，旧版本永久保留
- 有明确的"设为当前正式版"操作，由事项负责人执行
- 多人上传冲突检测：检测到中间有新版本时提示用户
- 编辑锁定机制：可选的"锁定-编辑-解锁"流程（借鉴 TortoiseSVN）

### 3. 共享模式：事项自动共享为主（80%），手动共享为辅（20%）
- 事项协作人自动拥有事项内所有文档的查看权限
- 跨事项引用：文档可关联到其他事项（只读）
- 指定人员共享：特殊场景（跨部门）使用

### 4. 文件状态可视化（借鉴 TortoiseSVN 图标叠加层)
- 文档列表中用颜色徽标标识状态：草稿/正式版/已签批/已归档/冲突
- 一眼可辨，无需点入详情

## 项目目录结构

### 后端 (FastAPI)

```
backend/
├── app/
│   ├── main.py                    # FastAPI 入口
│   ├── config.py                  # Pydantic Settings
│   ├── dependencies.py            # DI: get_db, get_current_user, check_permission
│   ├── core/
│   │   ├── security.py            # JWT, 密码哈希
│   │   ├── permissions.py         # RBAC 权限装饰器
│   │   ├── exceptions.py          # 自定义异常
│   │   ├── storage.py             # MinIO 客户端封装
│   │   └── pagination.py          # 分页工具
│   ├── models/                    # SQLAlchemy ORM 模型
│   │   ├── base.py                # 基类 + TimestampMixin
│   │   ├── user.py, role.py, department.py
│   │   ├── document.py, document_version.py, document_tag.py, tag.py
│   │   ├── document_edit_lock.py, cross_matter_reference.py
│   │   ├── matter.py, matter_type.py, matter_member.py, matter_comment.py
│   │   ├── workflow_template.py, workflow_template_node.py, workflow_node.py
│   │   ├── task.py, notification.py, operation_log.py
│   ├── schemas/                   # Pydantic 请求/响应模型
│   │   ├── common.py              # PaginatedResponse, ApiResponse
│   │   ├── auth.py, user.py, document.py, matter.py
│   │   ├── workflow.py, task.py, notification.py
│   │   ├── search.py, dashboard.py, audit.py
│   ├── api/v1/                    # 路由层（薄层，调用 service）
│   │   ├── router.py              # 聚合所有子路由
│   │   ├── auth.py, users.py, documents.py, matters.py
│   │   ├── workflow_templates.py, workflow_nodes.py, tasks.py
│   │   ├── notifications.py, search.py, dashboard.py, audit.py
│   ├── services/                  # 业务逻辑层
│   │   ├── auth_service.py, user_service.py
│   │   ├── document_service.py, document_version_service.py
│   │   ├── document_preview_service.py  # 文档转换编排
│   │   ├── archive_service.py           # 压缩包解压
│   │   ├── matter_service.py, matter_comment_service.py
│   │   ├── workflow_service.py, workflow_validation_service.py
│   │   ├── task_service.py, notification_service.py
│   │   ├── search_service.py, dashboard_service.py, audit_service.py
│   ├── tasks/                     # Celery 异步任务
│   │   ├── celery_app.py
│   │   ├── preview_tasks.py       # Office -> PDF 转换
│   │   ├── archive_tasks.py       # zip/rar/7z 解压
│   │   ├── search_tasks.py        # 全文索引更新
│   │   └── notification_tasks.py  # 邮件/通知发送
│   └── utils/
│       ├── file_utils.py          # MIME检测、安全文件名
│       └── text_extraction.py     # docx/xlsx/pdf 文本提取
├── alembic/                       # 数据库迁移
├── tests/
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

### 前端 (Vue 3)

```
frontend/
├── src/
│   ├── router/index.ts            # 路由定义 + 角色守卫
│   ├── stores/                    # Pinia 状态管理
│   │   ├── auth.ts                # 用户、token、登录/登出
│   │   ├── documents.ts           # 文档列表、上传进度、版本管理
│   │   ├── matters.ts             # 事项列表、当前事项
│   │   ├── workflow.ts            # 模板、节点
│   │   ├── tasks.ts               # 我的任务
│   │   ├── notifications.ts       # 通知（WebSocket连接）
│   │   ├── dashboard.ts           # 领导驾驶舱数据
│   │   └── system.ts              # 管理员：用户/角色/部门
│   ├── api/                       # Axios API 封装
│   │   ├── index.ts               # 实例 + 拦截器
│   │   ├── auth.ts, documents.ts, matters.ts
│   │   ├── workflow.ts, tasks.ts, notifications.ts
│   │   ├── dashboard.ts, search.ts, users.ts, audit.ts
│   ├── views/                     # 页面组件
│   │   ├── auth/LoginView.vue
│   │   ├── home/WorkbenchView.vue           # 个人工作台
│   │   ├── documents/DocumentCenterView.vue  # 文档中心
│   │   ├── documents/DocumentDetailView.vue  # 文档详情+预览+版本
│   │   ├── matters/MatterListView.vue
│   │   ├── matters/MatterDetailView.vue      # 事项工作台（核心页面）
│   │   ├── workflow/WorkflowTemplateListView.vue
│   │   ├── tasks/TaskCenterView.vue
│   │   ├── dashboard/LeadershipDashboardView.vue
│   │   ├── search/SearchResultsView.vue
│   │   ├── admin/UserManagementView.vue
│   │   ├── admin/RoleManagementView.vue
│   │   ├── audit/AuditLogView.vue
│   ├── components/                # 可复用组件
│   │   ├── layout/ (AppLayout, Sidebar, HeaderBar)
│   │   ├── documents/ (DocumentTable, DocumentUploader,
│   │   │              DocumentPreviewModal, VersionHistoryPanel,
│   │   │              EditLockIndicator, ArchiveExplorer)
│   │   ├── matters/ (MatterCard, MatterForm, MatterStatusBadge,
│   │   │             MatterProgressBar, MatterMemberPicker)
│   │   ├── workflow/ (WorkflowTimeline, WorkflowNodeCard,
│   │   │               WorkflowTemplateEditor, RequiredDocumentCheck)
│   │   ├── dashboard/ (StatCard, KeyProjectTable, RiskAlertList, ProgressChart)
│   │   ├── search/GlobalSearchBar.vue
│   │   ├── notifications/ (NotificationBell, NotificationList)
│   │   └── common/ (FileTypeIcon, StatusTag, ConfirmDialog, UserAvatar)
│   ├── composables/               # 组合函数
│   │   ├── useAuth.ts, usePagination.ts, useFileUpload.ts
│   │   ├── useWebSocket.ts, usePermission.ts
│   └── utils/ (format.ts, constants.ts, validators.ts, download.ts)
├── vite.config.ts
└── package.json
```

## 核心数据库表设计

在需求文档10张表基础上扩展为 18 张表：

| 表名 | 用途 | 关键字段 |
|---|---|---|
| **department** | 部门/科室 | id, name, code, parent_id |
| **user** | 用户 | username, password_hash, department_id, role, status |
| **role** | 角色 | role_name, role_code (general_staff/matter_owner/dept_leader/admin) |
| **user_role** | 用户-角色关联 | user_id, role_id |
| **matter_type** | 事项类型 | name, code (枚举值) |
| **document_category** | 文档分类 | name, code (通知文件/方案材料/报审材料等) |
| **tag** | 标签 | name, color |
| **document** | 文档 | file_name, file_type, storage_path, owner_id, matter_id, category_id, status, current_version_id, permission_scope |
| **document_version** | 文档版本 | document_id, version_no, file_path, upload_user_id, change_note, is_official |
| **document_tag** | 文档-标签关联 | document_id, tag_id |
| **document_edit_lock** | 编辑锁定 | document_id, locked_by, locked_at, expires_at |
| **cross_matter_reference** | 跨事项文档引用 | document_id, matter_id, is_readonly |
| **matter** | 业务事项 | matter_no, title, type_id, owner_id, status, is_key_project, progress, current_node_id, due_date |
| **matter_member** | 事项成员 | matter_id, user_id, role_in_matter (owner/collaborator) |
| **matter_comment** | 事项讨论 | matter_id, user_id, content |
| **workflow_template** | 流程模板 | name, matter_type_id, is_active |
| **workflow_template_node** | 模板节点 | template_id, node_name, node_order, owner_role, required_documents_rule |
| **workflow_node** | 事项实例节点 | matter_id, node_name, node_order, owner_id, status, planned_finish_time, actual_finish_time |
| **task** | 任务/待办 | matter_id, node_id, title, assigner_id, assignee_id, status, priority, due_time |
| **notification** | 通知 | user_id, type, title, content, is_read, related_matter_id |
| **operation_log** | 操作日志 | user_id, operation_type, target_type, target_id, detail, ip_address |

### 关键索引

```sql
-- 全文检索（PostgreSQL GIN索引）
CREATE INDEX idx_document_search ON document
  USING GIN(to_tsvector('simple', coalesce(original_name,'') || ' ' || coalesce(description,'')));

-- 事项进度查询（驾驶舱使用）
CREATE INDEX idx_matter_status ON matter(status);
CREATE INDEX idx_matter_due ON matter(due_date, status);

-- 操作日志查询
CREATE INDEX idx_oplog_user_time ON operation_log(user_id, created_at DESC);
```

## API 路由设计

所有路由前缀 `/api/v1`

### 认证
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/auth/login` | 登录，返回 JWT |
| POST | `/auth/logout` | 登出 |
| GET | `/auth/me` | 获取当前用户信息 |

### 文档管理
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/documents` | 文档列表（分页、筛选、排序） |
| POST | `/documents/upload` | 上传文件（分片上传） |
| GET | `/documents/{id}` | 文档详情 |
| PUT | `/documents/{id}` | 更新文档信息 |
| DELETE | `/documents/{id}` | 删除文档（软删除） |
| GET | `/documents/{id}/download` | 下载文件（权限校验） |
| GET | `/documents/{id}/preview` | 获取预览URL |
| GET | `/documents/{id}/versions` | 获取所有版本 |
| POST | `/documents/{id}/versions` | 上传新版本 |
| PUT | `/documents/{id}/versions/{vid}/official` | 设为正式版 |
| POST | `/documents/{id}/lock` | 锁定文档编辑 |
| DELETE | `/documents/{id}/lock` | 解锁 |
| POST | `/documents/{id}/reference` | 关联到其他事项 |

### 业务事项
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/matters` | 事项列表 |
| POST | `/matters` | 创建事项 |
| GET | `/matters/{id}` | 事项详情（含文档、节点、成员） |
| PUT | `/matters/{id}` | 更新事项 |
| PUT | `/matters/{id}/status` | 更新事项状态 |
| POST | `/matters/{id}/members` | 添加协作人 |
| DELETE | `/matters/{id}/members/{uid}` | 移除成员 |
| GET | `/matters/{id}/comments` | 获取讨论 |
| POST | `/matters/{id}/comments` | 发表讨论 |

### 流程管理
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/workflow/templates` | 流程模板列表 |
| POST | `/workflow/templates` | 创建模板 |
| GET | `/matters/{id}/nodes` | 事项流程节点 |
| PUT | `/matters/{id}/nodes/{nid}/advance` | 推进节点 |
| PUT | `/matters/{id}/nodes/{nid}/rollback` | 退回节点 |
| PUT | `/matters/{id}/nodes/{nid}/skip` | 跳过节点 |
| GET | `/matters/{id}/nodes/{nid}/validate` | 校验必需文档 |

### 其他
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/tasks` | 我的待办列表 |
| GET | `/search` | 全文搜索 |
| GET | `/dashboard/overview` | 驾驶舱总览 |
| GET | `/dashboard/key-projects` | 重点工作看板 |
| GET | `/dashboard/risks` | 风险预警列表 |
| GET | `/notifications` | 通知列表 |
| GET | `/audit-logs` | 操作日志 |

## 架构层次图

```
Vue 3 前端 (Element Plus)
    │  HTTP/REST + JWT
    ▼
Nginx (静态资源 + API反向代理)
    │
    ▼
FastAPI  (路由 → 依赖注入 → Service → ORM)
    │          │              │
    │          ├── PostgreSQL (数据)
    │          ├── MinIO     (文件)
    │          ├── Redis     (缓存 + 消息队列)
    │          └── Celery    (异步任务)
    │               │
    │               └── LibreOffice (文档转PDF)
    │
    └── WebSocket (实时通知)
```

## 分阶段实施计划

### Phase 1: 文档集中管理 + 在线预览（核心MVP）

**后端任务**：
1. 项目脚手架：FastAPI + SQLAlchemy + Alembic + Celery配置
2. 用户认证模块：登录/登出、JWT签发与校验
3. 文档模型 + 上传/下载 API + MinIO 集成
4. 文档分类、标签 CRUD API
5. 文档预览：LibreOffice 服务端转换 + PDF.js 前端渲染
6. 操作日志中间件 + 查询API
7. 基础 RBAC 权限拦截

**前端任务**：
1. 项目脚手架：Vite + Vue 3 + Element Plus + Pinia + Vue Router
2. 登录页面 + AppLayout（侧边栏 + 顶部栏）
3. 个人工作台（仪表盘首页）
4. 文档中心页面（分类树 + 文件列表 + 筛选）
5. 文档上传组件（拖拽、多文件、进度条）
6. 文档预览弹窗（PDF.js集成）
7. 文档详情面板 + 基础版本列表

**验收标准**：用户可登录、上传 docx/xlsx/pdf/txt/md/jpg/png、在线预览、下载、按分类查找

### Phase 2: 业务事项管理 + 协同

**后端任务**：
1. 事项 CRUD + 状态机
2. 事项成员管理 API
3. 事项文档关联（上传时绑定事项）
4. 事项讨论 API
5. 版本管理 API（多版本、正式版标记、冲突检测）
6. 编辑锁定 API
7. 跨事项引用 API

**前端任务**：
1. 事项列表页 + 创建/编辑对话框
2. 事项工作台页面（核心页面：信息 + 进度 + 文档 + 节点 + 讨论 + 日志）
3. 版本历史面板（时间线展示、设为正式版、版本回看）
4. 编辑锁定指示器
5. 事项成员选择器
6. 文档上传时选择事项

**验收标准**：可创建事项、指派责任人/协作人、事项内文档自动共享、版本管理正确

### Phase 3: 流程管理 + 防漏提醒

**后端任务**：
1. 流程模板 CRUD
2. 事项流程节点实例化
3. 节点操作 API（推进/退回/跳过）
4. 必需文档校验引擎
5. Celery Beat 定时任务：到期/逾期/无进展检测
6. 通知生成与推送（站内通知 + WebSocket）

**前端任务**：
1. 流程模板编辑器（拖拽节点排序）
2. 事项工作台内嵌流程时间线
3. 节点操作按钮 + 必需文档校验提示
4. 通知铃铛 + 通知列表
5. 待办中心页面

**验收标准**：流程模板可配置、节点可推进、缺少文档时拦截、到期/逾期可告警

### Phase 4: 领导驾驶舱

**后端任务**：
1. 驾驶舱聚合统计 API（聚合查询优化）
2. 关键指标计算：进行中/逾期/风险/完成率
3. 按维度统计 API（业务类型/责任人/月份）

**前端任务**：
1. 驾驶舱页面（指标卡片 + 重点工作表 + 风险列表）
2. ECharts 统计图表（饼图、柱状图、趋势图）
3. 风险预警列表（颜色标识严重程度）

**验收标准**：领导可查看全貌指标、重点事项进度、风险预警、待处理事项

## 关键技术方案

### 文档预览流程
```
用户点击预览
  → 前端请求 /documents/{id}/preview
  → 后端检查是否已有 PDF 缓存
    ├── 有缓存 → 返回 PDF URL
    └── 无缓存 → 下发 Celery 转换任务
         → LibreOffice 命令行: soffice --headless --convert-to pdf
         → 存入 MinIO preview/ 目录
         → 返回 PDF URL
  → 前端 PDF.js 渲染
```

### 编辑锁定流程（借鉴 TortoiseSVN Lock）
```
1. 用户A 点击"编辑" → POST /documents/{id}/lock
2. 系统记录锁定，返回锁定成功
3. 用户A 本地编辑文件
4. 用户A 上传新版本 → 系统校验锁持有人 → 创建新版本 → 自动解锁
5. 如果用户B 尝试锁定 → 返回"已被xxx锁定"
6. 超时自动解锁（例如24小时）
7. 用户A 可手动解锁（放弃编辑）
```

### 必需文档校验规则格式
```json
{
  "rules": [
    {
      "category": "报审稿",
      "min_count": 1
    },
    {
      "tag": "签批",
      "min_count": 1
    }
  ]
}
```
存储在 `workflow_template_node.required_documents_rule`，节点完成前动态评估。

## 验证方式

1. **单元测试**：pytest 覆盖所有 service 层方法
2. **API 测试**：httpx + pytest 覆盖所有路由
3. **前端测试**：Vitest 覆盖 Pinia stores 和 composables
4. **端到端**：手动按各阶段验收标准逐项测试
5. **性能测试**：上传 100MB 文件验证分片上传；1000 条文档列表分页加载

## 文档编辑工作流（详细设计）

### MVP 阶段：下载-编辑-回传 + 锁定

```
用户操作完整流程：

1. 预览确认
   → 在线预览文档，确认是需要编辑的文件

2. 点击「编辑」按钮
   → 弹出选择对话框：
     [锁定并下载] ← 推荐，防止冲突
     [仅下载]     ← 不锁定，自由下载
     [取消]

3. 选择「锁定并下载」
   → 文件下载到本地
   → 系统显示：🔒 张三正在编辑中（所有人可见）
   → 事项内其他人在文档列表中看到锁定标识

4. 本地使用 Office 软件修改

5. 回到系统，文档详情页顶部黄色提示条：
   "你正在编辑此文档。编辑完成后请上传新版本。"
   [上传新版本] [放弃编辑（解锁）]

6. 点击「上传新版本」
   → 系统已自动关联当前文档
   → 必须填写变更说明
   → 可选勾选"设为正式版"

7. 确认上传
   → 生成新版本号（v1→v2→v3...）
   → 自动解锁
   → 事项成员收到通知
```

### 锁定细节
- 超时自动解锁（24小时）
- 非锁定人尝试编辑时提示"正在被xxx编辑，已编辑x小时"
- 支持"提醒对方尽快完成"按钮
- 管理员可强制解锁

### 冲突检测
- 上传时检测是否有中间版本
- 如有 → 提示"自你下载后已有新版本vN，确认覆盖？"

### 后续扩展
- Phase 2+ 集成 OnlyOffice 实现在线编辑
- 支持版本差异对比

## 后续扩展预留

- 文档版本 Diff 对比（TortoiseSVN 风格）
- 电子签章集成接口
- 移动端小程序
- AI 文档摘要/自动分类/风险提醒
- 统一身份认证对接（LDAP/OAuth）
