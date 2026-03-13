from __future__ import annotations

from pathlib import Path

import fitz
import pytesseract
from PIL import Image

from app.core.config import get_settings


class OCRNotConfiguredError(RuntimeError):
    pass


class PDFOCRReader:
    def __init__(self) -> None:
        self.settings = get_settings()
        if self.settings.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.settings.tesseract_cmd

    def read_text(self, pdf_path: Path) -> str:
        if self.settings.tesseract_cmd and not Path(self.settings.tesseract_cmd).exists():
            raise OCRNotConfiguredError(
                f"Tesseract binary not found at configured path: {self.settings.tesseract_cmd}"
            )

        try:
            _ = pytesseract.get_tesseract_version()
        except Exception as exc:  # pragma: no cover - depends on user machine
            raise OCRNotConfiguredError(
                "Tesseract OCR is not available. Install Tesseract and set TESSERACT_CMD in .env."
            ) from exc

        doc = fitz.open(pdf_path)
        page_texts: list[str] = []
        zoom = self.settings.ocr_dpi / 72
        matrix = fitz.Matrix(zoom, zoom)

        for page in doc:
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text = pytesseract.image_to_string(image, lang=self.settings.ocr_language)
            page_texts.append(text)

        return "\n".join(page_texts).strip()
