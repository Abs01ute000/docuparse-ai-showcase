from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile


def save_upload_file(upload_file: UploadFile, destination_dir: Path) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(upload_file.filename or "document.pdf").suffix or ".pdf"
    safe_name = f"{uuid.uuid4().hex}{suffix}"
    destination = destination_dir / safe_name

    with destination.open("wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)

    return destination
