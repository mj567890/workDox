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

# Magic bytes / file signatures for common allowed formats
MAGIC_SIGNATURES: dict[str, list[tuple[int, bytes]]] = {
    "pdf":  [(0, b"%PDF")],
    "png":  [(0, b"\x89PNG\r\n\x1a\n")],
    "jpg":  [(0, b"\xff\xd8\xff")],
    "jpeg": [(0, b"\xff\xd8\xff")],
    "gif":  [(0, b"GIF87a"), (0, b"GIF89a")],
    "bmp":  [(0, b"BM")],
    "zip":  [(0, b"PK\x03\x04")],
    "docx": [(0, b"PK\x03\x04")],  # Office Open XML is ZIP-based
    "xlsx": [(0, b"PK\x03\x04")],
    "pptx": [(0, b"PK\x03\x04")],
    "rar":  [(0, b"Rar!\x1a\x07")],
    "7z":   [(0, b"7z\xbc\xaf'\x1c")],
    "doc":  [(0, b"\xd0\xcf\x11\xe0")],  # OLE compound document
    "xls":  [(0, b"\xd0\xcf\x11\xe0")],
    "ppt":  [(0, b"\xd0\xcf\x11\xe0")],
}

TEXT_EXTENSIONS = frozenset({"txt", "md", "csv"})


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


def validate_file_content(data: bytes, claimed_ext: str) -> bool:
    """Validate that file content matches its claimed extension via magic bytes.

    Returns True if:
    - The file type has a known magic signature and it matches
    - The file type is text-based (txt, md, csv) — verified as text below
    - The file type has no known signature and passes basic sanity checks

    Returns False if the magic bytes explicitly don't match the claimed type.
    """
    ext = claimed_ext.lower().lstrip(".")

    # Text-based formats: check for printable content (no null bytes in first 4KB)
    if ext in TEXT_EXTENSIONS:
        sample = data[:4096]
        # Allow empty files for text types
        if len(sample) == 0:
            return True
        # Check for null bytes which would indicate binary content
        return b"\x00" not in sample

    # Check magic signatures
    if ext in MAGIC_SIGNATURES:
        for offset, signature in MAGIC_SIGNATURES[ext]:
            if len(data) >= offset + len(signature) and data[offset:offset + len(signature)] == signature:
                # For Office Open XML files (docx, xlsx, pptx), also verify ZIP structure
                if ext in ("docx", "xlsx", "pptx"):
                    if data[:4] == b"PK\x03\x04":
                        return True
                    return False
                return True
        return False

    # Unknown file types with allowed extensions — allow (could be a new format)
    return True


def generate_storage_path(filename: str) -> str:
    unique_id = uuid.uuid4().hex[:12]
    safe_name = Path(filename).stem[:100].replace(" ", "_") + "_" + unique_id + Path(filename).suffix
    return f"documents/{safe_name}"


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
