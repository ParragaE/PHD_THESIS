from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any
from pypdf import PdfReader


def extract_pdf_pages(pdf_path: Path) -> List[Dict[str, Any]]:
    """Extract born-digital text page by page using pypdf. No OCR is used."""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    reader = PdfReader(str(pdf_path))
    pages = []
    for page_no, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append({"page": page_no, "text": text, "has_text": bool(text.strip())})
    return pages
