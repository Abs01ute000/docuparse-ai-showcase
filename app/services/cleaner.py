from __future__ import annotations

import re


class TextCleaner:
    def clean(self, text: str) -> str:
        text = text.replace("\r", "\n")
        text = re.sub(r"[\t\x0c\x0b]+", " ", text)
        text = re.sub(r"[ ]{2,}", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)
        text = re.sub(r"\s+([,.;:])", r"\1", text)
        text = re.sub(r"[•▪◦]+", "- ", text)
        text = re.sub(r"\u00a0", " ", text)
        return text.strip()
