import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    DATABASE_PATH = os.path.join(BASE_DIR, "database.db")
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB
    ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}
