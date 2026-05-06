# Phase 4: v-html XSS Sanitization Fix

**Date:** 2026-05-06

## Summary

Added DOMPurify sanitization to all `v-html` bindings in the WorkDox frontend to prevent XSS attacks. Three locations were identified and fixed.

## Changes

### New file
- `frontend/src/composables/useSanitize.ts` -- Composable exporting a `sanitize(html): string` function that wraps `DOMPurify.sanitize()` with a permissive but safe allowlist (supports markdown-rendered previews, search highlights, and similar-document headlines).

### Updated files

**`frontend/src/views/search/SearchResultsView.vue`**
- Line 31: `v-html="item.highlight || item.title"` replaced with `v-html="sanitize(item.highlight || item.title)"`
- Added import of `sanitize` from `@/composables/useSanitize`

**`frontend/src/views/documents/DocumentDetailView.vue`**
- Line 138: `v-html="previewHtml"` replaced with `v-html="sanitize(previewHtml)"` (markdown preview)
- Line 217: `v-html="row.headline"` replaced with `v-html="sanitize(row.headline)"` (similar-document headline highlights)
- Added import of `sanitize` from `@/composables/useSanitize`

### New dependency
- `dompurify` + `@types/dompurify` installed in `frontend/package.json`

## DOMPurify Configuration

Allowed tags: h1-h6, p, br, hr, ul, ol, li, table/thead/tbody/tr/th/td, strong, em, b, i, u, s, del, ins, a, code, pre, blockquote, span, div, img, mark, sub, sup

Allowed attributes: href, target, rel, class, style, src, alt, width, height, colspan, rowspan

Data attributes: disabled

This configuration supports markdown-rendered preview HTML, search result highlights (typically `<em>` or `<mark>` wrapping), and similar-document match snippets, while stripping dangerous elements like `<script>`, `<object>`, `<embed>`, and event handlers.

## Verification

- `vue-tsc --noEmit` ran successfully (pre-existing errors in unrelated files, zero new errors)
- All 3 v-html usages confirmed to pass through `sanitize()`
