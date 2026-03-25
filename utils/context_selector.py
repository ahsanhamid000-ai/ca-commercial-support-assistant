import re
from typing import Iterable


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have",
    "how", "in", "into", "is", "it", "its", "of", "on", "or", "that", "the", "their",
    "this", "to", "was", "were", "what", "when", "where", "which", "who", "why", "with",
    "your", "you", "about", "tell", "me", "please", "do", "does", "did", "can", "could",
    "should", "would", "will", "may", "might", "than", "then", "there", "here", "also",
    "only", "just", "any", "all", "if", "but", "we", "our", "they", "them", "he", "she",
    "his", "her", "themself", "themselves", "i", "my", "mine", "ours", "yours"
}

SYNONYM_GROUPS = {
    "purpose": {
        "purpose", "objective", "aim", "main", "overview", "about", "summary",
        "describe", "description", "goal", "intent"
    },
    "action": {
        "action", "actions", "task", "tasks", "todo", "todos", "steps",
        "requirements", "instruction", "instructions", "must", "submit",
        "include", "required", "deliverables"
    },
    "deadline": {
        "deadline", "deadlines", "due", "date", "dates", "schedule", "week", "submit"
    },
    "framework": {
        "framework", "react", "vue", "javascript", "frontend", "library"
    },
    "approval": {
        "approve", "approval", "approver", "responsible", "owner", "authorised", "authorized"
    },
}


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def tokenize(text: str) -> set[str]:
    if not text:
        return set()

    raw_tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
    tokens = {token for token in raw_tokens if token and token not in STOPWORDS}

    expanded = set(tokens)
    for token in list(tokens):
        for canonical, variants in SYNONYM_GROUPS.items():
            if token in variants:
                expanded.update(variants)
                expanded.add(canonical)

    return expanded


def split_into_paragraphs(text: str) -> list[str]:
    if not text:
        return []

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    raw_parts = re.split(r"\n\s*\n+", normalized)

    paragraphs: list[str] = []
    for part in raw_parts:
        cleaned = normalize_whitespace(part)
        if cleaned:
            paragraphs.append(cleaned)

    return paragraphs


def build_chunks(text: str, window_size: int = 2) -> list[str]:
    paragraphs = split_into_paragraphs(text)
    if not paragraphs:
        cleaned = normalize_whitespace(text)
        return [cleaned] if cleaned else []

    chunks: list[str] = []

    # Single-paragraph chunks
    chunks.extend(paragraphs)

    # Sliding-window chunks to preserve nearby context
    if len(paragraphs) > 1 and window_size > 1:
        for i in range(len(paragraphs)):
            window = paragraphs[i:i + window_size]
            if len(window) > 1:
                chunk = " ".join(window).strip()
                if chunk:
                    chunks.append(chunk)

    # Sentence-window chunks as a fallback for dense OCR text
    sentences = split_sentences(text)
    if len(sentences) > 3:
        for i in range(0, len(sentences), 3):
            chunk = " ".join(sentences[i:i + 3]).strip()
            if chunk:
                chunks.append(chunk)

    return deduplicate_preserving_order(chunks)


def split_sentences(text: str) -> list[str]:
    if not text:
        return []

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    raw_sentences = re.split(r"(?<=[.!?])\s+|\n+", normalized)

    sentences: list[str] = []
    for sentence in raw_sentences:
        cleaned = normalize_whitespace(sentence)
        if cleaned:
            sentences.append(cleaned)

    return sentences


def deduplicate_preserving_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []

    for item in items:
        normalized = normalize_whitespace(item)
        if not normalized:
            continue
        key = normalized.lower()
        if key not in seen:
            seen.add(key)
            output.append(normalized)

    return output


def score_chunk(question: str, chunk: str) -> float:
    if not question or not chunk:
        return 0.0

    question_tokens = tokenize(question)
    chunk_tokens = tokenize(chunk)

    if not question_tokens or not chunk_tokens:
        return 0.0

    overlap = question_tokens.intersection(chunk_tokens)
    overlap_score = float(len(overlap))

    question_lower = question.lower()
    chunk_lower = chunk.lower()

    phrase_bonus = 0.0

    if any(term in question_lower for term in {"main purpose", "purpose", "objective", "about", "summary"}):
        if any(term in chunk_lower for term in {"assessment objective", "objective", "overview", "this assignment", "purpose"}):
            phrase_bonus += 5.0

    if any(term in question_lower for term in {"action items", "actions", "requirements", "tasks", "list"}):
        if any(term in chunk_lower for term in {"action items", "instructions", "must", "submit", "include", "requirements"}):
            phrase_bonus += 5.0

    if any(term in question_lower for term in {"framework", "react", "vue", "javascript"}):
        if any(term in chunk_lower for term in {"react", "vue", "javascript framework", "frontend"}):
            phrase_bonus += 4.0

    if any(term in question_lower for term in {"deadline", "due date", "when due", "week"}):
        if any(term in chunk_lower for term in {"due date", "week", "deadline"}):
            phrase_bonus += 4.0

    # Reward chunks with slightly better density of matched terms
    density_bonus = len(overlap) / max(len(chunk_tokens), 1) * 10.0

    return overlap_score + phrase_bonus + density_bonus


def select_relevant_chunks(question: str, document_text: str, top_k: int = 4) -> str:
    chunks = build_chunks(document_text)
    if not chunks:
        return ""

    scored: list[tuple[float, str]] = []
    for chunk in chunks:
        score = score_chunk(question, chunk)
        if score > 0:
            scored.append((score, chunk))

    if not scored:
        # Fallback: return the opening portion of the document instead of blank
        return "\n\n".join(chunks[: max(1, min(top_k, 2))])

    scored.sort(key=lambda item: item[0], reverse=True)
    selected = [chunk for _, chunk in scored[:top_k]]

    return "\n\n".join(deduplicate_preserving_order(selected))
