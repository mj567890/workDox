"""
Shared rate-limiter instance for the application.

Uses slowapi with a custom key function that checks the X-Forwarded-For
header first so that rate limits apply to the real client IP when running
behind a reverse proxy (Nginx).
"""

from slowapi import Limiter
from starlette.requests import Request


def get_remote_address(request: Request) -> str:
    """Return the client IP, respecting X-Forwarded-For if present."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # The first entry is the original client IP.
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "127.0.0.1"


limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
