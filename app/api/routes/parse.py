from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.config import get_settings
from app.schemas.document import DocumentParseResponse, HealthResponse, SampleFileInfo, SampleListResponse
from app.services.parser_service import DocumentParserService
from app.utils.file_utils import save_upload_file

router = APIRouter(tags=["DocuParse AI"])
settings = get_settings()
SAMPLE_DESCRIPTIONS = {
    "sample_contract.pdf": "Clean text PDF with a service agreement structure.",
    "sample_policy.pdf": "Internal data policy sample used to test long-form extraction.",
    "sample_tender_spec.pdf": "Tender-style technical specification sample.",
    "sample_scanned_contract.pdf": "Scanned PDF sample intended for OCR fallback.",
    "sample_long_contract_stress.pdf": "Large multi-page contract stress test for long-document parsing.",
}


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(app=settings.app_name, environment=settings.app_env)


@router.get("/samples", response_model=SampleListResponse)
def list_samples() -> SampleListResponse:
    items: list[SampleFileInfo] = []
    for path in sorted(settings.samples_dir.glob("*.pdf")):
        items.append(
            SampleFileInfo(
                name=path.name,
                url=f"/sample-files/{path.name}",
                description=SAMPLE_DESCRIPTIONS.get(path.name),
            )
        )
    return SampleListResponse(items=items)


@router.post("/parse-pdf", response_model=DocumentParseResponse)
def parse_pdf(file: UploadFile = File(...)) -> DocumentParseResponse:
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename is required.")

    suffix = Path(file.filename).suffix.lower()
    if suffix != ".pdf":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are supported.")

    contents = file.file.read()
    size_mb = len(contents) / 1024 / 1024
    file.file.seek(0)
    if size_mb > settings.max_file_size_mb:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds max size of {settings.max_file_size_mb} MB.",
        )

    saved_path = save_upload_file(file, settings.temp_dir)
    parser = DocumentParserService()

    try:
        return parser.parse(saved_path, file.filename)
    finally:
        if saved_path.exists():
            saved_path.unlink(missing_ok=True)
