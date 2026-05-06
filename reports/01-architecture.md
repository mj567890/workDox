# Architecture Audit Report

**Date:** 2026-05-06
**Scope:** 101 backend Python files, 76 frontend TypeScript/Vue files
**Methodology:** Static analysis of imports, route registrations, model-service alignment, and cross-layer dependencies.

---

## Findings

### P1-High (needs confirmation/action)

#### 1. Five API modules not registered in router -- 2 FIXED

**Fixed:** `search.py` and `public_dashboard.py` were valid, working modules with no registration in `backend/app/api/v1/router.py`. Their API endpoints were completely unreachable.

- `/api/v1/search/?keyword=...` -- full-text document search
- `/api/v1/public/dashboard/overview` (and 6 other routes) -- public analytics dashboard

These have been registered in `router.py`.

**Not fixed (requires decision):** Three legacy modules remain unregistered:

- `matters.py` (15+ routes) -- imports from `app.models.matter` (a stub file with zero classes)
- `workflow_nodes.py` (7 routes) -- imports from `app.models.workflow` (stub)
- `workflow_templates.py` (5 routes) -- imports from `app.models.workflow` (stub)

These modules would fail at import time because the underlying model classes were removed via the `remove_legacy_matter_workflow` migration. They are dead code.

#### 2. Legacy matter/workflow system -- incomplete removal (8 dead files)

The migration `remove_legacy_matter_workflow` dropped tables but left behind:

| File | Status |
|---|---|
| `backend/app/models/matter.py` | Stub: `# stub - legacy matter tables removed` |
| `backend/app/models/workflow.py` | Stub: `# stub - legacy workflow tables removed` |
| `backend/app/models/task.py` | Re-export shim: `from app.models.task_manager import ProjectTask as Task` |
| `backend/app/services/matter_service.py` | Imports from stub models -- would fail at runtime |
| `backend/app/services/workflow_service.py` | Imports from stub models -- would fail at runtime |
| `backend/app/services/task_service.py` | Imports `Matter` from stub + never imported by any file |
| `backend/app/schemas/matter.py` | Never imported by any file |
| `backend/app/schemas/workflow.py` | Never imported by any file |
| `backend/app/api/v1/matters.py` | Not registered in router (would fail if it were) |
| `backend/app/api/v1/workflow_nodes.py` | Not registered in router |
| `backend/app/api/v1/workflow_templates.py` | Not registered in router |
| `backend/tests/test_matter.py` | References `matter_service` and `workflow_service` -- tests would fail |

#### 3. Alembic env.py missing model imports (4 models unregistered)

Models present in `backend/app/models/__init__.py` but NOT imported in `backend/alembic/env.py`:

| Model | Table (from model definition) |
|---|---|
| `DocumentReview` | `document_review` |
| `WebhookSubscription` | `webhook_subscription` |
| `DocumentChunk` | `document_chunk` |
| `AIConversation`, `AIMessage` | `ai_conversation`, `ai_message` |

These tables would not be auto-detected by Alembic's `--autogenerate` because SQLAlchemy needs the model classes imported at migration time. However, the tables may already exist from prior manual migrations.

**Note:** `DocumentTag` is imported in `alembic/env.py` but NOT in `models/__init__.py`. `ProjectTask` is imported in `alembic/env.py` but not in `models/__init__.py` (it is re-exported via `models/task.py` as `Task`).

---

### P2-Medium (fixed)

#### 4. Search API and Public Dashboard API -- registered [FIXED]

**File:** `backend/app/api/v1/router.py`

Added `search` and `public_dashboard` to the import tuple and added `include_router` calls:

```python
# imports added: search, public_dashboard
api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(public_dashboard.router, tags=["Public Dashboard"])
```

- `public_dashboard.router` has its own prefix `/public/dashboard`, so no additional prefix was added.
- `search.router` has no prefix, so `/search` was added, exposing `/api/v1/search/`.

---

### P3-Low (identified, not yet deleted -- requires project decision)

#### 5. Dead frontend views (3 files)

| File | Reason |
|---|---|
| `frontend/src/views/tasks/TaskDialog.vue` | Zero references in entire frontend codebase |
| `frontend/src/views/dashboard/LeadershipDashboardView.vue` | Zero references (separate from PublicDashboard which IS wired) |
| `frontend/src/views/admin/AIConfigView.vue` | Zero references |

#### 6. Dead frontend components (2 files)

| File | Reason |
|---|---|
| `frontend/src/components/common/ConfirmDialog.vue` | Zero references |
| `frontend/src/components/common/UserAvatar.vue` | Zero references |

#### 7. Dead backend service files (4 files)

| File | Reason |
|---|---|
| `backend/app/services/archive_service.py` | Zero imports from anywhere |
| `backend/app/services/document_preview_service.py` | Zero imports from anywhere |
| `backend/app/services/task_service.py` | Zero imports + imports from stub `matter.py` |
| `backend/app/utils/email_sender.py` | Zero imports from anywhere |

#### 8. Dead backend utility files (1 file)

| File | Reason |
|---|---|
| `backend/app/utils/dispatch.py` | `fire_webhook()` defined but never called from any module |

#### 9. Dead schema files -- entire schema layer unused by API (8 files)

All API route modules define Pydantic schemas inline. The dedicated `schemas/` directory is completely disconnected:

| File | Status |
|---|---|
| `backend/app/schemas/audit.py` | Never imported outside `schemas/` package |
| `backend/app/schemas/auth.py` | Never imported outside `schemas/` package |
| `backend/app/schemas/dashboard.py` | Never imported outside `schemas/` package |
| `backend/app/schemas/document.py` | Never imported outside `schemas/` package |
| `backend/app/schemas/matter.py` | Never imported outside `schemas/` package |
| `backend/app/schemas/notification.py` | Never imported outside `schemas/` package |
| `backend/app/schemas/search.py` | Never imported outside `schemas/` package |
| `backend/app/schemas/task.py` | Never imported outside `schemas/` package |
| `backend/app/schemas/workflow.py` | Never imported outside `schemas/` package |
| `backend/app/schemas/user.py` | Only imported by `schemas/auth.py` (also dead) |

Only `schemas/common.py` is alive (imported by other schema files in the same package for `PaginatedResponse`).

#### 10. Cross-layer violations -- API directly calls DB (systematic pattern)

17 out of 18 API route files (all except `ws.py`) use SQLAlchemy `select()`, `db.execute()`, `db.add()`, `db.commit()` directly. This is a systematic architectural pattern in this codebase -- the API layer performs data access directly rather than delegating to the service layer for most operations. The service layer exists but is used selectively.

Example: `tasks.py` performs all CRUD operations via direct `select(Task).where(...)` queries rather than routing through `TaskService`.

#### 11. Stub model files (2 files)

| File | Content |
|---|---|
| `backend/app/models/matter.py` | 1 comment line, no code |
| `backend/app/models/workflow.py` | 1 comment line, no code |

These are intentionally empty after a migration removed the tables. Their existence could mislead developers into thinking the matter/workflow system is still available.

#### 12. Empty `__init__.py` files

- `backend/app/schemas/__init__.py` -- empty (schemas are imported directly from their modules, but that never happens from external code)
- `backend/app/utils/__init__.py` -- empty

---

## Fix Checklist

| # | Item | Status |
|---|---|---|
| 1 | Register `search` router in `router.py` | **Done** |
| 2 | Register `public_dashboard` router in `router.py` | **Done** |
| 3 | Decide: delete or repair legacy matter/workflow files | Requires PM decision |
| 4 | Add missing models (`DocumentReview`, `WebhookSubscription`, `DocumentChunk`, `AIConversation`, `AIMessage`) to `alembic/env.py` | Recommended |
| 5 | Add `DocumentTag` to `models/__init__.py` (it is in `alembic/env.py` but not in `__init__.py`) | Recommended |
| 6 | Delete dead frontend views (3 files) | Requires PM decision |
| 7 | Delete dead frontend components (2 files) | Requires PM decision |
| 8 | Delete dead backend services (4 files) | Requires PM decision |
| 9 | Delete dead backend utils (1 file) | Requires PM decision |
| 10 | Delete dead schemas or reconnect them to API layer | Requires architectural decision |
| 11 | Remove stub model files (`matter.py`, `workflow.py`) | Requires PM decision |

---

## Model-Service Alignment Summary

### Service files WITH corresponding active models (healthy)
`auth_service`, `user_service`, `document_service`, `search_service`, `notification_service`, `audit_service`, `webhook_service`, `dashboard_service`, `task_management_service`, `ai_config`, `llm_service`, `rag_service`, `summarization_service`, `tool_service`, `template_seeder`, `cas_service`, `ldap_service`, `oauth2_service`, `document_intelligence`, `embedding_service`

### Service files WITHOUT corresponding active models (dead or broken)
`matter_service` (model stubbed), `workflow_service` (model stubbed), `task_service` (model stubbed + never imported), `archive_service` (never imported), `document_preview_service` (never imported)

### Models WITHOUT dedicated service files (API handles directly)
`system_config`, `ai_provider` -- managed directly by API routes or `ai_config` service

### Model `models/task.py`
Re-exports `ProjectTask` from `task_manager.py` as `Task`. This shim is used by `tasks.py` API, `test_approval.py`, and `task_service.py`.

---

## Frontend Route-View Alignment

All 23 routes in `frontend/src/router/index.ts` have corresponding view files. No missing views.

4 views exist without corresponding routes:
- `TaskDialog.vue` -- dead (never referenced anywhere)
- `LeadershipDashboardView.vue` -- dead (never referenced anywhere)
- `AIConfigView.vue` -- dead (never referenced anywhere)
- `DocumentApprovalPanel.vue` -- alive (referenced as sub-component by `DocumentDetailView.vue`)

---

## Recommendations

1. **Immediate:** The two fixed route registrations should be synced to the server and tested.

2. **High priority:** Add the 4 missing models to `alembic/env.py` before running any future `--autogenerate` migrations. Otherwise Alembic may drop those tables.

3. **Medium priority:** Decide the fate of the legacy matter/workflow system:
   - If permanently removed: delete all 11 dead files (models, services, API modules, schemas, test)
   - If planned for re-implementation: leave files but add a guard to prevent accidental use

4. **Medium priority:** Decide whether to:
   - Delete the disconnected `schemas/` directory (10 files, ~80% of the schema layer), OR
   - Migrate API routes to use the shared schemas instead of inline definitions

5. **Low priority:** Clean up dead frontend views and components (5 files).

6. **Low priority:** Clean up dead backend services and utilities (5 files).

7. **Architectural:** The systematic cross-layer violation (API calling DB directly) is a project-wide pattern. If this is intentional (thin API, fat services optional), document this in the architecture guide. If not, establish a rule that all DB access must go through the service layer.
