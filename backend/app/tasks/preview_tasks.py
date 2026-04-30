import os
import tempfile
import subprocess
import shutil
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.tasks.celery_app import celery_app
from app.config import get_settings

settings = get_settings()
sync_engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)


def get_sync_db():
    with Session(sync_engine) as session:
        yield session


@celery_app.task(bind=True, max_retries=3)
def convert_to_html(self, doc_id: int, storage_path: str, file_type: str):
    """
    Convert a document to HTML for in-page preview using LibreOffice.
    1. Download the file from MinIO to a temp path
    2. Run soffice to convert to HTML
    3. Upload the resulting HTML to MinIO under preview/{doc_id}/ path
    4. Update the document's preview_html_path in the database
    5. Clean up temp files
    """
    from app.core.storage import minio_client

    tmpdir = None
    try:
        # Download file from MinIO
        file_data = minio_client.download_file(storage_path)
        if not file_data:
            self.update_state(
                state="FAILURE",
                meta={"error": f"File not found in MinIO: {storage_path}"},
            )
            return {"status": "FAILURE", "error": "File not found in MinIO"}

        # Create temp directory
        tmpdir = tempfile.mkdtemp(prefix="odms_preview_")
        input_ext = Path(storage_path).suffix or f".{file_type}"
        input_path = os.path.join(tmpdir, f"input{input_ext}")
        output_path = tmpdir

        # Write file to temp path
        with open(input_path, "wb") as f:
            f.write(file_data)

        # Run LibreOffice conversion to HTML
        soffice_path = settings.LIBREOFFICE_PATH
        cmd = [
            soffice_path,
            "--headless",
            "--convert-to", "html",
            "--outdir", output_path,
            input_path,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            raise Exception(f"LibreOffice conversion failed: {error_msg}")

        # Find the generated HTML
        html_files = list(Path(output_path).glob("*.html"))
        if not html_files:
            raise Exception("No HTML file was generated")

        html_path = str(html_files[0])

        # Read the HTML content as text
        with open(html_path, "r", encoding="utf-8") as f:
            html_data = f.read()

        # Upload to MinIO under preview/ path
        preview_object_name = f"preview/{doc_id}/preview.html"
        minio_client.upload_file(
            preview_object_name,
            html_data.encode("utf-8"),
            content_type="text/html; charset=utf-8",
        )

        # Update database
        db = next(get_sync_db())
        try:
            # Ensure all model modules are loaded before accessing any model
            import app.models.user  # noqa: F401
            import app.models.role  # noqa: F401
            import app.models.department  # noqa: F401
            import app.models.document  # noqa: F401
            import app.models.notification  # noqa: F401
            import app.models.operation_log  # noqa: F401
            import app.models.webhook  # noqa: F401
            import app.models.ai  # noqa: F401
            from app.models.document import Document

            doc = db.execute(
                select(Document).where(Document.id == doc_id)
            ).scalar_one_or_none()

            if doc:
                doc.preview_html_path = preview_object_name
                db.commit()

            return {
                "status": "SUCCESS",
                "doc_id": doc_id,
                "preview_path": preview_object_name,
            }
        finally:
            db.close()

    except subprocess.TimeoutExpired:
        self.retry(exc=Exception("Conversion timed out"), countdown=60)

    except Exception as exc:
        self.update_state(state="FAILURE", meta={"error": str(exc)})
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))
        return {"status": "FAILURE", "error": str(exc)}

    finally:
        # Clean up temp files
        if tmpdir and os.path.isdir(tmpdir):
            try:
                shutil.rmtree(tmpdir)
            except Exception:
                pass
