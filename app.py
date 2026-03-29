import logging
import os

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from werkzeug.exceptions import RequestEntityTooLarge

from config import Config
from utils.file_handler import allowed_file, save_uploaded_file
from utils.parser import extract_text
from utils.cleaner import clean_text
from utils.validators import validate_question, validate_extracted_text
from utils.db_helper import (
    init_db,
    save_document,
    get_document,
    save_chat_message,
    get_chat_history,
)
from utils.summarizer import generate_summary
from utils.extractor import extract_key_information
from utils.report_generator import build_report_data, build_report_pdf
from utils.qa_engine import answer_question
from utils.general_qa import answer_general_openai, search_google

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NOT_FOUND_MESSAGE = "The requested information was not found in the uploaded document."

PRESET_QUESTIONS = [
    "What is the main purpose of this document?",
    "Summarize the important points.",
    "What framework is required?",
    "Are any deadlines mentioned?",
    "What action items are listed?",
    "Who is responsible for approval?",
]


def cleanup_file(path: str | None) -> None:
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            logger.warning("Could not remove file: %s", path)


def is_not_found_answer(answer: str) -> bool:
    normalized = (answer or "").strip().lower()
    return (not normalized) or (normalized == NOT_FOUND_MESSAGE.lower())


def resolve_custom_question(
    question: str,
    document_text: str,
    openai_api_key: str,
    google_api_key: str,
    google_cse_id: str,
    fallback_mode: str,
) -> tuple[str, str]:
    fallback_mode = (fallback_mode or "document_then_openai").strip()

    if fallback_mode == "openai_only":
        return answer_general_openai(question, openai_api_key), "OpenAI"

    if fallback_mode == "google_only":
        return search_google(question, google_api_key, google_cse_id), "Google"

    document_answer = answer_question(
        question=question,
        document_text=document_text,
        api_key=openai_api_key,
    )

    if not is_not_found_answer(document_answer):
        return document_answer, "Document"

    if fallback_mode == "document_then_google":
        return search_google(question, google_api_key, google_cse_id), "Google"

    return answer_general_openai(question, openai_api_key), "OpenAI"


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    # Optional fallback config if Config does not define these
    app.config["GOOGLE_API_KEY"] = app.config.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
    app.config["GOOGLE_CSE_ID"] = app.config.get("GOOGLE_CSE_ID") or os.getenv("GOOGLE_CSE_ID", "")

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    init_db(app.config["DATABASE_PATH"])

    @app.errorhandler(RequestEntityTooLarge)
    def handle_large_file(_error):
        return (
            render_template(
                "error.html",
                message="The uploaded file is too large. Maximum allowed size is 10 MB.",
            ),
            413,
        )

    @app.route("/", methods=["GET"])
    def index():
        return render_template("index.html")

    @app.route("/upload", methods=["POST"])
    def upload():
        file = request.files.get("document")

        if file is None or file.filename == "":
            flash("Please select a file before uploading.", "danger")
            return redirect(url_for("index"))

        if not allowed_file(file.filename, app.config["ALLOWED_EXTENSIONS"]):
            flash("Unsupported file type. Please upload PDF, DOCX, or TXT.", "danger")
            return redirect(url_for("index"))

        saved_path = None

        try:
            saved_path, original_name, extension = save_uploaded_file(
                file=file,
                upload_folder=app.config["UPLOAD_FOLDER"],
            )

            raw_text = extract_text(saved_path, extension)
            valid_text, text_message = validate_extracted_text(raw_text)

            if not valid_text:
                cleanup_file(saved_path)
                flash(text_message, "danger")
                return redirect(url_for("index"))

            cleaned_text = clean_text(raw_text)
            summary = generate_summary(cleaned_text, app.config["OPENAI_API_KEY"])
            extracted_info = extract_key_information(cleaned_text)

            doc_id = save_document(
                db_path=app.config["DATABASE_PATH"],
                file_name=original_name,
                file_path=saved_path,
                file_type=extension,
                raw_text=raw_text,
                cleaned_text=cleaned_text,
                summary=summary,
                extracted_info=extracted_info,
            )

            flash("Document uploaded and processed successfully.", "success")
            return redirect(url_for("result", doc_id=doc_id))

        except Exception as exc:
            logger.exception("Document upload/processing failed: %s", exc)
            cleanup_file(saved_path)
            flash(
                "An error occurred while processing the document. Please try another file.",
                "danger",
            )
            return redirect(url_for("index"))

    @app.route("/result/<int:doc_id>", methods=["GET"])
    def result(doc_id: int):
        document = get_document(app.config["DATABASE_PATH"], doc_id)
        if not document:
            return render_template("error.html", message="Document not found."), 404
        return render_template("result.html", document=document)

    @app.route("/chat/<int:doc_id>", methods=["GET"])
    def chat(doc_id: int):
        document = get_document(app.config["DATABASE_PATH"], doc_id)
        if not document:
            return render_template("error.html", message="Document not found."), 404

        chat_history = get_chat_history(app.config["DATABASE_PATH"], doc_id)

        return render_template(
            "chat.html",
            document=document,
            chat_history=chat_history,
            preset_questions=PRESET_QUESTIONS,
        )

    @app.route("/ask/<int:doc_id>", methods=["POST"])
    def ask(doc_id: int):
        document = get_document(app.config["DATABASE_PATH"], doc_id)
        if not document:
            return jsonify({"success": False, "message": "Document not found."}), 404

        question = request.form.get("question", "").strip()
        question_mode = request.form.get("question_mode", "preset").strip()
        fallback_mode = request.form.get("fallback_mode", "document_then_openai").strip()

        is_valid, error_message = validate_question(question)
        if not is_valid:
            return jsonify({"success": False, "message": error_message}), 400

        try:
            if question_mode == "custom":
                answer, source = resolve_custom_question(
                    question=question,
                    document_text=document["cleaned_text"],
                    openai_api_key=app.config["OPENAI_API_KEY"],
                    google_api_key=app.config.get("GOOGLE_API_KEY", ""),
                    google_cse_id=app.config.get("GOOGLE_CSE_ID", ""),
                    fallback_mode=fallback_mode,
                )
            else:
                answer = answer_question(
                    question=question,
                    document_text=document["cleaned_text"],
                    api_key=app.config["OPENAI_API_KEY"],
                )
                source = "Document"

            save_chat_message(
                db_path=app.config["DATABASE_PATH"],
                document_id=doc_id,
                user_question=question,
                chatbot_answer=answer,
            )

            return jsonify(
                {
                    "success": True,
                    "question": question,
                    "answer": answer,
                    "source": source,
                    "question_mode": question_mode,
                }
            )

        except Exception as exc:
            logger.exception("Chatbot request failed for document %s: %s", doc_id, exc)
            return jsonify(
                {
                    "success": False,
                    "message": "The chatbot is temporarily unavailable. Please try again.",
                }
            ), 500

    @app.route("/report/<int:doc_id>", methods=["GET"])
    def report(doc_id: int):
        document = get_document(app.config["DATABASE_PATH"], doc_id)
        if not document:
            return render_template("error.html", message="Document not found."), 404

        report_data = build_report_data(document)
        return render_template("report.html", report=report_data, document=document)

    @app.route("/report/<int:doc_id>/download", methods=["GET"])
    def download_report(doc_id: int):
        document = get_document(app.config["DATABASE_PATH"], doc_id)
        if not document:
            return render_template("error.html", message="Document not found."), 404

        report_data = build_report_data(document)
        pdf_buffer = build_report_pdf(report_data)
        download_name = f"report_{doc_id}.pdf"

        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=download_name,
            mimetype="application/pdf",
        )

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
