import os
import tempfile

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.tasks.celery_app import celery_app
from app.config import get_settings

settings = get_settings()
sync_engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)


def get_sync_db():
    with Session(sync_engine) as session:
        yield session


@celery_app.task
def update_search_index(doc_id: int):
    """
    Update the full-text search index for a document.

    This task:
    1. Downloads the document from MinIO
    2. Extracts text content based on file type
    3. Updates the PostgreSQL ts_vector index by re-saving the document
       (triggers the database-level ts_vector update)

    Since the document table uses a GIN index on ts_vector computed from
    original_name and description, we can update the description field
    with extracted text to enhance search results.
    """
    from app.core.storage import minio_client
    from app.utils.text_extraction import extract_text

    db = next(get_sync_db())
    try:
        from app.models.document import Document

        doc = db.execute(
            select(Document).where(Document.id == doc_id)
        ).scalar_one_or_none()

        if not doc:
            return {
                "status": "FAILURE",
                "doc_id": doc_id,
                "error": "Document not found",
            }

        # Download file
        file_data = minio_client.download_file(doc.storage_path)
        if not file_data:
            return {
                "status": "FAILURE",
                "doc_id": doc_id,
                "error": "File data not found in MinIO",
            }

        # Extract text
        extracted_text = extract_text(doc.file_type, file_data)

        if extracted_text:
            # Truncate to avoid overly long descriptions
            max_length = 5000
            if len(extracted_text) > max_length:
                extracted_text = extracted_text[:max_length] + "..."

            # Only add search text to description if it doesn't already contain it
            current_desc = doc.description or ""
            search_suffix = f"\n[Search Index: {extracted_text[:500]}]"

            # Remove old search suffix if exists
            old_suffix_start = current_desc.find("\n[Search Index:")
            if old_suffix_start >= 0:
                current_desc = current_desc[:old_suffix_start]

            doc.description = current_desc + search_suffix
            db.commit()

        # Also trigger a raw ts_vector refresh by touching the row
        db.execute(
            text(
                "UPDATE document SET updated_at = NOW() WHERE id = :doc_id"
            ),
            {"doc_id": doc_id},
        )
        db.commit()

        return {
            "status": "SUCCESS",
            "doc_id": doc_id,
            "text_length": len(extracted_text),
        }

    except Exception as exc:
        return {
            "status": "FAILURE",
            "doc_id": doc_id,
            "error": str(exc),
        }
    finally:
        db.close()
