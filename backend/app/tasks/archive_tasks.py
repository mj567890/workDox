import os
import tempfile
import shutil
import zipfile
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


@celery_app.task(bind=True)
def extract_archive(
    self,
    archive_doc_id: int,
    storage_path: str,
    file_type: str,
    user_id: int,
):
    """
    Extract an archive file (zip, rar, 7z) and create individual document records
    for each extracted file.

    1. Download archive from MinIO
    2. Extract based on type
    3. For each extracted file: determine type, upload to MinIO, create Document + DocumentVersion records
    4. Update archive document status
    """
    from app.core.storage import minio_client
    from app.utils.file_utils import detect_file_type, generate_storage_path, compute_sha256

    tmpdir = None
    try:
        # Download archive from MinIO
        file_data = minio_client.download_file(storage_path)
        if not file_data:
            return {"status": "FAILURE", "error": "File not found in MinIO"}

        # Create temp directory
        tmpdir = tempfile.mkdtemp(prefix="odms_archive_")
        archive_path = os.path.join(tmpdir, f"archive.{file_type}")

        with open(archive_path, "wb") as f:
            f.write(file_data)

        # Create extraction directory
        extract_dir = os.path.join(tmpdir, "extracted")
        os.makedirs(extract_dir, exist_ok=True)

        # Extract based on type
        if file_type == "zip":
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(extract_dir)
        elif file_type in ("rar", "7z"):
            # Try using patool or pyunpack
            try:
                from patoolib import extract_archive as patool_extract
                patool_extract(archive_path, outdir=extract_dir)
            except ImportError:
                try:
                    from pyunpack import Archive
                    Archive(archive_path).extractall(extract_dir)
                except ImportError:
                    # Fallback: try 7z command line
                    import subprocess
                    seven_zip_paths = [
                        "7z", "7za", "7zr",
                        r"C:\Program Files\7-Zip\7z.exe",
                        r"C:\Program Files (x86)\7-Zip\7z.exe",
                        "/usr/bin/7z",
                    ]
                    extracted = False
                    for p7z in seven_zip_paths:
                        try:
                            result = subprocess.run(
                                [p7z, "x", archive_path, f"-o{extract_dir}", "-y"],
                                capture_output=True,
                                text=True,
                                timeout=120,
                            )
                            if result.returncode == 0:
                                extracted = True
                                break
                        except (FileNotFoundError, subprocess.TimeoutExpired):
                            continue
                    if not extracted:
                        raise Exception(
                            "Cannot extract rar/7z files. Install 7-Zip, patool, or pyunpack."
                        )
        else:
            raise Exception(f"Unsupported archive type: {file_type}")

        # Get archive's matter_id to associate extracted files
        db = next(get_sync_db())
        try:
            from app.models.document import Document, DocumentVersion

            archive_doc = db.execute(
                select(Document).where(Document.id == archive_doc_id)
            ).scalar_one_or_none()

            matter_id = archive_doc.matter_id if archive_doc else None

            # Walk extracted files
            extracted_count = 0
            for root, dirs, files in os.walk(extract_dir):
                for filename in files:
                    file_path = os.path.join(root, filename)
                    relative_path = os.path.relpath(file_path, extract_dir)

                    # Determine file type and MIME
                    ext = Path(filename).suffix.lower().lstrip(".")
                    file_type_detected = ext or "unknown"
                    mime_map = {
                        "pdf": "application/pdf",
                        "doc": "application/msword",
                        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        "xls": "application/vnd.ms-excel",
                        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        "txt": "text/plain",
                        "jpg": "image/jpeg",
                        "jpeg": "image/jpeg",
                        "png": "image/png",
                    }
                    mime_type = mime_map.get(file_type_detected, "application/octet-stream")

                    with open(file_path, "rb") as f:
                        file_content = f.read()

                    file_size = len(file_content)
                    checksum = compute_sha256(file_content)
                    storage_path_extracted = generate_storage_path(
                        f"{filename}_{extracted_count}", matter_id
                    )

                    # Upload to MinIO
                    minio_client.upload_file(
                        storage_path_extracted,
                        file_content,
                        content_type=mime_type,
                    )

                    # Create Document record
                    doc = Document(
                        original_name=filename,
                        file_type=file_type_detected,
                        file_size=file_size,
                        mime_type=mime_type,
                        storage_path=storage_path_extracted,
                        description=f"Extracted from archive: {archive_doc.original_name if archive_doc else 'unknown'}",
                        owner_id=user_id,
                        matter_id=matter_id,
                        status="draft",
                    )
                    db.add(doc)
                    db.flush()

                    # Create DocumentVersion
                    version = DocumentVersion(
                        document_id=doc.id,
                        version_no=1,
                        file_path=storage_path_extracted,
                        file_size=file_size,
                        upload_user_id=user_id,
                        change_note=f"Extracted from archive (doc #{archive_doc_id})",
                        is_official=False,
                        checksum=checksum,
                    )
                    db.add(version)
                    db.flush()

                    doc.current_version_id = version.id
                    extracted_count += 1

            # Update archive document status
            if archive_doc:
                archive_doc.status = "extracted"
                archive_doc.description = (
                    f"{archive_doc.description or ''}\nExtracted: {extracted_count} files"
                ).strip()

            db.commit()

            return {
                "status": "SUCCESS",
                "archive_doc_id": archive_doc_id,
                "extracted_count": extracted_count,
            }

        finally:
            db.close()

    except Exception as exc:
        return {"status": "FAILURE", "error": str(exc)}

    finally:
        # Clean up temp files
        if tmpdir and os.path.isdir(tmpdir):
            try:
                shutil.rmtree(tmpdir)
            except Exception:
                pass
