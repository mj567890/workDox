from sqlalchemy import select, func, and_, or_, text, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.matter import Matter, MatterMember
from app.core.pagination import PaginationParams


class SearchService:

    async def search_documents(
        self,
        db: AsyncSession,
        keyword: str,
        file_type: str | None,
        matter_id: int | None,
        pagination: PaginationParams,
        current_user: dict,
    ) -> dict:
        """Search documents with access control and FTS/ILIKE support."""
        conditions = [Document.is_deleted == False]
        user_id = current_user.get("id")
        user_roles: list[str] = current_user.get("roles", [])
        is_admin_or_leader = "admin" in user_roles or "dept_leader" in user_roles

        # Access control: owner or matter member
        if not is_admin_or_leader:
            accessible_matter_ids = current_user.get("accessible_matter_ids", [])
            if accessible_matter_ids:
                conditions.append(or_(
                    Document.owner_id == user_id,
                    Document.matter_id.in_(accessible_matter_ids),
                ))
            else:
                conditions.append(Document.owner_id == user_id)

        if file_type:
            conditions.append(Document.file_type == file_type)
        if matter_id:
            conditions.append(Document.matter_id == matter_id)

        # Build search conditions
        search_conditions = []
        if keyword:
            # FTS using PostgreSQL tsvector
            doc_fts = func.to_tsvector(
                'simple', func.coalesce(Document.original_name, '')
            ).op('@@')(func.plainto_tsquery('simple', keyword))

            if len(keyword) <= 2:
                # Short query: combine FTS with ILIKE fallback
                search_conditions.append(or_(
                    doc_fts,
                    Document.original_name.ilike(f"%{keyword}%"),
                    Document.description.ilike(f"%{keyword}%"),
                ))
            else:
                search_conditions.append(doc_fts)

        if search_conditions:
            conditions.extend(search_conditions)

        base_query = select(
            Document.id,
            Document.original_name.label("title"),
            Document.description,
            Document.file_type,
            Document.matter_id,
            Document.created_at,
        ).where(and_(*conditions))

        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        stmt = (
            base_query
            .order_by(desc(Document.created_at))
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        result = await db.execute(stmt)
        rows = result.all()

        items = []
        for row in rows:
            items.append({
                "id": row.id,
                "title": row.title,
                "description": row.description,
                "file_type": row.file_type,
                "matter_id": row.matter_id,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            })

        return {"items": items, "total": total}

    async def search_matters(
        self,
        db: AsyncSession,
        keyword: str,
        pagination: PaginationParams,
        current_user: dict,
    ) -> dict:
        """Search matters with access control and FTS/ILIKE support."""
        conditions = []
        user_id = current_user.get("id")
        user_roles: list[str] = current_user.get("roles", [])
        is_admin_or_leader = "admin" in user_roles or "dept_leader" in user_roles

        # Access control: owner or matter member
        if not is_admin_or_leader:
            accessible_matter_ids = current_user.get("accessible_matter_ids", [])
            if accessible_matter_ids:
                conditions.append(or_(
                    Matter.owner_id == user_id,
                    Matter.id.in_(accessible_matter_ids),
                ))
            else:
                conditions.append(Matter.owner_id == user_id)

        # Build search conditions
        search_conditions = []
        if keyword:
            matter_fts = func.to_tsvector(
                'simple',
                func.coalesce(Matter.title, '') + ' ' +
                func.coalesce(Matter.matter_no, '') + ' ' +
                func.coalesce(Matter.description, '')
            ).op('@@')(func.plainto_tsquery('simple', keyword))

            if len(keyword) <= 2:
                # Short query: combine FTS with ILIKE fallback
                search_conditions.append(or_(
                    matter_fts,
                    Matter.title.ilike(f"%{keyword}%"),
                    Matter.matter_no.ilike(f"%{keyword}%"),
                    Matter.description.ilike(f"%{keyword}%"),
                ))
            else:
                search_conditions.append(matter_fts)

        if search_conditions:
            conditions.extend(search_conditions)

        base_query = select(
            Matter.id,
            Matter.title,
            Matter.description,
            Matter.matter_no,
            Matter.type_id,
            Matter.owner_id,
            Matter.status,
            Matter.created_at,
        ).where(and_(*conditions))

        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        stmt = (
            base_query
            .order_by(desc(Matter.created_at))
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        result = await db.execute(stmt)
        rows = result.all()

        items = []
        for row in rows:
            items.append({
                "id": row.id,
                "title": row.title,
                "description": row.description,
                "matter_no": row.matter_no,
                "type_id": row.type_id,
                "owner_id": row.owner_id,
                "status": row.status,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            })

        return {"items": items, "total": total}
