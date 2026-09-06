"""
document/ocr.py
Local OCR using pytesseract (Tesseract wrapper).
Never sends data to external services.
"""

import base64
import io
import os
import sys
from pathlib import Path
from typing import Optional, Union

_base = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _base)

from security.audit import log

try:
    import pytesseract
    from PIL import Image
    # Point pytesseract at the known install location (not always on PATH on Windows)
    _TESS_PATHS = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Users\kaust\AppData\Local\Tesseract-OCR\tesseract.exe",
    ]
    for _p in _TESS_PATHS:
        if os.path.isfile(_p):
            pytesseract.pytesseract.tesseract_cmd = _p
            break
    _TESSERACT_AVAILABLE = True
    # Verify the binary actually responds
    try:
        pytesseract.get_tesseract_version()
    except Exception:
        _TESSERACT_AVAILABLE = False
except ImportError:
    _TESSERACT_AVAILABLE = False

try:
    from PIL import Image as PILImage
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


def tesseract_available() -> bool:
    return _TESSERACT_AVAILABLE


def ocr_image(image) -> str:
    """
    Run OCR on a PIL Image object.
    Returns extracted text string.
    """
    if not _TESSERACT_AVAILABLE:
        return ""
    try:
        text = pytesseract.image_to_string(image, lang="eng")
        log("OCR_EXECUTED", engine="tesseract", chars=len(text))
        return text.strip()
    except Exception as e:
        log("OCR_ERROR", engine="tesseract", error=str(e))
        return ""


def ocr_image_file(image_path: str | Path) -> str:
    """Run OCR on an image file. Returns extracted text."""
    if not _PIL_AVAILABLE or not _TESSERACT_AVAILABLE:
        return ""
    try:
        img = PILImage.open(str(image_path))
        return ocr_image(img)
    except Exception as e:
        log("OCR_ERROR", path=str(image_path), error=str(e))
        return ""


def ocr_image_bytes(image_bytes: bytes) -> str:
    """Run OCR on raw image bytes."""
    if not _PIL_AVAILABLE or not _TESSERACT_AVAILABLE:
        return ""
    try:
        img = PILImage.open(io.BytesIO(image_bytes))
        return ocr_image(img)
    except Exception as e:
        log("OCR_ERROR", error=str(e))
        return ""


def image_to_base64(image) -> str:
    """
    Convert a PIL Image to base64 string for use with vision models.
    """
    buf = io.BytesIO()
    if hasattr(image, 'mode') and image.mode != 'RGB':
        image = image.convert('RGB')
    image.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def image_file_to_base64(image_path: str | Path) -> str:
    """Convert an image file to base64 string."""
    if not _PIL_AVAILABLE:
        # Raw base64
        with open(str(image_path), "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    try:
        img = PILImage.open(str(image_path))
        return image_to_base64(img)
    except Exception as e:
        log("IMAGE_B64_ERROR", path=str(image_path), error=str(e))
        return ""


def ocr_pdf_pages(pages: list[dict]) -> list[dict]:
    """
    Run OCR on scanned PDF pages.
    pages: list from pdf_processor.process_pdf()
    Returns pages with 'ocr_text' field added.
    """
    for page in pages:
        if page.get("is_scanned") and page.get("image"):
            ocr_text = ocr_image(page["image"])
            page["ocr_text"] = ocr_text
            page["text"] = ocr_text  # update main text field
            log("OCR_PAGE", page_num=page["page_num"], chars=len(ocr_text))
        elif not page.get("ocr_text"):
            page["ocr_text"] = page.get("text", "")
    return pages


def get_ocr_status() -> dict:
    """Return OCR engine status for health check."""
    return {
        "engine": "tesseract",
        "available": _TESSERACT_AVAILABLE,
        "cloud": False,
        "message": (
            "Tesseract OCR ready"
            if _TESSERACT_AVAILABLE
            else "Tesseract not found — install from https://github.com/UB-Mannheim/tesseract/wiki"
        ),
    }
