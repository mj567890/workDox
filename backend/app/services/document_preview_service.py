from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.core.storage import minio_client
from app.core.exceptions import NotFoundException


class DocumentPreviewService:
    PREVIEWABLE_TYPES = {"docx", "doc", "xlsx", "xls", "pptx", "ppt", "pdf", "txt", "md", "jpg", "jpeg", "png", "gif", "bmp"}
    DIRECTLY_VIEWABLE_TYPES = {"pdf", "txt", "md", "jpg", "jpeg", "png", "gif", "bmp"}
    CONVERTIBLE_TYPES = {"docx", "doc", "xlsx", "xls", "pptx", "ppt"}

    async def get_preview_url(self, db: AsyncSession, doc_id: int) -> dict:
        result = await db.execute(select(Document).where(Document.id == doc_id))
        doc = result.scalar_one_or_none()
        if not doc:
            raise NotFoundException("Document")

        if doc.file_type not in self.PREVIEWABLE_TYPES:
            return {"status": "unsupported", "url": None}

        # Check if cached PDF preview exists
        if doc.preview_pdf_path:
            url = minio_client.get_presigned_url(doc.preview_pdf_path)
            if url:
                return {"status": "ready", "url": url}

        # Directly viewable types
        if doc.file_type in self.DIRECTLY_VIEWABLE_TYPES:
            url = minio_client.get_presigned_url(doc.storage_path)
            return {"status": "ready", "url": url}

        # Office formats - trigger async conversion
        if doc.file_type in self.CONVERTIBLE_TYPES:
            self.trigger_conversion(doc_id, doc.storage_path, doc.file_type)
            return {"status": "processing", "url": None}

        return {"status": "unsupported", "url": None}

    def trigger_conversion(self, doc_id: int, storage_path: str, file_type: str):
        try:
            from app.tasks.preview_tasks import convert_to_pdf
            convert_to_pdf.delay(doc_id, storage_path, file_type)
        except Exception:
            pass
