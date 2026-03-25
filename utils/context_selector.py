import re
from utils.cleaner import chunk_text

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
    "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "was",
    "what", "when", "where", "which", "who", "why", "with", "about", "into",
    "does", "do", "did", "can", "could", "would", "should", "will", "shall",
    "please", "tell", "me", "we", "our", "you", "your"
}


def tokenize(text: str) -> set[str]:
    tokens = re.findall(r"\b[a-zA-Z0-9]+\b", text.lower())
    return {token for token in tokens if len(token) > 2 and token not in STOPWORDS}


def score_chunk(question_tokens: set[str], chunk: str) -> int:
    chunk_tokens = tokenize(chunk)
    overlap_score = len(question_tokens.intersection(chunk_tokens))

    phrase_bonus = 0
    lowered_chunk = chunk.lower()
    for token in question_tokens:
        if token in lowered_chunk:
            phrase_bonus += 1

    return overlap_score + phrase_bonus


def select_relevant_chunks(question: str, document_text: str, top_k: int = 2) -> str:
    chunks = chunk_text(document_text, chunk_size=1600, overlap=250)
    if not chunks:
        return ""

    question_tokens = tokenize(question)
    if not question_tokens:
        return chunks[0]

    scored_chunks: list[tuple[int, str]] = []
    for chunk in chunks:
        score = score_chunk(question_tokens, chunk)
        scored_chunks.append((score, chunk))

    scored_chunks.sort(key=lambda item: item[0], reverse=True)

    selected = [chunk for score, chunk in scored_chunks[:top_k] if score > 0]
    if not selected:
        return chunks[0]

    return "\n\n".join(selected)
