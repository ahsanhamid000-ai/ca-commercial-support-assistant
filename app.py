import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

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
from utils.report_generator import build_report_data
from utils.qa_engine import answer_question


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    init_db(app.config["DATABASE_PATH"])

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

        saved_path, original_name, extension = save_uploaded_file(
            file=file,
            upload_folder=app.config["UPLOAD_FOLDER"],
        )

        raw_text = extract_text(saved_path, extension)
        valid_text, text_message = validate_extracted_text(raw_text)
        if not valid_text:
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
        )

    @app.route("/ask/<int:doc_id>", methods=["POST"])
    def ask(doc_id: int):
        document = get_document(app.config["DATABASE_PATH"], doc_id)
        if not document:
            return jsonify({"success": False, "message": "Document not found."}), 404

        question = request.form.get("question", "").strip()
        is_valid, error_message = validate_question(question)
        if not is_valid:
            return jsonify({"success": False, "message": error_message}), 400

        answer = answer_question(
            question=question,
            document_text=document["cleaned_text"],
            api_key=app.config["OPENAI_API_KEY"],
        )

        save_chat_message(
            db_path=app.config["DATABASE_PATH"],
            document_id=doc_id,
            user_question=question,
            chatbot_answer=answer,
        )

        return jsonify({"success": True, "question": question, "answer": answer})

    @app.route("/report/<int:doc_id>", methods=["GET"])
    def report(doc_id: int):
        document = get_document(app.config["DATABASE_PATH"], doc_id)
        if not document:
            return render_template("error.html", message="Document not found."), 404

        report_data = build_report_data(document)
        return render_template("report.html", report=report_data, document=document)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
