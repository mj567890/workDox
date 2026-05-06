# Phase 4: Rate Limiting Implementation Report

**Date**: 2026-05-06
**Library**: slowapi 0.1.9

## Changes Made

### 1. New Dependency (`backend/requirements.txt`)
- Added `slowapi==0.1.9`

### 2. New Module: Shared Limiter (`backend/app/limiter.py`)
- Created a shared `Limiter` instance with `default_limits=["200/minute"]`
- Custom `get_remote_address()` key function that checks `X-Forwarded-For` header first (correctly identifies client IP behind Nginx reverse proxy), falls back to `request.client.host`, then to `"127.0.0.1"`

### 3. App Configuration (`backend/app/main.py`)
- Imported `_rate_limit_exceeded_handler` from `slowapi`
- Imported `RateLimitExceeded` from `slowapi.errors`
- Imported the shared `limiter` from `app.limiter`
- Set `app.state.limiter = limiter` (required by slowapi internals)
- Added exception handler: `app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)` -- returns HTTP 429 with a standard error body

### 4. Auth Endpoint Rate Limits (`backend/app/api/v1/auth.py`)

| Endpoint            | Method | Limit       | Rationale                                    |
|---------------------|--------|-------------|----------------------------------------------|
| `/api/v1/login`     | POST   | 5/minute    | Primary brute-force target                   |
| `/api/v1/ldap/login`| POST   | 5/minute    | Same sensitivity as local login              |
| `/api/v1/logout`    | POST   | 10/minute   | Auth-related, moderate sensitivity           |
| `/api/v1/sso/cas/callback` | GET | 10/minute | SSO ticket validation, moderate sensitivity |
| `/api/v1/oauth2/callback`  | GET | 10/minute | OAuth2 code exchange, moderate sensitivity  |

**Unaffected endpoints** (no explicit limit, use default 200/minute):
- `GET /api/v1/providers` -- public info, no brute-force risk
- `GET /api/v1/me` -- requires valid JWT, no brute-force risk
- `GET /api/v1/sso/cas/authorize` -- redirect, no sensitive processing
- `GET /api/v1/oauth2/authorize` -- redirect, no sensitive processing

### 5. Global Default
- All other endpoints inherit the default `200/minute` per client IP

## Verification
- Python syntax check passed on all modified files: `app/limiter.py`, `app/main.py`, `app/api/v1/auth.py`
- No circular import issues -- the shared limiter lives in its own module (`app/limiter.py`), imported by both `main.py` and `auth.py`

## Deployment Notes
- After `scp`ing changes and reinstalling requirements (`pip install slowapi==0.1.9`), restart the backend container
- RateLimitExceeded returns HTTP 429 with body: `{"error": "Rate limit exceeded: 5 per 1 minute"}`
- Redis is used by slowapi as the rate-limit storage backend (in-memory fallback if Redis unavailable -- note: **in-memory storage resets on container restart**; for production persistence, configure a Redis storage backend)
