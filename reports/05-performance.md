# 05 - Performance & Database Analysis

Date: 2026-05-06 | Agent: Agent-5 (Performance & DB Analyzer)

---

## 1. N+1 Query Detection

### 1.1 FIXED: tasks.py list_tasks -- N+1 template/creator name lookups

**File:** `backend/app/api/v1/tasks.py`

**Problem:** The `list_tasks` endpoint called `_task_to_out()` in a loop, which made 2 separate DB queries per task -- one for `TaskTemplate.name`, one for `User.real_name`. With 20 tasks per page, that was 40 extra queries.

**Fix:** Added `_build_task_out_batch()` helper that collects all `template_id` and `creator_id` values, performs two batch queries (`WHERE id IN (...)`), then builds the output dicts. The per-item `_task_to_out()` now delegates to the batch helper.

```python
# Before (N+1): 1 + 2*N queries
for t in tasks:
    items.append(await _task_to_out(t, db))  # 2 queries each

# After (batch): 1 + 2 queries total
items = await _build_task_out_batch(list(tasks), db)
```

### 1.2 FIXED: rag_service.py -- N+1 per-chunk document name lookups

**File:** `backend/app/services/rag_service.py`

**Problem:** `ask()` and `ask_stream()` called `_get_doc_name()` for each chunk individually -- once for the vector context and again for the sources list. With K=5 chunks, that was 10+ queries. Many chunks share the same `document_id`.

**Fix:** Added `_get_doc_names_batch()` method that takes a list of doc IDs and returns a `dict[int, str]` in a single query. Both `ask()` and `ask_stream()` now batch-load all document names upfront and reuse the dict.

```python
# Before: N queries for M chunks (some duplicate doc IDs)
for c in chunks:
    doc_name = await self._get_doc_name(db, c["document_id"])  # N queries

# After: 1 query for all unique doc IDs
doc_ids = [c["document_id"] for c in chunks]
doc_names = await self._get_doc_names_batch(db, doc_ids)  # 1 query
```

### 1.3 FIXED: task_management_service.py get_board -- N+1 slot versions

**File:** `backend/app/services/task_management_service.py`

**Problem:** `get_board()` called `get_slot_versions()` for each slot individually. A task with 6 stages and 4 slots each would make 24 extra queries.

**Fix:** Added `_get_slot_versions_batch()` that queries all slot versions for the task in one `WHERE slot_id IN (...)` query. `get_board()` now uses this batch method.

### 1.4 Already Correct -- Good Patterns

The following services already use `selectinload()` correctly:
- `document_service.py`: `selectinload` for owner, category, tags, current_version, versions, edit_lock, reviews
- `user_service.py`: `selectinload` for roles, department
- `task_management_service.py`: nested `selectinload` for template->stages->slots
- `audit_service.py`: `selectinload` for user
- `document_review_service.py`: `selectinload` for reviewer, document->owner

---

## 2. Missing Indexes

### 2.1 High-Priority Missing Indexes (DDL Below)

These columns are queried frequently but lack explicit indexes:

**document table:**
| Column | Query Pattern | Impact |
|--------|-------------|--------|
| `is_deleted` | Filtered in EVERY query | High - every list/read query |
| `status` | Filtered/sorted frequently | High |
| `owner_id` | FK, filtered in access checks | Medium |
| `category_id` | FK, filtered in list | Medium |
| `created_at` | Sorted DESC in list queries | Medium |

**document_version table:**
| Column | Query Pattern | Impact |
|--------|-------------|--------|
| `document_id` | FK, filtered/joined always | High |
| `is_official` | Filtered (set_official) | Low |

**document_edit_lock table:**
| Column | Query Pattern | Impact |
|--------|-------------|--------|
| `document_id` | FK, checked on every lock/unlock | High |
| `expires_at` | Filtered for active locks | Medium |

**document_review table:**
| Column | Query Pattern | Impact |
|--------|-------------|--------|
| `status` | Filtered for 'pending' | Medium |

**user table:**
| Column | Query Pattern | Impact |
|--------|-------------|--------|
| `department_id` | FK, filtered in user list | Medium |
| `status` | Filtered (active users) | Medium |

**department table:**
| Column | Query Pattern | Impact |
|--------|-------------|--------|
| `parent_id` | Self-referencing FK, tree building | Medium |

**task_instance (ProjectTask) table:**
| Column | Query Pattern | Impact |
|--------|-------------|--------|
| `template_id` | FK, joined in list | Medium |
| `creator_id` | FK, filtered in access checks | Medium |
| `status` | Filtered frequently | Medium |
| `created_at` | Sorted DESC in list | Medium |

**task_stage (ProjectStage) table:**
| Column | Query Pattern | Impact |
|--------|-------------|--------|
| `task_id` | FK, filtered/joined always | High |
| `status` | Filtered for active/overdue | Medium |

**task_slot (ProjectSlot) table:**
| Column | Query Pattern | Impact |
|--------|-------------|--------|
| `stage_id` | FK, filtered/joined always | High |
| `status` | Filtered for pending/filled/waived | Medium |
| `document_id` | FK | Medium |

**webhook_subscription table:**
| Column | Query Pattern | Impact |
|--------|-------------|--------|
| `is_active` | Filtered in dispatcher | Medium |

**slot_version table:**
| Column | Query Pattern | Impact |
|--------|-------------|--------|
| `slot_id` | FK, filtered always | High |

### 2.2 Recommended CREATE INDEX DDL

```sql
-- ============================================================
-- document table (highest priority)
-- ============================================================
CREATE INDEX CONCURRENTLY idx_document_is_deleted ON document (is_deleted);
CREATE INDEX CONCURRENTLY idx_document_status ON document (status);
CREATE INDEX CONCURRENTLY idx_document_owner_id ON document (owner_id);
CREATE INDEX CONCURRENTLY idx_document_category_id ON document (category_id);
CREATE INDEX CONCURRENTLY idx_document_created_at ON document (created_at DESC);

-- ============================================================
-- document_version table
-- ============================================================
CREATE INDEX CONCURRENTLY idx_doc_version_doc_id ON document_version (document_id);

-- ============================================================
-- document_edit_lock table
-- ============================================================
CREATE INDEX CONCURRENTLY idx_edit_lock_doc_id ON document_edit_lock (document_id);
CREATE INDEX CONCURRENTLY idx_edit_lock_expires ON document_edit_lock (expires_at)
    WHERE expires_at > NOW();  -- partial index for active locks

-- ============================================================
-- document_review table
-- ============================================================
CREATE INDEX CONCURRENTLY idx_doc_review_status ON document_review (status)
    WHERE status = 'pending';  -- partial index

-- ============================================================
-- user table
-- ============================================================
CREATE INDEX CONCURRENTLY idx_user_department_id ON "user" (department_id);
CREATE INDEX CONCURRENTLY idx_user_status ON "user" (status);

-- ============================================================
-- department table
-- ============================================================
CREATE INDEX CONCURRENTLY idx_department_parent_id ON department (parent_id);

-- ============================================================
-- task_instance (ProjectTask) table
-- ============================================================
CREATE INDEX CONCURRENTLY idx_task_inst_template_id ON task_instance (template_id);
CREATE INDEX CONCURRENTLY idx_task_inst_creator_id ON task_instance (creator_id);
CREATE INDEX CONCURRENTLY idx_task_inst_status ON task_instance (status);
CREATE INDEX CONCURRENTLY idx_task_inst_created_at ON task_instance (created_at DESC);

-- ============================================================
-- task_stage (ProjectStage) table
-- ============================================================
CREATE INDEX CONCURRENTLY idx_task_stage_task_id ON task_stage (task_id);
CREATE INDEX CONCURRENTLY idx_task_stage_status ON task_stage (status);

-- ============================================================
-- task_slot (ProjectSlot) table
-- ============================================================
CREATE INDEX CONCURRENTLY idx_task_slot_stage_id ON task_slot (stage_id);
CREATE INDEX CONCURRENTLY idx_task_slot_status ON task_slot (status);
CREATE INDEX CONCURRENTLY idx_task_slot_doc_id ON task_slot (document_id);

-- ============================================================
-- slot_version table
-- ============================================================
CREATE INDEX CONCURRENTLY idx_slot_version_slot_id ON slot_version (slot_id);

-- ============================================================
-- webhook_subscription table
-- ============================================================
CREATE INDEX CONCURRENTLY idx_webhook_is_active ON webhook_subscription (is_active)
    WHERE is_active = true;
```

**NOTE:** Use `CREATE INDEX CONCURRENTLY` to avoid locking tables in production. Run these during low-traffic periods.

### 2.3 Existing Indexes (Verified in Migrations)

| Table | Index | Type |
|-------|-------|------|
| user | `ix_user_username` (UNIQUE) | B-tree |
| role | `ix_role_role_code` (UNIQUE) | B-tree |
| document | `idx_document_search` | GIN (tsvector FTS) |
| document | `idx_document_embedding` | IVFFlat (vector) |
| document_chunk | `idx_document_chunk_doc_id` | B-tree |
| document_chunk | `idx_document_chunk_embedding` | IVFFlat (vector) |
| document_chunk | `uq_doc_chunk_idx` | UNIQUE (doc_id, chunk_index) |
| document_review | `idx_document_review_doc` | B-tree |
| document_review | `idx_document_review_reviewer` | B-tree |
| notification | `idx_notification_user_read` | B-tree (user_id, is_read) |
| operation_log | `idx_oplog_user_time` | B-tree (user_id, created_at) |
| webhook_subscription | `idx_webhook_user` | B-tree (user_id) |
| ai_conversation | `idx_ai_conversation_user_id` | B-tree |
| ai_message | `idx_ai_message_conv_id` | B-tree |

### 2.4 Vector Index Maintenance

Both `document.embedding` and `document_chunk.embedding` have IVFFlat indexes with 100 lists. IVFFlat requires periodic maintenance for optimal recall:

```sql
-- Rebuild IVFFlat indexes periodically (e.g., weekly or after bulk inserts)
-- IVFFlat needs data loaded before index creation; reindexing after significant
-- data changes improves recall at the cost of build time.
REINDEX INDEX idx_document_embedding;
REINDEX INDEX idx_document_chunk_embedding;
```

Consider switching to HNSW for better query performance at scale (PostgreSQL 15+ with pgvector 0.5+ supports it).

---

## 3. Redis Caching

### 3.1 What IS Cached

| Cache Key | TTL | Data | Invalidation |
|-----------|-----|------|-------------|
| `users:roles` | 600s | Role list | On create/update/delete |
| `users:departments` | 600s | Department list | On create/update/delete |
| `users:departments_tree` | 600s | Department tree | On create/update/delete |
| `users:document_categories` | 600s | Categories (admin) | On create/update/delete |
| `users:tags` | 600s | Tags (admin) | On create/update/delete |
| `matter:{id}` | 60s | Matter detail | On update/delete |

### 3.2 FIXED: Added Caching for Document API Routes

**File:** `backend/app/api/v1/documents.py`

The `/documents/categories` and `/documents/tags` endpoints lacked caching entirely, while the same data was cached when accessed via the users admin module. Added Redis caching with 600s TTL and proper invalidation on create/update/delete operations.

New cache keys:
- `documents:categories` -- TTL 600s
- `documents:tags` -- TTL 600s

### 3.3 Cache TTL Assessment

| TTL | Data | Assessment |
|-----|------|-----------|
| 600s (10 min) | Roles, departments, categories, tags | Reasonable -- these change rarely |
| 60s (1 min) | Matter detail | Reasonable -- balance freshness vs hit rate |
| 300s (default) | Cache.set() default | Reasonable default |

**No issues found.** TTLs are well-chosen for the data types.

### 3.4 What Could Still Be Cached

- **Dashboard overview stats** (`/dashboard/overview`): Currently executes 8 separate COUNT queries on every request. Cache with 60s TTL would dramatically reduce DB load.
- **AI provider list** (`/ai/providers`): Small, rarely-changing data. Could cache with 600s TTL.

---

## 4. Pagination Coverage

### 4.1 Paginated Endpoints (Good)

| Endpoint | Pagination |
|----------|-----------|
| GET /api/v1/documents/ | page, page_size |
| GET /api/v1/users/ | page, page_size |
| GET /api/v1/notifications/ | page, page_size |
| GET /api/v1/audit-logs/ | page, page_size |
| GET /api/v1/webhooks/ | page, page_size |
| GET /api/v1/tasks (tasks.py) | page, page_size |

### 4.2 FIXED: Added Pagination

| Endpoint | Before | After |
|----------|--------|-------|
| GET /api/v1/task-templates | Returns ALL templates | page, page_size with count |
| GET /api/v1/task-instances | Returns ALL task instances | page, page_size with count |

**Files changed:**
- `backend/app/services/task_management_service.py`: `list_templates()` and `list_tasks()` now accept optional `PaginationParams` and return `(items, total)` tuples.
- `backend/app/api/v1/task_templates.py`: Added `page`/`page_size` query params.
- `backend/app/api/v1/task_instances.py`: Added `page`/`page_size` query params.

### 4.3 Endpoints Without Pagination (Acceptable)

| Endpoint | Reason |
|----------|--------|
| GET /documents/categories | Small reference data (usually < 50) |
| GET /documents/tags | Small reference data (usually < 100) |
| GET /users/roles | Small (usually < 20) |
| GET /users/departments | Small (usually < 100) |
| GET /ai/conversations | Hardcoded LIMIT 50 |
| GET /dashboard/* | Aggregated stats |
| GET /system/ai-providers | Small (usually < 10) |

### 4.4 Queries Without LIMIT (Potential Risk)

| Location | Query | Risk |
|----------|-------|------|
| `export_tasks_excel` | SELECT all tasks | Could memory-bloat with many tasks |
| `export_documents_excel` | page_size=10000 | OK for moderate volumes |
| `_get_library_summary` | SELECT all non-deleted docs | Lists every doc name to AI context -- could be thousands |

**Recommendation:** Add a configurable cap (e.g., 200) to `_get_library_summary()` in `rag_service.py`.

---

## 5. Connection Pooling

### 5.1 Database Connection Pool

**File:** `backend/app/dependencies.py`

```python
engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```

**Issues:**
- No explicit `pool_size`, `max_overflow`, or `pool_recycle` configured.
- SQLAlchemy async defaults: `pool_size=5`, `max_overflow=10` (max 15 concurrent connections).
- No `pool_pre_ping` configured -- can cause stale connection errors after PostgreSQL restarts or network blips.

**Configuration:** The database URL is configured in `docker-compose.yml` and `.env` without any pool-related query parameters.

### 5.2 Redis Connection Pool

**File:** `backend/app/core/cache.py`

```python
class Cache:
    async def connect(self):
        if self.redis is None:
            self.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
```

- Uses default redis-py async connection pool (no explicit `max_connections`).
- No connection timeout or retry-on-timeout configured.

### 5.3 Recommended Configuration

**For database pool** -- add to `create_async_engine()` in `dependencies.py`:

```python
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=20,            # Increase from default 5 for production
    max_overflow=10,         # Allow 10 overflow connections
    pool_recycle=3600,       # Recycle connections after 1 hour
    pool_pre_ping=True,      # Verify connections before use
    pool_timeout=30,         # Wait up to 30s for a connection
)
```

**For Redis pool** -- add to `aioredis.from_url()` in `cache.py`:

```python
self.redis = aioredis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=20,
    socket_keepalive=True,
    socket_connect_timeout=5,
    retry_on_timeout=True,
)
```

---

## 6. Summary of Changes Made

### Files Modified

| File | Change | Issue |
|------|--------|-------|
| `backend/app/api/v1/tasks.py` | Added `_build_task_out_batch()` for batch template/creator name lookups | N+1 queries |
| `backend/app/services/rag_service.py` | Added `_get_doc_names_batch()` to replace per-chunk name lookups | N+1 queries |
| `backend/app/services/task_management_service.py` | Added `_get_slot_versions_batch()` for board view | N+1 queries |
| `backend/app/services/task_management_service.py` | Added pagination support to `list_templates()` and `list_tasks()` | Missing pagination |
| `backend/app/api/v1/task_templates.py` | Added `page`/`page_size` query params | Missing pagination |
| `backend/app/api/v1/task_instances.py` | Added `page`/`page_size` query params | Missing pagination |
| `backend/app/api/v1/documents.py` | Added Redis caching for `/categories` and `/tags` routes | Missing caching |

### Report Only (Index DDL, Pool Config)

- 20+ recommended `CREATE INDEX CONCURRENTLY` statements
- Database connection pool size increase from default 5 to 20
- Redis connection pool configuration
- `pool_pre_ping=True` recommendation
- IVFFlat reindex reminder
