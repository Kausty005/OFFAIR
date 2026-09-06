"""
document/pdf_processor.py
PDF parsing, scanned/digital detection, page-level text extraction.
Uses PyPDF2 for digital PDFs.
Falls back to image rendering + OCR for scanned pages.
"""

import io
import os
import sys
from pathlib import Path
from typing import Optional

_base = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _base)

from security.audit import log

try:
    import PyPDF2
    _PYPDF2_AVAILABLE = True
except ImportError:
    _PYPDF2_AVAILABLE = False

try:
    from PIL import Image
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


def _load_settings():
    import yaml
    cfg_path = os.path.join(_base, "config", "settings.yaml")
    with open(cfg_path) as f:
        return yaml.safe_load(f)


_settings = _load_settings()
MIN_TEXT = _settings["document"]["min_text_length_for_digital"]


def is_scanned_page(text: str) -> bool:
    """Heuristic: if extracted text is shorter than threshold, page is likely scanned."""
    return len(text.strip()) < MIN_TEXT


def extract_pages_digital(pdf_path: str | Path) -> list[dict]:
    """
    Extract text from a digital (text-based) PDF using PyPDF2.
    Returns list of: {page_num, text, is_scanned}
    """
    pages = []
    if not _PYPDF2_AVAILABLE:
        return pages

    try:
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                pages.append({
                    "page_num": i + 1,
                    "text": text,
                    "is_scanned": is_scanned_page(text),
                    "char_count": len(text),
                })
        log("PDF_PARSED", path=str(pdf_path), pages=len(pages), method="digital")
    except Exception as e:
        log("PDF_ERROR", path=str(pdf_path), error=str(e))
        pages.append({
            "page_num": 1,
            "text": "",
            "is_scanned": True,
            "error": str(e),
        })
    return pages


def pdf_to_images(pdf_path: str | Path, dpi: int = 150) -> list:
    """
    Convert PDF pages to PIL Images for OCR or vision model processing.
    Requires pdf2image (poppler) or falls back to a basic method.
    Returns list of PIL Image objects.
    """
    images = []
    try:
        from pdf2image import convert_from_path
        imgs = convert_from_path(str(pdf_path), dpi=dpi)
        images = imgs
        log("PDF_TO_IMAGES", path=str(pdf_path), pages=len(images), method="pdf2image")
    except ImportError:
        # pdf2image not available — try PyMuPDF
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(pdf_path))
            for page in doc:
                mat = fitz.Matrix(dpi / 72, dpi / 72)
                pix = page.get_pixmap(matrix=mat)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                images.append(img)
            log("PDF_TO_IMAGES", path=str(pdf_path), pages=len(images), method="pymupdf")
        except ImportError:
            log("PDF_TO_IMAGES_FAILED", path=str(pdf_path), error="Neither pdf2image nor PyMuPDF available")
    except Exception as e:
        log("PDF_TO_IMAGES_FAILED", path=str(pdf_path), error=str(e))
    return images


def process_pdf(pdf_path: str | Path) -> dict:
    """
    Main entry point for PDF processing.
    Detects digital vs scanned and extracts text accordingly.

    Returns:
        {
            "path": str,
            "total_pages": int,
            "is_scanned": bool,
            "full_text": str,
            "pages": [{"page_num", "text", "is_scanned"}],
            "needs_ocr": bool,
            "images_available": bool,
        }
    """
    pdf_path = Path(pdf_path)
    log("PDF_PROCESS_START", path=str(pdf_path))

    pages = extract_pages_digital(pdf_path)
    total_pages = len(pages)

    if total_pages == 0:
        return {
            "path": str(pdf_path),
            "total_pages": 0,
            "is_scanned": True,
            "full_text": "",
            "pages": [],
            "needs_ocr": True,
            "images_available": False,
            "error": "Could not read PDF",
        }

    # Determine if document is predominantly scanned
    scanned_count = sum(1 for p in pages if p["is_scanned"])
    is_predominantly_scanned = scanned_count > (total_pages * 0.5)

    full_text = "\n\n".join(
        f"--- Page {p['page_num']} ---\n{p['text']}"
        for p in pages
        if p.get("text")
    )

    # Try to get images for scanned pages
    images_available = False
    if is_predominantly_scanned:
        imgs = pdf_to_images(pdf_path)
        images_available = len(imgs) > 0
        # Attach image objects to pages
        for i, page in enumerate(pages):
            if i < len(imgs):
                page["image"] = imgs[i]

    log(
        "PDF_PROCESS_DONE",
        path=str(pdf_path),
        pages=total_pages,
        is_scanned=is_predominantly_scanned,
        needs_ocr=is_predominantly_scanned,
    )

    return {
        "path": str(pdf_path),
        "total_pages": total_pages,
        "is_scanned": is_predominantly_scanned,
        "full_text": full_text,
        "pages": pages,
        "needs_ocr": is_predominantly_scanned,
        "images_available": images_available,
    }
