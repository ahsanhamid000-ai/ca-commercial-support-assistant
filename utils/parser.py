import logging
from pathlib import Path

from PyPDF2 import PdfReader
from docx import Document

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path: str) -> str:
    text_parts: list[str] = []

    try:
        reader = PdfReader(file_path)
    except Exception as exc:
        logger.exception("Failed to open PDF file %s: %s", file_path, exc)
        return ""

    for page_number, page in enumerate(reader.pages, start=1):
        try:
            text_parts.append(page.extract_text() or "")
        except Exception as exc:
            logger.warning(
                "Failed to extract text from PDF page %s in %s: %s",
                page_number,
                file_path,
                exc,
            )

    return "\n".join(text_parts).strip()


def extract_text_from_docx(file_path: str) -> str:
    try:
        doc = Document(file_path)
        paragraphs = [paragraph.text for paragraph in doc.paragraphs if paragraph.text]
        return "\n".join(paragraphs).strip()
    except Exception as exc:
        logger.exception("Failed to parse DOCX file %s: %s", file_path, exc)
        return ""


def extract_text_from_txt(file_path: str) -> str:
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
            return file.read().strip()
    except Exception as exc:
        logger.exception("Failed to read TXT file %s: %s", file_path, exc)
        return ""


def extract_text(file_path: str, extension: str | None = None) -> str:
    ext = (extension or Path(file_path).suffix.replace(".", "")).lower()

    if ext == "pdf":
        return extract_text_from_pdf(file_path)
    if ext == "docx":
        return extract_text_from_docx(file_path)
    if ext == "txt":
        return extract_text_from_txt(file_path)

    raise ValueError(f"Unsupported file type: {ext}")
