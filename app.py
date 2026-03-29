import logging
import re
import sqlite3
import time
from io import BytesIO
from pathlib import Path

from flask import (
    Flask,
    abort,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from config import Config
from utils.qa_engine import (
    NOT_FOUND_MESSAGE,
    answer_question,
    answer_with_ai_fallback,
    generate_executive_summary_points,
    sanitize_document_text,
)
from utils.report_generator import build_report_data, build_report_pdf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        conn = sqlite3.connect(current_app.config["DATABASE_PATH"])
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db


def close_db(_error=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
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


def allowed_file(filename: str) -> bool:
    allowed_extensions = current_app.config.get("ALLOWED_EXTENSIONS", set())
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


def save_uploaded_file(file_storage) -> tuple[str, Path]:
    original_name = secure_filename(file_storage.filename or "document")
    timestamp_name = f"{int(time.time() * 1000)}_{original_name}"
    upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
    destination = upload_folder / timestamp_name
    file_storage.save(destination)
    return original_name, destination


def cleanup_file(path: Path | None) -> None:
    if path and path.exists():
        try:
            path.unlink()
        except OSError:
            logger.warning("Could not remove file: %s", path)


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
    try:
        return file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        logger.exception("TXT parsing failed: %s", exc)
        return ""


def extract_text_from_pdf(file_path: Path) -> str:
    text_parts: list[str] = []

    try:
        from pypdf import PdfReader
    except Exception:
        try:
            from PyPDF2 import PdfReader
        except Exception as exc:
            raise RuntimeError("PDF support requires pypdf or PyPDF2.") from exc

    try:
        reader = PdfReader(str(file_path))
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                text_parts.append(page_text)
    except Exception as exc:
        logger.exception("PDF parsing failed: %s", exc)
        return ""

    return "\n".join(text_parts)


def extract_text_from_docx(file_path: Path) -> str:
    try:
        from docx import Document
    except Exception as exc:
        raise RuntimeError("DOCX support requires python-docx.") from exc

    try:
        doc = Document(str(file_path))
        paragraphs = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
        return "\n".join(paragraphs)
    except Exception as exc:
        logger.exception("DOCX parsing failed: %s", exc)
        return ""


def normalize_document_text(text: str) -> str:
    lines = []
    for raw_line in (text or "").splitlines():
        line = " ".join(raw_line.split()).strip()
        if line:
            lines.append(line)
    return "\n".join(lines).strip()


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


def get_safe_upload_path(filename: str) -> Path:
    upload_root = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    requested_path = (upload_root / filename).resolve()

    if upload_root not in requested_path.parents and requested_path != upload_root:
        abort(404)

    if not requested_path.exists() or not requested_path.is_file():
        abort(404)

    return requested_path


def get_document_file_path(document: dict) -> Path:
    existing_path = document.get("file_path")
    if existing_path:
        existing_path_obj = Path(existing_path)
        if existing_path_obj.exists():
            return existing_path_obj

    stored_name = document.get("stored_name", "")
    return get_safe_upload_path(stored_name)


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


def insert_chat_history(document_id: int, question: str, answer: str) -> None:
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


def handle_upload_request():
    file_storage = request.files.get("document") or request.files.get("file")

    if not file_storage or not file_storage.filename:
        flash("Please choose a file to upload.", "error")
        return redirect(url_for("index"))

    if not allowed_file(file_storage.filename):
        flash("Only PDF, DOCX, and TXT files are allowed.", "error")
        return redirect(url_for("index"))

    saved_path = None

    try:
        original_name, saved_path = save_uploaded_file(file_storage)
        raw_text = extract_text_from_file(saved_path)
        document_text = normalize_document_text(raw_text)

        if not document_text:
            cleanup_file(saved_path)
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
        cleanup_file(saved_path)
        flash("Upload failed. Please try another file.", "error")
        return redirect(url_for("index"))


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["INSTANCE_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["DATABASE_PATH"]).parent.mkdir(parents=True, exist_ok=True)

    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()

    @app.errorhandler(RequestEntityTooLarge)
    def handle_large_file(_error):
        return (
            render_template(
                "error.html",
                message="The uploaded file is too large. Maximum allowed size is 16 MB.",
            ),
            413,
        )

    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename: str):
        file_path = get_safe_upload_path(filename)
        return send_file(
            file_path,
            as_attachment=False,
            conditional=True,
            download_name=file_path.name,
            max_age=0,
        )

    @app.route("/preview-page/<path:filename>/<int:page_number>")
    def preview_pdf_page(filename: str, page_number: int):
        file_path = get_safe_upload_path(filename)

        if file_path.suffix.lower() != ".pdf" or page_number < 1:
            abort(404)

        try:
            import fitz
        except Exception:
            abort(500)

        pdf = fitz.open(str(file_path))
        try:
            if page_number > pdf.page_count:
                abort(404)

            page = pdf.load_page(page_number - 1)
            matrix = fitz.Matrix(1.5, 1.5)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            image_bytes = pix.tobytes("png")
        finally:
            pdf.close()

        response = send_file(
            BytesIO(image_bytes),
            mimetype="image/png",
            as_attachment=False,
            download_name=f"{file_path.stem}_page_{page_number}.png",
            max_age=0,
        )
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        return response

    @app.route("/", methods=["GET", "POST"])
    def index():
        if request.method == "POST":
            return handle_upload_request()

        documents = get_recent_documents()
        return render_template("index.html", documents=documents)

    @app.route("/upload", methods=["POST"])
    def upload():
        return handle_upload_request()

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
            api_key_available=bool(current_app.config.get("OPENAI_API_KEY")),
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
        api_key = current_app.config.get("OPENAI_API_KEY", "")

        try:
            if mode == "ai":
                if not api_key:
                    return jsonify(
                        {
                            "success": False,
                            "message": "AI fallback is not available right now.",
                        }
                    ), 400

                answer = answer_with_ai_fallback(question, document_text, api_key)

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
                        "ai_fallback_available": True,
                    }
                )

            answer = answer_question(question, document_text, api_key)
            insert_chat_history(document_id, question, answer)

            return jsonify(
                {
                    "success": True,
                    "answer": answer,
                    "not_found": answer == NOT_FOUND_MESSAGE,
                    "mode": "document",
                    "ai_fallback_available": bool(api_key),
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
        structured_summary = document_dict.get("summary") or build_structured_summary(
            document_dict.get("document_text", "")
        )

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
        structured_summary = document_dict.get("summary") or build_structured_summary(
            document_dict.get("document_text", "")
        )

        report_data = build_report_data(
            document_dict,
            file_path=get_document_file_path(document_dict),
        )

        return render_template(
            "report.html",
            document=document_dict,
            structured_summary=structured_summary,
            report_data=report_data,
        )

    @app.route("/report/<int:document_id>/download", methods=["GET"])
    def download_report(document_id: int):
        document = get_document(document_id)
        if document is None:
            flash("Document not found.", "error")
            return redirect(url_for("index"))

        document_dict = dict(document)
        structured_summary = document_dict.get("summary") or build_structured_summary(
            document_dict.get("document_text", "")
        )

        report_data = build_report_data(
            document_dict,
            file_path=get_document_file_path(document_dict),
        )
        report_data["summary"] = structured_summary

        pdf_buffer = build_report_pdf(report_data)
        stem = Path(document_dict.get("file_name", f"report_{document_id}")).stem

        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=f"{stem}_report.pdf",
            mimetype="application/pdf",
        )

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
