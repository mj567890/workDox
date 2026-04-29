# WorkDox

> 让文档真正干活的协同工作平台

WorkDox 是一个面向中小团队的文档管理与业务协同平台，将文档、事项、流程、任务融为一体，让文件不只是被存储，而是真正参与到工作中。

## 功能架构

| 模块 | 说明 |
|------|------|
| 文档中心 | 上传/预览/分类/标签，支持全文搜索与智能文本提取 |
| 业务事项 | 事项跟踪、状态流转、进度可视化、SLA 时限管理 |
| 流程引擎 | 可视化模板编辑、节点推进、审批链、到期自动升级 |
| 待办中心 | 个人任务看板、优先级管理、批次操作 |
| 数据展板 | 公开数据大屏，无需登录即可查看整体进度 |
| 系统管理 | 用户/角色/部门管理，RBAC 权限控制 |
| 实时通知 | WebSocket 推送 + 邮件通知网关 |
| 操作审计 | 全操作日志记录与查询 |

## 技术栈

**后端**
- FastAPI (Python 3.12) + SQLAlchemy 2.0 异步
- PostgreSQL 15 + pgvector（全文搜索、向量检索）
- Redis（缓存 / Celery 队列 / Pub/Sub）
- Celery（异步任务、定时任务）
- MinIO（对象存储）

**前端**
- Vue 3 + TypeScript + Vite
- Element Plus + ECharts
- 响应式布局 / PWA 支持

**部署**
- Docker Compose 一键部署
- Nginx 反向代理

## 快速开始

```bash
# 克隆仓库
git clone https://github.com/mj567890/workDox.git
cd workDox

# 启动全部服务
docker-compose up -d

# 运行数据库迁移
docker-compose exec backend alembic upgrade head

# 访问
# 前端:        http://localhost:3000
# API 文档:    http://localhost:8000/docs
# 数据展板:    http://localhost:3000/dashboard
# MinIO 控制台: http://localhost:9001
```

默认管理员账号：`admin` / `admin123`

## 项目结构

```
workDox/
├── backend/
│   ├── app/
│   │   ├── api/v1/       # API 路由
│   │   ├── core/         # 配置、安全、缓存、权限
│   │   ├── models/       # SQLAlchemy 模型
│   │   ├── services/     # 业务服务层
│   │   └── utils/        # 工具函数
│   ├── alembic/          # 数据库迁移
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/          # API 请求层
│   │   ├── components/   # 公共组件
│   │   ├── views/        # 页面视图
│   │   ├── stores/       # Pinia 状态管理
│   │   ├── router/       # 路由配置
│   │   └── composables/  # 组合式函数
│   └── Dockerfile
└── docker-compose.yml
```

## License

MIT
