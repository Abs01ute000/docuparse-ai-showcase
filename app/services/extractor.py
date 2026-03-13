from __future__ import annotations

import re
from datetime import datetime

from app.schemas.document import PartyInfo


class RuleBasedExtractor:
    DATE_PATTERNS = [
        r"\b(\d{2}[./-]\d{2}[./-]\d{4})\b",
        r"\b(\d{4}[./-]\d{2}[./-]\d{2})\b",
    ]

    NUMBER_PATTERNS = [
        r"(?:Contract|Agreement|Document|Policy|Specification|Договор|Документ)\s*(?:No\.?|№|Number)\s*([A-Za-zА-Яа-я0-9\-/]+)",
        r"(?:No\.?|№|Number)\s*([A-Za-zА-Яа-я0-9\-/]+)",
    ]

    VALID_UNTIL_PATTERNS = [
        r"valid until\s*(\d{2}[./-]\d{2}[./-]\d{4})",
        r"effective until\s*(\d{2}[./-]\d{2}[./-]\d{4})",
        r"действует до\s*(\d{2}[./-]\d{2}[./-]\d{4})",
    ]

    def extract(self, text: str) -> dict:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        head = "\n".join(lines[:20])

        document_type = self._detect_document_type(head)
        title = self._extract_title(lines)
        document_number = self._extract_first(self.NUMBER_PATTERNS, head, flags=re.IGNORECASE)
        date = self._normalize_date(self._extract_first(self.DATE_PATTERNS, head))
        valid_until = self._normalize_date(self._extract_first(self.VALID_UNTIL_PATTERNS, text, flags=re.IGNORECASE))
        parties = self._extract_parties(lines, text)
        key_points = self._extract_key_points(lines)
        warnings = self._build_warnings(title, parties, key_points)
        summary = self._build_summary(document_type, title, parties, date, key_points)
        confidence_score = self._calculate_confidence(
            title, document_number, date, parties, valid_until, key_points, warnings
        )

        return {
            "document_type": document_type,
            "title": title,
            "document_number": document_number,
            "date": date,
            "parties": parties,
            "valid_until": valid_until,
            "key_points": key_points,
            "summary": summary,
            "extraction_method": "regex_showcase_v1",
            "confidence_score": confidence_score,
            "warnings": warnings,
            "extracted_fields_status": {
                "title": bool(title),
                "document_number": bool(document_number),
                "date": bool(date),
                "parties": bool(parties),
                "valid_until": bool(valid_until),
                "key_points": bool(key_points),
            },
        }

    def _extract_title(self, lines: list[str]) -> str | None:
        if not lines:
            return None

        skip_patterns = [
            r"^page\s+\d+$",
            r"^synthetic stress-test pdf",
            r"^document intelligence demo",
        ]
        preferred_keywords = [
            "agreement",
            "contract",
            "policy",
            "regulation",
            "specification",
            "instruction",
            "договор",
            "регламент",
            "положение",
            "инструкция",
            "техническое задание",
        ]

        candidates: list[tuple[int, str]] = []
        for idx, line in enumerate(lines[:15]):
            cleaned = line.strip(" :-")
            lowered = cleaned.lower()
            if any(re.match(pattern, lowered) for pattern in skip_patterns):
                continue
            if len(cleaned) < 4 or len(cleaned) > 160:
                continue
            candidates.append((idx, cleaned))

        for idx, cleaned in candidates:
            lowered = cleaned.lower()
            if any(keyword in lowered for keyword in preferred_keywords):
                if idx + 1 < len(lines):
                    next_line = lines[idx + 1].strip(" :-")
                    next_low = next_line.lower()
                    if (
                        next_line
                        and len(next_line) <= 40
                        and not re.match(r"^(contract|agreement|document|policy|specification)\s*(no\.?|№|number)", next_low)
                        and not re.match(r"^(дата|date|сторона|party|оплата|payment|неустойка|penalty|срок исполнения|term of performance|действует до|valid until)", next_low)
                        and re.match(r"^[A-ZА-Я0-9\s/&\-]+$", next_line)
                    ):
                        return f"{cleaned} {next_line}".strip()
                return cleaned

        if candidates:
            return candidates[0][1]
        return lines[0][:180]

    def _extract_first(self, patterns: list[str], text: str, *, flags: int = 0) -> str | None:
        for pattern in patterns:
            match = re.search(pattern, text, flags)
            if match:
                return match.group(1).strip()
        return None

    def _extract_parties(self, lines: list[str], text: str) -> list[PartyInfo]:
        party1 = None
        party2 = None
        normalized_lines = [re.sub(r"\s+", " ", line).strip() for line in lines]

        party1_patterns = [
            r"^(сторона\s*1|party\s*1)(\s*/\s*(party\s*1|сторона\s*1))?$",
            r"^(сторона\s*1\s*/\s*party\s*1)$",
            r"^(party\s*1\s*/\s*сторона\s*1)$",
        ]
        party2_patterns = [
            r"^(сторона\s*2|party\s*2)(\s*/\s*(party\s*2|сторона\s*2))?$",
            r"^(сторона\s*2\s*/\s*party\s*2)$",
            r"^(party\s*2\s*/\s*сторона\s*2)$",
        ]

        for i, line in enumerate(normalized_lines[:40]):
            lowered = line.lower()
            if any(re.match(pattern, lowered, re.IGNORECASE) for pattern in party1_patterns):
                if i + 1 < len(normalized_lines):
                    value = normalized_lines[i + 1].strip(" ,;")
                    if value:
                        party1 = value
            elif re.match(r"^(сторона\s*1|party\s*1)\s*[:\-]", lowered, re.IGNORECASE):
                value = re.sub(r"(?i)^(сторона\s*1|party\s*1)\s*[:\-]\s*", "", line).strip(" ,;")
                if value:
                    party1 = value

            if any(re.match(pattern, lowered, re.IGNORECASE) for pattern in party2_patterns):
                if i + 1 < len(normalized_lines):
                    value = normalized_lines[i + 1].strip(" ,;")
                    if value:
                        party2 = value
            elif re.match(r"^(сторона\s*2|party\s*2)\s*[:\-]", lowered, re.IGNORECASE):
                value = re.sub(r"(?i)^(сторона\s*2|party\s*2)\s*[:\-]\s*", "", line).strip(" ,;")
                if value:
                    party2 = value

        result = []
        if party1:
            result.append(PartyInfo(raw_value=party1[:220]))
        if party2:
            result.append(PartyInfo(raw_value=party2[:220]))
        if result:
            return result

        match_ru = re.search(r"между\s+(.+?)\s+и\s+(.+?)(?:\.|\n)", text, re.IGNORECASE | re.DOTALL)
        if match_ru:
            p1 = re.sub(r"\s+", " ", match_ru.group(1)).strip(" ,;")
            p2 = re.sub(r"\s+", " ", match_ru.group(2)).strip(" ,;")
            return [PartyInfo(raw_value=p1[:220]), PartyInfo(raw_value=p2[:220])]

        match_en = re.search(r"between\s+(.+?)\s+and\s+(.+?)(?:\.|\n)", text, re.IGNORECASE | re.DOTALL)
        if match_en:
            p1 = re.sub(r"\s+", " ", match_en.group(1)).strip(" ,;")
            p2 = re.sub(r"\s+", " ", match_en.group(2)).strip(" ,;")
            return [PartyInfo(raw_value=p1[:220]), PartyInfo(raw_value=p2[:220])]

        return []

    def _extract_key_points(self, lines: list[str]) -> list[str]:
        key_points: list[str] = []
        normalized_lines = [re.sub(r"\s+", " ", line).strip() for line in lines]

        label_aliases = {
            "payment": "Payment",
            "оплата": "Payment",
            "оплата / payment": "Payment",
            "payment / оплата": "Payment",
            "penalty": "Penalty",
            "неустойка": "Penalty",
            "неустойка / penalty": "Penalty",
            "penalty / неустойка": "Penalty",
            "term of performance": "Term of performance",
            "срок исполнения": "Term of performance",
            "срок исполнения / term of performance": "Term of performance",
            "term of performance / срок исполнения": "Term of performance",
            "valid until": "Valid until",
            "действует до": "Valid until",
            "действует до / valid until": "Valid until",
            "valid until / действует до": "Valid until",
        }

        skip_values = {
            "payment", "оплата", "/ payment", "/ оплата", "payment /", "оплата /",
            "payment / payment", "оплата / payment", "payment / оплата",
            "penalty", "неустойка", "/ penalty", "/ неустойка", "penalty /", "неустойка /",
            "penalty / penalty", "неустойка / penalty", "penalty / неустойка",
            "term of performance", "срок исполнения", "/ term of performance", "/ срок исполнения",
            "term of performance /", "срок исполнения /", "term of performance / term of performance",
            "срок исполнения / term of performance", "term of performance / срок исполнения",
            "valid until", "действует до", "/ valid until", "/ действует до",
            "valid until /", "действует до /", "valid until / valid until",
            "действует до / valid until", "valid until / действует до",
        }

        for i, line in enumerate(normalized_lines[:50]):
            low = line.lower().strip(" .;:")
            if low in label_aliases and i + 1 < len(normalized_lines):
                value = normalized_lines[i + 1].strip(" .;:")
                normalized_value = value.lower().strip(" .;:")
                if value and len(value) < 140 and normalized_value not in skip_values:
                    item = f"{label_aliases[low]}: {value}"
                    if item not in key_points:
                        key_points.append(item)

        inline_patterns = [
            (r"^(payment|оплата)\s*[:\-]?\s*(.+)$", "Payment"),
            (r"^(penalty|неустойка)\s*[:\-]?\s*(.+)$", "Penalty"),
            (r"^(term of performance|срок исполнения)\s*[:\-]?\s*(.+)$", "Term of performance"),
            (r"^(valid until|действует до)\s*[:\-]?\s*(.+)$", "Valid until"),
        ]
        for line in normalized_lines[:80]:
            for pattern, label in inline_patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    value = match.group(2).strip(" .;:")
                    normalized_value = value.lower().strip(" .;:")
                    if value and len(value) < 140 and normalized_value not in skip_values:
                        item = f"{label}: {value}"
                        if item not in key_points:
                            key_points.append(item)

        return key_points[:6]

    def _detect_document_type(self, head: str) -> str:
        lowered = head.lower()
        if re.search(r"\b(contract|agreement|договор)\b", lowered):
            return "contract"
        if re.search(r"\b(regulation|policy|регламент|положение|privacy policy)\b", lowered):
            return "policy"
        if re.search(r"\b(technical specification|terms of reference|техническое задание|scope of work|request for proposal)\b", lowered):
            return "technical_specification"
        if re.search(r"\b(instruction|инструкция)\b", lowered):
            return "instruction"
        return "unknown"

    def _normalize_date(self, value: str | None) -> str | None:
        if not value:
            return None
        for fmt in ("%d.%m.%Y", "%d-%m-%Y", "%d/%m/%Y", "%Y.%m.%d", "%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(value, fmt).date().isoformat()
            except ValueError:
                continue
        return value

    def _build_summary(
        self,
        document_type: str,
        title: str | None,
        parties: list[PartyInfo],
        date: str | None,
        key_points: list[str],
    ) -> str:
        parts: list[str] = []
        if title:
            parts.append(f"Document title: {title}")
        parts.append(f"Detected type: {document_type}")
        if date:
            parts.append(f"Date: {date}")
        if parties:
            parts.append("Parties: " + ", ".join(p.raw_value for p in parties))
        if key_points:
            parts.append("Key points: " + "; ".join(key_points[:4]))
        return ". ".join(parts) + "."

    def _build_warnings(self, title: str | None, parties: list[PartyInfo], key_points: list[str]) -> list[str]:
        warnings: list[str] = []
        if title and title.lower().startswith("page "):
            warnings.append("Title looks like a page marker, not a real document title.")
        if not parties:
            warnings.append("Parties were not extracted.")
        if len(key_points) < 2:
            warnings.append("Few key points extracted; document may need richer rules or OCR cleanup.")
        return warnings

    def _calculate_confidence(
        self,
        title: str | None,
        document_number: str | None,
        date: str | None,
        parties: list[PartyInfo],
        valid_until: str | None,
        key_points: list[str],
        warnings: list[str],
    ) -> float:
        score = 0.0
        if title:
            score += 0.15
        if document_number:
            score += 0.20
        if date:
            score += 0.15
        if parties:
            score += 0.20
        if valid_until:
            score += 0.15
        if key_points:
            score += 0.15
        score -= 0.08 * len(warnings)
        return round(max(0.0, min(score, 0.94)), 2)
