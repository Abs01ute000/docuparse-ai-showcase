from __future__ import annotations

from pathlib import Path

import fitz

from app.core.config import get_settings


class PDFSourceDetector:
    def __init__(self) -> None:
        self.settings = get_settings()

    def detect(self, pdf_path: Path) -> tuple[str, int]:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        extracted_lengths: list[int] = []

        for page in doc:
            text = page.get_text("text") or ""
            extracted_lengths.append(len(text.strip()))

        avg_chars = int(sum(extracted_lengths) / total_pages) if total_pages else 0
        source_type = "text_pdf" if avg_chars >= self.settings.text_threshold_per_page else "scanned_pdf"
        return source_type, total_pages
