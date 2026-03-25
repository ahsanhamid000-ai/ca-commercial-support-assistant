from pathlib import Path
from PyPDF2 import PdfReader
from docx import Document


def extract_text_from_pdf(file_path: str) -> str:
    text_parts: list[str] = []
    reader = PdfReader(file_path)
    for page in reader.pages:
        text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts).strip()


def extract_text_from_docx(file_path: str) -> str:
    doc = Document(file_path)
    return "\n".join([paragraph.text for paragraph in doc.paragraphs]).strip()


def extract_text_from_txt(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
        return file.read().strip()


def extract_text(file_path: str, extension: str | None = None) -> str:
    ext = extension or Path(file_path).suffix.replace(".", "").lower()

    if ext == "pdf":
        return extract_text_from_pdf(file_path)
    if ext == "docx":
        return extract_text_from_docx(file_path)
    if ext == "txt":
        return extract_text_from_txt(file_path)

    raise ValueError(f"Unsupported file type: {ext}")
