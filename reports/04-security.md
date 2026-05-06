# Security Audit Report

**Project**: WorkDox (ODMS) -- Online Document Management System
**Date**: 2026-05-06
**Auditor**: Agent-4 (Security Scanner)

---

## 1. Executive Summary

A comprehensive security audit of the ODMS codebase identified vulnerabilities in 6 categories. **5 issues were fixed directly** in this audit; **4 issues require architectural changes** and are reported for action.

### Severity Legend

| Level | Description |
|-------|-------------|
| Critical | Immediate risk -- credentials exposed, auth bypass |
| High | Significant risk -- XSS, data leakage |
| Medium | Moderate risk -- configuration hardening, missing headers |
| Low | Best-practice gap -- should be addressed in roadmap |

---

## 2. Findings & Fixes Applied

### 2.1 [CRITICAL] Hardcoded Credentials in docker-compose.yml (REPORTED)

**File**: `docker-compose.yml`
**Lines**: 5-6, 26-27, 42-51, 68-76

Multiple services contain hardcoded credentials directly in the compose file:

| Credential | Value | Services |
|------------|-------|----------|
| PostgreSQL password | `odms123` | db, backend, celery-worker, celery-beat |
| MinIO root user | `minioadmin` | minio, backend, celery-worker |
| MinIO root password | `minioadmin` | minio, backend, celery-worker |

These are Docker-internal credentials visible to anyone who can read the compose file. While the Docker network adds some protection, these should be moved to a `.env` file.

**Recommended fix**: Create a `.env` file in the project root with `POSTGRES_PASSWORD`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD` variables and reference them in docker-compose.yml via `${VARIABLE}` syntax.

**Related**: `backend/app/config.py` has insecure defaults:
- Line 10: `DATABASE_URL` default has hardcoded password `odms123`
- Line 17-18: `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` default to `minioadmin`
- Line 22: `JWT_SECRET_KEY` defaults to `"change-me-in-production"`
- Line 76-77: `SMTP_USERNAME` / `SMTP_PASSWORD` default to empty strings

A `.env.example` file has been created at `backend/.env.example` documenting all required variables with `CHANGE_ME` placeholders.

---

### 2.2 [HIGH] API Key Exposure in Admin Endpoint (FIXED)

**File**: `backend/app/api/v1/system.py`, line 141 (original)

The `GET /api/v1/ai-providers` endpoint returned full API keys in plaintext to any admin user:

```python
"api_key": p.api_key,  # FULL key exposed
```

This means admin users can read provider API keys from the browser. If an admin session is compromised, all AI provider keys are leaked.

**Fix**: Added `_mask_api_key()` helper function that replaces all but the last 4 characters with `****`. The GET endpoint now returns masked keys. The create/update endpoints already do NOT return the full key in response bodies (they return only `{"detail": ..., "id": ...}`).

---

### 2.3 [HIGH] Presigned URL TTL Too Long (FIXED)

**File**: `backend/app/core/storage.py`, line 62

Original default TTL was 3600 seconds (1 hour). For preview URLs fetched immediately by the frontend, this is unnecessarily long and increases the window for URL leakage attacks.

**Fix**: Changed default TTL from 3600s to 900s (15 minutes). Preview endpoints now use 600s (10 minutes) specifically. Download endpoints stream the file directly (no presigned URL), which is already secure.

---

### 2.4 [MEDIUM] File Upload: Extension-Only Validation (FIXED)

**File**: `backend/app/utils/file_utils.py`

Original validation only checked file extensions against an allowlist. An attacker could upload a malicious binary with a `.pdf` extension.

**Fix**: Added magic bytes (file signature) validation via `validate_file_content()`:
- Known binary types (PDF, PNG, JPG, ZIP, Office documents) are validated against their magic byte signatures.
- Text-based types (txt, md, csv) are checked for binary content (null bytes in first 4KB).
- The validation is enforced in all three upload paths: single upload, chunked upload completion, and version upload.

---

### 2.5 [MEDIUM] XSS via v-html (REPORTED)

**Files**:
- `frontend/src/views/documents/DocumentDetailView.vue` lines 138, 217
- `frontend/src/views/search/SearchResultsView.vue` line 31

Three instances of `v-html` render server-provided content without sanitization:

1. **Line 138**: `v-html="previewHtml"` -- Renders markdown preview content extracted from uploaded documents. A malicious document could contain embedded scripts.
2. **Line 217**: `v-html="row.headline"` -- Renders similar document headlines/matches.
3. **SearchResultsView line 31**: `v-html="item.highlight || item.title"` -- Renders search result highlights.

The preview iframe (line 137) correctly uses `sandbox="allow-same-origin"`, but the standalone v-html directives have no sanitization.

**Recommended fix**: Use DOMPurify or a similar sanitization library on all v-html content, or render via `textContent` where highlighting is not essential.

---

### 2.6 [MEDIUM] Nginx Missing Security Headers (FIXED)

**File**: `frontend/nginx.conf`

The nginx configuration lacked standard security headers.

**Fix**: Added the following headers to all responses:
- `X-Content-Type-Options: nosniff` -- Prevents MIME-type sniffing
- `X-Frame-Options: DENY` -- Prevents clickjacking
- `X-XSS-Protection: 1; mode=block` -- Enables browser XSS filter
- `Referrer-Policy: strict-origin-when-cross-origin` -- Limits referrer leakage
- `X-Download-Options: noopen` -- Prevents IE from opening downloads directly
- `X-Permitted-Cross-Domain-Policies: none` -- Blocks Adobe/Flash cross-domain requests

---

### 2.7 [LOW] Content-Disposition Header Injection (FIXED)

**File**: `backend/app/api/v1/documents.py`, line 690 (original)

The download endpoint used the raw filename in the `Content-Disposition` header:

```python
headers={"Content-Disposition": f'attachment; filename="{doc.original_name}"'}
```

A specially crafted filename containing quotes or newlines could manipulate the response header.

**Fix**: URL-encoded the filename using RFC 5987 `filename*=UTF-8''...` syntax:
```python
safe_filename = urllib.parse.quote(doc.original_name, safe='')
headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}"}
```

---

## 3. Authentication & Authorization Review

### 3.1 JWT Configuration

| Setting | Value | Assessment |
|---------|-------|------------|
| Algorithm | HS256 | Acceptable for current scale |
| Expiry | 480 min (8 hours) | Reasonable |
| Refresh mechanism | None | REPORT: consider refresh token rotation |
| Secret key default | `"change-me-in-production"` | INSECURE: must be overridden in production |

### 3.2 Endpoint Auth Coverage

**Verified**: All API endpoints (except intentionally public ones) require `get_current_user` dependency.

**Intentionally unauthenticated endpoints**:
| Endpoint | Reason |
|----------|--------|
| `POST /api/v1/auth/login` | Login |
| `POST /api/v1/auth/ldap/login` | SSO login |
| `GET /api/v1/auth/sso/cas/authorize` | CAS redirect |
| `GET /api/v1/auth/sso/cas/callback` | CAS callback |
| `GET /api/v1/auth/providers` | Auth method discovery |
| `GET /api/v1/auth/oauth2/authorize` | OAuth2 redirect |
| `GET /api/v1/auth/oauth2/callback` | OAuth2 callback |
| `GET /api/v1/public/dashboard/*` | Public aggregate data |
| `GET /health` | Health check |

All document, matter, task, user, system, AI, search, webhook, and notification endpoints have `Depends(get_current_user)` -- VERIFIED OK.

### 3.3 Admin Endpoint Permissions

System configuration endpoints (`/api/v1/system/*`) correctly require `check_permission(Permission.ADMIN_USER_MANAGE)`. Document lock/set-official endpoints have their respective permission checks.

### 3.4 WebSocket Authentication

**File**: `backend/app/api/v1/ws.py`

The WebSocket endpoint validates JWT tokens on connect:
- Token is required as a query parameter
- Token is decoded and validated
- `payload.sub` must match the `user_id` path parameter
- Connection is closed with code 4001/4003 on failure

Assessment: VALIDATED OK. Consider using `Sec-WebSocket-Protocol` header for token passing in production instead of query params.

---

## 4. Additional Findings

### 4.1 [HIGH] No Rate Limiting (REPORTED)

**No rate limiting was found anywhere in the application.**

This means:
- Login endpoint can be brute-forced
- File upload API can be abused for DoS
- API endpoints can be scraped without restriction

**Recommended**: Add rate limiting middleware (e.g., `slowapi` or custom Redis-based rate limiter) with:
- Stricter limits on `/auth/login` (5 attempts/minute/IP)
- Moderate limits on file uploads (20/minute/user)
- Default limits on all other endpoints (100/minute/user)

### 4.2 [MEDIUM] Subprocess Usage (VERIFIED SAFE)

**Files**: `backend/app/tasks/preview_tasks.py`, `backend/app/tasks/archive_tasks.py`

Both use `subprocess.run()` with list arguments (not `shell=True`). No command injection vector identified. The input filename to LibreOffice is generated server-side via `generate_storage_path()`, not from user input.

### 4.3 [LOW] Public Dashboard Data Exposure

The `/api/v1/public/dashboard/*` endpoints return aggregate task statistics without authentication. While intentionally public, review that no sensitive data (task titles, assignee names) is leaked through these endpoints. Currently, the endpoints return:
- `ActiveTaskItem.title` -- could contain sensitive project names
- `RiskAlertItem.title` -- could contain sensitive issue descriptions

Consider whether these fields should be anonymized for public access.

### 4.4 [LOW] Docker Container Runs as Root

**File**: `backend/Dockerfile`, `frontend/Dockerfile`

Neither Dockerfile specifies a non-root `USER`. The containers run as root by default.

**Recommended**: Add `USER 1000` (or similar) after all COPY/install operations in Dockerfiles.

### 4.5 [LOW] Error Message Information Leakage

Exception handling in the application could reveal internal paths or database details. The `ValidationException`, `NotFoundException`, etc. appear custom but should be audited to ensure `DEBUG=false` does not leak tracebacks.

---

## 5. Summary of Changes

### Files Modified (5)

| File | Change |
|------|--------|
| `backend/app/api/v1/system.py` | Added `_mask_api_key()` -- masks API keys in GET response |
| `backend/app/api/v1/documents.py` | Added magic bytes validation to uploads; fixed Content-Disposition header; reduced preview URL TTL |
| `backend/app/core/storage.py` | Reduced presigned URL default TTL from 3600s to 900s |
| `backend/app/utils/file_utils.py` | Added `MAGIC_SIGNATURES`, `TEXT_EXTENSIONS`, and `validate_file_content()` |
| `frontend/nginx.conf` | Added 6 security headers |

### Files Created (2)

| File | Purpose |
|------|---------|
| `backend/.env.example` | Template documenting all environment variables |
| `reports/04-security.md` | This report |

### No Changes Required (verified secure)

- CORS configuration: uses specific origins, not wildcard
- WebSocket authentication: validates JWT on connect
- SQL injection: SQLAlchemy 2.0 ORM used exclusively
- Command injection: subprocess uses list args (no shell=True)
- Path traversal: `generate_storage_path()` uses Path.stem (basename only)
- TTLs (non-presigned): 24h edit lock, 30-day preview cache -- all reasonable

---

## 6. Action Items for Development Team

| Priority | Item | Effort |
|----------|------|--------|
| P0 | Move docker-compose.yml credentials to `.env` file | Small |
| P0 | Set strong JWT_SECRET_KEY in production `.env` | Small |
| P1 | Add DOMPurify for v-html sanitization in frontend | Medium |
| P1 | Add rate limiting middleware | Medium |
| P2 | Add refresh token mechanism for JWT | Large |
| P2 | Add non-root USER to Dockerfiles | Small |
| P2 | Review public dashboard endpoint data exposure | Small |
| P2 | Ensure DEBUG=false hides tracebacks in production | Small |
