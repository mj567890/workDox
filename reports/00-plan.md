# 系统健康检查 — 编排计划

**版本**: v2.0（分析+修复）
**日期**: 2026-05-06
**状态**: Phase 2 执行中

---

## 一、总览

12 个 Agent 对 WorkDox 系统进行全方位健康检查，**发现问题直接修复**（高风险问题报告后等待确认）。

| Phase | 内容 | 产出 |
|-------|------|------|
| **Phase 1** ✓ | 编排计划 | `reports/00-plan.md` |
| **Phase 2** ← 当前 | 12 Agent 并行分析+修复 | `reports/01~12-*.md` |
| **Phase 3** | 汇总 + 未修复风险清单 | `reports/00-summary.md` |
| **Phase 4** | 高风险问题手动确认 | 交互确认 |

---

## 二、12 Agent 定义

### Agent 1 — architecture-auditor（架构审计）
**范围**: 循环依赖、路由注册完整性、死文件、模块结构
**操作**: 发现死文件直接删除，循环依赖标记修复建议

### Agent 2 — backend-quality（后端质量）
**范围**: 异常处理、SQL 注入风险、Session 泄漏、类型安全、日志覆盖
**操作**: 裸 except 加固、日志缺失补充、硬编码常量化

### Agent 3 — frontend-quality（前端质量）
**范围**: 组件过大、响应式误用、路由守卫、Element Plus deprecated API
**操作**: 过大组件标记、响应式问题修复

### Agent 4 — security-scanner（安全扫描）
**范围**: JWT、权限遗漏、硬编码密钥、CORS、文件上传限制、WebSocket 鉴权
**操作**: 低风险直接修（CORS 收紧、预签名过期调整），高风险报告

### Agent 5 — performance-db（性能与数据库）
**范围**: N+1 查询、缺失索引、缓存策略、分页完整性、pgvector 索引
**操作**: N+1 查询修复、缺失索引生成 DDL

### Agent 6 — rag-ai-evaluator（RAG + AI 评估）
**范围**: Agent 循环正确性、工具 schema 一致性、提示词质量、嵌入管线
**操作**: 代码逻辑修复、提示词优化、边界情况加固

### Agent 7 — test-coverage（测试覆盖）
**范围**: 测试存在性、关键路径覆盖、pytest 配置
**操作**: 如果测试框架存在则补充缺失测试，否则创建基础测试

### Agent 8 — devops-migration（DevOps & 迁移）
**范围**: Docker 健康检查、Alembic 迁移链、deploy.sh、环境变量
**操作**: 缺失健康检查补充、迁移断裂修复、配置文档化

### Agent 9 — bug-hunter（Bug 猎人）
**范围**: 竞态条件、空状态处理、网络错误处理、表单验证、日期时区
**操作**: 明确 bug 直接修复，需验证的标记

### Agent 10 — contract-reviewer（契约审查）
**范围**: 前后端 API 对齐、schema 一致性、README 准确性
**操作**: 路径不一致修复、字段名对齐、文档更新

### Agent 11 — dead-code-cleaner（死代码清理）[新增]
**范围**: 未使用导入、未使用变量、未调用函数、空文件、注释掉的代码块
**操作**: 直接清理

### Agent 12 — dependency-config-auditor（依赖与配置审计）[新增]
**范围**: Python/npm 依赖版本冲突、.env 配置完整性、Docker 镜像版本
**操作**: 配置缺失补充、版本冲突标记

---

## 三、修复策略

| 风险等级 | 策略 | 示例 |
|----------|------|------|
| **P3-低** | 直接修复 | 死代码、格式、日志补充、缺失配置 |
| **P2-中** | 修复 + 报告中说明 | N+1 查询、索引优化、异常处理 |
| **P1-高** | 仅报告，等确认 | 安全漏洞、架构变更、数据库迁移 |

---

## 四、执行顺序

```
Phase 2（12 Agent 并行执行）
┌────────────────────────────────────────────────────────────┐
│ A1  A2  A3  A4  A5  A6  A7  A8  A9  A10  A11  A12       │
└────────────────────────────────────────────────────────────┘
                           │
                           ▼
Phase 3（汇总）→ reports/00-summary.md → Phase 4（高风险确认）
```

---

## 五、产出文件

| 文件 | Agent | 内容 |
|------|-------|------|
| `reports/01-architecture.md` | A1 | 架构审计 |
| `reports/02-backend-quality.md` | A2 | 后端质量 |
| `reports/03-frontend-quality.md` | A3 | 前端质量 |
| `reports/04-security.md` | A4 | 安全扫描 |
| `reports/05-performance.md` | A5 | 性能与数据库 |
| `reports/06-rag-ai.md` | A6 | RAG + AI 评估 |
| `reports/07-test-coverage.md` | A7 | 测试覆盖 |
| `reports/08-devops.md` | A8 | DevOps & 迁移 |
| `reports/09-bugs.md` | A9 | Bug 猎人 |
| `reports/10-contracts.md` | A10 | 契约审查 |
| `reports/11-dead-code.md` | A11 | 死代码清理 |
| `reports/12-dependencies.md` | A12 | 依赖与配置 |
| `reports/00-summary.md` | — | 汇总分析 |
