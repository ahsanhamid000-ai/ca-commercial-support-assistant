import logging
import re
from typing import Iterable

from openai import OpenAI

from utils.context_selector import select_relevant_chunks, tokenize
from utils.prompt_builder import build_qa_prompt


logger = logging.getLogger(__name__)

NOT_FOUND_MESSAGE = "The requested information was not found in the uploaded document."
PROCESSING_ERROR_MESSAGE = "The uploaded document could not be processed correctly."


def answer_question(question: str, document_text: str, api_key: str | None = None) -> str:
    question = (question or "").strip()
    document_text = (document_text or "").strip()

    if not document_text:
        return PROCESSING_ERROR_MESSAGE

    if not question:
        return "Please enter a question about the uploaded document."

    context = select_relevant_chunks(question, document_text, top_k=4)
    if not context.strip():
        return NOT_FOUND_MESSAGE

    prompt = build_qa_prompt(context, question)

    if api_key:
        try:
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                temperature=0.1,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a document-grounded assistant. "
                            "Answer only from the provided context. "
                            "Be concise, clear, and accurate. "
                            f'If the answer is missing, reply exactly: "{NOT_FOUND_MESSAGE}"'
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )

            content = response.choices[0].message.content if response.choices else None
            answer = (content or "").strip()
            if answer:
                return answer
        except Exception as exc:
            logger.exception("OpenAI QA call failed: %s", exc)

    return local_fallback_answer(question, context)


def local_fallback_answer(question: str, context: str) -> str:
    if not context.strip():
        return NOT_FOUND_MESSAGE

    question_lower = question.lower()

    if is_list_request(question_lower):
        bullet_answer = answer_list_question(question, context)
        if bullet_answer:
            return bullet_answer

    sentences = split_sentences(context)
    if not sentences:
        return NOT_FOUND_MESSAGE

    ranked_sentences = rank_sentences(question, sentences)
    if not ranked_sentences:
        return NOT_FOUND_MESSAGE

    if any(term in question_lower for term in {"main purpose", "purpose", "objective", "about", "summary"}):
        best = ranked_sentences[:2]
        return " ".join(best).strip()

    if any(term in question_lower for term in {"framework", "react", "vue", "javascript"}):
        return ranked_sentences[0]

    if any(term in question_lower for term in {"deadline", "due date", "when due", "week"}):
        return ranked_sentences[0]

    return " ".join(ranked_sentences[:2]).strip()


def is_list_request(question_lower: str) -> bool:
    trigger_terms = {
        "list", "action items", "actions", "requirements", "tasks",
        "steps", "deliverables", "instructions", "items"
    }
    return any(term in question_lower for term in trigger_terms)


def answer_list_question(question: str, context: str) -> str:
    lines = extract_candidate_lines(context)
    if not lines:
        return ""

    ranked = rank_lines(question, lines)
    if not ranked:
        return ""

    best_lines = deduplicate_preserving_order(ranked[:8])
    if not best_lines:
        return ""

    return "\n".join(f"- {line}" for line in best_lines)


def extract_candidate_lines(text: str) -> list[str]:
    raw_lines = re.split(r"\n+|•|- ", text)

    candidates: list[str] = []
    for raw_line in raw_lines:
        line = normalize_whitespace(raw_line)
        if not line:
            continue

        lower = line.lower()
        if (
            len(line) >= 8
            and (
                "must" in lower
                or "should" in lower
                or "submit" in lower
                or "include" in lower
                or "application" in lower
                or "action item" in lower
                or "instruction" in lower
                or "requirement" in lower
                or "user interaction" in lower
            )
        ):
            candidates.append(line)

    if not candidates:
        candidates = split_sentences(text)

    return deduplicate_preserving_order(candidates)


def rank_lines(question: str, lines: list[str]) -> list[str]:
    question_tokens = tokenize(question)
    scored: list[tuple[float, str]] = []

    for line in lines:
        line_tokens = tokenize(line)
        overlap = len(question_tokens.intersection(line_tokens))

        lower = line.lower()
        bonus = 0.0
        if any(term in question.lower() for term in {"action", "requirement", "task", "list"}):
            if any(term in lower for term in {"must", "submit", "include", "instruction", "requirement"}):
                bonus += 3.0

        score = overlap + bonus
        if score > 0:
            scored.append((score, line))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [line for _, line in scored]


def rank_sentences(question: str, sentences: list[str]) -> list[str]:
    question_tokens = tokenize(question)
    scored_sentences: list[tuple[float, str]] = []

    for sentence in sentences:
        sentence_tokens = tokenize(sentence)
        if not sentence_tokens:
            continue

        overlap = len(question_tokens.intersection(sentence_tokens))
        lower = sentence.lower()
        bonus = 0.0

        q_lower = question.lower()
        if any(term in q_lower for term in {"purpose", "objective", "about", "summary"}):
            if any(term in lower for term in {"objective", "overview", "this assignment", "purpose"}):
                bonus += 3.0

        if any(term in q_lower for term in {"framework", "react", "vue", "javascript"}):
            if any(term in lower for term in {"react", "vue", "javascript framework"}):
                bonus += 3.0

        if any(term in q_lower for term in {"deadline", "due", "week"}):
            if any(term in lower for term in {"due date", "week"}):
                bonus += 3.0

        score = overlap + bonus
        if score > 0:
            scored_sentences.append((score, sentence))

    scored_sentences.sort(key=lambda item: item[0], reverse=True)
    return [sentence for _, sentence in scored_sentences]


def split_sentences(text: str) -> list[str]:
    raw_sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
    sentences = [normalize_whitespace(sentence) for sentence in raw_sentences]
    return [sentence for sentence in sentences if sentence]


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def deduplicate_preserving_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []

    for item in items:
        cleaned = normalize_whitespace(item)
        if not cleaned:
            continue

        key = cleaned.lower()
        if key not in seen:
            seen.add(key)
            output.append(cleaned)

    return output
