import re


def extract_key_information(text: str) -> dict:
    dates = extract_dates(text)
    emails = extract_emails(text)
    amounts = extract_amounts(text)
    action_items = extract_action_items(text)

    return {
        "dates": dates,
        "emails": emails,
        "amounts": amounts,
        "action_items": action_items,
    }


def extract_dates(text: str) -> list[str]:
    patterns = [
        r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}, \d{4}\b",
    ]
    matches = []
    for pattern in patterns:
        matches.extend(re.findall(pattern, text, flags=re.IGNORECASE))
    return list(dict.fromkeys(matches))


def extract_emails(text: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)))


def extract_amounts(text: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"(?:\$|USD\s?)\d[\d,]*(?:\.\d{2})?", text, flags=re.IGNORECASE)))


def extract_action_items(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    keywords = ("must", "should", "required", "action", "deadline", "submit", "review", "approve")
    results = [line for line in lines if any(keyword in line.lower() for keyword in keywords)]
    return results[:10]
