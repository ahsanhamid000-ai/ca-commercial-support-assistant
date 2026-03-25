NOT_FOUND_MESSAGE = "The requested information was not found in the uploaded document."


def build_qa_prompt(context: str, question: str) -> str:
    return f"""
You must answer ONLY from the document context below.

Rules:
1. Do not use outside knowledge.
2. If the answer is clearly present, answer directly and clearly.
3. If the user asks for a list, return a bullet list.
4. If the answer is not present in the context, reply exactly with:
{NOT_FOUND_MESSAGE}

Question:
{question}

Document Context:
{context}

Now provide the final answer.
""".strip()
