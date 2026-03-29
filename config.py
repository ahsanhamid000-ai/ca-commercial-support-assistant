import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    UPLOAD_FOLDER = str(BASE_DIR / "uploads")
    INSTANCE_FOLDER = str(BASE_DIR / "instance")
    DATABASE_PATH = str(BASE_DIR / "instance" / "assistant.db")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}
