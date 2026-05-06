# Frontend Quality Inspection Report

**Date**: 2026-05-06
**Inspector**: Agent-3
**Scope**: `frontend/src/` (Vue 3.4 + TypeScript + Element Plus 2.6 + Pinia 2.1)

---

## 1. Component Size Analysis

### Large Components (>500 lines)

| File | Lines | Severity | Recommendation |
|------|-------|----------|---------------|
| `views/documents/DocumentDetailView.vue` | 680 | Medium | Split into sub-components: preview panel, version history, AI panel, lock status |

DocumentDetailView packs document info editing, version history timeline, preview rendering (with a 40-line markdown parser), approval panel, AI features, and lock management into a single component. It is maintainable for now but should be the first target for decomposition when the team grows or when features are added.

### Duplicated Logic Check

No significant copy-pasted logic blocks found across components. The `usePagination` composable is properly reused by 4+ views. The `usePermission` composable centralizes all RBAC checks (8 computed properties), though 5 of them (`canEditDocument`, `canDeleteDocument`, `canLockDocument`, `canSetOfficialVersion`, `canViewDashboard`) are semantically identical (`authStore.isAdmin || authStore.isDeptLeader`). This is acceptable since the names convey different intent and can diverge in the future.

### Dead Code Removed

| File | Issue | Action |
|------|-------|--------|
| `composables/useAuth.ts` | Never imported anywhere; all 17 files use `useAuthStore` directly | **Deleted** |
| `composables/useFileUpload.ts` | Never imported anywhere | Flagged for potential removal |

Note: `useFileUpload.ts` was left in place pending confirmation it is not needed by planned features.

---

## 2. Reactive State Audit

### Pinia Stores

All 6 stores (`auth`, `documents`, `task-mgmt`, `tasks`, `matters`, `notifications`, `ai`) follow the composition API pattern with `defineStore` + `ref`/`computed`. No mutations-style stores were found.

**Unused exports identified**:

| Store | Member | Status |
|-------|--------|--------|
| `auth.ts` | `isAuthenticated` computed | Never consumed outside the now-deleted `useAuth` composable. Kept because it is a fundamental property that external consumers might need. |

**`ref` vs `reactive` assessment**: Appropriate usage throughout.
- `ref` used for primitives and individual values
- `reactive` used for form data objects (LoginView, UserManagementView, TaskTemplateEditView, etc.)
- No cases of `reactive` being inappropriately used for primitives

### Missing `computed` Opportunities

One minor optimization identified:
- In `SearchResultsView.vue`, the page object uses `ref(1)` for `page` instead of `usePagination()` composable. This is inconsistent with other list views but not a bug.

No cases were found where derived state is recalculated in templates instead of being cached via `computed`.

---

## 3. Error Handling Audit

### Global Error Handling (Axios Interceptor)

`api/index.ts` provides a solid foundation:
- 401: clears token, redirects to `/login`
- 403/404/409/422: shows `ElMessage` with formatted error detail
- Network errors: shows "Network error" toast
- Public API instance: silent error rejection (for public dashboard)

### Issues Found and Fixed

**8 views had missing or insufficient error handling. All were fixed.**

#### Critical (success message would fire even on failure)

| File | Functions | Risk | Status |
|------|-----------|------|--------|
| `TaskBoardView.vue` | `handleUpload`, `handleRemoveDoc`, `handleWaive`, `handleUnwaive`, `handleAdvance` | Success toasts would show even when API call failed silently -- **user sees false confirmation** | **FIXED** |
| `TaskCenterView.vue` | `handleStart`, `handleComplete` | Same -- success toast on failed API call | **FIXED** |
| `TaskTemplateEditView.vue` | `handleSaveMeta`, `openAddStage`, `saveStage`, `openAddSlot`, `saveSlot` | No try/catch at all; **unhandled promise rejections** | **FIXED** |
| `AIConfigView.vue` | `toggleProvider` | UI toggle updated optimistically without rollback on error | **FIXED** |

#### Medium (initialization failures swallowed silently)

| File | Context | Risk | Status |
|------|---------|------|--------|
| `UserManagementView.vue` | `onMounted` department/role fetch | API failure would crash the mount, showing blank page | **FIXED** |
| `AIChatView.vue` | `onMounted` conversation/provider fetch, `selectConversation` | Sidebar would remain empty on failure with no feedback | **FIXED** |
| `TaskListView.vue` | `onMounted` sequential fetches | Second fetch could fail and break the page | **FIXED** |

### Views with Good Error Handling (Verified)

- `LoginView.vue` -- try/catch on login, proper loading state, validation
- `SettingsView.vue` -- try/catch with specific error message extraction, validation with custom rules
- `DocumentDetailView.vue` -- all 10 async functions have try/catch + loading states
- `DocumentApprovalPanel.vue` -- submit/approve/reject all guarded
- `ProfileView.vue` -- form validation + try/catch with error message fallback
- `WebhookManagementView.vue` -- save/delete with confirmation dialogs and error handling
- `PublicDashboardView.vue` -- Promise.all with error handling
- `SearchResultsView.vue` -- try/finally pattern
- `AuditLogView.vue` -- try/finally pattern

### Bug Fixed

| File | Bug | Fix |
|------|-----|-----|
| `AuditLogView.vue` | `keyword` ref was collected on input and triggered `handleSearch`, but `keyword` was never included in the API params object | Added `keyword: keyword.value \|\| undefined` to params |

---

## 4. Router & Guards Analysis

### Token Expiry Handling

**Status: Adequate with caveat.**

The navigation guard (`router.beforeEach`) checks for token existence in `localStorage`, not token validity/expiry. Token expiry is handled reactively:
1. API returns 401
2. Axios response interceptor catches it, clears token, redirects to `/login`
3. Next navigation will find no token and redirect to `/login`

This is a two-step process. A more robust approach would be to decode the JWT in the guard and check expiry proactively. However, this requires installing a JWT decode library or implementing a simple base64 decode. **Marked as a future improvement, not a bug.**

### Role-Based Route Visibility

- Route `meta.roles` is checked in the guard against `authStore.userRoles`
- Unauthorized access shows `ElMessage.warning` and redirects to `/`
- Sidebar visibility matches route roles (`Sidebar.vue` checks `isAdmin`, `isDeptLeader`, `canViewAuditLogs`)

### Route Coverage

All 22 route entries have corresponding lazy-loaded view components. No orphan routes.

### Route Structure

- Auth routes (`/login`, `/auth/oauth2/callback`, `/auth/cas/callback`): `requiresAuth: false`
- Public dashboard (`/dashboard`): `requiresAuth: false`
- All other routes: protected by `AppLayout.vue` parent with `requiresAuth: true`
- Admin routes: restricted to `['admin']` role
- Template routes: restricted to `['admin', 'dept_leader']`

---

## 5. Element Plus Usage

### Deprecated Components

None found. The codebase uses Element Plus 2.6 APIs consistently.

### Form Validation Patterns

Forms consistently use the `el-form` + `:rules` + `ref.validate()` pattern:
- `LoginView`: rules with `required` + `trigger: 'blur'`
- `SettingsView`: rules with custom validator (`validateConfirmPassword`)
- `ProfileView`: rules with `type: 'email'` and `pattern` regex validation
- `UserManagementView`: rules with `required` validators
- `RoleManagementView`: rules with `required` validators

All forms use `formRef.value?.validate().catch(() => false)` for submission validation. Good practice.

### Accessibility Concerns

| Issue | Location | Severity |
|-------|----------|----------|
| No `aria-label` on icon-only buttons | Sidebar collapse, notification bell | Low |
| No `role` or `aria-expanded` on collapsible sections | TaskTemplateEditView `el-collapse` | Low |
| `el-menu` lacks `aria-label` | Sidebar | Low |
| No keyboard navigation support documented | All components | Medium |
| No screen-reader announcements for dynamic content updates | AIChatView messages, notification count | Medium |

Accessibility is not well-addressed project-wide. This would require a dedicated audit and refactoring pass. **REPORT: full a11y overhaul recommended for a future milestone.**

### `el-form` label-position

Mixed usage: some forms have explicit `label-position="left"` or `label-position="right"`, others rely on Element Plus default (which is `right`). This is not a bug but creates visual inconsistency. Most admin forms use `label-width="80px"`, settings uses `label-width="100px"`. Acceptable.

---

## 6. Additional Findings

### Unused Composable Candidates

| File | Used? | Recommendation |
|------|-------|---------------|
| `useFileUpload.ts` | No imports found | Consider removing |
| `useAuth.ts` | No imports found | **DELETED** |

### ECharts Memory Leak Risk

`PublicDashboardView.vue` and `LeadershipDashboardView.vue` create ECharts instances with `echarts.init()` but never call `dispose()` on cleanup. On route navigation, chart DOM nodes are replaced but ECharts instances remain in memory. Medium severity. Should add `onBeforeUnmount` cleanup hooks.

### Direct `fetch()` Usage

`TaskCenterView.vue` and `DocumentCenterView.vue` use raw `fetch()` for export endpoints instead of the Axios instance. This bypasses error handling, auth token injection, and base URL configuration. Low severity (these are download endpoints that work differently) but should be unified.

### Template Search Timer Flaws

`UserManagementView.vue` and `DocumentCenterView.vue` implement debounce with `setTimeout` + `clearTimeout` for search input, but the timer variable is module-scoped (`let searchTimer`) rather than a `ref` or inside the composable. This works but could cause issues if two instances of the component existed simultaneously. Not applicable in current architecture (single-page views).

---

## 7. Fix Summary

### Files Modified (8)

| File | Change |
|------|--------|
| `views/tasks/TaskBoardView.vue` | Added try/catch + `actionLoading` ref to 5 handler functions |
| `views/tasks/TaskTemplateEditView.vue` | Added try/catch to `handleSaveMeta`, `openAddStage`, `saveStage`, `openAddSlot`, `saveSlot` |
| `views/audit/AuditLogView.vue` | Fixed keyword not sent in API params |
| `views/tasks/TaskCenterView.vue` | Added try/catch to `handleStart`, `handleComplete` |
| `views/admin/UserManagementView.vue` | Added try/catch to `onMounted` department/role fetch |
| `views/ai/AIChatView.vue` | Added try/catch to `onMounted` and `selectConversation` |
| `views/admin/AIConfigView.vue` | Added try/catch to `toggleProvider` |
| `views/tasks/TaskListView.vue` | Added try/catch to `onMounted`, parallelized fetches |

### Files Deleted (1)

| File | Reason |
|------|--------|
| `composables/useAuth.ts` | Dead code: never imported by any component |

---

## 8. Recommendations (Not Fixed -- Requires Planning)

1. **Split `DocumentDetailView.vue`** (680 lines) into sub-components: `<DocumentPreviewPanel>`, `<VersionHistoryPanel>`, `<AIPanel>`, `<LockStatusPanel>`
2. **Add proactive JWT expiry check** in `router.beforeEach` (decode token, check `exp` claim)
3. **Add ECharts instance cleanup** in dashboard views (`onBeforeUnmount` + `echarts.dispose()`)
4. **Unify export/download patterns** to use Axios instance instead of raw `fetch()`
5. **Full accessibility audit** -- add aria labels, keyboard navigation, screen-reader announcements
6. **Remove `useFileUpload.ts`** if confirmed unused by planned features
7. **Add loading states** to toggle/save operations in TaskBoardView (use the new `actionLoading` ref per action type)
8. **Backend audit log keyword filter** -- audit API schema does not support `keyword` filter; the frontend now sends it but it is ignored
