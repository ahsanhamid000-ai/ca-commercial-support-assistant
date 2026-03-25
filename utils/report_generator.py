def build_report_data(document: dict) -> dict:
    extracted_info = document.get("extracted_info", {})
    return {
        "document_name": document.get("file_name", ""),
        "document_type": document.get("file_type", ""),
        "summary": document.get("summary", ""),
        "dates": extracted_info.get("dates", []),
        "emails": extracted_info.get("emails", []),
        "amounts": extracted_info.get("amounts", []),
        "action_items": extracted_info.get("action_items", []),
    }
