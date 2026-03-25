import re
from openai import OpenAI

from utils.cleaner import chunk_text

MAX_CHUNK_SIZE = 3500
CHUNK_OVERLAP = 300
MAX_CHUNKS = 6


def generate_summary(text: str, api_key: str) -> str:
    normalized = text.strip()
    if not normalized:
        return "No summary is available because the document content is empty."

    if not api_key:
        return fallback_summary(normalized)

    try:
        client = OpenAI(api_key=api_key)
        chunks = chunk_text(
            normalized,
            chunk_size=MAX_CHUNK_SIZE,
            overlap=CHUNK_OVERLAP,
        )[:MAX_CHUNKS]

        if len(chunks) == 1:
            return summarize_single_chunk(client, chunks[0])

        chunk_summaries: list[str] = []
        for index, chunk in enumerate(chunks, start=1):
            chunk_summary = summarize_chunk(
                client=client,
                chunk=chunk,
                part_number=index,
                total_parts=len(chunks),
            )
            if chunk_summary:
                chunk_summaries.append(chunk_summary)

        if not chunk_summaries:
            return fallback_summary(normalized)

        combined_summary = "\n".join(f"- {item}" for item in chunk_summaries)

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a professional commercial document summarizer. "
                        "Create a concise executive summary in 6-8 sentences. "
                        "Keep it accurate, business-focused, and avoid repetition."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Combine the following partial summaries into one final "
                        f"executive summary:\n\n{combined_summary}"
                    ),
                },
            ],
        )

        final_summary = response.choices[0].message.content
        return final_summary.strip() if final_summary else fallback_summary(normalized)

    except Exception:
        return fallback_summary(normalized)


def summarize_single_chunk(client: OpenAI, chunk: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a professional commercial document summarizer. "
                    "Generate a concise executive summary in 5-8 sentences."
                ),
            },
            {
                "role": "user",
                "content": f"Summarize this document:\n\n{chunk}",
            },
        ],
    )
    content = response.choices[0].message.content
    return content.strip() if content else fallback_summary(chunk)


def summarize_chunk(client: OpenAI, chunk: str, part_number: int, total_parts: int) -> str:
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are summarizing one section of a commercial document. "
                    "Produce 3-4 sentences focused on important facts, obligations, "
                    "dates, money, approvals, and action items."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"This is part {part_number} of {total_parts}.\n\n"
                    f"Summarize the following section:\n\n{chunk}"
                ),
            },
        ],
    )
    content = response.choices[0].message.content
    return content.strip() if content else ""


def fallback_summary(text: str) -> str:
    flattened = re.sub(r"\s+", " ", text).strip()
    if not flattened:
        return "No summary is available because the document content is empty."

    sentences = re.split(r"(?<=[.!?])\s+", flattened)
    selected = [sentence.strip() for sentence in sentences if sentence.strip()][:4]

    if selected:
        return " ".join(selected)

    if len(flattened) > 700:
        return flattened[:700].rstrip() + "..."
    return flattened
