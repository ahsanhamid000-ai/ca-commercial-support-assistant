import logging
from typing import Optional

import requests
from openai import OpenAI


logger = logging.getLogger(__name__)


def answer_general_openai(question: str, api_key: Optional[str]) -> str:
    question = (question or "").strip()

    if not question:
        return "Please enter a question."

    if not api_key:
        return "OpenAI fallback is not configured. Please add OPENAI_API_KEY to your environment or config."

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a concise and helpful assistant. "
                        "Answer clearly and directly. "
                        "If the question is broad, give a short structured answer."
                    ),
                },
                {
                    "role": "user",
                    "content": question,
                },
            ],
        )

        if response.choices and response.choices[0].message:
            return (response.choices[0].message.content or "").strip() or "No answer was returned."

        return "No answer was returned."

    except Exception as exc:
        logger.exception("OpenAI general QA failed: %s", exc)
        return "OpenAI could not answer the question right now."


def search_google(
    question: str,
    google_api_key: Optional[str],
    google_cse_id: Optional[str],
    max_results: int = 3,
) -> str:
    question = (question or "").strip()

    if not question:
        return "Please enter a question."

    if not google_api_key or not google_cse_id:
        return (
            "Google search fallback is not configured. "
            "Please add GOOGLE_API_KEY and GOOGLE_CSE_ID to your environment or config."
        )

    try:
        response = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key": google_api_key,
                "cx": google_cse_id,
                "q": question,
                "num": max_results,
            },
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()

        items = data.get("items", [])
        if not items:
            return "Google search did not find any useful results."

        blocks = ["Google search results:"]
        for item in items[:max_results]:
            title = (item.get("title") or "").strip()
            snippet = (item.get("snippet") or "").strip()
            link = (item.get("link") or "").strip()

            line = f"- {title}" if title else "- Result"
            if snippet:
                line += f": {snippet}"
            if link:
                line += f"\n  {link}"

            blocks.append(line)

        return "\n".join(blocks)

    except Exception as exc:
        logger.exception("Google search failed: %s", exc)
        return "Google search could not answer the question right now."
