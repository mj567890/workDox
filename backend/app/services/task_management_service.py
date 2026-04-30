from datetime import datetime, timezone

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task import (
    TaskTemplate, StageTemplate, SlotTemplate,
    Task, Stage, Slot, SlotVersion,
)
from app.core.exceptions import NotFoundException, ValidationException


class TaskTemplateService:

    async def list_templates(self, db: AsyncSession, category: str | None = None) -> list[TaskTemplate]:
        stmt = select(TaskTemplate).options(
            selectinload(TaskTemplate.stages).selectinload(StageTemplate.slots)
        ).order_by(TaskTemplate.id)
        if category:
            stmt = stmt.where(TaskTemplate.category == category)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_template(self, db: AsyncSession, template_id: int) -> TaskTemplate:
        stmt = select(TaskTemplate).options(
            selectinload(TaskTemplate.stages).selectinload(StageTemplate.slots)
        ).where(TaskTemplate.id == template_id)
        result = await db.execute(stmt)
        template = result.scalars().first()
        if not template:
            raise NotFoundException(resource="TaskTemplate")
        return template

    async def create_template(self, db: AsyncSession, data: dict) -> TaskTemplate:
        stages_data = data.pop("stages", [])
        template = TaskTemplate(
            name=data["name"],
            description=data.get("description"),
            category=data.get("category"),
            is_system=data.get("is_system", False),
        )
        db.add(template)
        await db.flush()

        for i, stage_data in enumerate(stages_data):
            slots_data = stage_data.pop("slots", [])
            stage = StageTemplate(
                template_id=template.id,
                name=stage_data["name"],
                order=stage_data.get("order", i + 1),
                description=stage_data.get("description"),
                deadline_offset_days=stage_data.get("deadline_offset_days"),
            )
            db.add(stage)
            await db.flush()

            for j, slot_data in enumerate(slots_data):
                slot = SlotTemplate(
                    stage_template_id=stage.id,
                    name=slot_data["name"],
                    description=slot_data.get("description"),
                    is_required=slot_data.get("is_required", True),
                    file_type_hints=slot_data.get("file_type_hints"),
                    auto_tags=slot_data.get("auto_tags"),
                    sort_order=slot_data.get("sort_order", j + 1),
                )
                db.add(slot)

        await db.commit()
        await db.refresh(template)
        return await self.get_template(db, template.id)

    async def update_template(self, db: AsyncSession, template_id: int, data: dict) -> TaskTemplate:
        template = await self.get_template(db, template_id)
        for key in ("name", "description", "category"):
            if key in data:
                setattr(template, key, data[key])
        await db.commit()
        await db.refresh(template)
        return template

    async def delete_template(self, db: AsyncSession, template_id: int):
        template = await self.get_template(db, template_id)
        await db.delete(template)
        await db.commit()

    async def clone_template(self, db: AsyncSession, template_id: int) -> TaskTemplate:
        template = await self.get_template(db, template_id)
        new_data = {
            "name": f"{template.name} (副本)",
            "description": template.description,
            "category": template.category,
            "stages": []
        }
        for stage in template.stages:
            stage_data = {
                "name": stage.name,
                "order": stage.order,
                "description": stage.description,
                "deadline_offset_days": stage.deadline_offset_days,
                "slots": []
            }
            for slot in stage.slots:
                stage_data["slots"].append({
                    "name": slot.name,
                    "description": slot.description,
                    "is_required": slot.is_required,
                    "file_type_hints": slot.file_type_hints,
                    "auto_tags": slot.auto_tags,
                    "sort_order": slot.sort_order,
                })
            new_data["stages"].append(stage_data)
        return await self.create_template(db, new_data)

    async def add_stage(self, db: AsyncSession, template_id: int, data: dict) -> StageTemplate:
        template = await self.get_template(db, template_id)
        max_order = max((s.order for s in template.stages), default=0)
        stage = StageTemplate(
            template_id=template_id,
            name=data["name"],
            order=data.get("order", max_order + 1),
            description=data.get("description"),
            deadline_offset_days=data.get("deadline_offset_days"),
        )
        db.add(stage)
        await db.commit()
        await db.refresh(stage)
        return stage

    async def update_stage(self, db: AsyncSession, template_id: int, stage_id: int, data: dict):
        template = await self.get_template(db, template_id)
        stage = next((s for s in template.stages if s.id == stage_id), None)
        if not stage:
            raise NotFoundException(resource="StageTemplate")
        for key in ("name", "order", "description", "deadline_offset_days"):
            if key in data:
                setattr(stage, key, data[key])
        await db.commit()

    async def delete_stage(self, db: AsyncSession, template_id: int, stage_id: int):
        template = await self.get_template(db, template_id)
        stage = next((s for s in template.stages if s.id == stage_id), None)
        if not stage:
            raise NotFoundException(resource="StageTemplate")
        await db.delete(stage)
        await db.commit()

    async def reorder_stages(self, db: AsyncSession, template_id: int, stage_ids: list[int]):
        for i, sid in enumerate(stage_ids, 1):
            stmt = select(StageTemplate).where(
                and_(StageTemplate.id == sid, StageTemplate.template_id == template_id)
            )
            result = await db.execute(stmt)
            stage = result.scalars().first()
            if stage:
                stage.order = i
        await db.commit()

    async def add_slot(self, db: AsyncSession, template_id: int, stage_id: int, data: dict):
        slot = SlotTemplate(
            stage_template_id=stage_id,
            name=data["name"],
            description=data.get("description"),
            is_required=data.get("is_required", True),
            file_type_hints=data.get("file_type_hints"),
            auto_tags=data.get("auto_tags"),
            sort_order=data.get("sort_order", 0),
        )
        db.add(slot)
        await db.commit()
        await db.refresh(slot)
        return slot

    async def update_slot(self, db: AsyncSession, template_id: int, stage_id: int, slot_id: int, data: dict):
        stmt = select(SlotTemplate).where(SlotTemplate.id == slot_id)
        result = await db.execute(stmt)
        slot = result.scalars().first()
        if not slot:
            raise NotFoundException(resource="SlotTemplate")
        for key in ("name", "description", "is_required", "file_type_hints", "auto_tags", "sort_order"):
            if key in data:
                setattr(slot, key, data[key])
        await db.commit()

    async def delete_slot(self, db: AsyncSession, template_id: int, stage_id: int, slot_id: int):
        stmt = select(SlotTemplate).where(SlotTemplate.id == slot_id)
        result = await db.execute(stmt)
        slot = result.scalars().first()
        if slot:
            await db.delete(slot)
            await db.commit()

    async def reorder_slots(self, db: AsyncSession, template_id: int, stage_id: int, slot_ids: list[int]):
        for i, sid in enumerate(slot_ids):
            stmt = select(SlotTemplate).where(SlotTemplate.id == sid)
            result = await db.execute(stmt)
            slot = result.scalars().first()
            if slot:
                slot.sort_order = i + 1
        await db.commit()


class TaskInstanceService:

    async def list_tasks(self, db: AsyncSession, status: str | None = None) -> list[Task]:
        stmt = select(Task).options(
            selectinload(Task.template),
            selectinload(Task.stages).selectinload(Stage.slots),
        ).order_by(Task.id.desc())
        if status:
            stmt = stmt.where(Task.status == status)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_task(self, db: AsyncSession, task_id: int) -> Task:
        stmt = select(Task).options(
            selectinload(Task.template),
            selectinload(Task.stages).selectinload(Stage.slots).selectinload(Slot.document),
        ).where(Task.id == task_id)
        result = await db.execute(stmt)
        task = result.scalars().first()
        if not task:
            raise NotFoundException(resource="Task")
        return task

    async def create_task(self, db: AsyncSession, data: dict, creator_id: int) -> Task:
        template = await db.execute(
            select(TaskTemplate).options(
                selectinload(TaskTemplate.stages).selectinload(StageTemplate.slots)
            ).where(TaskTemplate.id == data["template_id"])
        )
        template = template.scalars().first()
        if not template:
            raise NotFoundException(resource="TaskTemplate")

        task = Task(
            template_id=template.id,
            matter_id=data.get("matter_id"),
            title=data.get("title", template.name),
            status="pending",
            current_stage_order=1,
            creator_id=creator_id,
        )
        db.add(task)
        await db.flush()

        for st in template.stages:
            stage = Stage(
                task_id=task.id,
                stage_template_id=st.id,
                order=st.order,
                name=st.name,
                status="in_progress" if st.order == 1 else "locked",
            )
            db.add(stage)
            await db.flush()

            for sl in st.slots:
                slot = Slot(
                    stage_id=stage.id,
                    slot_template_id=sl.id,
                    name=sl.name,
                    description=sl.description,
                    is_required=sl.is_required,
                    status="pending",
                )
                db.add(slot)

        await db.commit()
        await db.refresh(task)
        return await self.get_task(db, task.id)

    async def update_task(self, db: AsyncSession, task_id: int, data: dict) -> Task:
        task = await self.get_task(db, task_id)
        for key in ("title", "status", "matter_id"):
            if key in data:
                setattr(task, key, data[key])
        await db.commit()
        await db.refresh(task)
        return task

    async def delete_task(self, db: AsyncSession, task_id: int):
        task = await self.get_task(db, task_id)
        await db.delete(task)
        await db.commit()

    async def advance_stage(self, db: AsyncSession, task_id: int) -> Task:
        task = await self.get_task(db, task_id)
        current_stage = next((s for s in task.stages if s.order == task.current_stage_order), None)
        if not current_stage:
            raise ValidationException(detail="Current stage not found")

        # Check required slots
        missing = [s.name for s in current_stage.slots if s.is_required and s.status == "pending"]
        if missing:
            raise ValidationException(detail=f"Required slots not completed: {', '.join(missing)}")

        next_stage = next((s for s in task.stages if s.order == task.current_stage_order + 1), None)
        if not next_stage:
            raise ValidationException(detail="No next stage to advance to")

        current_stage.status = "completed"
        next_stage.status = "in_progress"
        task.current_stage_order = next_stage.order

        all_done = all(
            s.status == "completed"
            for s in task.stages
            if all(sl.is_required for sl in s.slots) or s.status == "completed"
        )
        remaining = [s for s in task.stages if s.order > next_stage.order]
        if not remaining:
            all_required_filled = all(
                not sl.is_required or sl.status != "pending"
                for s in task.stages
                for sl in s.slots
            )
            if all_required_filled:
                task.status = "completed"

        await db.commit()
        await db.refresh(task)
        return await self.get_task(db, task.id)

    async def upload_to_slot(
        self, db: AsyncSession, task_id: int, stage_id: int, slot_id: int,
        document_id: int, maturity: str = "draft", maturity_note: str | None = None,
        user_id: int | None = None,
    ) -> Slot:
        task = await self.get_task(db, task_id)
        stage = next((s for s in task.stages if s.id == stage_id), None)
        if not stage:
            raise NotFoundException(resource="Stage")

        slot = next((s for s in stage.slots if s.id == slot_id), None)
        if not slot:
            raise NotFoundException(resource="Slot")

        if slot.document_id and slot.document_id != document_id:
            SlotVersion(
                slot_id=slot.id,
                document_id=slot.document_id,
                maturity=slot.maturity,
                maturity_note=slot.maturity_note,
                created_by=user_id or task.creator_id,
            )
            db.add(SlotVersion)

        slot.document_id = document_id
        slot.status = "filled"
        slot.maturity = maturity
        slot.maturity_note = maturity_note

        SlotVersion(
            slot_id=slot.id,
            document_id=document_id,
            maturity=maturity,
            maturity_note=maturity_note,
            created_by=user_id or task.creator_id,
        )
        db.add(SlotVersion)

        await db.commit()
        await db.refresh(slot)
        return slot

    async def replace_slot_document(
        self, db: AsyncSession, task_id: int, stage_id: int, slot_id: int,
        document_id: int, maturity: str = "draft", maturity_note: str | None = None,
        user_id: int | None = None,
    ) -> Slot:
        return await self.upload_to_slot(
            db, task_id, stage_id, slot_id, document_id, maturity, maturity_note, user_id
        )

    async def remove_slot_document(
        self, db: AsyncSession, task_id: int, stage_id: int, slot_id: int
    ) -> Slot:
        task = await self.get_task(db, task_id)
        stage = next((s for s in task.stages if s.id == stage_id), None)
        if not stage:
            raise NotFoundException(resource="Stage")
        slot = next((s for s in stage.slots if s.id == slot_id), None)
        if not slot:
            raise NotFoundException(resource="Slot")

        slot.document_id = None
        slot.status = "pending"
        slot.maturity = None
        slot.maturity_note = None
        await db.commit()
        await db.refresh(slot)
        return slot

    async def update_slot_maturity(
        self, db: AsyncSession, task_id: int, stage_id: int, slot_id: int,
        maturity: str, maturity_note: str | None = None,
    ) -> Slot:
        task = await self.get_task(db, task_id)
        stage = next((s for s in task.stages if s.id == stage_id), None)
        if not stage:
            raise NotFoundException(resource="Stage")
        slot = next((s for s in stage.slots if s.id == slot_id), None)
        if not slot:
            raise NotFoundException(resource="Slot")

        slot.maturity = maturity
        slot.maturity_note = maturity_note
        await db.commit()
        await db.refresh(slot)
        return slot

    async def waive_slot(
        self, db: AsyncSession, task_id: int, stage_id: int, slot_id: int, reason: str,
    ) -> Slot:
        task = await self.get_task(db, task_id)
        stage = next((s for s in task.stages if s.id == stage_id), None)
        if not stage:
            raise NotFoundException(resource="Stage")
        slot = next((s for s in stage.slots if s.id == slot_id), None)
        if not slot:
            raise NotFoundException(resource="Slot")

        slot.status = "waived"
        slot.waive_reason = reason
        await db.commit()
        await db.refresh(slot)
        return slot

    async def unwaive_slot(
        self, db: AsyncSession, task_id: int, stage_id: int, slot_id: int,
    ) -> Slot:
        task = await self.get_task(db, task_id)
        stage = next((s for s in task.stages if s.id == stage_id), None)
        if not stage:
            raise NotFoundException(resource="Stage")
        slot = next((s for s in stage.slots if s.id == slot_id), None)
        if not slot:
            raise NotFoundException(resource="Slot")

        slot.status = "pending" if not slot.document_id else "filled"
        slot.waive_reason = None
        await db.commit()
        await db.refresh(slot)
        return slot

    async def get_slot_versions(self, db: AsyncSession, task_id: int, stage_id: int, slot_id: int) -> list[SlotVersion]:
        stmt = select(SlotVersion).options(
            selectinload(SlotVersion.document),
            selectinload(SlotVersion.creator),
        ).where(SlotVersion.slot_id == slot_id).order_by(SlotVersion.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_board(self, db: AsyncSession, task_id: int) -> dict:
        task = await self.get_task(db, task_id)
        total_required = sum(1 for s in task.stages for sl in s.slots if sl.is_required)
        filled_required = sum(
            1 for s in task.stages for sl in s.slots
            if sl.is_required and sl.status in ("filled", "waived")
        )
        progress = round(filled_required / total_required * 100, 1) if total_required else 0

        stages_data = []
        for stage in task.stages:
            slots_data = []
            for slot in stage.slots:
                versions = await self.get_slot_versions(db, task_id, stage.id, slot.id)
                slots_data.append({
                    "id": slot.id,
                    "name": slot.name,
                    "description": slot.description,
                    "is_required": slot.is_required,
                    "status": slot.status,
                    "waive_reason": slot.waive_reason,
                    "maturity": slot.maturity,
                    "maturity_note": slot.maturity_note,
                    "document_id": slot.document_id,
                    "document_name": slot.document.original_name if slot.document else None,
                    "version_count": len(versions),
                })
            stages_data.append({
                "id": stage.id,
                "order": stage.order,
                "name": stage.name,
                "status": stage.status,
                "notes": stage.notes,
                "slots": slots_data,
            })

        return {
            "task_id": task.id,
            "title": task.title,
            "status": task.status,
            "current_stage_order": task.current_stage_order,
            "progress": progress,
            "stages": stages_data,
        }
