from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes.parse import router as parse_router
from app.core.config import get_settings

settings = get_settings()
STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title=settings.app_name,
    version="1.2.0",
    debug=settings.debug,
    description=(
        "DocuParse AI is a document intelligence demo for PDF parsing, OCR fallback, "
        "rule-based extraction, optional OpenAI enrichment, and developer-friendly JSON output."
    ),
    contact={"name": "DocuParse AI", "url": "https://github.com/"},
)
app.include_router(parse_router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/sample-files", StaticFiles(directory=settings.samples_dir), name="sample-files")


@app.get("/", include_in_schema=False)
def landing_page() -> HTMLResponse:
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(STATIC_DIR / "favicon.png")
