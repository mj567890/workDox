# 开发日志 #003 — 参考数据管理 + 服务器部署与同步

**日期**：2026-04-29
**阶段**：功能扩展 + 开发环境搭建
**产出**：3 个管理页面 + 3 组 CRUD API + Git 同步体系 + 远程部署

## 完成内容

### 1. 参考数据管理（全栈 CRUD）

新增三组参考数据管理，覆盖前后端：

**文档分类管理** (`document_category`):
- 后端：`GET/POST/PUT/DELETE /api/v1/users/document-categories`，含 Redis 缓存（TTL 600s）
- 前端：`DocumentCategoryManagementView.vue` — 表格列表 + 创建/编辑弹窗 + 删除确认
- 系统分类（is_system=true）不可删除，共 6 个预置分类：通知文件、方案材料、报审材料、签批文件、会议纪要、其他材料

**标签管理** (`tag`):
- 后端：`GET/POST/PUT/DELETE /api/v1/users/tags`
- 前端：`TagManagementView.vue` — 支持颜色选择器

**事项类型管理** (`matter_type`):
- 后端：`GET/POST/PUT/DELETE /api/v1/users/matter-types`
- 前端：`MatterTypeManagementView.vue`

**权限控制**:
- 新增 `ADMIN_REFDATA_MANAGE` 权限码
- 所有写操作需该权限，读操作需登录

**后端改动文件**:
| 文件 | 改动 |
|------|------|
| `backend/app/api/v1/users.py` | +265 行：3 组 CRUD 端点 + Pydantic Schema + 缓存 |
| `backend/app/services/user_service.py` | +288 行：DocumentCategoryService, TagService, MatterTypeService |
| `backend/app/core/permissions.py` | +1 行：ADMIN_REFDATA_MANAGE 权限 |

**前端改动文件**:
| 文件 | 改动 |
|------|------|
| `frontend/src/api/users.ts` | +40 行：3 组 API 方法 + TypeScript 类型 |
| `frontend/src/router/index.ts` | +3 条路由（admin 角色守卫） |
| `frontend/src/components/layout/Sidebar.vue` | +3 个菜单项（系统管理子菜单） |
| `frontend/src/views/admin/RoleManagementView.vue` | 角色管理更新 |
| `frontend/src/views/admin/DocumentCategoryManagementView.vue` | **新建**（142 行） |
| `frontend/src/views/admin/MatterTypeManagementView.vue` | **新建**（130 行） |
| `frontend/src/views/admin/TagManagementView.vue` | **新建**（129 行） |

### 2. 远程开发环境搭建

**服务器信息**:
- IP：10.10.50.205
- 系统：Ubuntu 24.04.3 LTS
- 项目路径：`/home/jhdns/odms`

**部署架构**:
- 本地（`D:\odms`）仅保存和编辑源码，不运行 Docker
- 远程服务器运行全部 Docker 容器（PostgreSQL、Redis、MinIO、FastAPI、Nginx、Celery）

**Git 同步体系**:
- 服务器 Git 仓库已初始化，`receive.denyCurrentBranch = updateInstead`
- 本地添加 `server` 远程：`jhdns@10.10.50.205:~/odms`
- 推送命令：`git push server master`
- 拉取命令：`git pull server master`

**部署注意事项**:
- 后端代码（volume-mounted）：scp 或 push 后 `docker restart odms-backend` 即可
- 前端代码：需 `docker-compose build frontend` + 重建容器
- docker-compose v1.29.2 与 Docker 29.1.3 存在兼容问题，`up` 命令不可用，需手动 `docker run` 创建容器

### 3. 数据播种

后端已播种 6 个预置文档分类（种子数据），验证通过。

## 当前系统状态

| 层级 | 完成率 | 说明 |
|------|--------|------|
| Tier 1 立刻见效 | 8/8 ✅ | 全部完成 |
| Tier 2 核心升级 | 8/8 ✅ | 全部完成 |
| Tier 3 远景蓝图 | 5/7 | 智能处理 (3.5) 和 LDAP/OAuth2 (3.3) 未开始 |

**前端页面总数**：20 个（原有 17 + 新增 3 个管理页面）
**后端 API 端点**：~60 个（新增 12 个参考数据管理端点）

## 后续待办

- [ ] AI 文档助手 (RAG)：pgvector + sentence-transformers + LLM
- [ ] LDAP/OAuth2 集成：AD + OAuth2/OIDC + SSO
- [ ] 单元测试覆盖
- [ ] API 集成测试
- [ ] OnlyOffice 在线编辑集成
- [ ] 前端页面性能优化（大 chunk 拆分）

## Git 提交

```
5c3baa7 feat: add reference data management — document categories, tags, matter types
ebdd806 docs: add user journey — admin setup and daily worker flow
86b92be fix: update logo from OD to WD
3e12270 docs: polish README with badges, architecture diagram, and feature highlights
688eb21 Initial commit: WorkDox v1.0
```

---

*记录人：Claude Code*
