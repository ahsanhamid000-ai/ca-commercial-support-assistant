import re
from openai import OpenAI

from utils.context_selector import select_relevant_chunks, tokenize
from utils.prompt_builder import build_qa_prompt


NOT_FOUND_MESSAGE = "The requested information was not found in the uploaded document."


def answer_question(question: str, document_text: str, api_key: str) -> str:
    if not document_text.strip():
        return "The uploaded document could not be processed correctly."

    context = select_relevant_chunks(question, document_text, top_k=2)
    if not context.strip():
        return NOT_FOUND_MESSAGE

    prompt = build_qa_prompt(context, question)

    if not api_key:
        return local_fallback_answer(question, context)

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
                        "Answer strictly from the provided context. "
                        "Keep the answer concise and business-focused. "
                        f'If the answer is missing, reply exactly: "{NOT_FOUND_MESSAGE}"'
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        content = response.choices[0].message.content
        if not content:
            return NOT_FOUND_MESSAGE

        answer = content.strip()
        return answer if answer else NOT_FOUND_MESSAGE

    except Exception:
        return local_fallback_answer(question, context)


def local_fallback_answer(question: str, context: str) -> str:
    sentences = split_sentences(context)
    if not sentences:
        return NOT_FOUND_MESSAGE

    question_tokens = tokenize(question)
    if not question_tokens:
        return (
            "I could not generate a full AI answer right now, but the most relevant "
            f"document passage is:\n\n{sentences[0]}"
        )

    scored_sentences: list[tuple[int, str]] = []
    for sentence in sentences:
        sentence_tokens = tokenize(sentence)
        score = len(question_tokens.intersection(sentence_tokens))
        if score > 0:
            scored_sentences.append((score, sentence))

    scored_sentences.sort(key=lambda item: item[0], reverse=True)

    if not scored_sentences:
        return NOT_FOUND_MESSAGE

    best_sentence = scored_sentences[0][1]
    return (
        "I could not generate a full AI answer right now, but the most relevant "
        f"document passage is:\n\n{best_sentence}"
    )


def split_sentences(text: str) -> list[str]:
    raw_sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [sentence.strip() for sentence in raw_sentences if sentence.strip()]
