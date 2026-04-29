from sqlalchemy.ext.asyncio import AsyncSession


class ArchiveService:
    async def extract_and_import(self, db: AsyncSession, archive_doc_id: int, user_id: int) -> dict:
        from sqlalchemy import select
        from app.models.document import Document
        from app.core.exceptions import NotFoundException

        result = await db.execute(select(Document).where(Document.id == archive_doc_id))
        doc = result.scalar_one_or_none()
        if not doc:
            raise NotFoundException("Archive document")

        self.trigger_extraction(archive_doc_id, doc.storage_path, doc.file_type, user_id, doc.matter_id)
        return {"status": "processing", "message": "Archive extraction started"}

    def trigger_extraction(self, archive_doc_id: int, storage_path: str, file_type: str, user_id: int, matter_id: int | None = None):
        try:
            from app.tasks.archive_tasks import extract_archive
            extract_archive.delay(archive_doc_id, storage_path, file_type, user_id, matter_id)
        except Exception:
            pass
