from utils.context_selector import select_relevant_chunks
from utils.prompt_builder import build_qa_prompt
from utils.validators import validate_question


def test_context_selector_returns_string():
    document_text = "Payment deadline is March 15, 2026.\nApproval is required by finance."
    question = "What is the payment deadline?"
    context = select_relevant_chunks(question, document_text)
    assert isinstance(context, str)
    assert "Payment deadline" in context or "March 15, 2026" in context


def test_prompt_builder_contains_question():
    prompt = build_qa_prompt("Some context", "What is the deadline?")
    assert "What is the deadline?" in prompt


def test_validate_question_rejects_empty_string():
    is_valid, error = validate_question("")
    assert is_valid is False
    assert error == "Please enter a question."


def test_validate_question_accepts_normal_input():
    is_valid, error = validate_question("What is the payment deadline?")
    assert is_valid is True
    assert error == ""
