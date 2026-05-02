import hashlib
import uuid
from pathlib import Path

ALLOWED_EXTENSIONS = {
    "docx", "doc", "xlsx", "xls", "pptx", "ppt",
    "pdf", "txt", "md", "csv",
    "jpg", "jpeg", "png", "gif", "bmp",
    "zip", "rar", "7z",
}

MIME_MAP = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.ms-excel": "xls",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "application/pdf": "pdf",
    "text/plain": "txt",
    "text/markdown": "md",
    "text/csv": "csv",
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/bmp": "bmp",
    "application/zip": "zip",
    "application/x-rar-compressed": "rar",
    "application/x-7z-compressed": "7z",
}


def detect_file_type(filename: str, mime_type: str) -> str:
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext in ALLOWED_EXTENSIONS:
        return ext
    if mime_type in MIME_MAP:
        return MIME_MAP[mime_type]
    return ext or "unknown"


def is_allowed_file(filename: str) -> bool:
    ext = Path(filename).suffix.lower().lstrip(".")
    return ext in ALLOWED_EXTENSIONS


def generate_storage_path(filename: str) -> str:
    unique_id = uuid.uuid4().hex[:12]
    safe_name = Path(filename).stem[:100].replace(" ", "_") + "_" + unique_id + Path(filename).suffix
    return f"documents/{safe_name}"


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
