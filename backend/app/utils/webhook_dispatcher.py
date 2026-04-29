"""
Webhook event dispatcher.

Dispatches system events to registered webhook subscribers asynchronously.
Uses HMAC-SHA256 signing for payload verification on the receiving end.
"""

import asyncio
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

logger = logging.getLogger("webhook")

# Supported event types
EVENT_TYPES = [
    "matter.created",
    "matter.updated",
    "matter.completed",
    "document.uploaded",
    "document.approved",
    "document.rejected",
    "task.assigned",
    "task.completed",
    "node.advanced",
    "notification.created",
]


async def dispatch_event(
    db_session_factory,
    event_type: str,
    payload: dict,
    actor_id: int | None = None,
):
    """
    Dispatch an event to all active webhook subscriptions matching the event type.

    Args:
        db_session_factory: AsyncSession factory for database queries
        event_type: One of EVENT_TYPES
        payload: Event data to send to subscribers
        actor_id: ID of the user who triggered the event
    """
    if event_type not in EVENT_TYPES:
        logger.warning(f"Unknown event type: {event_type}")
        return

    from app.models.webhook import WebhookSubscription

    async with db_session_factory() as db:
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

    # Dispatch to all matching subscribers concurrently
    tasks = [_deliver_webhook(sub, event_payload) for sub in subscriptions]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Update subscription statuses
    from app.models.webhook import WebhookSubscription
    async with db_session_factory() as db:
        for sub, result in zip(subscriptions, results):
            sub.last_triggered_at = datetime.now(timezone.utc)
            if isinstance(result, Exception):
                sub.last_status = "failed"
                logger.error(f"Webhook delivery failed for {sub.name}: {result}")
            else:
                sub.last_status = "success"
            db.add(sub)
        await db.commit()


async def _deliver_webhook(subscription, payload: dict) -> bool:
    """Deliver a webhook payload to a single subscriber with HMAC signing."""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    # Compute HMAC-SHA256 signature
    signature = hmac.new(
        subscription.secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "X-ODMS-Event": payload["event"],
        "X-ODMS-Signature": f"sha256={signature}",
        "X-ODMS-Delivery-ID": str(hash(body)),
        "User-Agent": "ODMS-Webhook/1.0",
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
        response = await client.post(subscription.url, content=body, headers=headers)
        if 200 <= response.status_code < 300:
            logger.info(f"Webhook delivered to {subscription.name}: {response.status_code}")
            return True
        else:
            logger.warning(f"Webhook {subscription.name} returned {response.status_code}")
            raise RuntimeError(f"HTTP {response.status_code}: {response.text[:200]}")


def verify_webhook_signature(secret: str, body: bytes, signature_header: str) -> bool:
    """
    Verify a webhook payload signature.
    Can be used by receiving endpoints to validate incoming webhooks.
    """
    if not signature_header.startswith("sha256="):
        return False
    expected = signature_header[7:]
    computed = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(computed, expected)
