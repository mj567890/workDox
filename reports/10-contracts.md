# API Contract Review Report

**Date**: 2026-05-06
**Reviewer**: Agent-10 (Contract Reviewer)
**Scope**: Full frontend-backend API consistency audit

---

## Findings Summary

### Critical Issues

#### 1. Dead Backend Modules Not Registered in Router
Five backend route files exist with complete endpoint implementations but are **never registered** in `backend/app/api/v1/router.py`, meaning they are unreachable at runtime:

| File | Routes | Status |
|------|--------|--------|
| `matters.py` | 15 routes | NOT registered |
| `search.py` | 1 route | NOT registered |
| `workflow_templates.py` | 18 routes | NOT registered |
| `workflow_nodes.py` | 5 routes | NOT registered |
| `public_dashboard.py` | 6 routes | NOT registered |

**Impact**:
- `/api/v1/matters/*` -- Frontend `mattersApi` and `mattersStore` call these, but they 404.
- `/api/v1/search` -- Frontend `searchApi` calls this, returns 404.
- `/api/v1/public/dashboard/*` -- Public dashboard returns 404. The frontend `publicDashboardApi` is unusable.
- `workflow_templates` and `workflow_nodes` routes have no frontend usage and the underlying model files (`models/matter.py`, `models/workflow.py`) are stubs (tables removed via migration `remove_legacy_matter_workflow`). These are fully dead code.

**Fix needed**: Frontend `mattersApi`, `mattersStore`, `searchApi`, and `publicDashboardApi` are hitting endpoints that do not exist. The backend modules must either be registered in `router.py`, or the frontend dead references should be cleaned up. For matters and workflow, since the DB tables are gone, the correct fix is to remove the dead frontend code and drop the orphan backend route files.

#### 2. Document LockStatus Interface Mismatch (FIXED)
**Backend** `LockStatusOut` returns:
```json
{ "is_locked": true, "locked_by": 123, "locked_by_name": "John", "locked_at": "...", "expires_at": "..." }
```
**Frontend** `LockStatus` (old) expected:
```typescript
{ locked: boolean, locked_by: string, locked_at: string, expires_at: string }
```

Field name mismatch (`is_locked` vs `locked`) and type mismatch (`locked_by` as string vs int). The document locking UI in `DocumentDetailView.vue` was completely broken -- lock alerts never appeared.

**Fixed in this review**: Aligned `LockStatus` interface and all references in `DocumentDetailView.vue`.

#### 3. Backend POST /lock Returns Incomplete Response (FIXED)
The `POST /documents/{id}/lock` endpoint returned `{"detail": "Document locked", "expires_at": "..."}` instead of a full `LockStatusOut`. The frontend used the return value directly as `lockStatus`, receiving garbage.

**Fixed in this review**: Both `POST /lock` and `DELETE /lock` now return proper `LockStatusOut`.

---

### Type Schema Misalignments

#### Minor Inconsistencies

| Endpoint | Field | Backend | Frontend | Severity |
|----------|-------|---------|----------|----------|
| GET /documents | `matter_id`, `matter_title` | Present | Missing | Low (backend sends extra, TS ignores) |
| GET /documents | `extracted_text_length` | Missing | Present | Low (frontend field always undefined) |
| GET /users/departments | `children_count` | Missing | Present | Low |
| GET /users/departments | `updated_at` | Present | Missing | Low |
| GET /notifications | `related_matter_id`, `related_matter_title` | Present | Missing | Low |
| GET /dashboard/key-projects | `created_at` | Missing | Present | Low |

None of these cause runtime errors, but frontend types are incomplete/incorrect.

---

### HTTP Method Consistency

**PASS** -- All frontend HTTP methods match backend route decorators. No inconsistencies found.

**PASS** -- No GET endpoints accept request bodies. All data is passed via query parameters or path variables.

---

### Error Response Handling

**PASS** -- Backend uses `AppException(HTTPException)` with string `detail` field. The default FastAPI error format `{"detail": "..."}` is consistent across all custom exceptions (`NotFoundException`, `ForbiddenException`, `ValidationException`, `ConflictException`, etc.).

**PASS** -- Frontend error interceptor (`frontend/src/api/index.ts`) correctly handles:
- String `detail` (custom exceptions)
- Array `detail` (FastAPI 422 validation errors)
- Status-based routing (401 redirect, 403/404/409/422 user messages)

---

### README & Docs Accuracy

#### README Count Fixes Applied
| Item | Old | Actual | Status |
|------|-----|--------|--------|
| API route modules | "15" | 13 registered (20 files) | Fixed |
| ORM models | "9" | 12 active | Fixed |
| Business services | "15" | 25 (excl. __init__) | Fixed |
| Frontend API modules | "11" | 15 | Fixed |
| Components | "15" | 12 | Fixed |
| Pinia stores | "6" | 7 | Fixed |
| Element Plus version | "2.5" | 2.6 | Fixed |

---

### Orphan Endpoints (Backend-only, no frontend usage)

These backend endpoints exist but have no corresponding frontend API call:

| Endpoint | File |
|----------|------|
| POST /documents/upload/init | documents.py |
| POST /documents/upload/chunk | documents.py |
| POST /documents/upload/complete | documents.py |
| POST /documents/{id}/generate-embedding | documents.py |
| GET /documents/{id}/similar-vector | documents.py |
| GET /documents/export/excel | documents.py |
| POST /tasks/batch/complete | tasks.py |
| GET /tasks/export/excel | tasks.py |
| POST /notifications/batch/read | notifications.py |
| GET /tasks/export/excel | tasks.py |
| POST /matters/batch/assign | matters.py (unregistered) |
| GET /matters/export/excel | matters.py (unregistered) |
| All /task-templates/{id}/stages/{sid}/slots/reorder | task_templates.py |

Most are legitimate (chunked upload is server-only, exports not yet wired to UI). The `reorderSlots` endpoint is the only one that appears to be a missing frontend method.

---

### Missing Frontend API Methods

| Backend Endpoint | Missing Frontend Method |
|------------------|------------------------|
| PUT /task-templates/{id}/stages/{sid}/slots/reorder | `taskTemplatesApi.reorderSlots` |

---

### Frontend API Modules With No Backend

| Frontend Module | Backend Router | Status |
|-----------------|---------------|--------|
| `matters.ts` (mattersApi) | matters.py unregistered, tables dropped | Dead code |
| `publicDashboard.ts` | public_dashboard.py unregistered | Dead code |

---

### Files Modified

1. **`frontend/src/api/documents.ts`** -- Fixed `LockStatus` interface field names (`locked` -> `is_locked`, `locked_by` type string -> number, added `locked_by_name`)
2. **`frontend/src/views/documents/DocumentDetailView.vue`** -- Updated all `lockStatus.locked` -> `lockStatus.is_locked` and `lockStatus.locked_by` -> `lockStatus.locked_by_name` (4 locations)
3. **`backend/app/api/v1/documents.py`** -- Changed `POST /lock` and `DELETE /lock` to return proper `LockStatusOut` instead of ad-hoc dicts
4. **`README.md`** -- Updated all outdated module/component counts to match actual codebase

---

### Recommendations

1. **HIGH** -- Either register `public_dashboard.py` in `router.py` or remove the frontend `publicDashboard.ts` and `PublicDashboardView.vue` (they are non-functional).
2. **HIGH** -- Either register `search.py` in `router.py` or remove the frontend `search.ts` and `SearchResultsView.vue` (they are non-functional).
3. **MEDIUM** -- Remove dead backend files: `matters.py`, `workflow_templates.py`, `workflow_nodes.py` (DB tables dropped, no route registration).
4. **MEDIUM** -- Remove dead frontend code: `matters.ts`, `stores/matters.ts` (backend matters endpoints and tables don't exist).
5. **LOW** -- Add missing `reorderSlots` method to frontend `taskTemplatesApi`.
6. **LOW** -- Consider consolidating inline Pydantic schemas (`DepartmentOut`, `RoleOut` in `users.py`, `ReviewOut` in `documents.py`) into `backend/app/schemas/` to avoid duplication with `schemas/user.py` (`DepartmentResponse`, `RoleInfo`).
