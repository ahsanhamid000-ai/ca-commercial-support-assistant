from utils.report_generator import build_report_data, build_report_pdf


def test_build_report_data():
    document = {
        "file_name": "sample.pdf",
        "file_type": "pdf",
        "summary": "Sample summary",
        "document_text": "Payment deadline is 2026-03-15. Contact test@example.com. Amount is $1000.",
    }

    report = build_report_data(document)

    assert report["document_name"] == "sample.pdf"
    assert report["summary"] == "Sample summary"
    assert "2026-03-15" in report["dates"]
    assert "test@example.com" in report["emails"]
    assert "$1000" in report["amounts"]
    assert "preview_text" in report


def test_build_report_pdf_returns_bytes():
    report = {
        "document_name": "sample.pdf",
        "document_type": "pdf",
        "summary": "This is a sample summary for PDF generation.",
        "dates": ["2026-03-15"],
        "emails": ["test@example.com"],
        "amounts": ["$1000"],
        "action_items": ["Submit the invoice."],
        "preview_text": "This is the preview section."
    }

    pdf_buffer = build_report_pdf(report)
    pdf_content = pdf_buffer.read()

    assert isinstance(pdf_content, bytes)
    assert len(pdf_content) > 0
