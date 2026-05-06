# 11-dead-code.md -- Dead Code Audit

## Summary

| Category | Issues Found | Fixed | Flagged |
|---|---|---|---|
| Unused Python imports | 7 | 7 | 0 |
| Dead functions/classes | 6 | 0 | 6 |
| Dead files | 3 (.py) + 3 (.vue) | 0 | 6 |
| Duplicate functionality | 2 pattern pairs | 0 | 2 |
| Commented-out code blocks | 0 | -- | -- |
| Empty `__init__.py` files | 7 | 0 | 7 |
| Unused store/composable members | 0 | -- | -- |

---

## 1. Unused Python Imports (FIXED)

All 7 unused imports removed from the codebase:

| File | Line | Import removed | Reason |
|---|---|---|---|
| `services/document_service.py` | 24 | `from app.core.permissions import RoleCode` | Never referenced in file |
| `api/v1/documents.py` | 5 | `or_` from `sqlalchemy` | Never used (no `or_(` calls) |
| `api/v1/matters.py` | 5 | `or_` from `sqlalchemy` | Never used (no `or_(` calls) |
| `api/v1/matters.py` | 14 | `RoleCode` from `app.core.permissions` | Never referenced in file |
| `api/v1/users.py` | 4 | `func` from `sqlalchemy` | Never used (only `select` is used) |
| `services/cas_service.py` | 1 | `import secrets` | Never called in file |
| `services/oauth2_service.py` | 32 | `from app.core.security import create_access_token` | Duplicate of top-level import on line 10; removed the inner one, kept `from datetime import timedelta` which is genuinely needed only in that method |

---

## 2. Dead Functions and Classes (FLAGGED -- keept for design review)

These are defined but never called by any code in the project. Not removed because they may be intended for future use or only exposed externally (e.g., webhook signature verification by receiving systems).

### 2a. `utils/dispatch.py` -- `fire_webhook()`

- Defined on line 15. Never imported by any file (the only references to `dispatch.py` are inside its own docstring).
- The actual webhook dispatch used by the app comes from `utils/webhook_dispatcher.py` (used via `webhook_service.py`).
- **Recommendation:** Delete `utils/dispatch.py` or merge its fire-and-forget pattern into `webhook_dispatcher.py`.

### 2b. `services/archive_service.py` -- `ArchiveService`

- Entire class never imported or instantiated.
- `archive_tasks.py` has `extract_archive` task that appears self-contained (no use of ArchiveService).
- **Recommendation:** Delete if RAR/ZIP extraction is handled elsewhere. Otherwise wire it into the API.

### 2c. `services/document_preview_service.py` -- `DocumentPreviewService`

- Entire class never imported or instantiated.
- References `convert_to_pdf.delay(...)` which does NOT exist. The actual Celery task is `convert_to_html` in `preview_tasks.py`. This indicates the preview service was written for an older task interface and never updated or wired in.
- Preview logic is instead implemented directly in `api/v1/documents.py` (lines 764+).
- **Recommendation:** Delete. The route handler has its own preview logic that works with the actual `convert_to_html` task.

### 2d. `utils/webhook_dispatcher.py` -- `dispatch_event()` and `verify_webhook_signature()`

- Only `EVENT_TYPES` is imported by `webhook_service.py`. The `dispatch_event` and `verify_webhook_signature` functions are exported but never called internally.
- `verify_webhook_signature` may be intended for use by receiving endpoints (webhook consumers) but no such endpoint exists in the current codebase.
- `dispatch_event` has an older design (passes `db_session_factory` vs the newer fire-and-forget pattern).
- **Recommendation:** Keep `EVENT_TYPES`. Consider whether `dispatch_event` should replace `fire_webhook` in `dispatch.py`, or if both should be consolidated.

### 2e. `services/document_service.py` -- `_check_document_access_with_db()`

- Private method on `DocumentService` (line 311), never called.
- The actual access check uses `_check_document_access()` (line 299) which silently returns for all callers -- it never raises `ForbiddenException`. The `_with_db` variant would properly raise.
- **Bug concern:** The permissive version `_check_document_access` is wired in, meaning access control on `DocumentService.get_document` does not actually reject unauthorized users. The `_check_document_access_with_db` was presumably meant to replace it.
- **Recommendation:** Replace `_check_document_access` with `_check_document_access_with_db` (or delete the unused variant and fix the active one).

### 2f. `api/v1/documents.py` -- `_check_document_access()` helper

- Separate standalone function (not a class method) on line 192. Correctly uses `RoleCode` and `db` to verify access. This is the one wired into routes.
- Not dead -- this is the working access check for document endpoints. Included for contrast with the bug in (2e).

---

## 3. Dead Files

### 3a. Python Dead Files

| File | Status |
|---|---|
| `utils/dispatch.py` | `fire_webhook` never imported (see 2a) |
| `services/archive_service.py` | `ArchiveService` never imported (see 2b) |
| `services/document_preview_service.py` | `DocumentPreviewService` never imported (see 2c) |

### 3b. Orphaned Vue Frontend Views

These `.vue` files are defined but never referenced by the router or imported by any other component:

| File | Notes |
|---|---|
| `views/admin/AIConfigView.vue` | AI config is handled by `views/admin/UserManagementView.vue` (system settings section). This separate view has no route. |
| `views/dashboard/LeadershipDashboardView.vue` | Only `PublicDashboardView` is in the router. `LeadershipDashboardView` has no route and no imports. |
| `views/tasks/TaskDialog.vue` | Task creation/editing is done inline in `TaskCenterView` and `TaskBoardView`. This separate dialog component is unused. |

**Recommendation:** Delete these 3 `.vue` files.

---

## 4. Duplicate Functionality (FLAGGED)

### 4a. `utils/text_extraction.py` vs `utils/text_extractor.py`

Both extract text from documents:

| Aspect | `text_extraction.py` (69 lines) | `text_extractor.py` (288 lines) |
|---|---|---|
| Formats | docx, xlsx, pdf, txt/md/csv | docx, xlsx/xls, pdf (3 fallbacks), pptx, 80+ text formats |
| PDF extraction | pdfplumber only | pdfplumber -> pdfminer -> pypdfium2 fallback |
| Table extraction | None | From DOCX tables, XLSX sheets, PPTX tables |
| Encoding | UTF-8, GBK | UTF-8, GBK, GB2312, GB18030, Latin-1 |
| Errors | Silent empty string | Returns None, logs warnings |
| Max chars | No limit | 50,000 char soft cap |

**Usage:**
- `text_extraction` is imported only in `tasks/search_tasks.py` (line 35, lazy import)
- `text_extractor` is imported in `api/v1/documents.py` and `services/document_intelligence.py`

**Recommendation:** Migrate `search_tasks.py` to use `text_extractor` (the superior version), then delete `text_extraction.py`.

### 4b. `utils/webhook_dispatcher.py` vs `utils/dispatch.py`

Both dispatch webhook events:

| Aspect | `webhook_dispatcher.py` (136 lines) | `dispatch.py` (97 lines) |
|---|---|---|
| Concurrency | `asyncio.gather` (concurrent) | Sequential `for` loop |
| HMAC signing | Yes | Yes |
| Error handling | Broad exceptions | Specific `httpx.HTTPError`, etc. |
| DB session | Passed as factory | Creates own via `_get_async_session_factory` |
| Subscription update | Batch commit | Batch commit |

**Recommendation:** Consolidate into a single dispatcher. The `dispatch.py` fire-and-forget pattern (safe for route handlers) is the better API design, but it should use `webhook_dispatcher.py`'s concurrent delivery.

---

## 5. Commented-Out Code Blocks

**No commented-out code blocks found.** All `#` lines in the Python codebase are explanatory comments or section dividers, not disabled code.

---

## 6. Empty / Near-Empty Files

### 6a. Empty `__init__.py` files (7 files)

All 7 `__init__.py` files below are completely empty (0 lines of code). They serve as Python namespace package markers. Keep them for correctness, but they contribute zero functionality:

- `backend/app/__init__.py`
- `backend/app/api/__init__.py`
- `backend/app/api/v1/__init__.py`
- `backend/app/core/__init__.py`
- `backend/app/schemas/__init__.py`
- `backend/app/services/__init__.py`
- `backend/app/tasks/__init__.py`
- `backend/app/utils/__init__.py`

(Note: `models/__init__.py` is NOT empty -- it re-exports all model classes.)

### 6b. Near-empty service files

`services/archive_service.py` (27 lines): Contains a single class (`ArchiveService`) with one method (`extract_and_import`) and one helper (`trigger_extraction`). The class is never imported. See section 2b.

---

## 7. Frontend Assets Audit

### 7a. Vue Components -- All router-referenced views confirmed used

Every view referenced in `router/index.ts` has a corresponding `.vue` file. Three views exist on disk but have no route (see 3b).

### 7b. Vue Components -- Sub-components

All sub-components are referenced:
- `DocumentApprovalPanel.vue` -- imported by `DocumentDetailView.vue`
- `NotificationBell.vue` -- imported by `HeaderBar.vue`  
- `GlobalSearchBar.vue` -- imported by `HeaderBar.vue`
- `Breadcrumb.vue`, `ConfirmDialog.vue`, `DragUploadZone.vue`, `FileTypeIcon.vue`, `StatusTag.vue`, `UserAvatar.vue` -- all used across views

### 7c. Composable Functions -- All 9 used

All composables in `frontend/src/composables/` are imported by at least one view or component:
`useAuth`, `useBatchSelection`, `useFileUpload`, `usePagination`, `usePermission`, `useResponsive`, `useShortcuts`, `useTheme`, `useWebSocket`

### 7d. API Modules -- All 16 used

All API modules in `frontend/src/api/` are imported by at least one view or store:
`ai`, `audit`, `auth`, `dashboard`, `documents`, `index`, `matters`, `notifications`, `publicDashboard`, `search`, `system`, `task-instances`, `task-templates`, `tasks`, `users`

### 7e. Pinia Stores -- All 7 used across views

`auth`, `ai`, `documents`, `matters`, `notifications`, `tasks`, `task-mgmt`

### 7f. Store Members -- All exported members appear referenced

No unused store getters, actions, or state properties detected in the 7 store modules.

---

## 8. Recommended Actions

### Immediate (low risk)
1. **Delete** `views/admin/AIConfigView.vue` -- orphaned
2. **Delete** `views/dashboard/LeadershipDashboardView.vue` -- orphaned
3. **Delete** `views/tasks/TaskDialog.vue` -- orphaned

### Short-term (requires verification)
4. **Delete** `utils/dispatch.py` -- consolidate with `webhook_dispatcher.py` if the fire-and-forget pattern is needed; otherwise just delete
5. **Delete** `services/archive_service.py` -- or wire it into the API
6. **Delete** `services/document_preview_service.py` -- references a non-existent task name, superseded by inline logic in `documents.py`
7. **Migrate** `search_tasks.py` from `text_extraction` to `text_extractor`, then delete `utils/text_extraction.py`

### Requires design discussion
8. Fix `DocumentService._check_document_access` -- currently never denies access (see 2e). Either replace with `_check_document_access_with_db` or fix the active version.
9. Consolidate the two webhook dispatchers (see 4b).
10. Consider removing empty `__init__.py` files if using Python 3.3+ namespace packages -- but verify this does not break Alembic migration discovery or pytest collection.
