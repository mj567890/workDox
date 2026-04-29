from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone, timedelta

from app.models.workflow import WorkflowTemplate, WorkflowTemplateNode, WorkflowNode
from app.models.matter import Matter
from app.core.exceptions import NotFoundException, ConflictException


class WorkflowService:
    async def get_templates(
        self, db: AsyncSession, pagination,
        matter_type_id: int = None, is_active: bool = None,
    ) -> tuple[list[WorkflowTemplate], int]:
        query = select(WorkflowTemplate).options(
            selectinload(WorkflowTemplate.matter_type_obj),
            selectinload(WorkflowTemplate.template_nodes),
        )
        count_query = select(func.count(WorkflowTemplate.id))

        if matter_type_id is not None:
            query = query.where(WorkflowTemplate.matter_type_id == matter_type_id)
            count_query = count_query.where(WorkflowTemplate.matter_type_id == matter_type_id)

        if is_active is not None:
            query = query.where(WorkflowTemplate.is_active == is_active)
            count_query = count_query.where(WorkflowTemplate.is_active == is_active)

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        offset = (pagination.page - 1) * pagination.page_size
        result = await db.execute(
            query.order_by(WorkflowTemplate.created_at.desc())
            .offset(offset)
            .limit(pagination.page_size)
        )
        return list(result.scalars().all()), total

    async def create_template(self, db: AsyncSession, data) -> WorkflowTemplate:
        # Check for duplicate name within same matter type
        existing_result = await db.execute(
            select(WorkflowTemplate).where(
                WorkflowTemplate.name == data.name,
                WorkflowTemplate.matter_type_id == data.matter_type_id,
            )
        )
        if existing_result.scalar_one_or_none():
            raise ConflictException(
                detail="Template with this name already exists for this matter type"
            )

        template = WorkflowTemplate(
            name=data.name,
            matter_type_id=data.matter_type_id,
            is_active=data.is_active if hasattr(data, "is_active") else True,
            description=data.description,
        )
        db.add(template)
        await db.flush()

        for node_data in data.nodes:
            required_rule = node_data.required_documents_rule
            if hasattr(required_rule, "model_dump"):
                required_rule = required_rule.model_dump()
            node = WorkflowTemplateNode(
                template_id=template.id,
                node_name=node_data.node_name,
                node_order=node_data.node_order,
                owner_role=node_data.owner_role,
                sla_hours=node_data.sla_hours if hasattr(node_data, "sla_hours") else None,
                required_documents_rule=required_rule,
                description=node_data.description,
            )
            db.add(node)

        await db.commit()

        # Re-fetch with eager-loaded relations for response formatting
        result = await db.execute(
            select(WorkflowTemplate).options(
                selectinload(WorkflowTemplate.matter_type_obj),
                selectinload(WorkflowTemplate.template_nodes),
            ).where(WorkflowTemplate.id == template.id)
        )
        return result.scalar_one()

    async def get_template(self, db: AsyncSession, template_id: int) -> WorkflowTemplate:
        template_result = await db.execute(
            select(WorkflowTemplate).options(
                selectinload(WorkflowTemplate.matter_type_obj),
                selectinload(WorkflowTemplate.template_nodes),
            ).where(WorkflowTemplate.id == template_id)
        )
        template = template_result.scalar_one_or_none()
        if not template:
            raise NotFoundException("Workflow template")
        return template

    async def update_template(self, db: AsyncSession, template_id: int, data) -> WorkflowTemplate:
        result = await db.execute(
            select(WorkflowTemplate).options(
                selectinload(WorkflowTemplate.matter_type_obj),
                selectinload(WorkflowTemplate.template_nodes),
            ).where(WorkflowTemplate.id == template_id)
        )
        template = result.scalar_one_or_none()
        if not template:
            raise NotFoundException("Workflow template")

        if data.name is not None:
            template.name = data.name
        if data.is_active is not None:
            template.is_active = data.is_active
        if data.description is not None:
            template.description = data.description

        await db.commit()
        await db.refresh(template)
        return template

    async def delete_template(self, db: AsyncSession, template_id: int) -> bool:
        result = await db.execute(select(WorkflowTemplate).where(WorkflowTemplate.id == template_id))
        template = result.scalar_one_or_none()
        if not template:
            raise NotFoundException("Workflow template")
        await db.delete(template)
        await db.commit()
        return True

    async def instantiate_nodes(self, db: AsyncSession, matter_id: int, template_id: int) -> list[WorkflowNode]:
        result = await db.execute(
            select(WorkflowTemplateNode)
            .where(WorkflowTemplateNode.template_id == template_id)
            .order_by(WorkflowTemplateNode.node_order)
        )
        template_nodes = result.scalars().all()

        nodes = []
        for i, tn in enumerate(template_nodes):
            planned = None
            if tn.sla_hours:
                planned = datetime.now(timezone.utc) + timedelta(hours=tn.sla_hours)
            node = WorkflowNode(
                matter_id=matter_id,
                node_name=tn.node_name,
                node_order=tn.node_order,
                owner_id=0,
                status="pending" if i > 0 else "pending",
                planned_finish_time=planned,
                required_documents_rule=tn.required_documents_rule,
            )
            db.add(node)
            nodes.append(node)

        await db.commit()
        return nodes

    async def get_nodes(self, db: AsyncSession, matter_id: int) -> list[WorkflowNode]:
        result = await db.execute(
            select(WorkflowNode).options(
                selectinload(WorkflowNode.owner),
            )
            .where(WorkflowNode.matter_id == matter_id)
            .order_by(WorkflowNode.node_order)
        )
        return list(result.scalars().all())

    async def advance_node(self, db: AsyncSession, matter_id: int, node_id: int, user_id: int) -> WorkflowNode:
        node_result = await db.execute(
            select(WorkflowNode).options(selectinload(WorkflowNode.owner))
            .where(WorkflowNode.id == node_id)
        )
        node = node_result.scalar_one_or_none()
        if not node:
            raise NotFoundException("Workflow node")

        node.status = "completed"
        node.actual_finish_time = datetime.now(timezone.utc)

        # Find next pending node (not just +1, find first pending with higher order)
        next_result = await db.execute(
            select(WorkflowNode).where(
                WorkflowNode.matter_id == matter_id,
                WorkflowNode.node_order > node.node_order,
                WorkflowNode.status == "pending",
            ).order_by(WorkflowNode.node_order).limit(1)
        )
        next_node = next_result.scalar_one_or_none()

        matter_result = await db.execute(select(Matter).where(Matter.id == matter_id))
        matter = matter_result.scalar_one_or_none()

        if next_node:
            next_node.status = "in_progress"
            if matter:
                matter.current_node_id = next_node.id
        else:
            # All nodes completed
            if matter:
                matter.status = "completed"
                matter.progress = 100.0
                matter.current_node_id = node.id

        # Update matter progress (counting both completed and skipped)
        total_nodes_result = await db.execute(
            select(func.count(WorkflowNode.id)).where(WorkflowNode.matter_id == matter_id)
        )
        total_nodes = total_nodes_result.scalar() or 1

        completed_nodes_result = await db.execute(
            select(func.count(WorkflowNode.id)).where(
                WorkflowNode.matter_id == matter_id,
                WorkflowNode.status.in_(["completed", "skipped"]),
            )
        )
        completed_nodes = completed_nodes_result.scalar() or 0

        if matter:
            matter.progress = round((completed_nodes / total_nodes) * 100, 1)

        await db.commit()
        await db.refresh(node)
        return node

    async def rollback_node(self, db: AsyncSession, matter_id: int, node_id: int, user_id: int) -> WorkflowNode:
        node_result = await db.execute(
            select(WorkflowNode).options(selectinload(WorkflowNode.owner))
            .where(WorkflowNode.id == node_id)
        )
        node = node_result.scalar_one_or_none()
        if not node:
            raise NotFoundException("Workflow node")

        # Check that no later nodes are completed
        later_nodes_result = await db.execute(
            select(func.count(WorkflowNode.id)).where(
                WorkflowNode.matter_id == matter_id,
                WorkflowNode.node_order > node.node_order,
                WorkflowNode.status == "completed",
            )
        )
        later_completed = later_nodes_result.scalar() or 0
        if later_completed > 0:
            raise ConflictException(
                detail="Cannot rollback: later nodes are already completed. Roll them back first."
            )

        node.status = "rolled_back"
        node.actual_finish_time = None

        matter_result = await db.execute(select(Matter).where(Matter.id == matter_id))
        matter = matter_result.scalar_one_or_none()
        if matter:
            matter.current_node_id = node.id
            matter.status = "in_progress"

        await db.commit()
        await db.refresh(node)
        return node

    async def skip_node(self, db: AsyncSession, matter_id: int, node_id: int, user_id: int) -> WorkflowNode:
        node_result = await db.execute(
            select(WorkflowNode).options(selectinload(WorkflowNode.owner))
            .where(WorkflowNode.id == node_id)
        )
        node = node_result.scalar_one_or_none()
        if not node:
            raise NotFoundException("Workflow node")

        node.status = "skipped"
        node.actual_finish_time = datetime.now(timezone.utc)

        # Update matter progress (counting both completed and skipped)
        total_nodes_result = await db.execute(
            select(func.count(WorkflowNode.id)).where(WorkflowNode.matter_id == matter_id)
        )
        total_nodes = total_nodes_result.scalar() or 1

        completed_nodes_result = await db.execute(
            select(func.count(WorkflowNode.id)).where(
                WorkflowNode.matter_id == matter_id,
                WorkflowNode.status.in_(["completed", "skipped"]),
            )
        )
        completed_nodes = completed_nodes_result.scalar() or 0

        matter_result = await db.execute(select(Matter).where(Matter.id == matter_id))
        matter = matter_result.scalar_one_or_none()
        if matter:
            matter.progress = round((completed_nodes / total_nodes) * 100, 1)

        await db.commit()
        await db.refresh(node)
        return node


class WorkflowValidationService:
    async def validate_node_documents(self, db: AsyncSession, matter_id: int, node_id: int) -> dict:
        result = await db.execute(select(WorkflowNode).where(WorkflowNode.id == node_id))
        node = result.scalar_one_or_none()
        if not node:
            raise NotFoundException("Workflow node")

        missing = []
        warnings = []

        if node.required_documents_rule and isinstance(node.required_documents_rule, dict):
            rules = node.required_documents_rule.get("rules", [])
            from app.models.document import Document, DocumentCategory

            for rule in rules:
                category = rule.get("category")
                min_count = rule.get("min_count", 1)
                if category:
                    count = (await db.execute(
                        select(func.count(Document.id)).where(
                            Document.matter_id == matter_id,
                            Document.category.has(DocumentCategory.name == category),
                            Document.is_deleted == False,
                        )
                    )).scalar() or 0
                    if count < min_count:
                        missing.append(f"缺少'{category}'类文档 (需要至少{min_count}个，当前{count}个)")

                tag = rule.get("tag")
                if tag:
                    from app.models.document import Tag
                    count = (await db.execute(
                        select(func.count(Document.id)).where(
                            Document.matter_id == matter_id,
                            Document.tags.any(Tag.name == tag),
                            Document.is_deleted == False,
                        )
                    )).scalar() or 0
                    if count < min_count:
                        missing.append(f"缺少带有'{tag}'标签的文档 (需要至少{min_count}个，当前{count}个)")

        return {
            "valid": len(missing) == 0,
            "missing_documents": missing,
            "warnings": warnings,
        }
