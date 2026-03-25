from openai import OpenAI


def generate_summary(text: str, api_key: str) -> str:
    if not api_key:
        return fallback_summary(text)

    try:
        client = OpenAI(api_key=api_key)
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
                    "content": f"Summarize this document:\n\n{text[:12000]}",
                },
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return fallback_summary(text)


def fallback_summary(text: str) -> str:
    short_text = text.strip().replace("\n", " ")
    if len(short_text) > 500:
        return short_text[:500] + "..."
    return short_text
