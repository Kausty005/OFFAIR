"""
document_tools/common.py
Common helpers, validation, security checks, and safe path utilities.
No AI, no cloud APIs, strictly local sandboxed operations.
"""

from __future__ import annotations

import io
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException

# Output directory within application workspace
_OUTPUT_DIR = Path("workspace/outputs")
_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 50 MB per file limit
_MAX_FILE_BYTES = 50 * 1024 * 1024


def format_file_size(size_in_bytes: int) -> str:
    """Format byte count into human readable B / KB / MB."""
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes / 1024:.1f} KB"
    else:
        return f"{size_in_bytes / (1024 * 1024):.2f} MB"


def safe_filename(name: str, default: str = "output") -> str:
    """Strip path traversal characters and sanitize filename."""
    name = Path(name).name
    # Keep alphanumeric, dot, hyphen, underscore
    cleaned = re.sub(r"[^\w.\-]", "_", name)
    cleaned = re.sub(r"_+", "_", cleaned).strip("._")
    return cleaned if cleaned else default


def get_output_path(filename: str) -> Path:
    """Return a validated, safe path inside workspace/outputs/."""
    safe_name = safe_filename(filename)
    dest = _OUTPUT_DIR / safe_name
    return dest


def save_output_bytes(data: bytes, filename: str) -> Path:
    """Save bytes to workspace/outputs and return safe path."""
    path = get_output_path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def validate_file_size(data: bytes, label: str = "File", max_bytes: int = _MAX_FILE_BYTES) -> None:
    """Ensure file size is within allowable bounds."""
    if len(data) == 0:
        raise HTTPException(status_code=400, detail=f"{label} is empty (0 bytes)")
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail=f"{label} exceeds maximum allowed size ({max_bytes // (1024 * 1024)} MB)")


def validate_pdf(data: bytes, label: str = "PDF file") -> None:
    """Validate PDF magic bytes and size."""
    validate_file_size(data, label=label)
    if not data.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail=f"{label}: Not a valid PDF document (missing %PDF signature)")


def validate_image(data: bytes, label: str = "Image file") -> None:
    """Validate image magic bytes."""
    validate_file_size(data, label=label)
    # Check signatures: PNG, JPEG, WebP, GIF, BMP
    is_png = data.startswith(b"\x89PNG")
    is_jpg = data[:3] == b"\xff\xd8\xff"
    is_webp = len(data) > 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    is_gif = data.startswith(b"GIF87a") or data.startswith(b"GIF89a")
    is_bmp = data.startswith(b"BM")
    if not (is_png or is_jpg or is_webp or is_gif or is_bmp):
        raise HTTPException(status_code=400, detail=f"{label}: Unsupported image format. Supported formats: PNG, JPG/JPEG, WebP, GIF, BMP")


def validate_docx(data: bytes, label: str = "Word file") -> None:
    """Validate DOCX zip container."""
    validate_file_size(data, label=label)
    if not data.startswith(b"PK\x03\x04"):
        raise HTTPException(status_code=400, detail=f"{label}: Not a valid DOCX document (invalid zip header)")


def validate_pptx(data: bytes, label: str = "PowerPoint file") -> None:
    """Validate PPTX zip container."""
    validate_file_size(data, label=label)
    if not data.startswith(b"PK\x03\x04"):
        raise HTTPException(status_code=400, detail=f"{label}: Not a valid PPTX presentation (invalid zip header)")


def validate_xlsx(data: bytes, label: str = "Excel file") -> None:
    """Validate XLSX zip container."""
    validate_file_size(data, label=label)
    if not data.startswith(b"PK\x03\x04"):
        raise HTTPException(status_code=400, detail=f"{label}: Not a valid XLSX spreadsheet (invalid zip header)")


def parse_page_ranges(spec: str, total_pages: int) -> List[int]:
    """
    Parse a range specification like '1-3,5,7-9' into a sorted, unique list of 1-based page numbers.
    Raises HTTPException on invalid or out-of-range inputs.
    """
    spec = spec.strip()
    if not spec:
        raise HTTPException(status_code=400, detail="Page range specification cannot be empty")

    if spec.lower() == "all":
        return list(range(1, total_pages + 1))

    pages: set[int] = set()
    parts = [p.strip() for p in spec.split(",") if p.strip()]

    if not parts:
        raise HTTPException(status_code=400, detail="Invalid page range specification")

    for part in parts:
        if "-" in part:
            bounds = part.split("-", 1)
            try:
                start, end = int(bounds[0].strip()), int(bounds[1].strip())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid page range token: '{part}'")
            if start < 1:
                raise HTTPException(status_code=400, detail=f"Page numbers start at 1, got '{start}'")
            if start > end:
                raise HTTPException(status_code=400, detail=f"Invalid range '{part}': start ({start}) > end ({end})")
            if end > total_pages:
                raise HTTPException(
                    status_code=400,
                    detail=f"Range '{part}' exceeds total document page count ({total_pages})"
                )
            pages.update(range(start, end + 1))
        else:
            try:
                page_num = int(part)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid page number: '{part}'")
            if page_num < 1 or page_num > total_pages:
                raise HTTPException(
                    status_code=400,
                    detail=f"Page number {page_num} out of range (document has {total_pages} pages)"
                )
            pages.add(page_num)

    if not pages:
        raise HTTPException(status_code=400, detail="No valid pages specified")

    return sorted(pages)


def create_zip_archive(files_map: Dict[str, bytes], zip_name: str) -> Path:
    """Create a ZIP archive containing {filename: content_bytes}."""
    zip_path = get_output_path(zip_name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files_map.items():
            safe_name = safe_filename(name)
            zf.writestr(safe_name, data)
    return zip_path
