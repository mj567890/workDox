# 任务管理系统设计文档

**日期**：2026-04-30
**状态**：设计完成，待实施

---

## 一、设计目标

构建一个**可自定义的文档任务引擎**——用户通过模板定义流程（阶段+文档槽位），实例化后按阶段推进、按槽位上传文档。采购项目管理是其中一个预设模板。

### 核心原则

- **定义层 vs 实例层完全解耦**：模板定义"应该有什么"，实例记录"实际有什么"
- **槽位（Slot）是关键抽象**：阶段内有多少文档位，填没填，什么成熟度，一目了然
- **纯文档管理，不掺审批流程**
- **复用现有文档系统**：槽位引用已有 Document 表，不走重复存储

---

## 二、数据模型

### 定义层（用户设计）

```
TaskTemplate（任务模板）
  ├── id, name, description, category
  ├── is_system: bool              # 系统预置 or 用户自建
  └── stages → StageTemplate[]

StageTemplate（阶段模板）
  ├── id, template_id, name, order, description
  ├── deadline_offset_days: int | None   # 相对上一阶段的建议截止天数
  └── slots → SlotTemplate[]

SlotTemplate（文档槽位模板）
  ├── id, stage_template_id, name, description
  ├── is_required: bool            # 必填 / 可选
  ├── file_type_hints: str[]       # 建议文件类型 ['docx','pdf','zip']
  ├── auto_tags: str[]             # 上传时自动打标签
  └── sort_order: int
```

### 实例层（运行时）

```
Task（任务实例）
  ├── id, template_id → TaskTemplate
  ├── matter_id → Matter
  ├── title, status (pending|active|completed|cancelled)
  ├── current_stage_order: int
  └── stages → Stage[]

Stage（阶段实例）
  ├── id, task_id, stage_template_id
  ├── order, name
  ├── status: locked | in_progress | completed
  ├── notes: str | None
  │        └── locked    = 前一阶段未完成
  │        └── in_progress = 当前活跃
  │        └── completed = 必填全部 filled or waived
  └── slots → Slot[]

Slot（文档槽位实例）
  ├── id, stage_id, slot_template_id
  ├── name, description, is_required
  ├── status: pending | filled | waived
  ├── waive_reason: str | None     # 豁免时填写理由
  ├── maturity: str | None         # 文档成熟度
  │        └── draft     = 起草
  │        └── revision  = 修改（系统自动计第 n 版）
  │        └── final     = 定稿/完成 ✅
  │        └── custom    = 自定义（搭配 maturity_note）
  ├── maturity_note: str | None    # 成熟度的文字说明
  ├── document_id → Document       # 当前版本关联的文档
  └── versions → SlotVersion[]     # 版本历史

SlotVersion（槽位版本记录）
  ├── id, slot_id
  ├── document_id → Document       # 每次上传/替换的文档
  ├── maturity: str                # 当时的成熟度
  ├── maturity_note: str | None
  ├── created_by, created_at
  └── （保留完整替换链）
```

---

## 三、状态机与规则

### 3.1 槽位状态流转

```
      上传文档（选成熟度）     删除/替换文档
pending ─────────────────→ filled ────────────→ pending
   │                         │
   │  标记豁免 + 理由          │  替换文档
   └────────────────────→ waived
```

### 3.2 阶段解锁规则

```
阶段 N 解锁条件：
  阶段 N-1 的所有 is_required=True 槽位
  必须为 filled 或 waived

即：必填的全搞定（已上传或已豁免）→ 下一阶段自动解锁。
```

### 3.3 文档成熟度

| maturity | 含义 | 看板颜色 |
|----------|------|----------|
| `draft` | 起草 | 🔴 红灯 |
| `revision` | 修改第 n 版（自动计数） | 🔴 红灯 |
| `final` | 定稿/完成 | 🟢 绿灯 |
| `custom` | 自定义（如"已签张三李四，待王五签"） | 🔴 红灯 |

成熟度选 `revision` 时，系统自动统计该槽位历史上 revision + final 次数作为版本号。`final` 不是终态，发现错误可以替换重传，成熟度回退到 `revision`。

### 3.4 进度计算

```
任务整体进度 = (所有必填槽位中 status=filled 的个数 / 总必填槽位数) × 100%

阶段进度     = (该阶段必填槽位中 status=filled 的个数 / 该阶段总必填槽位数) × 100%
```

---

## 四、看板设计

### 4.1 任务列表（聚合视图）

```
┌─ 任务列表 ───────────────────────────────────────────────┐
│  任务名称              事项      当前阶段    进度     状态  │
│  ────────────────────  ────────  ─────────  ────────  ─── │
│  2026设备采购(公开招标)  设备更新   招标实施   ████░ 67%  🔄 │
│  实验室耗材(询价)       实验室建设  验收     █████ 100%  ✅ │
│  校舍维修(竞争性谈判)    基建维修   审计     ██░░░ 33%  🔄 │
│  科研项目结题           科研管理   实施     ███░░ 50%  🔄 │
│  新教师入职             人事管理   验收     ████░ 80%  🔄 │
└──────────────────────────────────────────────────────────┘
```

### 4.2 阶段颜色标识

| 图标 | 状态 | 条件 |
|------|------|------|
| ○ 灰 | locked | 前一阶段未完成 |
| ◉ 蓝 | in_progress | 当前活跃 |
| ✅ 绿 | completed | 必填全填 + 可选全填 |
| ⚠ 黄 | completed | 必填全填但可选有缺 |
| 🔴 红 | in_progress / locked | 有必填槽位空着 |

### 4.3 槽位看板（单任务视图）

```
┌─ 招标实施阶段 ──────────────────────────────────────┐
│  槽位名称          成熟度     状态      操作          │
│  ────────────────  ─────────  ────────  ─────────── │
│  🟢 意向公开文件    final      ✅ 已填   [查看][替换] │
│  🟢 议题呈报单      final      ✅ 已填   [查看][替换] │
│  🔴 三重一大审批表* custom    ✅ 已填   [查看][替换] │
│     备注: 已签张三李四，待王五签                     │
│  🔴 采购中心清单*   draft      ⚠ 待填   [上传]      │
│  🔴 评分办法*      ─          ⚠ 待填   [上传]      │
│  🔴 合同*          revision   ✅ 已填   [查看][替换] │
│     版本: v1→v2→v3                                   │
│  ⚪ 投标文件(zip)   final      ✅ 已填   [下载]      │
│  🚫 公示文件        waived    豁免     [撤销豁免]    │
│     理由: 协议供货无需公示                             │
│  🟢 中标通知书      final      ✅ 已填   [查看][替换] │
│  ⚪ 补充协议         ─          ○ 待填   [上传]      │
└─────────────────────────────────────────────────────┘
```

### 4.4 文件预览策略

| 文件类型 | 行为 | 按钮 |
|----------|------|------|
| docx / xlsx / pptx 等 Office | HTML 预览 | [查看] [替换] [下载] |
| pdf / md / txt / csv 等 | 文本/markdown 预览 | [查看] [替换] [下载] |
| zip / rar / 7z / tar.gz 等 | 不支持预览 | [下载] [替换] |

压缩包类文件（zip/rar/7z/tar/gz/bz2/xz）只提供下载，不预览。与现有预览系统完全兼容。

---

## 五、API 设计

### 5.1 模板相关

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/task-templates` | 模板列表 |
| POST | `/task-templates` | 创建模板 |
| GET | `/task-templates/:id` | 模板详情（含阶段+槽位） |
| PUT | `/task-templates/:id` | 更新模板基本信息 |
| DELETE | `/task-templates/:id` | 删除模板 |
| POST | `/task-templates/:id/stages` | 添加阶段 |
| PUT | `/task-templates/:id/stages/:sid` | 更新阶段 |
| DELETE | `/task-templates/:id/stages/:sid` | 删除阶段 |
| PUT | `/task-templates/:id/stages/reorder` | 阶段排序 |
| POST | `/task-templates/:id/stages/:sid/slots` | 添加槽位 |
| PUT | `/task-templates/:id/stages/:sid/slots/:slid` | 更新槽位 |
| DELETE | `/task-templates/:id/stages/:sid/slots/:slid` | 删除槽位 |
| PUT | `/task-templates/:id/stages/:sid/slots/reorder` | 槽位排序 |
| POST | `/task-templates/:id/clone` | 复制模板 |

### 5.2 任务实例

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/tasks` | 任务列表（聚合视图，含进度） |
| POST | `/tasks` | 从模板创建任务 |
| GET | `/tasks/:id` | 任务详情 |
| PUT | `/tasks/:id` | 更新任务基本信息 |
| DELETE | `/tasks/:id` | 删除任务 |
| PUT | `/tasks/:id/advance` | 推进到下一阶段 |
| GET | `/tasks/:id/board` | 任务看板数据 |

### 5.3 槽位操作

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/tasks/:id/stages/:sid/slots/:slid/upload` | 上传文档到槽位 |
| PUT | `/tasks/:id/stages/:sid/slots/:slid/replace` | 替换文档（记录版本） |
| DELETE | `/tasks/:id/stages/:sid/slots/:slid/document` | 移除文档（回退到 pending） |
| PUT | `/tasks/:id/stages/:sid/slots/:slid/maturity` | 更新成熟度 |
| PUT | `/tasks/:id/stages/:sid/slots/:slid/waive` | 豁免槽位 |
| PUT | `/tasks/:id/stages/:sid/slots/:slid/unwaive` | 撤销豁免 |
| GET | `/tasks/:id/stages/:sid/slots/:slid/versions` | 获取槽位版本历史 |

---

## 六、预置模板

### 采购类（6 个）

| 模板 | 阶段数 | 必填槽位 | 说明 |
|------|--------|----------|------|
| 公开招标 | 6 | 18 | 预算→审计→招标→实施→验收→请款 |
| 邀请招标 | 6 | 16 | 同上，略减 |
| 竞争性谈判 | 5 | 14 | 无公开招标阶段 |
| 询价 | 4 | 10 | 预算→询价→实施→验收（无审计/招标） |
| 单一来源 | 4 | 8 | 简化流程 |
| 协议供货 | 4 | 8 | 简化流程 |

### 通用类（3 个）

| 模板 | 阶段数 | 说明 |
|------|--------|------|
| 科研项目 | 4 | 立项→研究→结题→归档 |
| 人事入职 | 4 | 准备→入职→试用→转正 |
| 自定义空白 | 0 | 用户从零编排 |

---

## 七、实施计划

| 阶段 | 内容 | 产出 |
|------|------|------|
| **P1** | 6 张新表 + 模板 CRUD API + 预置模板数据 | Model / Migration / API |
| **P2** | 任务看板前后端 — 从模板创建 → 阶段槽位展示 → 上传/替换/豁免 | 完整可用看板 |
| **P3** | 模板编辑器 — 可视化编排阶段和槽位（拖拽增删改排序） | 用户可自定义 |
| **P4** | 看板聚合视图、阶段锁定自动推进、一键打包 PDF、进度预警 | 完善体验 |

---

## 八、文件变更清单（预估，P1）

### 新建文件

| 文件 | 说明 |
|------|------|
| `backend/app/models/task.py` | Task, Stage, Slot, SlotVersion + 对应的 Template 模型 |
| `backend/alembic/versions/add_task_tables.py` | DDL 迁移 |
| `backend/app/api/v1/task_templates.py` | 模板 CRUD API |
| `backend/app/api/v1/tasks.py` | 任务实例 API |
| `backend/app/services/task_service.py` | 任务业务逻辑 |
| `frontend/src/api/tasks.ts` | 任务 API 封装 |
| `frontend/src/stores/tasks.ts` | 任务 Pinia Store |
| `frontend/src/views/tasks/TaskListView.vue` | 任务列表 |
| `frontend/src/views/tasks/TaskBoardView.vue` | 任务看板 |
| `frontend/src/views/tasks/TemplateEditView.vue` | 模板编辑器 |

### 修改文件

| 文件 | 变更 |
|------|------|
| `backend/app/api/v1/router.py` | 注册 task 路由 |
| `frontend/src/router/index.ts` | +/tasks 路由 |
| `frontend/src/components/layout/Sidebar.vue` | +任务管理菜单 |

---

## 九、验证方法

```bash
# 创建模板
curl -X POST http://10.10.50.205:8000/api/v1/task-templates \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"测试模板","category":"测试","stages":[{"name":"阶段1","order":1,"slots":[{"name":"必填文件","is_required":true}]}]}'

# 从模板创建任务
curl -X POST http://10.10.50.205:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"template_id":1,"title":"测试任务","matter_id":null}'

# 查看看板
curl http://10.10.50.205:8000/api/v1/tasks/1/board \
  -H "Authorization: Bearer $TOKEN"
```

---

*设计者：用户 + Claude Code*
*日期：2026-04-30*
