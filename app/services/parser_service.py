from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.schemas.document import DocumentParseResponse, FieldStatus, PartyInfo
from app.services.cleaner import TextCleaner
from app.services.detector import PDFSourceDetector
from app.services.extractor import RuleBasedExtractor
from app.services.ocr_reader import OCRNotConfiguredError, PDFOCRReader
from app.services.openai_service import OpenAIEnricher
from app.services.pdf_reader import PDFTextReader


class DocumentParserService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.detector = PDFSourceDetector()
        self.pdf_reader = PDFTextReader()
        self.ocr_reader = PDFOCRReader()
        self.cleaner = TextCleaner()
        self.extractor = RuleBasedExtractor()
        self.ai_enricher = OpenAIEnricher() if self.settings.enable_ai_enrichment and self.settings.openai_api_key else None

    def parse(self, pdf_path: Path, original_filename: str) -> DocumentParseResponse:
        warnings: list[str] = []
        source_type, pages = self.detector.detect(pdf_path)
        ocr_used = source_type == "scanned_pdf"

        if source_type == "text_pdf":
            raw_text = self.pdf_reader.read_text(pdf_path)
        else:
            try:
                raw_text = self.ocr_reader.read_text(pdf_path)
            except OCRNotConfiguredError as exc:
                warnings.append(str(exc))
                raw_text = ""

        cleaned_text = self.cleaner.clean(raw_text)
        if not cleaned_text:
            warnings.append("No readable text was extracted from the document.")

        extracted = self.extractor.extract(cleaned_text)

        if self.ai_enricher and cleaned_text:
            try:
                extracted = self.ai_enricher.enrich(extracted, cleaned_text)
            except Exception as exc:  # pragma: no cover - network dependent
                warnings.append(f"OpenAI enrichment skipped: {exc}")

        parties = extracted.get("parties", [])
        normalized_parties: list[PartyInfo] = []
        for party in parties:
            if isinstance(party, PartyInfo):
                if party.raw_value:
                    normalized_parties.append(party)
            elif isinstance(party, str):
                value = party.strip()
                if value:
                    normalized_parties.append(PartyInfo(raw_value=value))
            elif isinstance(party, dict):
                value = str(party.get("raw_value", "")).strip()
                if value:
                    normalized_parties.append(PartyInfo(raw_value=value))

        extracted_status = extracted.get("extracted_fields_status") or {}
        field_status = FieldStatus(
            title=bool(extracted_status.get("title", bool(extracted.get("title")))),
            document_number=bool(extracted_status.get("document_number", bool(extracted.get("document_number")))),
            date=bool(extracted_status.get("date", bool(extracted.get("date")))),
            parties=bool(extracted_status.get("parties", bool(normalized_parties))),
            valid_until=bool(extracted_status.get("valid_until", bool(extracted.get("valid_until")))),
            key_points=bool(extracted_status.get("key_points", bool(extracted.get("key_points", [])))),
        )

        warnings.extend(extracted.get("warnings", []))
        # deduplicate while preserving order
        warnings = list(dict.fromkeys(warnings))

        confidence_score = float(extracted.get("confidence_score", 0.0))
        if confidence_score <= 0:
            score_parts = [
                field_status.title,
                field_status.document_number,
                field_status.date,
                field_status.parties,
                field_status.valid_until,
                field_status.key_points,
            ]
            confidence_score = round(sum(score_parts) / 6, 2)

        summary = extracted.get("summary") or self._build_fallback_summary(
            extracted.get("title"),
            extracted.get("document_type", "unknown"),
            normalized_parties,
            extracted.get("date"),
            extracted.get("key_points", []),
        )

        return DocumentParseResponse(
            filename=original_filename,
            document_type=extracted.get("document_type", "unknown"),
            title=extracted.get("title"),
            document_number=extracted.get("document_number"),
            date=extracted.get("date"),
            parties=normalized_parties,
            valid_until=extracted.get("valid_until"),
            key_points=extracted.get("key_points", []),
            summary=summary,
            pages=pages,
            source_type=source_type,
            ocr_used=ocr_used,
            detected_language=self._detect_language(cleaned_text),
            extraction_method=extracted.get("extraction_method", "regex"),
            confidence_score=confidence_score,
            extracted_fields_status=field_status,
            raw_text_preview=cleaned_text[:1400],
            warnings=warnings,
        )

    def _detect_language(self, text: str) -> str:
        if not text.strip():
            return "unknown"
        latin = sum(1 for ch in text if 'a' <= ch.lower() <= 'z')
        cyr = sum(1 for ch in text if '\u0400' <= ch <= '\u04FF')
        if latin and cyr:
            return "mixed"
        if cyr:
            return "ru"
        if latin:
            return "en"
        return "unknown"

    def _build_fallback_summary(
        self,
        title: str | None,
        document_type: str,
        parties: list[PartyInfo],
        date: str | None,
        key_points: list[str],
    ) -> str:
        bits: list[str] = []
        if title:
            bits.append(f"Document title: {title}")
        bits.append(f"Detected type: {document_type}")
        if date:
            bits.append(f"Date: {date}")
        if parties:
            bits.append("Parties: " + ", ".join(p.raw_value for p in parties))
        if key_points:
            bits.append("Key points: " + "; ".join(key_points[:4]))
        return ". ".join(bits) + "."
