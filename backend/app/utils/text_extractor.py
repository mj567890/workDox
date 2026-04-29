"""Text extraction from common document formats: docx, xlsx, pdf, txt."""

import io
import traceback
import logging

logger = logging.getLogger(__name__)

# Lazy imports to avoid hard dependency failures at module load time
_import_errors: dict[str, str] = {}


def _get_docx_doc():
    try:
        import docx
        return docx
    except ImportError as e:
        _import_errors["docx"] = str(e)
        return None


def _get_pdf_plumber():
    try:
        import pdfplumber
        return pdfplumber
    except ImportError as e:
        _import_errors["pdfplumber"] = str(e)
        return None


def _get_openpyxl():
    try:
        import openpyxl
        return openpyxl
    except ImportError as e:
        _import_errors["openpyxl"] = str(e)
        return None


MAX_EXTRACT_CHARS = 50000  # Soft cap to avoid storing huge texts


def extract_text(file_data: bytes, file_type: str, original_name: str = "") -> str | None:
    """Extract readable text from a file's binary content.

    Returns extracted text string, or None if extraction fails or is unsupported.
    """
    file_type = file_type.lower()

    try:
        if file_type == "txt":
            return _extract_txt(file_data)

        if file_type == "docx":
            return _extract_docx(file_data)

        if file_type == "pdf":
            return _extract_pdf(file_data)

        if file_type in ("xlsx", "xls"):
            return _extract_xlsx(file_data)

        logger.debug(f"No text extractor for file type: {file_type}")
        return None
    except Exception:
        logger.warning(f"Text extraction failed for {original_name} ({file_type}):\n{traceback.format_exc()}")
        return None


def _extract_txt(data: bytes) -> str:
    """Extract text from plain text files."""
    for encoding in ("utf-8", "gbk", "gb2312", "latin-1"):
        try:
            text = data.decode(encoding)
            return text[:MAX_EXTRACT_CHARS]
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")[:MAX_EXTRACT_CHARS]


def _extract_docx(data: bytes) -> str | None:
    """Extract text from .docx Word documents."""
    docx_mod = _get_docx_doc()
    if docx_mod is None:
        logger.warning("python-docx not installed, skipping docx extraction")
        return None

    doc = docx_mod.Document(io.BytesIO(data))
    paragraphs = []
    for para in doc.paragraphs:
        if para.text.strip():
            paragraphs.append(para.text.strip())

    # Also extract text from tables
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
            if row_text:
                paragraphs.append(row_text)

    text = "\n".join(paragraphs)
    return text[:MAX_EXTRACT_CHARS] if text.strip() else None


def _extract_pdf(data: bytes) -> str | None:
    """Extract text from PDF files using pdfplumber, fallback to pdfminer."""
    # Try pdfplumber first (better quality)
    pdfplumber_mod = _get_pdf_plumber()
    if pdfplumber_mod is not None:
        try:
            pages_text = []
            with pdfplumber_mod.open(io.BytesIO(data)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        pages_text.append(page_text)
            text = "\n".join(pages_text)
            if text.strip():
                return text[:MAX_EXTRACT_CHARS]
        except Exception:
            logger.debug(f"pdfplumber extraction failed, trying pdfminer fallback")

    # Fallback to pdfminer.six
    try:
        from pdfminer.high_level import extract_text as pdfminer_extract
        text = pdfminer_extract(io.BytesIO(data))
        if text.strip():
            return text[:MAX_EXTRACT_CHARS]
    except Exception:
        pass

    # Fallback to pypdfium2
    try:
        import pypdfium2
        pdf = pypdfium2.PdfDocument(data)
        pages_text = []
        for page in pdf:
            text_page = page.get_textpage()
            pages_text.append(text_page.get_text_range())
        pdf.close()
        text = "\n".join(pages_text)
        if text.strip():
            return text[:MAX_EXTRACT_CHARS]
    except Exception:
        pass

    return None


def _extract_xlsx(data: bytes) -> str | None:
    """Extract text from Excel spreadsheets."""
    openpyxl_mod = _get_openpyxl()
    if openpyxl_mod is None:
        logger.warning("openpyxl not installed, skipping xlsx extraction")
        return None

    wb = openpyxl_mod.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    all_text = []

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        sheet_lines = [f"[Sheet: {sheet_name}]"]
        for row in ws.iter_rows(values_only=True):
            row_values = [str(cell) for cell in row if cell is not None]
            if row_values:
                sheet_lines.append(" | ".join(row_values))
        all_text.append("\n".join(sheet_lines))

    wb.close()
    text = "\n\n".join(all_text)
    return text[:MAX_EXTRACT_CHARS] if text.strip() else None
