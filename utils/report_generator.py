from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def build_report_data(document: dict) -> dict:
    extracted_info = document.get("extracted_info", {})
    cleaned_text = document.get("cleaned_text", "")

    return {
        "document_name": document.get("file_name", ""),
        "document_type": document.get("file_type", ""),
        "summary": document.get("summary", ""),
        "dates": extracted_info.get("dates", []),
        "emails": extracted_info.get("emails", []),
        "amounts": extracted_info.get("amounts", []),
        "action_items": extracted_info.get("action_items", []),
        "preview": cleaned_text[:1200] + ("..." if len(cleaned_text) > 1200 else ""),
    }


def build_report_pdf(report: dict) -> BytesIO:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4
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
            write_line(f"- {item}")

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
    preview = report.get("preview", "No preview available.")
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
