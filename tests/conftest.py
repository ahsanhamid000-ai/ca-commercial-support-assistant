import io
import os
import tempfile

import pytest

import app as app_module
from config import Config


@pytest.fixture()
def client(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_assistant.db")
        upload_folder = os.path.join(temp_dir, "uploads")
        instance_folder = os.path.join(temp_dir, "instance")

        os.makedirs(upload_folder, exist_ok=True)
        os.makedirs(instance_folder, exist_ok=True)

        monkeypatch.setattr(Config, "DATABASE_PATH", db_path, raising=False)
        monkeypatch.setattr(Config, "UPLOAD_FOLDER", upload_folder, raising=False)
        monkeypatch.setattr(Config, "INSTANCE_FOLDER", instance_folder, raising=False)
        monkeypatch.setattr(Config, "OPENAI_API_KEY", "", raising=False)
        monkeypatch.setattr(Config, "SECRET_KEY", "test-secret-key", raising=False)

        monkeypatch.setattr(app_module, "build_summary", lambda text: "Test summary", raising=False)
        monkeypatch.setattr(app_module, "build_structured_summary", lambda text: "Test summary", raising=False)
        monkeypatch.setattr(
            app_module,
            "answer_question",
            lambda question, document_text, api_key: "Test chatbot answer",
            raising=False,
        )

        flask_app = app_module.create_app()
        flask_app.config["TESTING"] = True

        with flask_app.test_client() as test_client:
            yield test_client


@pytest.fixture()
def sample_upload():
    content = b"""
    Commercial Agreement
    Payment deadline is March 15, 2026.
    Contact email is finance@example.com.
    Amount due is $1500.
    The finance manager should review and approve the invoice.
    """
    return {
        "document": (io.BytesIO(content), "sample.txt")
    }
