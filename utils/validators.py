def validate_question(question: str) -> tuple[bool, str]:
    if not question or not question.strip():
        return False, "Please enter a question."
    if len(question.strip()) < 2:
        return False, "Question is too short."
    if len(question) > 1000:
        return False, "Question is too long."
    return True, ""


def validate_extracted_text(text: str) -> tuple[bool, str]:
    if not text:
        return False, "No readable text was extracted from the uploaded document."
    if len(text.strip()) < 20:
        return False, "The uploaded document does not contain enough readable text."
    return True, ""
