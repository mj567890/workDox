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

## 一天怎么用

### 管理员：花半小时搭好框架，后续几乎免维护

<details open>
<summary><b>初次配置（一次性）</b></summary>

1. **建部门树** — 系统管理 → 部门管理，按实际组织架构创建层级（如：局领导 → 办公室 / 招生处 / 教务科...）
2. **配角色** — 新建"部门负责人""办事员""兼职档案员"等角色，勾选对应权限
3. **加用户** — 填写姓名、邮箱、选择所属部门、赋予角色，员工即可登录
4. **画流程** — 流程模板页，拖拽节点画出实际业务流程（如"招生文件审批"：起草 → 科长审核 → 处长批准），给关键节点设 SLA 时限

</details>

<details>
<summary><b>日常（偶尔看看）</b></summary>

5. 打开**数据展板**挂在大屏上，领导路过就能看到：当前办了多少事项、哪个快逾期了
6. 有什么文件忘了流转，在**操作日志**里按操作人、时间、动作查到每一步记录
7. 新人入职？加个用户就行，其他不用改

</details>

---

### 普通员工：打开系统就知道今天该做什么

<details open>
<summary><b>上午：处理文件 & 事项</b></summary>

1. 登录后进入**工作台**，上周上传的文档系统自动提取了文字、建议了分类，确认一下就行
2. 收到通知：科长刚把"2026 招生方案"推进到"会签"节点——点击直达该事项详情
3. 在**文档中心**搜索"培训协议"，不用记文件名，输入关键词毫秒级出结果
4. 把一个待办标记完成，系统自动通知下一节点负责人

</details>

<details>
<summary><b>下午：协作 & 跟踪</b></summary>

5. **待办中心**显示自己还剩 3 个任务，按优先级排好，逐个处理
6. 在事项详情里上传相关附件，拖拽到上传区即可，大文件自动分片
7. 下班前看一眼工作台——本周完成了 5 个任务，连续达标 12 天

</details>

---

> 核心体验：**文件不再是死的数据，而是跟着业务流程走**——每个文档属于哪个事项、流转到哪个节点、谁在负责，全程透明可追踪。

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
