import secrets

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import WebhookSubscription
from app.core.pagination import PaginationParams
from app.core.exceptions import NotFoundException, ValidationException


class WebhookService:

    async def create(
        self, db: AsyncSession, user_id: int, data: "WebhookCreate"
    ) -> WebhookSubscription:
        # Validate events
        from app.utils.webhook_dispatcher import EVENT_TYPES
        for evt in data.events:
            if evt not in EVENT_TYPES:
                raise ValidationException(detail=f"Unknown event type: {evt}")

        sub = WebhookSubscription(
            user_id=user_id,
            name=data.name,
            url=data.url,
            secret=secrets.token_hex(32),
            events=",".join(data.events),
            is_active=data.is_active if hasattr(data, "is_active") else True,
        )
        db.add(sub)
        await db.commit()
        await db.refresh(sub)
        return sub

    async def get_list(
        self, db: AsyncSession, user_id: int, pagination: PaginationParams
    ) -> tuple[list[WebhookSubscription], int]:
        base_query = select(WebhookSubscription).where(
            WebhookSubscription.user_id == user_id
        )

        count_result = await db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = count_result.scalar() or 0

        stmt = (
            base_query
            .order_by(WebhookSubscription.created_at.desc())
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        result = await db.execute(stmt)
        items = result.scalars().all()
        return list(items), total

    async def get(self, db: AsyncSession, sub_id: int, user_id: int) -> WebhookSubscription:
        result = await db.execute(
            select(WebhookSubscription).where(
                WebhookSubscription.id == sub_id,
                WebhookSubscription.user_id == user_id,
            )
        )
        sub = result.scalars().first()
        if not sub:
            raise NotFoundException(resource="WebhookSubscription")
        return sub

    async def update(
        self, db: AsyncSession, sub_id: int, user_id: int, data: "WebhookUpdate"
    ) -> WebhookSubscription:
        sub = await self.get(db, sub_id, user_id)

        update_data = data.model_dump(exclude_unset=True)
        if "events" in update_data and update_data["events"]:
            from app.utils.webhook_dispatcher import EVENT_TYPES
            for evt in update_data["events"]:
                if evt not in EVENT_TYPES:
                    raise ValidationException(detail=f"Unknown event type: {evt}")
            update_data["events"] = ",".join(update_data["events"])

        for key, value in update_data.items():
            if hasattr(sub, key) and key != "id":
                setattr(sub, key, value)

        await db.commit()
        await db.refresh(sub)
        return sub

    async def regenerate_secret(
        self, db: AsyncSession, sub_id: int, user_id: int
    ) -> str:
        sub = await self.get(db, sub_id, user_id)
        new_secret = secrets.token_hex(32)
        sub.secret = new_secret
        await db.commit()
        return new_secret

    async def delete(
        self, db: AsyncSession, sub_id: int, user_id: int
    ) -> bool:
        sub = await self.get(db, sub_id, user_id)
        await db.delete(sub)
        await db.commit()
        return True

    async def get_all_active(
        self, db: AsyncSession, event_type: str
    ) -> list[WebhookSubscription]:
        """Get all active subscriptions matching an event type (for dispatcher)."""
        result = await db.execute(
            select(WebhookSubscription).where(
                WebhookSubscription.is_active == True,
                WebhookSubscription.events.contains(event_type),
            )
        )
        return list(result.scalars().all())


webhook_service = WebhookService()
