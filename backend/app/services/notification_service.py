from sqlalchemy import select, func, and_, desc, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Notification
from app.core.pagination import PaginationParams
from app.core.exceptions import NotFoundException, ForbiddenException


class NotificationService:

    async def create_notification(
        self,
        db: AsyncSession,
        user_id: int,
        type: str,
        title: str,
        content: str | None = None,
        matter_id: int | None = None,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            type=type,
            title=title,
            content=content,
            related_matter_id=matter_id,
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        return notification

    async def get_notifications(
        self,
        db: AsyncSession,
        user_id: int,
        pagination: PaginationParams,
        is_read: bool | None = None,
        notification_type: str | None = None,
    ) -> tuple[list[Notification], int]:
        conditions = [Notification.user_id == user_id]

        if is_read is not None:
            conditions.append(Notification.is_read == is_read)
        if notification_type:
            conditions.append(Notification.type == notification_type)

        base_query = select(Notification).where(and_(*conditions))

        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        stmt = (
            base_query
            .order_by(desc(Notification.created_at))
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        result = await db.execute(stmt)
        items = result.scalars().all()

        return list(items), total

    async def mark_as_read(
        self, db: AsyncSession, notification_id: int, user_id: int
    ) -> Notification:
        stmt = select(Notification).where(Notification.id == notification_id)
        result = await db.execute(stmt)
        notification = result.scalars().first()

        if not notification:
            raise NotFoundException(resource="Notification")

        if notification.user_id != user_id:
            raise ForbiddenException(detail="Cannot mark another user's notification")

        notification.is_read = True
        await db.commit()
        await db.refresh(notification)
        return notification

    async def mark_all_as_read(
        self, db: AsyncSession, user_id: int
    ) -> int:
        stmt = (
            update(Notification)
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False,
                )
            )
            .values(is_read=True)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

    async def batch_mark_read(
        self, db: AsyncSession, notification_ids: list[int], user_id: int
    ) -> int:
        stmt = select(Notification).where(
            Notification.id.in_(notification_ids),
            Notification.user_id == user_id,
        )
        result = await db.execute(stmt)
        notifications = result.scalars().all()
        for n in notifications:
            n.is_read = True
        await db.commit()
        return len(notifications)

    async def get_unread_count(
        self, db: AsyncSession, user_id: int
    ) -> int:
        stmt = select(func.count()).where(
            and_(
                Notification.user_id == user_id,
                Notification.is_read == False,
            )
        )
        result = await db.execute(stmt)
        return result.scalar() or 0
