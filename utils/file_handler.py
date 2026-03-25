import os
import uuid
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


def allowed_file(filename: str, allowed_extensions: set[str]) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


def save_uploaded_file(file: FileStorage, upload_folder: str) -> tuple[str, str, str]:
    original_name = secure_filename(file.filename)
    extension = original_name.rsplit(".", 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}_{original_name}"
    saved_path = os.path.join(upload_folder, unique_name)
    file.save(saved_path)
    return saved_path, original_name, extension
