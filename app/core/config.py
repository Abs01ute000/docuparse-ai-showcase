from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


@dataclass(slots=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "DocuParse AI")
    app_env: str = os.getenv("APP_ENV", "development")
    debug: bool = os.getenv("DEBUG", "true").lower() == "true"
    host: str = os.getenv("HOST", "127.0.0.1")
    port: int = int(os.getenv("PORT", "8000"))

    temp_dir: Path = BASE_DIR / os.getenv("TEMP_DIR", "data/temp")
    samples_dir: Path = BASE_DIR / os.getenv("SAMPLES_DIR", "data/samples")
    max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "20"))
    text_threshold_per_page: int = int(os.getenv("TEXT_THRESHOLD_PER_PAGE", "80"))
    ocr_language: str = os.getenv("OCR_LANGUAGE", "eng")
    tesseract_cmd: str | None = os.getenv("TESSERACT_CMD") or None
    ocr_dpi: int = int(os.getenv("OCR_DPI", "200"))

    enable_ai_enrichment: bool = os.getenv("ENABLE_AI_ENRICHMENT", "false").lower() == "true"
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY") or None
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    ai_max_input_chars: int = int(os.getenv("AI_MAX_INPUT_CHARS", "12000"))

    def __post_init__(self) -> None:
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.samples_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
