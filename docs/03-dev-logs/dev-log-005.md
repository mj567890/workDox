# 开发日志 #005 — 预览升级 HTML + 文档编辑模式 + MD 表格修复

**日期**：2026-04-30
**阶段**：P2 预览体验优化 + 文档管理功能
**产出**：4 个新功能 + 2 项修复

## 一、LibreOffice HTML 预览（替代 PDF）

### 背景
此前预览链路为 PDF 转换 → MinIO → 预签名 URL → 浏览器下载。两个问题：
1. 系统无 PDF 内嵌组件，浏览器强制下载
2. PDF 中文乱码（字体缺失）

后改为文本提取，但纯文本丢失表格、粗体、标题等排版。

### 方案
LibreOffice `--convert-to html` → MinIO → API 返回 HTML → 前端 `<iframe srcdoc>` 展示。

### 变更

| 文件 | 变更 |
|------|------|
| `backend/app/tasks/preview_tasks.py` | `convert_to_pdf` → `convert_to_html`，soffice 输出 HTML |
| `backend/app/models/document.py` | +`preview_html_path` String(500) |
| `backend/alembic/versions/add_preview_html_path.py` | DDL 迁移 |
| `backend/app/api/v1/documents.py` | `get_preview_text` 三层优先级；上传时 dispatch `convert_to_html` |
| `frontend/src/api/documents.ts` | `PreviewText.format` +`'html'`，+`can_generate_html` |
| `frontend/src/views/documents/DocumentDetailView.vue` | `<iframe srcdoc>` HTML 预览展示 |

### 预览优先级（三层回退）

```
get_preview_text(doc_id)
  ├── 1. OFFICE_FORMATS + preview_html_path → MinIO 取 HTML → format: "html"
  ├── 2. extracted_text 有缓存或可提取 → format: "markdown" / "text"
  └── 3. 不支持 → has_content: false
```

### 文件类型策略

| 类型 | 预览方式 | 原因 |
|------|----------|------|
| docx/xlsx/pptx/odt/rtf 等 | LibreOffice → HTML → iframe | 保留表格、排版 |
| md | markdown 渲染 | 文本即源码，无需 HTML 转换 |
| pdf/txt/csv/代码等 | 纯文本提取 | LibreOffice 对 PDF/纯文本无益 |

## 二、旧文档重新生成预览

### 新增端点

`POST /api/v1/documents/{doc_id}/generate-preview` — 触发 Celery 重新生成 HTML 预览

### 前端按钮

预览卡片内，当 `format !== 'html' && can_generate_html === true` 时显示「生成 HTML 预览（保留排版）」按钮。

## 三、文档信息编辑模式

### 问题
文档详情页「文档信息」卡片纯只读，无法修改文件名、分类、标签、描述。

### 实现
- 「文档信息」卡片 header 加「编辑」按钮（有权限时显示）
- 点击进入编辑模式：文件名、分类（下拉）、共享范围、标签（多选）、描述
- 调用已有 `PUT /{doc_id}` 接口保存
- 权限控制：仅上传者或 admin 可编辑

### 编辑表单字段

| 字段 | 组件 | 说明 |
|------|------|------|
| 文件名 | `el-input` | 修改 `original_name` |
| 文档分类 | `el-select` | 从 `docStore.categories` 加载 |
| 共享范围 | `el-select` | matter / global |
| 标签 | `el-select multiple` | 从 `docStore.tags` 加载，可多选筛选 |
| 描述 | `el-input textarea` | 修改 `description` |

## 四、Bug 修复

### 1. Markdown 表格不渲染
**根因**：`renderMarkdown()` 未处理表格语法
**修复**：正则匹配 `|...|...|` 行块，转换为 `<table><thead><tbody>` 结构 (`DocumentDetailView.vue:251`)

### 2. PDF HTML 预览空白
**根因**：LibreOffice 将 PDF 当图片打开，转 HTML 输出为空页面
**修复**：从 `OFFICE_FORMATS` 中移除 `pdf`，PDF 回退到 pdfplumber 文本提取

## 验证命令

```bash
# 获取 token
TOKEN=$(curl -s -X POST http://10.10.50.205:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

# Office 文件预览（HTML 格式）
curl http://10.10.50.205:8000/api/v1/documents/4/preview-text \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys,json; d=json.load(sys.stdin)
print(f'format={d[\"format\"]}, can_gen={d.get(\"can_generate_html\")}')"

# 旧文档重新生成 HTML 预览
curl -X POST http://10.10.50.205:8000/api/v1/documents/4/generate-preview \
  -H "Authorization: Bearer $TOKEN"

# MD 文件预览（markdown 格式）
curl http://10.10.50.205:8000/api/v1/documents/5/preview-text \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys,json; d=json.load(sys.stdin)
print(f'format={d[\"format\"]}, can_gen={d.get(\"can_generate_html\")}')"
```

## 当前系统状态

| 组件 | 状态 |
|------|------|
| 后端容器 (7个) | 全部运行中 |
| LibreOffice | 7.4.7.2，HTML 转换正常 |
| 前端 | 编辑模式 + HTML 预览 + MD 表格渲染 |
| 数据库 | `preview_html_path` 列已添加 |
| GitHub | 已推送 `c799074` |

---

*记录人：Claude Code*
