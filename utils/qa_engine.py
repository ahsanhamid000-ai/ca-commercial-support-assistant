from openai import OpenAI
from utils.context_selector import select_relevant_chunks
from utils.prompt_builder import build_qa_prompt


def answer_question(question: str, document_text: str, api_key: str) -> str:
    if not document_text.strip():
        return "The uploaded document could not be processed correctly."

    context = select_relevant_chunks(question, document_text)
    prompt = build_qa_prompt(context, question)

    if not api_key:
        return simple_fallback_answer(context)

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            temperature=0.1,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a document-grounded commercial support assistant. "
                        "Answer strictly from the provided context."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        content = response.choices[0].message.content
        return content.strip() if content else "The requested information was not found in the uploaded document."
    except Exception:
        return simple_fallback_answer(context)


def simple_fallback_answer(context: str) -> str:
    if not context:
        return "The requested information was not found in the uploaded document."
    return f"Relevant document context:\n{context[:600]}..."
