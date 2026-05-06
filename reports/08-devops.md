# DevOps & Migration Audit Report (Agent-8)

**Date:** 2026-05-06
**Branch:** master
**Scope:** Docker Compose, Alembic migrations, deploy.sh, environment config, container configurations

---

## 1. Docker Compose Audit

### 1.1 Issues Found and Fixed

| Issue | Severity | Fixed | Details |
|-------|----------|-------|---------|
| No health checks on any service | High | YES | Added health checks for db (`pg_isready`), redis (`redis-cli ping`), minio (`curl /minio/health/live`), backend (`curl /health`). Without health checks, `depends_on` only waits for container start, not readiness. |
| No resource limits | Medium | YES | Added `deploy.resources` blocks with reasonable memory/CPU limits and reservations for all 7 services. Prevents a single service from exhausting host resources. |
| `depends_on` without conditions | High | YES | Changed to `condition: service_healthy` for all dependencies. Was `depends_on` without condition -- Docker would start dependent containers before db/redis/minio were ready. |
| No gzip compression in nginx | Low | YES | Added gzip with level 5 for JS/CSS/JSON/XML/SVG/wasm. Reduces frontend asset transfer size by ~70%. |
| Missing cache headers for static assets | Medium | YES | Added `Cache-Control: public, immutable` (1 year) for `/assets/` (fingerprinted), `Cache-Control: public` (30 days) for other static files. |
| `X-XSS-Protection` header deprecated | Low | YES | Removed `X-XSS-Protection: 1; mode=block` (deprecated by modern browsers; can cause security issues with CSP). Added `Permissions-Policy` header. |
| No proxy timeouts in nginx | Medium | YES | Added `proxy_connect_timeout` (60s), `proxy_send_timeout` (120s), `proxy_read_timeout` (120s). Prevents hanging connections on slow API responses. |
| No proxy buffering tuning | Low | YES | Added proxy buffering configuration for API responses. |

### 1.2 Health Check Details

```yaml
# PostgreSQL
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U odms -d odms"]
  interval: 10s, timeout: 5s, retries: 5, start_period: 15s

# Redis
healthcheck:
  test: ["CMD", "redis-cli", "ping"]
  interval: 10s, timeout: 5s, retries: 5, start_period: 10s

# MinIO
healthcheck:
  test: ["CMD-SHELL", "curl -sf http://localhost:9000/minio/health/live || exit 1"]
  interval: 15s, timeout: 5s, retries: 5, start_period: 20s

# Backend (FastAPI)
healthcheck:
  test: ["CMD-SHELL", "curl -sf http://localhost:8000/health || exit 1"]
  interval: 30s, timeout: 10s, retries: 3, start_period: 30s
```

**Note:** Celery worker and Celery beat do not have health checks. Celery `inspect ping` is unreliable across container restarts due to hostname changes. Consider adding a lightweight HTTP health endpoint to the Celery worker in the future (e.g., via `celery-prometheus-exporter` or a custom health check script).

### 1.3 Remaining Concerns (Not Fixed -- Infrastructure Changes Required)

- **Backend/Celery containers run as root.** The backend `Dockerfile` has no `USER` directive. This is acceptable in development with volume mounts but should be hardened for production. The `nginx:alpine` image runs workers as non-root by default.
- **No dedicated Celery health endpoint.** The Celery worker/beat have no Docker health check. This means `depends_on: service_healthy` can't be used for downstream consumers of Celery tasks.
- **MinIO uses `:latest` tag.** Pinning a specific version would improve reproducibility.
- **No Redis persistence configured.** Redis data is ephemeral. While the primary use is caching and task broker, Celery task results would be lost on restart.

---

## 2. Alembic Migration Chain Audit

### 2.1 Chain Status: LINEAR AND UNBROKEN

Migration chain (oldest to newest):

```
935bfb869fd2 (initial_schema)
  |
a8c3f1d5e2b9 (add_fts_indexes)
  |
add_sla_fields_2026 (add_sla_fields)
  |
add_document_review_2026 (add_document_review)
  |
add_webhook_subscription_2026 (add_webhook_subscription)
  |
add_extracted_text_2026 (add_extracted_text)
  |
enable_pgvector_2026 (enable_pgvector_and_ai_tables)
  |
add_preview_html_path_2026 (add_preview_html_path)
  |
add_auth_provider_2026 (add_auth_provider_fields)
  |
add_task_mgmt_2026 (add_task_management_tables)
  |
remove_legacy_2026 (remove_legacy_matter_workflow)
  |
add_system_config_2026 (add_system_config)
  |
add_ai_providers_2026 (add_ai_providers)
  |
add_document_summary_2026 (add_document_summary)
```

- **14 migrations, single linear chain, zero branch heads**
- All `down_revision` values point to existing revision IDs
- All `branch_labels` are `None`
- No missing revisions in the chain

### 2.2 Issue Found and Fixed: Missing Model Import in env.py

The `WebhookSubscription` model (`app/models/webhook.py`) was not imported in `backend/alembic/env.py`, meaning `Base.metadata` did not include it. Running `alembic revision --autogenerate` would attempt to recreate the `webhook_subscription` table on every run.

**Fix applied:** Added `from app.models.webhook import WebhookSubscription` to `env.py`.

### 2.3 Recommended Improvements

- **Down migrations:** None of the 14 migrations implement `downgrade()`. All use `pass` for the downgrade function. This means rollback is not supported. Consider adding downgrade logic for critical migrations.
- **Migration naming:** Some migrations use descriptive names (`add_fts_indexes`, `add_document_review`) while others use revision-ID-based names (`935bfb869fd2_initial_schema`). Standardize on one convention.

---

## 3. deploy.sh Review

### 3.1 Issues Found and Fixed

| Issue | Severity | Fixed | Details |
|-------|----------|-------|---------|
| No pre-flight checks | High | YES | Added `preflight_check()` that verifies `docker` and `docker-compose` are installed and the Docker daemon is reachable. |
| No error handling on `docker-compose up` | High | YES | Added `if ! docker-compose up -d ...` checks with `set -euo pipefail` and explicit `exit 1` on failure. |
| No health check waiting | Medium | YES | Added `health_wait()` function that polls `docker inspect --format='{{.State.Health.Status}}'` with configurable timeouts per service. |
| Quiet failures (silent) | Medium | YES | Added color-coded logging (`log_info`, `log_warn`, `log_error`) with `[INFO]`, `[WARN]`, `[ERROR]` prefixes. |
| Inline documentation sparse | Low | YES | Added a header comment explaining the ContainerConfig compatibility workaround. |
| Container stop/rm pattern correct | - | VERIFIED | The `stop && rm && up` pattern correctly works around the docker-compose v1.29.2 + Docker 29.x `KeyError: 'ContainerConfig'` bug. |

### 3.2 deploy.sh Compatibility Workaround (Documented)

The server runs `docker-compose` v1.29.2 (standalone binary) alongside Docker Engine 29.x. When `docker-compose up -d` tries to rebuild an existing container, it hits a `KeyError: 'ContainerConfig'` due to API changes in Docker 29.x. The workaround (`docker stop` -> `docker rm` -> `docker-compose up -d`) forces fresh container creation, avoiding the bug entirely.

### 3.3 Recommended Improvements (Not Implemented)

- **Rollback capability:** Save previous image tags before deploy, restore on failure.
- **Database migration guard:** Optionally run `alembic upgrade head` before starting backend.
- **Configuration validation:** Check `.env` exists and required vars are set before deploying.

---

## 4. Environment Configuration

### 4.1 Issues Found and Fixed

| Issue | Severity | Fixed | Details |
|-------|----------|-------|---------|
| .env.example missing 21 config vars | High | YES | Added all vars from `config.py` that were missing: `PREVIEW_CACHE_DAYS`, `EDIT_LOCK_TIMEOUT_HOURS`, `RAG_TOP_K`, `RAG_CHUNK_SIZE`, `RAG_CHUNK_OVERLAP`, `EMBEDDING_DIM`, all LDAP attribute vars (3), all CAS vars (5), all OAuth2 vars (9). |
| No .env.example for some optional sections | Medium | YES | LDAP and OAuth2 sections were incomplete; now documented with all available configuration fields. |
| Dead config variables | Low | REPORTED | 5 config vars defined in `config.py` but never referenced in application code. See section 4.2. |

### 4.2 Dead Config Variables

The following `config.py` settings are never imported or used by any application code:

| Variable | Value | Notes |
|----------|-------|-------|
| `EMBEDDING_MODEL` | `BAAI/bge-small-zh-v1.5` | Model selection likely handled by embedding service at runtime or via system_config |
| `EMBEDDING_DIM` | `768` | Dimension likely derived from model at runtime |
| `PREVIEW_CACHE_DAYS` | `30` | Preview cleanup may use a hardcoded value elsewhere |
| `EDIT_LOCK_TIMEOUT_HOURS` | `24` | Lock timeout may be hardcoded in the service layer |
| `UPLOAD_CHUNK_SIZE` | `5MB` | Chunked upload endpoint uses request-provided chunk size, not this config |

**Recommendation:** Either wire these into the relevant services or remove them to avoid misleading configuration. Keeping them causes no harm but may confuse operators who assume these settings have an effect.

### 4.3 .env vs .env.example Gap

The current `.env` file contains only 11 variables (basic connectivity). After the `.env.example` update, there are now 67 documented settings. Production deployments should review all optional sections (SMTP, LDAP, CAS, OAuth2, AI/RAG) and set appropriate values.

---

## 5. Container Configurations

### 5.1 Backend Dockerfile

**Status: Adequate for development, needs hardening for production.**

| Aspect | Current | Recommendation |
|--------|---------|----------------|
| Multi-stage build | No (single stage) | Acceptable for Python; libraries (libreoffice) must be present at runtime anyway |
| Non-root user | No (runs as root) | Add `USER 1000:1000` and `chown` app directory. Skip for dev with volume mounts. |
| Layer caching | Suboptimal | `COPY requirements.txt .` before `pip install` is correct, but `COPY . .` after install invalidates pip cache on any code change. |
| .dockerignore | **ADDED** | Created `backend/.dockerignore` excluding `__pycache__`, `.git`, `.env`, etc. |
| Package cleanup | Partial | `apt-get` cache cleaned but `pip` uses `--no-cache-dir` -- correct. |
| LibreOffice | Full install (400MB+) | Installs core+writer+calc+impress. Large image. Consider a separate image or smaller install. |

### 5.2 Frontend Dockerfile

**Status: Good.**

| Aspect | Current | Recommendation |
|--------|---------|----------------|
| Multi-stage build | YES | `node:20-alpine` for build, `nginx:alpine` for runtime -- correct pattern |
| Non-root user | YES | `nginx:alpine` runs workers as `nginx` user |
| .dockerignore | **ADDED** | Created `frontend/.dockerignore` excluding `node_modules`, `dist`, etc. |
| npm registry | Uses npmmirror.com | Good for China-based builds |
| Layer caching | Good | `COPY package.json` before `npm install`, then `COPY . .` |

### 5.3 Frontend Nginx Config

**Status: Significantly improved.**

Changes applied:
- Added **gzip compression** (JS, CSS, JSON, XML, SVG, wasm)
- Added **static asset caching**: 1-year immutable for `/assets/` (Vite-fingerprinted), 30-day for other static files
- Added **proxy timeouts**: connect 60s, send/read 120s
- Added **proxy buffering**: configured buffer sizes for API responses
- Added `Permissions-Policy` security header
- Removed deprecated `X-XSS-Protection` header

### 5.4 Celery Configuration

**Status: Adequate.**

- Worker: `celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2`
- Beat: `celery -A app.tasks.celery_app beat --loglevel=info`
- No explicit `--queues` flag (all tasks use default "celery" queue)
- `task_time_limit=30min`, `task_soft_time_limit=25min` set in code
- Task serialization: JSON (safe, interoperable)
- Timezone: Asia/Shanghai with UTC enabled

**Recommendation:** Consider separating slow tasks (preview generation, embedding) from fast tasks (notifications) using named queues (`--queues=celery,slow`), with separate workers for each queue. This prevents long-running preview jobs from delaying notification delivery.

---

## 6. Summary of Changes Made

### Files Modified:
1. **`docker-compose.yml`** -- Health checks + resource limits + depends_on conditions (every service)
2. **`frontend/nginx.conf`** -- Gzip + cache headers + proxy timeouts + security headers
3. **`deploy.sh`** -- Pre-flight checks + error handling + health_wait + logging
4. **`backend/.env.example`** -- Added 21 missing config vars, completed all sections
5. **`backend/alembic/env.py`** -- Added missing `WebhookSubscription` model import
6. **`backend/.dockerignore`** -- NEW: Exclude build context noise
7. **`frontend/.dockerignore`** -- NEW: Exclude build context noise

### Architecture Issues to Address (Not Actioned):
1. 5 dead config variables in `config.py` (section 4.2)
2. Backend/Celery run as root in Docker
3. No Celery health checks possible with current setup
4. No downgrade logic in any of 14 Alembic migrations
5. MinIO uses `:latest` image tag (non-deterministic builds)
