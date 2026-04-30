# WorkDox (ODMS) - 在线文档管理系统

## 开发模式

**所有代码在服务器上运行，本地仅编辑代码。**

- 服务器: `10.10.50.205` (SSH: jhdns, 已配置免密登录)
- 项目路径: 服务器 `/home/jhdns/odms`, 本地 `D:\workDox\odms`

### 部署架构
- 7 个 Docker 容器: db(postgres+pgvector), redis, minio, backend(FastAPI), celery-worker, celery-beat, frontend(Nginx+Vue3)
- backend/worker/beat 有 volume 挂载 (`./backend:/app`)，代码变更后重启容器生效
- frontend 无 volume 挂载，需要 rebuild 镜像

### 开发流程
1. 本地编辑代码
2. scp 变更文件到服务器对应路径
3. 重启受影响容器

### 服务端口
- 前端: http://10.10.50.205:3000
- 后端 API: http://10.10.50.205:8000
- API 文档: http://10.10.50.205:8000/docs
- MinIO 控制台: http://10.10.50.205:9001

### 默认管理员
- 用户名: admin / 密码: admin123

## 技术栈

### 后端
- Python 3.12, FastAPI 0.110, SQLAlchemy 2.0 (async), Pydantic v2
- PostgreSQL 15 + pgvector, Redis 7, MinIO (S3)
- Celery 5.3 (Redis broker), Alembic 1.13
- JWT 认证 (python-jose + bcrypt), RBAC 权限

### 前端
- Vue 3.4 + TypeScript, Vite 5
- Element Plus 2.6, ECharts 5.5, Pinia 2.1
- pdfjs-dist 4.0, Axios 1.6

### 目录结构
```
backend/app/
  main.py          - FastAPI 入口, CORS, lifespan
  config.py        - Pydantic Settings (37 配置项)
  dependencies.py  - DI: get_db, get_current_user, check_permission
  core/            - security, permissions, cache, storage, ws_manager, pagination
  models/          - 21 张表: user, role, department, document(8表), matter(3表), workflow(3表), task, notification, webhook
  schemas/         - Pydantic 请求/响应模型
  api/v1/          - ~60+ API 端点, 15 个路由模块
  services/        - 14 个业务服务
  tasks/           - Celery 任务: preview, archive, search, notification
  utils/           - 文件工具, 文本提取, 邮件, webhook
frontend/src/
  views/           - 20 个页面视图
  components/      - 9 个公共组件
  stores/          - 6 个 Pinia store
  api/             - 11 个 API 模块
  router/          - 20 条路由 + 导航守卫
  composables/     - 5 个组合函数

docs/
  01-requirements/ - 需求文档
  02-design/       - 设计决策 + 技术实现计划
  03-dev-logs/     - 开发日志 (3次AI编码会话)
```

## 常用命令

### 同步代码到服务器
```bash
# 单个文件
scp local_file jhdns@10.10.50.205:/home/jhdns/odms/path/to/file

# 整个目录
scp -r local_dir/ jhdns@10.10.50.205:/home/jhdns/odms/path/to/dir/

# 批量同步 backend
scp -r backend/app/ jhdns@10.10.50.205:/home/jhdns/odms/backend/app/
```

### 重启服务

**注意**: 服务器使用 docker-compose v1.29.2（独立版），与 Docker 29.x 存在兼容性问题。
- `docker-compose up -d` 重建已有容器时会报 `KeyError: 'ContainerConfig'`
- 部署请统一使用 `deploy.sh` 脚本（已处理兼容性）

```bash
# 【推荐】使用部署脚本（自动处理 stop+rm+up 流程）
ssh jhdns@10.10.50.205 "cd /home/jhdns/odms && bash deploy.sh backend"

# 仅代码变更（.env/docker-compose.yml 未变）可简单重启
ssh jhdns@10.10.50.205 "docker restart odms-backend odms-celery-worker odms-celery-beat"

# 前端变更（需要 rebuild）
ssh jhdns@10.10.50.205 "cd /home/jhdns/odms && bash deploy.sh frontend"

# 完全重新部署
ssh jhdns@10.10.50.205 "cd /home/jhdns/odms && bash deploy.sh all"

# 查看日志
ssh jhdns@10.10.50.205 "docker logs --tail 50 odms-backend"
```

### 数据库迁移
```bash
ssh jhdns@10.10.50.205 "docker exec odms-backend alembic upgrade head"
```
