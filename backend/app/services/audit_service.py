from datetime import datetime, timezone

from sqlalchemy import select, func, and_, desc, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operation_log import OperationLog
from app.core.pagination import PaginationParams


class AuditService:

    async def log_operation(
        self,
        db: AsyncSession,
        user_id: int,
        operation_type: str,
        target_type: str,
        target_id: int | None,
        detail: str | None,
        ip_address: str | None,
    ) -> OperationLog:
        log_entry = OperationLog(
            user_id=user_id,
            operation_type=operation_type,
            target_type=target_type,
            target_id=target_id,
            detail=detail,
            ip_address=ip_address,
        )
        db.add(log_entry)
        await db.commit()
        await db.refresh(log_entry)
        return log_entry

    async def get_logs(
        self,
        db: AsyncSession,
        pagination: PaginationParams,
        filters: dict,
    ) -> tuple[list[OperationLog], int]:
        conditions = []

        if filters.get("user_id"):
            conditions.append(OperationLog.user_id == filters["user_id"])
        if filters.get("operation_type"):
            conditions.append(OperationLog.operation_type == filters["operation_type"])
        if filters.get("target_type"):
            conditions.append(OperationLog.target_type == filters["target_type"])
        if filters.get("target_id"):
            conditions.append(OperationLog.target_id == filters["target_id"])
        if filters.get("start_date"):
            conditions.append(OperationLog.created_at >= filters["start_date"])
        if filters.get("end_date"):
            conditions.append(OperationLog.created_at <= filters["end_date"])
        if filters.get("keyword"):
            keyword = filters["keyword"]
            like_expr = or_(
                OperationLog.operation_type.ilike(f"%{keyword}%"),
                OperationLog.target_type.ilike(f"%{keyword}%"),
                OperationLog.detail.ilike(f"%{keyword}%"),
            )
            conditions.append(like_expr)

        base_query = select(OperationLog).options(selectinload(OperationLog.user))
        if conditions:
            base_query = base_query.where(and_(*conditions))

        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        stmt = (
            base_query
            .order_by(desc(OperationLog.created_at))
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        result = await db.execute(stmt)
        items = result.scalars().all()

        return list(items), total
