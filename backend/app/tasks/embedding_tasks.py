"""Celery background tasks for embedding generation and auto-summarization."""

import asyncio
import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.tasks.celery_app import celery_app
from app.config import get_settings

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def embed_document_task(self, doc_id: int):
    """Background task: generate embeddings for a document."""
    settings = get_settings()
    sync_engine = create_engine(settings.DATABASE_URL_SYNC)

    try:
        with Session(sync_engine) as db:
            result = db.execute(
                text("SELECT extracted_text FROM document WHERE id = :did"),
                {"did": doc_id},
            )
            row = result.fetchone()
            if not row or not row[0]:
                return {"status": "SKIPPED", "reason": "No extracted text"}

        # Run async embedding in separate event loop
        async def _run():
            from app.services.rag_service import RAGService
            from sqlalchemy.ext.asyncio import (
                create_async_engine,
                AsyncSession,
                async_sessionmaker,
            )

            async_engine = create_async_engine(settings.DATABASE_URL)
            session_factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
            async with session_factory() as async_db:
                rag = RAGService()
                count = await rag.embed_and_store_document(async_db, doc_id)
            await async_engine.dispose()
            return count

        loop = asyncio.new_event_loop()
        try:
            count = loop.run_until_complete(_run())
        finally:
            loop.close()

        return {"status": "SUCCESS", "doc_id": doc_id, "chunks": count}

    except Exception as exc:
        logger.exception("Embed task failed for doc %d: %s", doc_id, exc)
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def summarize_document_task(self, doc_id: int):
    """Background task: auto-summarize a document after upload."""
    settings = get_settings()

    try:
        with Session(create_engine(settings.DATABASE_URL_SYNC)) as db:
            result = db.execute(
                text("SELECT extracted_text, original_name FROM document WHERE id = :did"),
                {"did": doc_id},
            )
            row = result.fetchone()
            if not row or not row[0]:
                return {"status": "SKIPPED", "reason": "No extracted text"}
            extracted_text, doc_name = row[0], row[1]

        async def _run():
            from app.services.summarization_service import SummarizationService
            svc = SummarizationService()
            return await svc.summarize_document(extracted_text, doc_name)

        loop = asyncio.new_event_loop()
        try:
            summary = loop.run_until_complete(_run())
        finally:
            loop.close()

        # Store summary (optional - could add summary column later)
        logger.info("Auto-summary for doc %d (%s): %s", doc_id, doc_name, summary[:100])
        return {"status": "SUCCESS", "doc_id": doc_id, "summary": summary[:500]}

    except Exception as exc:
        logger.exception("Summarize task failed for doc %d: %s", doc_id, exc)
        raise self.retry(exc=exc)
