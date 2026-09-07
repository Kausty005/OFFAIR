"""
tools/pdf_generator.py
Sovereign PDF generator using PyMuPDF (fitz) or fpdf.
Generates structured industrial and business PDF documents from Markdown/text.
100% local, air-gap compliant, zero cloud dependencies.
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

_base = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _base)

from security.audit import log
from tools.files import get_output_path

try:
    import pymupdf as fitz
    _MUPDF_AVAILABLE = True
except ImportError:
    try:
        import fitz
        _MUPDF_AVAILABLE = True
    except ImportError:
        _MUPDF_AVAILABLE = False

try:
    import fpdf
    _FPDF_AVAILABLE = True
except ImportError:
    _FPDF_AVAILABLE = False


def pdf_available() -> bool:
    """Return whether local PDF generation libraries are installed."""
    return _MUPDF_AVAILABLE or _FPDF_AVAILABLE


def create_pdf_from_markdown(
    content: str,
    title: Optional[str] = None,
    output_path: Optional[Union[str, Path]] = None,
) -> dict:
    """
    Render markdown content into a clean, professional PDF document.

    Args:
        content: Markdown or plain-text content to render.
        title: Optional document title. If not provided, inferred from text.
        output_path: Target filesystem path. If None, auto-generated in workspace/outputs/.

    Returns:
        dict: {"success": bool, "path": str, "size": int, "error": str | None}
    """
    if not pdf_available():
        return {
            "success": False,
            "path": "",
            "size": 0,
            "error": "Neither PyMuPDF (pymupdf) nor fpdf are installed.",
        }

    # Determine safe output path
    if output_path is None:
        safe_title = re.sub(r"[^\w\-]", "_", (title or "Document")[:30]).strip("_") or "Document"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_title}_{timestamp}.pdf"
        out_file = get_output_path(filename)
    else:
        out_file = Path(output_path)

    out_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        if _MUPDF_AVAILABLE:
            return _generate_pdf_mupdf(content, title, out_file)
        else:
            return _generate_pdf_fpdf(content, title, out_file)
    except Exception as exc:
        log("PDF_GENERATION_ERROR", error=str(exc))
        return {
            "success": False,
            "path": "",
            "size": 0,
            "error": str(exc),
        }


def _generate_pdf_mupdf(content: str, title: Optional[str], out_file: Path) -> dict:
    """Render PDF using PyMuPDF (fitz) Story or TextWriter layout."""
    doc = fitz.open()

    page_width, page_height = 595.0, 842.0  # Standard A4 in points
    margin = 54.0  # 0.75 inch margin
    printable_width = page_width - (margin * 2)
    bottom_limit = page_height - margin - 30.0

    lines = content.strip().split("\n")
    if not title:
        # Detect first heading or use default
        for line in lines:
            if line.startswith("#"):
                title = line.lstrip("#").strip()
                break
        if not title:
            title = "Report"

    current_page = doc.new_page(width=page_width, height=page_height)
    y = margin

    def _add_page():
        nonlocal current_page, y
        # Add running header & footer to finished page
        _add_header_footer(current_page, doc.page_count, title)
        current_page = doc.new_page(width=page_width, height=page_height)
        y = margin + 20.0

    # Document Header Title
    current_page.insert_text(
        (margin, y),
        title.upper(),
        fontsize=18,
        fontname="helv",
        color=(0.1, 0.2, 0.4),  # Dark navy blue
    )
    y += 24.0

    # Subtitle / Generation metadata
    meta_text = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Sovereign AI Workbench | Local Verification"
    current_page.insert_text(
        (margin, y),
        meta_text,
        fontsize=9,
        fontname="helv",
        color=(0.4, 0.4, 0.4),
    )
    y += 18.0

    # Horizontal divider rule
    shape = current_page.new_shape()
    shape.draw_line(fitz.Point(margin, y), fitz.Point(page_width - margin, y))
    shape.finish(color=(0.8, 0.8, 0.8), width=0.75)
    shape.commit()
    y += 18.0

    # Process markdown lines
    in_code_block = False

    for line in lines:
        stripped = line.strip()

        # Handle code blocks
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            y += 6.0
            continue

        if not stripped:
            y += 8.0
            continue

        if y > bottom_limit:
            _add_page()

        # Headings
        if stripped.startswith("# ") and not in_code_block:
            h1 = stripped[2:].strip()
            if y + 24.0 > bottom_limit:
                _add_page()
            current_page.insert_text((margin, y + 14), h1, fontsize=14, fontname="hebo", color=(0.12, 0.22, 0.38))
            y += 24.0
        elif stripped.startswith("## ") and not in_code_block:
            h2 = stripped[3:].strip()
            if y + 20.0 > bottom_limit:
                _add_page()
            current_page.insert_text((margin, y + 12), h2, fontsize=12, fontname="hebo", color=(0.2, 0.3, 0.45))
            y += 20.0
        elif stripped.startswith("### ") and not in_code_block:
            h3 = stripped[4:].strip()
            if y + 16.0 > bottom_limit:
                _add_page()
            current_page.insert_text((margin, y + 10), h3, fontsize=11, fontname="hebo", color=(0.25, 0.35, 0.5))
            y += 16.0
        # Bullet list items
        elif (stripped.startswith("- ") or stripped.startswith("* ")) and not in_code_block:
            bullet_text = stripped[2:].strip()
            bullet_text = re.sub(r"\*\*(.*?)\*\*", r"\1", bullet_text)  # Strip markdown bold marks
            rect = fitz.Rect(margin + 12, y, page_width - margin, y + 100)
            current_page.insert_text((margin + 2, y + 8), "•", fontsize=10, fontname="helv", color=(0.2, 0.4, 0.7))
            inserted = current_page.insert_textbox(rect, bullet_text, fontsize=10, fontname="helv", color=(0.15, 0.15, 0.15))
            step_y = max(14.0, (inserted + 4.0) if inserted > 0 else 14.0)
            y += step_y
        # Code block line
        elif in_code_block:
            rect = fitz.Rect(margin + 8, y, page_width - margin, y + 14)
            current_page.insert_text((margin + 8, y + 8), stripped, fontsize=9, fontname="couri", color=(0.2, 0.2, 0.2))
            y += 13.0
        # Regular paragraph
        else:
            clean_p = re.sub(r"\*\*(.*?)\*\*", r"\1", stripped)
            rect = fitz.Rect(margin, y, page_width - margin, y + 300)
            inserted = current_page.insert_textbox(rect, clean_p, fontsize=10, fontname="helv", color=(0.15, 0.15, 0.15))
            step_y = max(15.0, (inserted + 6.0) if inserted > 0 else 15.0)
            y += step_y

    # Add header/footer to the final page
    _add_header_footer(current_page, doc.page_count, title)

    doc.save(str(out_file))
    doc.close()

    file_size = out_file.stat().st_size
    log("PDF_GENERATED", path=str(out_file), size=file_size)
    return {
        "success": True,
        "path": str(out_file),
        "size": file_size,
        "error": None,
    }


def _add_header_footer(page, page_num: int, title: str):
    """Insert header and footer labels on a page."""
    # Running header
    header_text = f"OFFAIR AI · {title[:40]}"
    page.insert_text((54.0, 32.0), header_text, fontsize=8, fontname="helv", color=(0.55, 0.55, 0.55))

    # Running footer
    footer_text = f"Sovereign AI Workbench · Page {page_num} · 100% Local Air-Gapped"
    page.insert_text((54.0, 816.0), footer_text, fontsize=8, fontname="helv", color=(0.55, 0.55, 0.55))


def _generate_pdf_fpdf(content: str, title: Optional[str], out_file: Path) -> dict:
    """Fallback PDF generator using FPDF."""
    pdf = fpdf.FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, (title or "Report").encode("latin-1", "replace").decode("latin-1"), ln=True, align="L")
    pdf.ln(5)

    pdf.set_font("Helvetica", size=10)
    for line in content.split("\n"):
        clean = line.encode("latin-1", "replace").decode("latin-1")
        if clean.startswith("# "):
            pdf.set_font("Helvetica", "B", 13)
            pdf.cell(0, 8, clean[2:], ln=True)
            pdf.set_font("Helvetica", size=10)
        elif clean.startswith("## "):
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 7, clean[3:], ln=True)
            pdf.set_font("Helvetica", size=10)
        else:
            pdf.multi_cell(0, 5, clean)

    pdf.output(str(out_file))
    size = out_file.stat().st_size
    return {"success": True, "path": str(out_file), "size": size, "error": None}
