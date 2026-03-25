import itertools
import logging
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from utils.qa_engine import answer_question

# Optional project helpers. This app can adapt to a few common function names.
from utils import cleaner as cleaner_utils
from utils import extractor as extractor_utils
from utils import file_handler as file_handler_utils
from utils import parser as parser_utils
from utils import report_generator as report_utils
from utils import summarizer as summarizer_utils
from utils import validators as validators_utils


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-this-secret-key")
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

DOCUMENT_STORE: dict[int, dict[str, Any]] = {}
NEXT_DOC_ID = itertools.count(1)


def call_first_available(module: Any, names: list[str], attempts: list[tuple[tuple[Any, ...], dict[str, Any]]]) -> Any:
    for name in names:
        func = getattr(module, name, None)
        if not callable(func):
            continue

        for args, kwargs in attempts:
            try:
                return func(*args, **kwargs)
            except TypeError:
                continue

    raise AttributeError(f"No compatible function found in {module.__name__} for candidates: {names}")


def allowed_file(filename: str) -> bool:
    try:
        result = call_first_available(
            validators_utils,
            ["allowed_file", "is_allowed_file", "validate_file_extension"],
            [((filename,), {})],
        )
        return bool(result)
    except Exception:
        return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(file_storage) -> str:
    filename = secure_filename(file_storage.filename or "")
    if not filename:
        raise ValueError("Uploaded file is missing a valid filename.")

    target_path = UPLOAD_DIR / filename

    try:
        result = call_first_available(
            file_handler_utils,
            ["save_uploaded_file", "save_file"],
            [((file_storage, str(UPLOAD_DIR)), {}), ((file_storage,), {})],
        )
        if isinstance(result, str) and result.strip():
            return result
    except Exception:
        pass

    file_storage.save(target_path)
    return str(target_path)


def extract_document_text(file_path: str) -> str:
    try:
        result = call_first_available(
            parser_utils,
            ["extract_text_from_file", "extract_text", "parse_document", "parse_file"],
            [((file_path,), {})],
        )
        return str(result or "").strip()
    except Exception as exc:
        logger.exception("Text extraction failed: %s", exc)
        return ""


def clean_document_text(text: str) -> str:
    if not text:
        return ""

    try:
        result = call_first_available(
            cleaner_utils,
            ["clean_text", "clean_document_text", "normalize_text", "preprocess_text"],
            [((text,), {})],
        )
        return str(result or "").strip()
    except Exception:
        return fallback_clean_text(text)


def generate_summary(text: str) -> str:
    if not text:
        return "No summary could be generated."

    try:
        result = call_first_available(
            summarizer_utils,
            ["generate_summary", "summarize_text", "summarize_document"],
            [
                ((text, OPENAI_API_KEY), {}),
                ((text,), {}),
            ],
        )
        summary = str(result or "").strip()
        return summary if summary else fallback_summary(text)
    except Exception as exc:
        logger.exception("Summary generation failed: %s", exc)
        return fallback_summary(text)


def extract_information(text: str) -> dict[str, list[str]]:
    if not text:
        return {"dates": [], "emails": [], "amounts": [], "action_items": []}

    try:
        result = call_first_available(
            extractor_utils,
            ["extract_key_info", "extract_information", "extract_entities"],
            [((text,), {})],
        )
        return normalize_extracted_info(result)
    except Exception as exc:
        logger.exception("Information extraction failed: %s", exc)
        return fallback_extract_info(text)


def build_report(document: dict[str, Any]) -> str:
    try:
        result = call_first_available(
            report_utils,
            ["generate_report", "build_report", "create_report", "generate_structured_report"],
            [
                ((document,), {}),
                ((document["filename"], document["file_type"], document["summary"], document["extracted_info"], document["preview"]), {}),
                ((document["summary"], document["extracted_info"], document["preview"]), {}),
            ],
        )
        if isinstance(result, str) and result.strip():
            return result.strip()
    except Exception as exc:
        logger.exception("Report generation failed: %s", exc)

    return fallback_report(document)


def fallback_clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fallback_summary(text: str, max_sentences: int = 4) -> str:
    sentences = split_sentences(text)
    if not sentences:
        return "No summary could be generated."
    return " ".join(sentences[:max_sentences]).strip()


def fallback_extract_info(text: str) -> dict[str, list[str]]:
    dates = re.findall(r"\b(?:week\s+\d+|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\b", text, flags=re.IGNORECASE)
    emails = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text)
    amounts = re.findall(r"(?:\$|USD\s*|PKR\s*|AUD\s*)\d[\d,]*(?:\.\d{1,2})?", text, flags=re.IGNORECASE)

    action_items: list[str] = []
    for line in re.split(r"\n+|•|- ", text):
        cleaned = re.sub(r"\s+", " ", line).strip()
        lower = cleaned.lower()
        if not cleaned:
            continue
        if any(term in lower for term in {"must", "submit", "include", "required", "application must"}):
            action_items.append(cleaned)

    return {
        "dates": dedupe(dates),
        "emails": dedupe(emails),
        "amounts": dedupe(amounts),
        "action_items": dedupe(action_items[:10]),
    }


def normalize_extracted_info(data: Any) -> dict[str, list[str]]:
    normalized = {
        "dates": [],
        "emails": [],
        "amounts": [],
        "action_items": [],
    }

    if isinstance(data, dict):
        for key in normalized.keys():
            value = data.get(key, [])
            if isinstance(value, str):
                value = [value]
            elif not isinstance(value, list):
                value = list(value) if value else []
            normalized[key] = [str(item).strip() for item in value if str(item).strip()]

    return normalized


def fallback_report(document: dict[str, Any]) -> str:
    extracted = document["extracted_info"]

    action_items = extracted.get("action_items") or []
    action_block = "\n".join(f"- {item}" for item in action_items[:10]) if action_items else "- None found"

    return f"""
CA Commercial Support Assistant Report

Document Name: {document["filename"]}
Document Type: {document["file_type"]}

Executive Summary
{document["summary"]}

Dates
{format_list_block(extracted.get("dates"))}

Emails
{format_list_block(extracted.get("emails"))}

Amounts
{format_list_block(extracted.get("amounts"))}

Action Items
{action_block}

Document Preview
{document["preview"]}
""".strip()


def format_list_block(items: list[str] | None) -> str:
    if not items:
        return "- None found"
    return "\n".join(f"- {item}" for item in items)


def split_sentences(text: str) -> list[str]:
    raw_sentences = re.split(r"(?<=[.!?])\s+|\n+", text or "")
    sentences = [re.sub(r"\s+", " ", sentence).strip() for sentence in raw_sentences]
    return [sentence for sentence in sentences if sentence]


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []

    for item in items:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            output.append(item.strip())

    return output


def get_document_or_404(doc_id: int) -> dict[str, Any] | None:
    return DOCUMENT_STORE.get(doc_id)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_document():
    uploaded_file = request.files.get("document") or request.files.get("file")

    if not uploaded_file or not uploaded_file.filename:
        flash("Please choose a file to upload.", "error")
        return redirect(url_for("index"))

    if not allowed_file(uploaded_file.filename):
        flash("Unsupported file type. Please upload PDF, DOCX, or TXT.", "error")
        return redirect(url_for("index"))

    try:
        saved_path = save_uploaded_file(uploaded_file)
        raw_text = extract_document_text(saved_path)
        cleaned_text = clean_document_text(raw_text)

        if not cleaned_text:
            flash("The document could not be processed. Please try another file.", "error")
            return redirect(url_for("index"))

        summary = generate_summary(cleaned_text)
        extracted_info = extract_information(cleaned_text)

        doc_id = next(NEXT_DOC_ID)
        document = {
            "id": doc_id,
            "filename": secure_filename(uploaded_file.filename),
            "file_type": Path(uploaded_file.filename).suffix.replace(".", "").upper() or "UNKNOWN",
            "saved_path": saved_path,
            "raw_text": raw_text,
            "cleaned_text": cleaned_text,
            "summary": summary,
            "extracted_info": extracted_info,
            "preview": cleaned_text[:2000],
            "chat_history": [],
        }
        document["report_text"] = build_report(document)

        DOCUMENT_STORE[doc_id] = document

        flash("Document uploaded and processed successfully.", "success")
        return redirect(url_for("result_page", doc_id=doc_id))

    except Exception as exc:
        logger.exception("Upload processing failed: %s", exc)
        flash("An unexpected error occurred while processing the document.", "error")
        return redirect(url_for("index"))


@app.route("/result/<int:doc_id>", methods=["GET"])
def result_page(doc_id: int):
    document = get_document_or_404(doc_id)
    if not document:
        flash("Document not found.", "error")
        return redirect(url_for("index"))

    return render_template(
        "result.html",
        doc_id=doc_id,
        document=document,
        filename=document["filename"],
        file_type=document["file_type"],
        summary=document["summary"],
        executive_summary=document["summary"],
        extracted_info=document["extracted_info"],
        extracted_information=document["extracted_info"],
        preview=document["preview"],
        document_preview=document["preview"],
    )


@app.route("/chat/<int:doc_id>", methods=["GET", "POST"])
def chat_page(doc_id: int):
    document = get_document_or_404(doc_id)
    if not document:
        flash("Document not found.", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        question = (
            request.form.get("question")
            or request.form.get("user_question")
            or request.form.get("message")
            or ""
        ).strip()

        if question:
            answer = answer_question(question, document["cleaned_text"], OPENAI_API_KEY)
            document["chat_history"].append(
                {
                    "question": question,
                    "answer": answer,
                }
            )
        else:
            flash("Please type a question first.", "error")

    return render_template(
        "chat.html",
        doc_id=doc_id,
        document=document,
        filename=document["filename"],
        document_name=document["filename"],
        chat_history=document["chat_history"],
        history=document["chat_history"],
    )


@app.route("/report/<int:doc_id>", methods=["GET"])
def report_page(doc_id: int):
    document = get_document_or_404(doc_id)
    if not document:
        flash("Document not found.", "error")
        return redirect(url_for("index"))

    return render_template(
        "report.html",
        doc_id=doc_id,
        document=document,
        filename=document["filename"],
        report_text=document["report_text"],
        report=document["report_text"],
    )


@app.route("/health", methods=["GET"])
def health_check():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    app.run(debug=True)
