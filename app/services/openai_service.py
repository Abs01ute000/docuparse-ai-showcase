from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from app.core.config import get_settings


class OpenAIEnricher:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = OpenAI(api_key=self.settings.openai_api_key)

    def enrich(self, extracted: dict[str, Any], text: str) -> dict[str, Any]:
        clipped_text = text[: self.settings.ai_max_input_chars]
        prompt = (
            "You are an information extraction assistant. Improve the extracted metadata for a document. "
            "Return strict JSON with keys: document_type, title, document_number, date, parties, valid_until, key_points, summary. "
            "Parties must be an array of strings. key_points must be an array of short strings.\n\n"
            f"Current extraction:\n{json.dumps(extracted, ensure_ascii=False, default=str)}\n\n"
            f"Document text:\n{clipped_text}"
        )

        response = self.client.responses.create(
            model=self.settings.openai_model,
            input=prompt,
        )
        output_text = (response.output_text or "").strip()
        parsed = json.loads(output_text)
        parsed["extraction_method"] = f"openai:{self.settings.openai_model}"
        return parsed
