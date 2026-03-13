from __future__ import annotations

from pathlib import Path

import fitz


class PDFTextReader:
    def read_text(self, pdf_path: Path) -> str:
        doc = fitz.open(pdf_path)
        pages: list[str] = []
        for page in doc:
            pages.append(page.get_text("text") or "")
        return "\n".join(pages).strip()
