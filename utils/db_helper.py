import json
import sqlite3
from typing import Any


def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str) -> None:
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_type TEXT NOT NULL,
            raw_text TEXT NOT NULL,
            cleaned_text TEXT NOT NULL,
            summary TEXT,
            extracted_info TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            user_question TEXT NOT NULL,
            chatbot_answer TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES documents (id)
        )
    """)

    conn.commit()
    conn.close()


def save_document(
    db_path: str,
    file_name: str,
    file_path: str,
    file_type: str,
    raw_text: str,
    cleaned_text: str,
    summary: str,
    extracted_info: dict[str, Any],
) -> int:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO documents (
            file_name, file_path, file_type, raw_text, cleaned_text, summary, extracted_info
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        file_name,
        file_path,
        file_type,
        raw_text,
        cleaned_text,
        summary,
        json.dumps(extracted_info),
    ))
    conn.commit()
    doc_id = cursor.lastrowid
    conn.close()
    return int(doc_id)


def get_document(db_path: str, doc_id: int) -> dict[str, Any] | None:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    document = dict(row)
    try:
        document["extracted_info"] = json.loads(document["extracted_info"] or "{}")
    except json.JSONDecodeError:
        document["extracted_info"] = {}

    return document


def save_chat_message(
    db_path: str,
    document_id: int,
    user_question: str,
    chatbot_answer: str,
) -> None:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chat_history (document_id, user_question, chatbot_answer)
        VALUES (?, ?, ?)
    """, (document_id, user_question, chatbot_answer))
    conn.commit()
    conn.close()


def get_chat_history(db_path: str, document_id: int) -> list[dict[str, Any]]:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM chat_history
        WHERE document_id = ?
        ORDER BY id ASC
    """, (document_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
