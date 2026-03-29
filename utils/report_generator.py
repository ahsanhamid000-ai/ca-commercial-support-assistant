import re
from io import BytesIO
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def dedupe_keep_order(items: list[str]) -> list[str]:
    seen = set()
    output = []

    for item in items:
        cleaned = " ".join((item or "").split()).strip()
        if not cleaned:
            continue

        key = cleaned.lower()
        if key not in seen:
            seen.add(key)
            output.append(cleaned)

    return output


def extract_dates(text: str) -> list[str]:
    patterns = [
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b",
        r"\bweek\s+\d+\b",
    ]

    matches: list[str] = []
    for pattern in patterns:
        matches.extend(re.findall(pattern, text, flags=re.IGNORECASE))
    return dedupe_keep_order(matches)


def extract_emails(text: str) -> list[str]:
    return dedupe_keep_order(
        re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text)
    )


def extract_amounts(text: str) -> list[str]:
    return dedupe_keep_order(
        re.findall(r"(?:\$|USD\s*)\d[\d,]*(?:\.\d{2})?", text, flags=re.IGNORECASE)
    )


def extract_action_items(text: str) -> list[str]:
    lines = []
    for raw_line in (text or "").splitlines():
        line = " ".join(raw_line.split()).strip()
        if line:
            lines.append(line)

    keywords = (
        "must",
        "should",
        "required",
        "deadline",
        "submit",
        "review",
        "approve",
        "approval",
        "complete",
    )

    items = [line for line in lines if any(keyword in line.lower() for keyword in keywords)]
    return dedupe_keep_order(items[:12])


def get_pdf_page_count(file_path: Path | None) -> int:
    if not file_path or not file_path.exists() or file_path.suffix.lower() != ".pdf":
        return 0

    try:
        import fitz
    except Exception:
        return 0

    pdf = fitz.open(str(file_path))
    try:
        return pdf.page_count
    finally:
        pdf.close()


def build_report_data(document: dict, file_path: Path | None = None) -> dict:
    text = (
        document.get("document_text")
        or document.get("cleaned_text")
        or ""
    )

    extracted_info = document.get("extracted_info", {})
    if not isinstance(extracted_info, dict):
        extracted_info = {}

    dates = extracted_info.get("dates") or extract_dates(text)
    emails = extracted_info.get("emails") or extract_emails(text)
    amounts = extracted_info.get("amounts") or extract_amounts(text)
    action_items = extracted_info.get("action_items") or extract_action_items(text)

    preview_text = text[:9000].strip()
    if len(text) > 9000:
        preview_text += "..."

    file_name = document.get("file_name", "")
    file_type = document.get("file_type", "")
    is_pdf = str(file_name).lower().endswith(".pdf") or str(file_type).lower() == "pdf"

    pdf_page_count = get_pdf_page_count(file_path) if is_pdf else 0
    pdf_preview_available = pdf_page_count > 0

    return {
        "document_name": file_name,
        "document_type": file_type or (file_name.rsplit(".", 1)[1] if "." in file_name else ""),
        "summary": document.get("summary", ""),
        "dates": dates,
        "emails": emails,
        "amounts": amounts,
        "action_items": action_items,
        "preview_text": preview_text,
        "preview": preview_text,
        "is_pdf": is_pdf,
        "pdf_page_count": pdf_page_count,
        "pdf_preview_available": pdf_preview_available,
    }


def build_report_pdf(report: dict) -> BytesIO:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    _, height = A4
    y = height - 50

    def write_line(text: str, font: str = "Helvetica", size: int = 11, gap: int = 18):
        nonlocal y
        if y < 50:
            pdf.showPage()
            y = height - 50
        pdf.setFont(font, size)
        pdf.drawString(50, y, text[:100])
        y -= gap

    def write_list(title: str, items: list[str]):
        write_line(title, font="Helvetica-Bold", size=12, gap=20)
        if not items:
            write_line("- None found")
            return
        for item in items:
            for line in split_text_for_pdf(f"- {item}", 90):
                write_line(line)

    pdf.setTitle("Commercial Support Report")

    write_line("CA Commercial Support Assistant Report", font="Helvetica-Bold", size=16, gap=24)
    write_line(f"Document Name: {report.get('document_name', '')}")
    write_line(f"Document Type: {str(report.get('document_type', '')).upper()}")
    y -= 8

    write_line("Executive Summary", font="Helvetica-Bold", size=12, gap=20)
    summary = report.get("summary", "No summary available.")
    for line in split_text_for_pdf(summary, 90):
        write_line(line)

    y -= 8
    write_list("Dates", report.get("dates", []))
    y -= 8
    write_list("Emails", report.get("emails", []))
    y -= 8
    write_list("Amounts", report.get("amounts", []))
    y -= 8
    write_list("Action Items", report.get("action_items", []))
    y -= 8

    write_line("Document Preview", font="Helvetica-Bold", size=12, gap=20)
    preview = report.get("preview_text") or report.get("preview") or "No preview available."
    for line in split_text_for_pdf(preview, 90):
        write_line(line)

    pdf.save()
    buffer.seek(0)
    return buffer


def split_text_for_pdf(text: str, max_chars: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]

    lines = []
    current_line = []

    for word in words:
        test_line = " ".join(current_line + [word])
        if len(test_line) <= max_chars:
            current_line.append(word)
        else:
            lines.append(" ".join(current_line))
            current_line = [word]

    if current_line:
        lines.append(" ".join(current_line))

    return lines
