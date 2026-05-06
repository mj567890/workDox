# Phase 4: Legacy Matter/Workflow Dead Code Cleanup

Date: 2026-05-06

## Summary

Removed 11 dead files related to legacy matter and workflow systems whose database tables were dropped via the `remove_legacy_matter_workflow` migration. Models `backend/app/models/matter.py` and `backend/app/models/workflow.py` were already stubs; the remaining service, API, schema, and test files formed a dead dependency chain not registered in the API router.

## Files Deleted (11 total)

### Model stubs
| File | Reason |
|------|--------|
| `backend/app/models/matter.py` | Stub. Only imported by other dead files. Not in `models/__init__.py`. |
| `backend/app/models/workflow.py` | Stub. Only imported by other dead files. Not in `models/__init__.py`. |

### Services
| File | Reason |
|------|--------|
| `backend/app/services/matter_service.py` | Imported only by `api/v1/matters.py` (dead, not in router). Imports non-existent `MatterType` from `document.py`. |
| `backend/app/services/workflow_service.py` | Imported only by dead API files (`matters.py`, `workflow_templates.py`, `workflow_nodes.py`). Imports from deleted models. |
| `backend/app/services/task_service.py` | No external imports at all. New task system uses `task_management_service.py`. Imports from deleted models. |

### API Routes
| File | Reason |
|------|--------|
| `backend/app/api/v1/matters.py` | Not registered in `api/v1/router.py`. Imports from deleted models and services. |
| `backend/app/api/v1/workflow_nodes.py` | Not registered in `api/v1/router.py`. Imports from deleted models. |
| `backend/app/api/v1/workflow_templates.py` | Not registered in `api/v1/router.py`. Imports from deleted workflow service. |

### Schemas
| File | Reason |
|------|--------|
| `backend/app/schemas/matter.py` | Zero external imports. Used only by deleted API/service files. |
| `backend/app/schemas/workflow.py` | Zero external imports. Used only by deleted API/service files. |

### Tests
| File | Reason |
|------|--------|
| `backend/tests/test_matter.py` | References deleted `matter_service` and `MatterType` (non-existent class). |

## Files NOT Deleted (and Why)

| File | Reason |
|------|--------|
| `backend/app/models/task.py` | Actively re-exports `ProjectTask as Task` from `task_manager`. Used by `api/v1/tasks.py` (registered in router). |
| `backend/app/models/task_manager.py` | Core of the new task system (`TaskTemplate`, `ProjectTask`, `ProjectStage`, etc.). Actively used. |
| `backend/app/services/task_management_service.py` | Service for the new task system. Actively used by `api/v1/tasks.py` and `api/v1/task_instances.py`. |

## Issues Flagged for Follow-Up

### 1. `backend/app/services/user_service.py:613-690` -- Dead MatterTypeService class

The `MatterTypeService` class performs lazy imports of `MatterType` from `app.models.document`, but `MatterType` does not exist in `document.py`. The class is not called from `api/v1/users.py`, so it is effectively dead code within a live file. It should be removed in a separate cleanup.

### 2. `backend/app/api/v1/notifications.py:21-22,68-69` -- Broken matter attributes

The `NotificationOut` schema and list handler access `n.related_matter_id` and `n.related_matter.title`, but the `Notification` model has no such columns/relationships. Calling `/api/v1/notifications/` will raise `AttributeError` at runtime.

### 3. Frontend matter references (10 files)

These files reference the now-deleted backend matter/workflow endpoints:

| File | Concern |
|------|---------|
| `frontend/src/api/matters.ts` | API calls to `/matters` -- backend routes deleted |
| `frontend/src/stores/matters.ts` | Store wrapping the dead matter API |
| `frontend/src/api/tasks.ts` | `TaskItem` interface has `matter_id`, `matter_title` fields |
| `frontend/src/views/tasks/TaskCenterView.vue` | May reference matter-related data |
| `frontend/src/views/tasks/TaskDialog.vue` | May reference matter-related data |
| `frontend/src/views/documents/DocumentCenterView.vue` | May reference matter-related data |
| `frontend/src/views/dashboard/PublicDashboardView.vue` | May reference matter-related data |
| `frontend/src/views/dashboard/LeadershipDashboardView.vue` | May reference matter-related data |
| `frontend/src/views/search/SearchResultsView.vue` | May reference matter-related data |
| `frontend/src/components/documents/DocumentRelationGraph.vue` | May reference matter-related data |

These are **not deleted** -- frontend cleanup requires a product decision on whether to replace with new task system equivalents or remove entirely.

### 4. Active tables/columns with "matter" naming

- `backend/app/models/document.py:54` -- `permission_scope` column default `"matter"`. This is a harmless string default on an active table, not a dead reference to the legacy system.

## Verification

- Full-project grep confirms zero remaining imports from any deleted file across `backend/`
- `backend/app/models/__init__.py` compiles cleanly
- `backend/app/api/v1/router.py` compiles cleanly
- `backend/app/main.py` compiles cleanly
