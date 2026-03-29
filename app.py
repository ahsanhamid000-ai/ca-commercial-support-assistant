import logging
import os
import re
import sqlite3
import time
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, flash, g, jsonify, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from utils.qa_engine import (
    NOT_FOUND_MESSAGE,
    answer_question,
    answer_with_ai_fallback,
    extract_action_items,
    generate_executive_summary_points,
    sanitize_document_text,
)


BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
UPLOAD_FOLDER = BASE_DIR / "uploads"
DATABASE_PATH = INSTANCE_DIR / "assistant.db"

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-this-secret-key")
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["DATABASE_PATH"] = str(DATABASE_PATH)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        conn = sqlite3.connect(app.config["DATABASE_PATH"])
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            stored_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            document_text TEXT NOT NULL,
            summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            user_question TEXT NOT NULL,
            chatbot_answer TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
        )
        """
    )

    db.commit()


with app.app_context():
    init_db()


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(file_storage) -> tuple[str, Path]:
    original_name = secure_filename(file_storage.filename or "document")
    timestamp_name = f"{int(time.time() * 1000)}_{original_name}"
    destination = UPLOAD_FOLDER / timestamp_name
    file_storage.save(destination)
    return original_name, destination


def extract_text_from_file(file_path: Path) -> str:
    suffix = file_path.suffix.lower()

    if suffix == ".txt":
        return extract_text_from_txt(file_path)

    if suffix == ".pdf":
        return extract_text_from_pdf(file_path)

    if suffix == ".docx":
        return extract_text_from_docx(file_path)

    raise ValueError("Unsupported file type.")


def extract_text_from_txt(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8", errors="ignore")


def extract_text_from_pdf(file_path: Path) -> str:
    text_parts: list[str] = []

    try:
        from pypdf import PdfReader
    except Exception:
        try:
            from PyPDF2 import PdfReader
        except Exception as exc:
            raise RuntimeError("PDF support requires pypdf or PyPDF2 to be installed.") from exc

    reader = PdfReader(str(file_path))
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text.strip():
            text_parts.append(page_text)

    return "\n".join(text_parts)


def extract_text_from_docx(file_path: Path) -> str:
    try:
        from docx import Document
    except Exception as exc:
        raise RuntimeError("DOCX support requires python-docx to be installed.") from exc

    doc = Document(str(file_path))
    paragraphs = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
    return "\n".join(paragraphs)


def normalize_document_text(text: str) -> str:
    lines = []
    for raw_line in (text or "").splitlines():
        line = " ".join(raw_line.split()).strip()
        if line:
            lines.append(line)
    return "\n".join(lines).strip()


def dedupe_keep_order(items: list[str]) -> list[str]:
    seen = set()
    output = []

    for item in items:
        cleaned = " ".join((item or "").split()).strip()
        if not cleaned:
            continue

        key = cleaned.lower()
        if key not in seen:
            seen.add(key)
            output.append(cleaned)

    return output


def build_structured_summary(document_text: str) -> str:
    cleaned = sanitize_document_text(document_text or "")
    if not cleaned:
        return "No summary available."

    points = generate_executive_summary_points(cleaned)

    if not points:
        fallback = []
        for sentence in re.split(r"(?<=[.!?])\s+", cleaned):
            sentence = sentence.strip()
            if len(sentence) >= 35:
                fallback.append(sentence)
        points = fallback[:6]

    if not points:
        return "No summary available."

    return "\n".join(f"- {point}" for point in points[:8])


def build_summary(document_text: str) -> str:
    return build_structured_summary(document_text)


def extract_report_data(document_text: str) -> dict:
    cleaned = sanitize_document_text(document_text or "")

    date_patterns = [
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b",
        r"\bweek\s+\d+\b",
    ]

    dates: list[str] = []
    for pattern in date_patterns:
        dates.extend(re.findall(pattern, cleaned, flags=re.IGNORECASE))

    emails = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", cleaned)
    amounts = re.findall(r"(?:\$|USD\s*)\d[\d,]*(?:\.\d{2})?", cleaned, flags=re.IGNORECASE)
    action_items = extract_action_items(cleaned)

    preview = cleaned[:1400].strip()
    if len(cleaned) > 1400:
        preview += "..."

    return {
        "dates": dedupe_keep_order(dates),
        "emails": dedupe_keep_order(emails),
        "amounts": dedupe_keep_order(amounts),
        "action_items": dedupe_keep_order(action_items),
        "preview": preview,
    }


def insert_document(file_name: str, stored_name: str, file_path: Path, document_text: str) -> int:
    db = get_db()
    summary = build_summary(document_text)

    cursor = db.execute(
        """
        INSERT INTO documents (file_name, stored_name, file_path, document_text, summary)
        VALUES (?, ?, ?, ?, ?)
        """,
        (file_name, stored_name, str(file_path), document_text, summary),
    )
    db.commit()
    return int(cursor.lastrowid)


def get_document(document_id: int):
    db = get_db()
    return db.execute(
        "SELECT * FROM documents WHERE id = ?",
        (document_id,),
    ).fetchone()


def get_recent_documents(limit: int = 10):
    db = get_db()
    return db.execute(
        """
        SELECT id, file_name, created_at
        FROM documents
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def get_chat_history(document_id: int):
    db = get_db()
    return db.execute(
        """
        SELECT user_question, chatbot_answer, created_at
        FROM chat_history
        WHERE document_id = ?
        ORDER BY id ASC
        """,
        (document_id,),
    ).fetchall()


def insert_chat_history(document_id: int, question: str, answer: str):
    db = get_db()
    db.execute(
        """
        INSERT INTO chat_history (document_id, user_question, chatbot_answer)
        VALUES (?, ?, ?)
        """,
        (document_id, question, answer),
    )
    db.commit()


def append_ai_answer_to_latest_not_found(document_id: int, question: str, ai_answer: str) -> bool:
    db = get_db()
    row = db.execute(
        """
        SELECT id, chatbot_answer
        FROM chat_history
        WHERE document_id = ? AND user_question = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (document_id, question),
    ).fetchone()

    if row is None:
        return False

    current_answer = (row["chatbot_answer"] or "").strip()
    if not current_answer:
        return False

    if current_answer == NOT_FOUND_MESSAGE:
        combined_answer = f"{current_answer}\n\n{ai_answer}"
    elif ai_answer not in current_answer:
        combined_answer = f"{current_answer}\n\n{ai_answer}"
    else:
        return True

    db.execute(
        "UPDATE chat_history SET chatbot_answer = ? WHERE id = ?",
        (combined_answer, row["id"]),
    )
    db.commit()
    return True


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        return handle_upload_request()

    documents = get_recent_documents()
    return render_template("index.html", documents=documents)


@app.route("/upload", methods=["POST"])
def upload():
    return handle_upload_request()


def handle_upload_request():
    file_storage = request.files.get("document") or request.files.get("file")

    if not file_storage or not file_storage.filename:
        flash("Please choose a file to upload.", "error")
        return redirect(url_for("index"))

    if not allowed_file(file_storage.filename):
        flash("Only PDF, DOCX, and TXT files are allowed.", "error")
        return redirect(url_for("index"))

    try:
        original_name, saved_path = save_uploaded_file(file_storage)
        raw_text = extract_text_from_file(saved_path)
        document_text = normalize_document_text(raw_text)

        if not document_text:
            flash("The uploaded document could not be processed correctly.", "error")
            return redirect(url_for("index"))

        document_id = insert_document(
            file_name=original_name,
            stored_name=saved_path.name,
            file_path=saved_path,
            document_text=document_text,
        )

        return redirect(url_for("result", document_id=document_id))

    except Exception as exc:
        logger.exception("Upload failed: %s", exc)
        flash(f"Upload failed: {exc}", "error")
        return redirect(url_for("index"))


@app.route("/chat/<int:document_id>", methods=["GET"])
def chat(document_id: int):
    document = get_document(document_id)
    if document is None:
        flash("Document not found.", "error")
        return redirect(url_for("index"))

    chat_history = get_chat_history(document_id)

    return render_template(
        "chat.html",
        document=dict(document),
        chat_history=[dict(row) for row in chat_history],
    )


@app.route("/ask/<int:document_id>", methods=["POST"])
def ask(document_id: int):
    document = get_document(document_id)
    if document is None:
        return jsonify({"success": False, "message": "Document not found."}), 404

    question = (request.form.get("question") or "").strip()
    mode = (request.form.get("mode") or "document").strip().lower()

    if not question:
        return jsonify({"success": False, "message": "Please enter a question."}), 400

    document_text = document["document_text"] or ""

    try:
        if mode == "ai":
            answer = answer_with_ai_fallback(question, document_text, OPENAI_API_KEY)

            updated_existing = append_ai_answer_to_latest_not_found(
                document_id=document_id,
                question=question,
                ai_answer=answer,
            )

            if not updated_existing:
                insert_chat_history(document_id, question, answer)

            return jsonify(
                {
                    "success": True,
                    "answer": answer,
                    "not_found": False,
                    "mode": "ai",
                }
            )

        answer = answer_question(question, document_text, OPENAI_API_KEY)
        insert_chat_history(document_id, question, answer)

        return jsonify(
            {
                "success": True,
                "answer": answer,
                "not_found": answer == NOT_FOUND_MESSAGE,
                "mode": "document",
            }
        )

    except Exception as exc:
        logger.exception("Ask route failed: %s", exc)
        return jsonify(
            {
                "success": False,
                "message": "The chatbot could not answer right now.",
            }
        ), 500


@app.route("/result/<int:document_id>", methods=["GET"])
def result(document_id: int):
    document = get_document(document_id)
    if document is None:
        flash("Document not found.", "error")
        return redirect(url_for("index"))

    document_dict = dict(document)
    structured_summary = build_structured_summary(document_dict.get("document_text", ""))

    return render_template(
        "result.html",
        document=document_dict,
        structured_summary=structured_summary,
    )


@app.route("/report/<int:document_id>", methods=["GET"])
def report(document_id: int):
    document = get_document(document_id)
    if document is None:
        flash("Document not found.", "error")
        return redirect(url_for("index"))

    document_dict = dict(document)
    document_text = document_dict.get("document_text", "")

    structured_summary = build_structured_summary(document_text)
    report_data = extract_report_data(document_text)

    return render_template(
        "report.html",
        document=document_dict,
        structured_summary=structured_summary,
        report_data=report_data,
    )


if __name__ == "__main__":
    app.run(debug=True)
