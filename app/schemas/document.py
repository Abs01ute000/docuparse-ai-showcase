from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PartyInfo(BaseModel):
    raw_value: str = Field(..., description="Extracted party or responsible person line")


class FieldStatus(BaseModel):
    title: bool = False
    document_number: bool = False
    date: bool = False
    parties: bool = False
    valid_until: bool = False
    key_points: bool = False


class DocumentParseResponse(BaseModel):
    filename: str
    document_type: str = Field(default="unknown")
    title: str | None = None
    document_number: str | None = None
    date: str | None = None
    parties: list[PartyInfo] = Field(default_factory=list)
    valid_until: str | None = None
    key_points: list[str] = Field(default_factory=list)
    summary: str | None = None
    pages: int = 0
    source_type: Literal["text_pdf", "scanned_pdf"]
    ocr_used: bool = False
    detected_language: Literal["en", "ru", "mixed", "unknown"] = "unknown"
    extraction_method: str = Field(default="regex")
    confidence_score: float = 0.0
    extracted_fields_status: FieldStatus = Field(default_factory=FieldStatus)
    raw_text_preview: str = Field(default="")
    warnings: list[str] = Field(default_factory=list)


class SampleFileInfo(BaseModel):
    name: str
    url: str
    description: str | None = None


class SampleListResponse(BaseModel):
    items: list[SampleFileInfo] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str = "ok"
    app: str
    environment: str
