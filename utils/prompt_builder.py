def build_qa_prompt(context: str, question: str) -> str:
    return f"""
You are a commercial support assistant.

Answer only using the uploaded document context below.
Do not invent facts.
If the answer is not present in the context, reply exactly:
"The requested information was not found in the uploaded document."

Document Context:
{context}

User Question:
{question}
""".strip()
