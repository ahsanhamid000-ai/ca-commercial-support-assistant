import re
from utils.cleaner import chunk_text


def tokenize(text: str) -> set[str]:
    return set(re.findall(r"\b[a-zA-Z0-9]+\b", text.lower()))


def select_relevant_chunks(question: str, document_text: str, top_k: int = 3) -> str:
    chunks = chunk_text(document_text, chunk_size=1500, overlap=200)
    question_tokens = tokenize(question)

    scored_chunks: list[tuple[int, str]] = []
    for chunk in chunks:
        chunk_tokens = tokenize(chunk)
        score = len(question_tokens.intersection(chunk_tokens))
        scored_chunks.append((score, chunk))

    scored_chunks.sort(key=lambda item: item[0], reverse=True)
    selected = [chunk for score, chunk in scored_chunks[:top_k] if score > 0]

    if not selected:
        return chunks[0] if chunks else ""

    return "\n\n".join(selected)
