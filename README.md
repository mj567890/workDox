<p align="center">
  <img src="frontend/public/vite.svg" width="80" alt="WorkDox Logo" />
</p>

<h1 align="center">WorkDox</h1>
<p align="center"><strong>让文档真正干活的协同工作平台</strong></p>

<p align="center">
  <a href="#license"><img src="https://img.shields.io/badge/license-MIT-blue.svg" /></a>
  <a href="#tech"><img src="https://img.shields.io/badge/python-3.12-3776AB?logo=python" /></a>
  <a href="#tech"><img src="https://img.shields.io/badge/vue-3.x-4FC08D?logo=vue.js" /></a>
  <a href="#quick-start"><img src="https://img.shields.io/badge/docker-compose-2496ED?logo=docker" /></a>
</p>

---

WorkDox 面向中小团队，将 **文档管理**、**业务事项**、**流程引擎**、**任务看板** 融为一体——让文件不再只是被存放，而是流转、审批、追踪、沉淀，真正参与到团队的日常工作流中。

---

## 亮点

<table>
<tr>
<td width="50%">

### 文档智能管线
上传即自动提取文本内容（docx / xlsx / pdf），基于内容建议分类标签，PostgreSQL 全文搜索毫秒级响应，力导向图展示文档关联网络。

</td>
<td width="50%">

### 事项 & 流程引擎
可视化流程模板编辑，节点 SLA 时限约束，到期自动升级通知。事项-任务-文档三层联动，进度一目了然。

</td>
</tr>
<tr>
<td width="50%">

### 实时通知 & 邮件网关
WebSocket 推送 + Redis Pub/Sub 分发，通知铃铛实时更新。任务分配、节点推进、到期预警自动邮件提醒，支持摘要模式。

</td>
<td width="50%">

### 批次操作 & 数据导出
表格多选 + 浮动操作栏，批量完成任务、标记已读、分配事项。数据一键导出 Excel / PDF，所有列表页面即开即用。

</td>
</tr>
<tr>
<td width="50%">

### 公开数据展板
无需登录即可查看部门整体进度、风险预警、趋势图表——ECharts 多维度可视化，适合大屏展示。

</td>
<td width="50%">

### RBAC 权限体系
用户 → 角色 → 权限三层控制，支持部门树层级，路由级守卫 + API 级校验双层防护。

</td>
</tr>
</table>

---

## 系统架构

```
                                ┌──────────────┐
                                │   Nginx :80  │
                                │  (Frontend)   │
                                └──────┬───────┘
                                       │
                              ┌────────┴────────┐
                              │   FastAPI :8000 │
                              │   (Backend)      │
                              └───────┬─────────┘
                                      │
          ┌───────────────┬───────────┼───────────┬───────────────┐
          │               │           │           │               │
    ┌─────┴─────┐   ┌─────┴─────┐  ┌──┴────┐  ┌──┴───┐   ┌──────┴──────┐
    │ PostgreSQL │   │   Redis   │  │ Celery│  │ MinIO │   │ External    │
    │ + pgvector │   │           │  │Worker │  │ :9000 │   │ SMTP / LLM  │
    └───────────┘   └───────────┘  └───────┘  └──────┘   └─────────────┘
```

---

## 技术栈

| 层级 | 技术 |
|------|------|
| **后端框架** | FastAPI 0.110 + Python 3.12 |
| **ORM & DB** | SQLAlchemy 2.0 异步 + PostgreSQL 15 + pgvector |
| **缓存 & 队列** | Redis 7（缓存 / Celery Broker / Pub/Sub） |
| **异步任务** | Celery 5.3（Worker + Beat 定时调度） |
| **对象存储** | MinIO（S3 兼容） |
| **前端框架** | Vue 3 + TypeScript + Vite 5 |
| **UI 组件** | Element Plus 2.5 + ECharts 5 |
| **实时通信** | WebSocket + Redis Pub/Sub |
| **搜索引擎** | PostgreSQL `tsvector` / `tsquery` + GIN 索引 |
| **文本提取** | python-docx / openpyxl / pdfplumber / pdfminer |
| **部署** | Docker Compose 一键编排，Nginx 静态服务 |

---

## 快速开始

```bash
# 克隆
git clone git@github.com:mj567890/workDox.git && cd workDox

# 启动 （需要 Docker 环境）
docker-compose up -d

# 初始化数据库
docker-compose exec backend alembic upgrade head

# 填充种子数据（可选）
docker-compose exec backend python seed.py
```

启动后访问：

| 服务 | 地址 |
|------|------|
| 前端应用 | http://localhost:3000 |
| 公开数据展板 | http://localhost:3000/dashboard |
| Swagger 文档 | http://localhost:8000/docs |
| MinIO 控制台 | http://localhost:9001 |

**默认管理员**：`admin` / `admin123`

---

## 项目结构

```
workDox/
├── backend/
│   ├── app/
│   │   ├── api/v1/           # 15 个 API 路由模块
│   │   ├── core/             # 缓存、安全、权限、分页、WebSocket
│   │   ├── models/           # 9 个 ORM 模型
│   │   ├── schemas/          # Pydantic 校验
│   │   ├── services/         # 14 个业务服务
│   │   ├── tasks/            # Celery 异步/定时任务
│   │   └── utils/            # 文本提取、邮件、文件、Webhook
│   └── alembic/              # 数据库迁移脚本
├── frontend/
│   ├── src/
│   │   ├── api/              # 11 个 API 请求模块
│   │   ├── components/       # 15 个公共组件
│   │   ├── composables/      # 9 个组合式函数
│   │   ├── stores/           # 6 个 Pinia Store
│   │   ├── views/            # 20+ 页面视图
│   │   └── router/           # 路由 + 角色守卫
│   └── Dockerfile
├── docs/                     # 需求、设计、开发日志
└── docker-compose.yml        # 7 个服务一键编排
```

---

## License

MIT © WorkDox
