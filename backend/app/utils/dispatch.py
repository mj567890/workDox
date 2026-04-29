"""
Helper to fire-and-forget webhook events from route handlers.

Usage in route:
    from app.utils.dispatch import fire_webhook
    fire_webhook("matter.created", {"id": matter.id, "title": matter.title}, current_user.id)
"""

import asyncio
import logging

logger = logging.getLogger("webhook.dispatch")


def fire_webhook(event_type: str, payload: dict, actor_id: int | None = None):
    """
    Fire a webhook event asynchronously (fire-and-forget).
    Safe to call from route handlers — won't block the response.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return  # No event loop running

    loop.create_task(_do_dispatch(event_type, payload, actor_id))


async def _do_dispatch(event_type: str, payload: dict, actor_id: int | None):
    """Internal async dispatch with its own db session."""
    import hashlib
    import hmac
    import json
    from datetime import datetime, timezone

    import httpx
    from sqlalchemy import select

    from app.dependencies import _get_async_session_factory
    from app.models.webhook import WebhookSubscription

    try:
        factory = _get_async_session_factory()
        async with factory() as db:
            result = await db.execute(
                select(WebhookSubscription).where(
                    WebhookSubscription.is_active == True,
                    WebhookSubscription.events.contains(event_type),
                )
            )
            subscriptions = result.scalars().all()

        if not subscriptions:
            return

        event_payload = {
            "event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor_id": actor_id,
            "data": payload,
        }
        body = json.dumps(event_payload, ensure_ascii=False).encode("utf-8")

        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            for sub in subscriptions:
                try:
                    signature = hmac.new(
                        sub.secret.encode("utf-8"), body, hashlib.sha256
                    ).hexdigest()

                    headers = {
                        "Content-Type": "application/json; charset=utf-8",
                        "X-ODMS-Event": event_type,
                        "X-ODMS-Signature": f"sha256={signature}",
                        "User-Agent": "ODMS-Webhook/1.0",
                    }

                    resp = await client.post(sub.url, content=body, headers=headers)
                    status = "success" if 200 <= resp.status_code < 300 else "failed"

                    # Update last status
                    sub.last_triggered_at = datetime.now(timezone.utc)
                    sub.last_status = status

                except Exception:
                    sub.last_triggered_at = datetime.now(timezone.utc)
                    sub.last_status = "failed"

            # Batch update statuses
            async with factory() as db:
                for sub in subscriptions:
                    db.add(sub)
                await db.commit()

    except Exception as e:
        logger.error(f"Webhook dispatch error: {e}")
