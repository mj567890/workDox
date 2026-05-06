# Phase 4: ECharts Memory Leak Fix

## Summary

Fixed ECharts memory leaks by ensuring all `echarts.init()` calls are paired with
corresponding `.dispose()` calls in `onUnmounted` lifecycle hooks.

## Affected Files

### 1. `frontend/src/views/dashboard/PublicDashboardView.vue`
- **5 chart leak sites** in `renderFunnelChart`, `renderTemplateChart`,
  `renderTrendChart`, `renderStatusChart`, `renderDeptChart`.
- **Fix**: Added `const charts: echarts.ECharts[] = []` to collect chart instances.
  Each render function pushes its instance with `charts.push(chart)`. An
  `onUnmounted` hook disposes all: `charts.forEach(c => c.dispose())`.

### 2. `frontend/src/views/dashboard/LeadershipDashboardView.vue`
- **5 chart leak sites** in `renderProgressChart`, `renderTypeChart`,
  `renderTrendChart`, `renderDeptChart`, `renderPriorityChart`.
- **Fix**: Same pattern -- charts array, push in each render, dispose in onUnmounted.

### 3. `frontend/src/components/documents/DocumentRelationGraph.vue`
- **Already correct**: Disposes chart via `chart?.dispose()` in `onBeforeUnmount`,
  and removes window resize handler. No changes needed.

## Changes Detail

| File | Charts Fixed | Approach |
|------|-------------|----------|
| PublicDashboardView.vue | 5 | `charts: ECharts[]` array + `onUnmounted` dispose loop |
| LeadershipDashboardView.vue | 5 | `charts: ECharts[]` array + `onUnmounted` dispose loop |
| DocumentRelationGraph.vue | 0 (already correct) | n/a |

## Verification

- `vue-tsc --noEmit` passes for the changed files (pre-existing errors in
  unrelated files remain, none related to these changes).
- No new TypeScript errors introduced.
