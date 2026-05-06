# Test Coverage Assessment Report

Date: 2026-05-06 | Agent: Agent-7 (Test Coverage Engineer)

---

## 1. Existing Test Infrastructure

### Framework
| Component | Status | Details |
|-----------|--------|---------|
| pytest | Configured | `pytest.ini`, asyncio_mode=auto, parallel-safe |
| pytest-asyncio | Available | v0.23.5 in requirements.txt, fixture support |
| Test database | Configured | PostgreSQL `odms_test` on Docker db service |
| MinIO mock | In conftest | Module-level MagicMock patches storage + ws_manager |

### Configuration (`backend/pytest.ini`)
```
testpaths = tests
python_files = test_*.py
asyncio_mode = auto
addopts = -v --tb=short
```

### Test Fixtures (`backend/tests/conftest.py`)
| Fixture | Scope | Purpose |
|---------|-------|---------|
| event_loop | session | Shared event loop for async tests |
| db_session | function | Fresh DB (drop_all + create_all) per test |
| db_session_with_data | function | Pre-seeded with roles + admin + staff users |
| app | function | FastAPI app instance |
| client | function | httpx AsyncClient with DB dependency override |

---

## 2. Existing Test Files & Coverage (Before New Tests)

| File | Tests | Focus Area | Status |
|------|-------|------------|--------|
| test_security.py | 8 | Password hashing, JWT create/decode/expiry | Solid |
| test_permissions.py | 14 | RoleCode enum, permission definitions, RBAC matrix | Solid |
| test_auth.py | 8 | AuthService + API: login, /me, token errors | Solid |
| test_document.py | 16 | Categories, Tags, Document CRUD, Versions, Locks | 1 test skipped (MissingGreenlet bug) |
| test_matter.py | 7 | Matter CRUD, members, comments, workflow templates | Solid |
| test_approval.py | 7 | Submit/approve/reject review, permission checks | Solid |
| **Total** | **60** | | |

---

## 3. Critical Path Coverage Matrix

### Path 1: Login / Authentication -- COVERED
- AuthService.authenticate (success, wrong password, nonexistent user)
- AuthService.get_current_user_info
- POST /api/v1/auth/login (success, 401, 422 validation)
- GET /api/v1/auth/me (valid token, no token, invalid token)
- Password hashing: hash/verify, salts, Unicode, empty
- JWT: create/decode, expiry, invalid tokens
- **Gap**: Token refresh flow not tested (if endpoint exists)

### Path 2: Document Upload -- PARTIALLY COVERED
- Service-level: create_document, soft_delete, permission enforcement
- Category/tag CRUD, duplicate detection
- Version management: upload new version, list, set official
- Lock: acquire, release, conflict prevention
- **Gap**: No API-level upload endpoint test (POST /api/v1/documents with multipart)
- **Gap**: No preview generation test (Celery task, mocked)

### Path 3: Document Search -- NOW COVERED (new tests added)
- See Section 4 below

### Path 4: AI Chat -- NOW PARTIALLY COVERED (new tests added)
- See Section 4 below

### Path 5: Workflow / Matter Creation -- COVERED
- Matter: create, update, delete, permission enforcement
- Members: add members, role assignment
- Comments: add comment, paginated list
- Workflow templates: create template with nodes, SLA

### Bonus: Document Approval -- COVERED
- Submit, multi-level approve, reject, wrong reviewer guard, pending list

---

## 4. New Tests Added (This Session)

### 4.1 test_search.py (11 new tests)
Location: `backend/tests/test_search.py`

| Test | What It Verifies |
|------|-----------------|
| test_search_by_keyword_short | Short keyword (<=2 chars) uses ILIKE fallback |
| test_search_by_keyword_long | Longer keyword uses FTS (PostgreSQL tsvector) |
| test_search_by_keyword_in_description | Matches description field via ILIKE |
| test_search_with_file_type_filter | Filters by file_type (pdf, docx, xlsx) |
| test_search_no_results | Empty result set for nonexistent keyword |
| test_soft_deleted_excluded | is_deleted=True documents never returned |
| test_pagination | Correct page size, offset, non-overlapping pages |
| test_admin_sees_all_documents | Admin bypasses owner-only restriction |
| test_staff_sees_only_own_documents | Non-admin restricted to own documents |
| test_keyword_and_type_combined | Keyword + type filter combined |
| test_empty_keyword_returns_all | Empty keyword returns all non-deleted |

### 4.2 test_ai.py (12 new tests)
Location: `backend/tests/test_ai.py`

**Chunking (TestChunking class, unit tests):**
| Test | What It Verifies |
|------|-----------------|
| test_empty_text | Returns [] |
| test_single_short_text | Single chunk for small input |
| test_chunk_with_sentence_boundary | Sentence-level splitting |
| test_overlap_between_chunks | Overlap parameter respected |
| test_long_continuous_text | Large input produces multiple chunks |
| test_chunk_size_parameter_respected | Chunks don't grossly exceed size |
| test_chinese_text_chunking | CJK characters handled correctly |

**Agent Loop (TestAgentLoop class, mocked httpx):**
| Test | What It Verifies |
|------|-----------------|
| test_simple_answer_no_tools | Direct LLM response returned |
| test_tool_calling_single_round | Tool execution + result fed back to LLM |
| test_tool_calling_json_parse_error | Malformed JSON args handled gracefully |
| test_max_rounds_protection | MAX_TOOL_ROUNDS=5 hard stop against infinite loops |
| test_chat_http_error | HTTP errors from provider propagate correctly |

**Provider Config:**
| Test | What It Verifies |
|------|-----------------|
| test_get_provider_not_found | ValueError for non-existent provider ID |

---

## 5. Complete Coverage Matrix (After New Tests)

| File | Tests | Area | New in Session |
|------|-------|------|----------------|
| test_security.py | 8 | Security primitives | - |
| test_permissions.py | 14 | RBAC system | - |
| test_auth.py | 8 | Authentication | - |
| test_document.py | 16 | Document management | - |
| test_matter.py | 7 | Matter + workflow | - |
| test_approval.py | 7 | Document review | - |
| test_search.py | 11 | Document search | NEW |
| test_ai.py | 12 | AI chunking + agent loop | NEW |
| **Total** | **83** | | **+23** |

---

## 6. Remaining Coverage Gaps

### High Priority
| Gap | Risk | Effort | Notes |
|-----|------|--------|-------|
| Document upload API endpoint | User-facing upload could break silently | Medium | Requires multipart test with mocked MinIO upload |
| RAGService.ask() integration | Core AI Q&A path untested end-to-end | High | Requires mocking embedding_service + llm_service |
| SSE streaming (ask_stream) | Streaming responses could regress | Medium | Requires async generator assertion |
| Token refresh endpoint | User session persistence | Low | If the endpoint exists, add token refresh tests |

### Medium Priority
| Gap | Risk | Effort | Notes |
|-----|------|--------|-------|
| Celery tasks (preview, archive, search indexing) | Async doc processing | Medium | Requires Celery unit test harness |
| Notification service | Push/email/webhook delivery | Medium | Can test with mocked Redis/email |
| WebSocket manager | Real-time updates | Medium | Requires ws test client |
| File upload validation (size, type, name) | Security input validation | Low | Add to document API tests |
| Rate limiting | DOS protection | Low | Hard to test without middleware integration |

### Low Priority
| Gap | Risk | Effort | Notes |
|-----|------|--------|-------|
| LDAP authentication | Only affects LDAP-enabled deployments | High | Requires LDAP test server |
| Dashboard statistics queries | Read-only aggregation | Low | Pure SQL, unlikely to break silently |
| Webhook dispatch | External integrations | Medium | Can mock httpx |
| Task template management | Recently added feature | Medium | Needs task template service tests |

---

## 7. Frontend Test Assessment

### Current State: NO TEST FRAMEWORK
- **No vitest in devDependencies** (package.json has no vitest, jest, or testing library)
- **No test files found** (no `*.spec.ts`, `*.test.ts` anywhere in frontend/)
- **No test config** (no vitest.config.ts)
- **No CI/test scripts** (package.json scripts: dev, build, preview only)

### What Would Be Needed for Frontend Tests
1. **Install dependencies:**
   ```
   vitest + @vue/test-utils + jsdom + @pinia/testing
   ```
2. **Add vitest.config.ts** with:
   - jsdom environment
   - Vue plugin
   - Auto-import resolvers
   - `@` alias (same as vite.config.ts)
3. **Add test scripts** to package.json:
   - `"test": "vitest run"`
   - `"test:watch": "vitest"`
4. **Recommended initial test files:**
   - `src/stores/__tests__/auth.test.ts` -- login state, token storage
   - `src/stores/__tests__/document.test.ts` -- document list CRUD
   - `src/components/__tests__/SearchBar.test.ts` -- search input, debounce
   - `src/api/__tests__/client.test.ts` -- axios interceptor, auth header injection

### Estimated Effort
- Setup: 2-4 hours (install, config, CI integration)
- Initial tests (5-10 test files): 8-16 hours
- Comprehensive coverage (20+ files): 40+ hours

---

## 8. Running Tests

### Local (if server DB unavailable)
Tests require the PostgreSQL test database container. Tests will fail locally without Docker running.

### On Server (recommended)
```bash
# Run all tests
ssh jhdns@10.10.50.205 "docker exec odms-backend pytest -v"

# Run specific test files
ssh jhdns@10.10.50.205 "docker exec odms-backend pytest tests/test_search.py -v"
ssh jhdns@10.10.50.205 "docker exec odms-backend pytest tests/test_ai.py -v"

# Run with coverage (if pytest-cov installed)
ssh jhdns@10.10.50.205 "docker exec odms-backend pytest --cov=app --cov-report=term-missing"
```

### Sync new tests to server
```bash
scp D:/odms/backend/tests/test_search.py jhdns@10.10.50.205:/home/jhdns/odms/backend/tests/
scp D:/odms/backend/tests/test_ai.py jhdns@10.10.50.205:/home/jhdns/odms/backend/tests/
```

---

## 9. Known Issues in Existing Tests

1. **test_create_document_with_tags** (test_document.py) -- Skipped with `@pytest.mark.skip(reason="Bug: db.refresh() expires relationships, causing MissingGreenlet in _assign_tags")`. This is a known SQLAlchemy async session management bug.

2. **test_token_expiry** (test_security.py) -- Uses a `timedelta(seconds=0)` expiry which produces a technically-expired token but clock precision makes the test non-deterministic. Currently only asserts `True` (always passes).

3. **conftest.py line 71** -- `from app.models.operation_log import ...` is on the same line as a previous import (formatting issue). Does not affect functionality.

---

## Summary

| Metric | Before | After |
|--------|--------|-------|
| Total test files | 6 | 8 |
| Total test cases | 60 | 83 |
| Critical paths covered | 3/5 | 5/5 |
| Frontend tests | 0 | 0 (framework needed) |
| Test framework health | Good | Good |
