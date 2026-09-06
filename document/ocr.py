"""
document/ocr.py
Local OCR using pytesseract (Tesseract wrapper).
Never sends data to external services (Air-gap safe).
"""

from __future__ import annotations

import base64
import io
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

_base = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _base)

from security.audit import log

# Centralized detection variables
_RESOLVED_CMD: Optional[str] = None
_TESSERACT_AVAILABLE: bool = False
_TESSERACT_VERSION: Optional[str] = None
_AVAILABLE_LANGUAGES: List[str] = []
_PIL_AVAILABLE: bool = False

try:
    from PIL import Image as PILImage
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


def _resolve_tesseract_path() -> Optional[str]:
    """
    Robust Tesseract binary resolution order:
    1. TESSERACT_CMD environment variable (and legacy TESSERACT_PATH)
    2. Tesseract available through PATH
    3. Windows default path: C:\\Program Files\\Tesseract-OCR\\tesseract.exe
       followed by standard Windows install locations.
    """
    # 1. Environment variable
    env_cmd = os.environ.get("TESSERACT_CMD") or os.environ.get("TESSERACT_PATH")
    if env_cmd and os.path.isfile(env_cmd):
        return env_cmd

    # 2. PATH resolution
    which_cmd = shutil.which("tesseract") or shutil.which("tesseract.exe")
    if which_cmd and os.path.isfile(which_cmd):
        return which_cmd

    # 3. Windows default locations
    windows_defaults = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe"),
    ]
    for candidate in windows_defaults:
        if candidate and os.path.isfile(candidate):
            return candidate

    return None


def init_tesseract() -> bool:
    """Initialize and configure local Tesseract engine."""
    global _RESOLVED_CMD, _TESSERACT_AVAILABLE, _TESSERACT_VERSION, _AVAILABLE_LANGUAGES

    try:
        import pytesseract

        cmd = _resolve_tesseract_path()
        if not cmd:
            _TESSERACT_AVAILABLE = False
            _RESOLVED_CMD = None
            _TESSERACT_VERSION = None
            _AVAILABLE_LANGUAGES = []
            return False

        _RESOLVED_CMD = cmd
        pytesseract.pytesseract.tesseract_cmd = cmd

        # Automatically configure TESSDATA_PREFIX if not explicitly set
        tessdata_dir = os.path.join(os.path.dirname(cmd), "tessdata")
        if os.path.isdir(tessdata_dir) and not os.environ.get("TESSDATA_PREFIX"):
            os.environ["TESSDATA_PREFIX"] = tessdata_dir

        # Verify executable by retrieving version
        ver = pytesseract.get_tesseract_version()
        _TESSERACT_VERSION = str(ver)

        # Detect installed languages safely
        langs: List[str] = []
        try:
            langs = pytesseract.get_languages()
        except Exception:
            try:
                proc = subprocess.run(
                    [cmd, "--list-langs"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if proc.returncode == 0:
                    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
                    # First line is usually "List of available languages..."
                    langs = [l for l in lines if not l.lower().startswith("list of")]
            except Exception:
                langs = ["eng"]

        _AVAILABLE_LANGUAGES = langs if langs else ["eng"]
        _TESSERACT_AVAILABLE = True
        return True

    except Exception as exc:
        log("TESSERACT_INIT_ERROR", error=str(exc))
        _TESSERACT_AVAILABLE = False
        _RESOLVED_CMD = None
        _TESSERACT_VERSION = None
        _AVAILABLE_LANGUAGES = []
        return False


# Initialize on module load
init_tesseract()


def tesseract_available() -> bool:
    """Return whether local Tesseract OCR engine is detected and ready."""
    return _TESSERACT_AVAILABLE


def get_available_languages() -> List[str]:
    """Return the list of installed OCR languages detected from Tesseract."""
    return list(_AVAILABLE_LANGUAGES)


def get_default_ocr_lang() -> str:
    """
    Return the optimal OCR language combination based on installed languages.
    If 'hin' is installed alongside 'eng', returns 'eng+hin'; otherwise returns 'eng'.
    """
    if "hin" in _AVAILABLE_LANGUAGES and "eng" in _AVAILABLE_LANGUAGES:
        return "eng+hin"
    if "eng" in _AVAILABLE_LANGUAGES:
        return "eng"
    return _AVAILABLE_LANGUAGES[0] if _AVAILABLE_LANGUAGES else "eng"


def resolve_ocr_lang(requested_lang: Optional[str] = None) -> str:
    """
    Validate and resolve language request against installed languages.
    Falls back to available languages if requested language is missing.
    """
    if not requested_lang:
        return get_default_ocr_lang()

    # Split combinations like eng+hin
    parts = [p.strip() for p in requested_lang.split("+") if p.strip()]
    valid_parts = [p for p in parts if p in _AVAILABLE_LANGUAGES]

    if valid_parts:
        return "+".join(valid_parts)
    return get_default_ocr_lang()


def get_tesseract_config() -> Dict[str, Any]:
    """Return centralized configuration and runtime diagnostics."""
    return {
        "available": _TESSERACT_AVAILABLE,
        "version": _TESSERACT_VERSION,
        "command": _RESOLVED_CMD,
        "languages": get_available_languages(),
        "default_language": get_default_ocr_lang(),
    }


def ocr_image(image, lang: Optional[str] = None) -> str:
    """
    Run OCR on a PIL Image object using local Tesseract.
    Returns extracted text string. Never sends data externally.
    """
    if not _TESSERACT_AVAILABLE:
        return ""

    try:
        import pytesseract

        selected_lang = resolve_ocr_lang(lang)
        text = pytesseract.image_to_string(image, lang=selected_lang)
        log("OCR_EXECUTED", engine="tesseract", lang=selected_lang, chars=len(text))
        return text.strip()
    except Exception as exc:
        log("OCR_ERROR", engine="tesseract", error=str(exc))
        return ""


def ocr_image_file(image_path: Union[str, Path], lang: Optional[str] = None) -> str:
    """Run OCR on an image file. Returns extracted text."""
    if not _PIL_AVAILABLE or not _TESSERACT_AVAILABLE:
        return ""
    try:
        img = PILImage.open(str(image_path))
        return ocr_image(img, lang=lang)
    except Exception as exc:
        log("OCR_ERROR", path=str(image_path), error=str(exc))
        return ""


def ocr_image_bytes(image_bytes: bytes, lang: Optional[str] = None) -> str:
    """Run OCR on raw image bytes."""
    if not _PIL_AVAILABLE or not _TESSERACT_AVAILABLE:
        return ""
    try:
        img = PILImage.open(io.BytesIO(image_bytes))
        return ocr_image(img, lang=lang)
    except Exception as exc:
        log("OCR_ERROR", error=str(exc))
        return ""


def image_to_base64(image) -> str:
    """Convert a PIL Image to base64 string."""
    buf = io.BytesIO()
    if hasattr(image, "mode") and image.mode != "RGB":
        image = image.convert("RGB")
    image.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def image_file_to_base64(image_path: Union[str, Path]) -> str:
    """Convert an image file to base64 string."""
    if not _PIL_AVAILABLE:
        with open(str(image_path), "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    try:
        img = PILImage.open(str(image_path))
        return image_to_base64(img)
    except Exception as exc:
        log("IMAGE_B64_ERROR", path=str(image_path), error=str(exc))
        return ""


def ocr_pdf_pages(pages: list[dict], lang: Optional[str] = None) -> list[dict]:
    """
    Run OCR on scanned PDF pages.
    pages: list from pdf_processor.process_pdf()
    Returns pages with 'ocr_text' field added.
    """
    for page in pages:
        if page.get("is_scanned") and page.get("image"):
            ocr_text = ocr_image(page["image"], lang=lang)
            page["ocr_text"] = ocr_text
            page["text"] = ocr_text
            log("OCR_PAGE", page_num=page["page_num"], chars=len(ocr_text))
        elif not page.get("ocr_text"):
            page["ocr_text"] = page.get("text", "")
    return pages


def get_ocr_status() -> dict:
    """Return OCR engine status for health checks."""
    if _TESSERACT_AVAILABLE:
        lang_str = ", ".join(_AVAILABLE_LANGUAGES)
        msg = f"Tesseract OCR ready ({lang_str})"
    else:
        msg = "Tesseract OCR is not available. Install Tesseract or configure TESSERACT_CMD."

    return {
        "engine": "tesseract",
        "available": _TESSERACT_AVAILABLE,
        "version": _TESSERACT_VERSION,
        "languages": get_available_languages(),
        "default_language": get_default_ocr_lang(),
        "cloud": False,
        "message": msg,
    }
