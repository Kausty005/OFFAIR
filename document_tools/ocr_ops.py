"""
document_tools/ocr_ops.py
OCR operations using the existing OFFAIR Tesseract integration (document/ocr.py).
Air-gap safe. If Tesseract is missing, returns clear friendly status without crashing.
"""

from __future__ import annotations

import io
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from PIL import Image as PILImage

try:
    import pymupdf as fitz
    _PYMUPDF_AVAILABLE = True
except ImportError:
    try:
        import fitz
        _PYMUPDF_AVAILABLE = True
    except ImportError:
        _PYMUPDF_AVAILABLE = False

from document.ocr import (
    get_available_languages as _existing_get_available_languages,
    get_default_ocr_lang as _existing_get_default_ocr_lang,
    get_ocr_status as _existing_get_ocr_status,
    ocr_image as _existing_ocr_image,
    tesseract_available,
)
from document_tools.common import (
    parse_page_ranges,
    validate_image,
    validate_pdf,
)


def get_ocr_engine_status() -> Dict[str, Any]:
    """Check if local Tesseract OCR engine is available and return diagnostics."""
    status = _existing_get_ocr_status()
    return {
        "engine": "Tesseract (local)",
        "available": status.get("available", False),
        "version": status.get("version"),
        "languages": status.get("languages", []),
        "default_language": status.get("default_language", "eng"),
        "cloud": False,
        "message": status.get("message", "Tesseract status checked"),
    }


def _check_tesseract_or_raise() -> None:
    if not tesseract_available():
        raise HTTPException(
            status_code=503,
            detail="Tesseract OCR is not available. Install Tesseract or configure TESSERACT_CMD.",
        )


def ocr_single_image(image_bytes: bytes, lang: Optional[str] = None) -> str:
    """Run OCR on uploaded image bytes."""
    validate_image(image_bytes)
    _check_tesseract_or_raise()

    try:
        img = PILImage.open(io.BytesIO(image_bytes))
        extracted = _existing_ocr_image(img, lang=lang)
        return extracted.strip() if extracted else "[No text recognized]"
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="OCR processing failed. Ensure the image is valid and readable.",
        )


def ocr_pdf_document(
    data: bytes,
    pages: str = "all",
    lang: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Rasterize PDF pages using PyMuPDF and perform OCR on each page.
    Returns per-page text and consolidated text.
    """
    validate_pdf(data)
    _check_tesseract_or_raise()

    if not _PYMUPDF_AVAILABLE:
        raise HTTPException(
            status_code=500,
            detail="PyMuPDF is required for PDF page rasterization.",
        )

    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Could not open PDF file. File may be corrupted or encrypted.",
        )

    try:
        total_pages = len(doc)
        target_pages = parse_page_ranges(pages, total_pages)

        pages_result: List[Dict[str, Any]] = []
        full_text_parts: List[str] = []
        mat = fitz.Matrix(150 / 72.0, 150 / 72.0)

        for p_num in target_pages:
            page = doc[p_num - 1]
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = PILImage.frombytes("RGB", [pix.width, pix.height], pix.samples)
            page_text = _existing_ocr_image(img, lang=lang).strip()

            pages_result.append({
                "page_number": p_num,
                "text": page_text if page_text else "[No text detected]",
                "char_count": len(page_text),
            })
            full_text_parts.append(
                f"--- Page {p_num} ---\n{page_text if page_text else '[No text detected]'}\n"
            )

        doc.close()
        return {
            "total_pages_ocr": len(target_pages),
            "pages": pages_result,
            "full_text": "\n".join(full_text_parts),
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to rasterize and OCR PDF pages.",
        )


def create_searchable_pdf(
    data: bytes,
    pages: str = "all",
    lang: Optional[str] = None,
) -> bytes:
    """
    Rasterize scanned PDF and embed OCR text layer into a new searchable PDF.
    """
    validate_pdf(data)
    _check_tesseract_or_raise()

    if not _PYMUPDF_AVAILABLE:
        raise HTTPException(
            status_code=500,
            detail="PyMuPDF is required for searchable PDF generation.",
        )

    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Could not open PDF file. File may be corrupted or encrypted.",
        )

    try:
        total_pages = len(doc)
        target_pages = set(parse_page_ranges(pages, total_pages))

        out_doc = fitz.open()
        mat = fitz.Matrix(150 / 72.0, 150 / 72.0)

        for i in range(total_pages):
            page = doc[i]
            p_num = i + 1
            w, h = page.rect.width, page.rect.height

            new_page = out_doc.new_page(width=w, height=h)
            new_page.show_pdf_page(fitz.Rect(0, 0, w, h), doc, i)

            if p_num in target_pages:
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img = PILImage.frombytes("RGB", [pix.width, pix.height], pix.samples)
                text = _existing_ocr_image(img, lang=lang).strip()
                if text:
                    # Insert hidden / invisible text layer
                    new_page.insert_textbox(
                        fitz.Rect(20, 20, w - 20, h - 20),
                        text,
                        fontsize=8,
                        render_mode=3,  # invisible text layer for searching/selection
                    )

        out_bytes = out_doc.tobytes(garbage=4, deflate=True)
        out_doc.close()
        doc.close()
        return out_bytes
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate searchable PDF.",
        )
