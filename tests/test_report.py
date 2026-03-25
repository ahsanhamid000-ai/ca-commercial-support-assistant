from utils.report_generator import build_report_data


def test_build_report_data():
    document = {
        "file_name": "sample.pdf",
        "file_type": "pdf",
        "summary": "Sample summary",
        "extracted_info": {
            "dates": ["2026-03-15"],
            "emails": ["test@example.com"],
            "amounts": ["$1000"],
            "action_items": ["Submit the invoice."]
        }
    }

    report = build_report_data(document)

    assert report["document_name"] == "sample.pdf"
    assert report["summary"] == "Sample summary"
    assert "2026-03-15" in report["dates"]
