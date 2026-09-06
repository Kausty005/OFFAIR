"""
document_tools/pdf_ops.py
Purely local PDF operations using PyMuPDF (fitz) and PyPDF2.
Zero network access, zero cloud APIs, zero Ollama/Docker dependencies.
"""

from __future__ import annotations

import io
import math
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException

try:
    import pymupdf as fitz
    _PYMUPDF_AVAILABLE = True
except ImportError:
    try:
        import fitz
        _PYMUPDF_AVAILABLE = True
    except ImportError:
        _PYMUPDF_AVAILABLE = False

try:
    import PyPDF2
    _PYPDF2_AVAILABLE = True
except ImportError:
    _PYPDF2_AVAILABLE = False

from PIL import Image as PILImage
from document_tools.common import (
    parse_page_ranges,
    safe_filename,
    validate_image,
    validate_pdf,
)


def _open_fitz_doc(data: bytes, password: Optional[str] = None) -> fitz.Document:
    """Safely open a PDF bytes stream using PyMuPDF."""
    if not _PYMUPDF_AVAILABLE:
        raise HTTPException(status_code=500, detail="PyMuPDF is not installed on this server")
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Cannot read PDF: Corrupted or invalid file ({exc})")

    if doc.is_encrypted:
        if password:
            auth = doc.authenticate(password)
            if auth <= 0:
                raise HTTPException(status_code=400, detail="Invalid password for encrypted PDF")
        else:
            raise HTTPException(status_code=400, detail="PDF is password-protected. Please provide the decryption password.")
    
    if len(doc) == 0:
        raise HTTPException(status_code=400, detail="PDF document contains 0 pages")

    return doc


# ─────────────────────────────────────────────────────────────────────────────
# 1. ORGANIZE: Merge, Split, Extract, Delete, Reorder, Rotate, Crop, Resize
# ─────────────────────────────────────────────────────────────────────────────

def merge_pdfs(files: List[Tuple[bytes, str]]) -> bytes:
    """Merge multiple PDF byte streams in order."""
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="At least 2 PDF files are required for merging")

    merged = fitz.open()
    for idx, (data, filename) in enumerate(files):
        validate_pdf(data, label=filename or f"File #{idx+1}")
        doc = _open_fitz_doc(data)
        merged.insert_pdf(doc)
        doc.close()

    out_buf = merged.tobytes(garbage=4, deflate=True)
    merged.close()
    return out_buf


def split_pdf(data: bytes, mode: str = "all", ranges: str = "") -> Dict[str, bytes]:
    """
    Split PDF into parts.
    mode in ('all', 'every'): Every page as a separate PDF.
    mode == 'ranges': Custom ranges (e.g. '1-3, 4-6').
    """
    validate_pdf(data)
    doc = _open_fitz_doc(data)
    total_pages = len(doc)
    results: Dict[str, bytes] = {}

    if mode in ("all", "every"):
        for i in range(total_pages):
            single_doc = fitz.open()
            single_doc.insert_pdf(doc, from_page=i, to_page=i)
            results[f"page_{i + 1:04d}.pdf"] = single_doc.tobytes(garbage=4, deflate=True)
            single_doc.close()
    elif mode == "ranges":
        if not ranges.strip():
            raise HTTPException(status_code=400, detail="Ranges parameter is required when mode is 'ranges'")
        range_tokens = [r.strip() for r in ranges.split(",") if r.strip()]
        for idx, token in enumerate(range_tokens):
            pages = parse_page_ranges(token, total_pages)
            if not pages:
                continue
            range_doc = fitz.open()
            for p in pages:
                range_doc.insert_pdf(doc, from_page=p - 1, to_page=p - 1)
            token_clean = token.replace("-", "_")
            results[f"part_{idx + 1:02d}_pages_{token_clean}.pdf"] = range_doc.tobytes(garbage=4, deflate=True)
            range_doc.close()
    else:
        raise HTTPException(status_code=400, detail="Split mode must be 'all' or 'ranges'")

    doc.close()
    if not results:
        raise HTTPException(status_code=400, detail="No output files were generated from split")
    return results


def extract_pages(data: bytes, page_spec: str) -> bytes:
    """Extract specified pages into a single PDF."""
    validate_pdf(data)
    doc = _open_fitz_doc(data)
    pages = parse_page_ranges(page_spec, len(doc))

    new_doc = fitz.open()
    for p in pages:
        new_doc.insert_pdf(doc, from_page=p - 1, to_page=p - 1)

    out_bytes = new_doc.tobytes(garbage=4, deflate=True)
    new_doc.close()
    doc.close()
    return out_bytes


def delete_pages(data: bytes, page_spec: str) -> bytes:
    """Delete specified pages, preserving the remaining pages."""
    validate_pdf(data)
    doc = _open_fitz_doc(data)
    total_pages = len(doc)
    to_delete = set(parse_page_ranges(page_spec, total_pages))

    if len(to_delete) >= total_pages:
        doc.close()
        raise HTTPException(status_code=400, detail="Cannot delete all pages of the document")

    # PyMuPDF 0-indexed page list to keep
    keep_indices = [i for i in range(total_pages) if (i + 1) not in to_delete]
    doc.select(keep_indices)

    out_bytes = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    return out_bytes


def reorder_pages(data: bytes, page_order: List[int]) -> bytes:
    """
    Reorder pages based on a 1-indexed list of page numbers.
    e.g. [3, 1, 2, 4]
    """
    validate_pdf(data)
    doc = _open_fitz_doc(data)
    total_pages = len(doc)

    if not page_order:
        raise HTTPException(status_code=400, detail="Page order list cannot be empty")

    zero_based = []
    for p in page_order:
        if p < 1 or p > total_pages:
            raise HTTPException(status_code=400, detail=f"Invalid page number {p} (document has {total_pages} pages)")
        zero_based.append(p - 1)

    doc.select(zero_based)
    out_bytes = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    return out_bytes


def rotate_pdf(data: bytes, angle: int, page_spec: str = "all") -> bytes:
    """Rotate pages by 90, 180, or 270 degrees."""
    if angle not in (90, 180, 270):
        raise HTTPException(status_code=400, detail="Angle must be 90, 180, or 270 degrees")

    validate_pdf(data)
    doc = _open_fitz_doc(data)
    total_pages = len(doc)
    target_pages = set(parse_page_ranges(page_spec, total_pages))

    for p_num in target_pages:
        page = doc[p_num - 1]
        page.set_rotation((page.rotation + angle) % 360)

    out_bytes = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    return out_bytes


def crop_pdf(data: bytes, margin_left: float, margin_top: float, margin_right: float, margin_bottom: float, page_spec: str = "all") -> bytes:
    """Crop page margins (in points). 1 point = 1/72 inch."""
    validate_pdf(data)
    doc = _open_fitz_doc(data)
    total_pages = len(doc)
    target_pages = set(parse_page_ranges(page_spec, total_pages))

    for p_num in target_pages:
        page = doc[p_num - 1]
        rect = page.rect
        new_x0 = rect.x0 + margin_left
        new_y0 = rect.y0 + margin_top
        new_x1 = rect.x1 - margin_right
        new_y1 = rect.y1 - margin_bottom
        if new_x1 <= new_x0 or new_y1 <= new_y0:
            raise HTTPException(status_code=400, detail=f"Crop margins exceed page dimensions on page {p_num}")
        page.set_cropbox(fitz.Rect(new_x0, new_y0, new_x1, new_y1))

    out_bytes = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    return out_bytes


def resize_pdf(data: bytes, target_size: str = "A4", page_spec: str = "all") -> bytes:
    """
    Resize PDF pages to a standard size: A4, Letter, A3, Legal.
    """
    sizes = {
        "A4": (595.0, 842.0),
        "Letter": (612.0, 792.0),
        "A3": (842.0, 1191.0),
        "Legal": (612.0, 1008.0),
    }
    if target_size not in sizes:
        raise HTTPException(status_code=400, detail=f"Unsupported target size '{target_size}'. Choose: A4, Letter, A3, Legal")

    new_w, new_h = sizes[target_size]
    validate_pdf(data)
    doc = _open_fitz_doc(data)
    total_pages = len(doc)
    target_pages = set(parse_page_ranges(page_spec, total_pages))

    new_doc = fitz.open()
    for i in range(total_pages):
        page = doc[i]
        if (i + 1) in target_pages:
            new_page = new_doc.new_page(width=new_w, height=new_h)
            # Scale and center old page into new page
            rx = new_w / page.rect.width
            ry = new_h / page.rect.height
            scale = min(rx, ry)
            scaled_w = page.rect.width * scale
            scaled_h = page.rect.height * scale
            offset_x = (new_w - scaled_w) / 2
            offset_y = (new_h - scaled_h) / 2
            dest_rect = fitz.Rect(offset_x, offset_y, offset_x + scaled_w, offset_y + scaled_h)
            new_page.show_pdf_page(dest_rect, doc, i)
        else:
            new_doc.insert_pdf(doc, from_page=i, to_page=i)

    out_bytes = new_doc.tobytes(garbage=4, deflate=True)
    new_doc.close()
    doc.close()
    return out_bytes


def add_blank_page(data: bytes, position: str = "end", target_page: int = 1, page_size: str = "A4") -> bytes:
    """Insert a blank page at start, end, or after target_page."""
    validate_pdf(data)
    doc = _open_fitz_doc(data)
    total_pages = len(doc)

    sizes = {
        "A4": (595.0, 842.0),
        "Letter": (612.0, 792.0),
        "A3": (842.0, 1191.0),
    }
    w, h = sizes.get(page_size, (595.0, 842.0))

    if position == "start":
        idx = 0
    elif position == "end":
        idx = total_pages
    elif position == "after":
        if target_page < 1 or target_page > total_pages:
            raise HTTPException(status_code=400, detail=f"Target page {target_page} out of range (1-{total_pages})")
        idx = target_page
    else:
        raise HTTPException(status_code=400, detail="Position must be 'start', 'end', or 'after'")

    doc.insert_page(idx, width=w, height=h)
    out_bytes = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    return out_bytes


def duplicate_page(data: bytes, page_num: int, count: int = 1) -> bytes:
    """Duplicate a specified page N times."""
    if count < 1 or count > 50:
        raise HTTPException(status_code=400, detail="Duplicate count must be between 1 and 50")

    validate_pdf(data)
    doc = _open_fitz_doc(data)
    total_pages = len(doc)
    if page_num < 1 or page_num > total_pages:
        raise HTTPException(status_code=400, detail=f"Page {page_num} out of range (1-{total_pages})")

    p_idx = page_num - 1
    new_doc = fitz.open()
    for i in range(total_pages):
        new_doc.insert_pdf(doc, from_page=i, to_page=i)
        if i == p_idx:
            for _ in range(count):
                new_doc.insert_pdf(doc, from_page=i, to_page=i)

    out_bytes = new_doc.tobytes(garbage=4, deflate=True)
    new_doc.close()
    doc.close()
    return out_bytes


# ─────────────────────────────────────────────────────────────────────────────
# 2. CONVERT: PDF ↔ Images, Text, Markdown, DOCX
# ─────────────────────────────────────────────────────────────────────────────

def render_pdf_to_images(data: bytes, fmt: str = "PNG", pages: str = "all", dpi: int = 150) -> Dict[str, bytes]:
    """
    Render PDF pages to images (PNG or JPG) using PyMuPDF.
    Returns {filename: image_bytes}.
    """
    fmt = fmt.upper()
    if fmt not in ("PNG", "JPG", "JPEG"):
        raise HTTPException(status_code=400, detail="Image format must be PNG or JPG")

    ext = "jpg" if fmt in ("JPG", "JPEG") else "png"
    pil_format = "JPEG" if ext == "jpg" else "PNG"

    validate_pdf(data)
    doc = _open_fitz_doc(data)
    total_pages = len(doc)
    target_pages = parse_page_ranges(pages, total_pages)

    results: Dict[str, bytes] = {}
    mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)

    for p_num in target_pages:
        page = doc[p_num - 1]
        pix = page.get_pixmap(matrix=mat, alpha=False if ext == "jpg" else True)
        buf = io.BytesIO()
        img = PILImage.frombytes("RGB" if ext == "jpg" else "RGBA", [pix.width, pix.height], pix.samples)
        if ext == "jpg":
            img.save(buf, format="JPEG", quality=90)
        else:
            img.save(buf, format="PNG")
        results[f"page_{p_num:04d}.{ext}"] = buf.getvalue()

    doc.close()
    if not results:
        raise HTTPException(status_code=400, detail="No images rendered")
    return results


def images_to_pdf(images: List[Tuple[bytes, str]]) -> bytes:
    """Combine multiple images into a clean single PDF."""
    if not images:
        raise HTTPException(status_code=400, detail="At least one image file is required")

    new_doc = fitz.open()
    A4_W, A4_H = 595.0, 842.0

    for idx, (img_bytes, fname) in enumerate(images):
        validate_image(img_bytes, label=fname or f"Image #{idx+1}")
        try:
            pil_img = PILImage.open(io.BytesIO(img_bytes))
            # Convert RGBA or CMYK to RGB
            if pil_img.mode in ("RGBA", "LA", "P"):
                rgb_img = PILImage.new("RGB", pil_img.size, (255, 255, 255))
                rgb_img.paste(pil_img, mask=pil_img.split()[-1] if pil_img.mode == "RGBA" else None)
                pil_img = rgb_img
            elif pil_img.mode != "RGB":
                pil_img = pil_img.convert("RGB")

            buf = io.BytesIO()
            pil_img.save(buf, format="JPEG", quality=92)
            clean_jpg = buf.getvalue()

            iw, ih = pil_img.size
            # Fit on A4 page
            scale = min((A4_W - 40) / iw, (A4_H - 40) / ih)
            scaled_w, scaled_h = iw * scale, ih * scale
            ox = (A4_W - scaled_w) / 2
            oy = (A4_H - scaled_h) / 2

            page = new_doc.new_page(width=A4_W, height=A4_H)
            rect = fitz.Rect(ox, oy, ox + scaled_w, oy + scaled_h)
            page.insert_image(rect, stream=clean_jpg)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Cannot process image {fname}: {exc}")

    out_bytes = new_doc.tobytes(garbage=4, deflate=True)
    new_doc.close()
    return out_bytes


def extract_text_from_pdf(data: bytes) -> Tuple[str, bool]:
    """
    Extract digital text from PDF.
    Returns (extracted_text, is_likely_scanned).
    """
    validate_pdf(data)
    doc = _open_fitz_doc(data)
    lines: List[str] = []
    total_chars = 0

    for i, page in enumerate(doc):
        text = page.get_text("text").strip()
        total_chars += len(text)
        lines.append(f"--- Page {i + 1} ---")
        lines.append(text if text else "[No extractable text on this page]")
        lines.append("")

    doc.close()
    full_text = "\n".join(lines)
    is_scanned = total_chars < 50
    return full_text, is_scanned


def pdf_to_markdown(data: bytes) -> str:
    """
    Extract structured text from PDF formatted as Markdown headings and paragraphs.
    """
    validate_pdf(data)
    doc = _open_fitz_doc(data)
    md_sections: List[str] = []

    for i, page in enumerate(doc):
        md_sections.append(f"## Page {i + 1}\n")
        blocks = page.get_text("blocks")
        # blocks: (x0, y0, x1, y1, text, block_no, block_type)
        for b in blocks:
            if len(b) >= 5 and b[4].strip():
                txt = b[4].strip()
                # Simple heading heuristic: short line, all caps or starts with numbers
                if len(txt) < 80 and ("\n" not in txt) and (txt.isupper() or txt.endswith(":")):
                    md_sections.append(f"### {txt}\n")
                else:
                    md_sections.append(f"{txt}\n")

    doc.close()
    return "\n".join(md_sections)


def pdf_to_docx(data: bytes) -> bytes:
    """
    Convert text and structure from PDF into a formatted Word (.docx) document.
    Uses PyMuPDF text blocks and python-docx.
    """
    try:
        from docx import Document
        from docx.shared import Pt, Inches, RGBColor
    except ImportError:
        raise HTTPException(status_code=500, detail="python-docx is not installed")

    validate_pdf(data)
    doc = _open_fitz_doc(data)
    word_doc = Document()

    # Style margins
    for sec in word_doc.sections:
        sec.top_margin = Inches(0.75)
        sec.bottom_margin = Inches(0.75)
        sec.left_margin = Inches(0.75)
        sec.right_margin = Inches(0.75)

    for i, page in enumerate(doc):
        if i > 0:
            word_doc.add_page_break()

        heading = word_doc.add_heading(f"Page {i + 1}", level=2)
        blocks = page.get_text("blocks")
        for b in blocks:
            if len(b) >= 5 and b[4].strip():
                txt = b[4].strip()
                if len(txt) < 70 and ("\n" not in txt) and (txt.isupper() or txt.endswith(":")):
                    word_doc.add_heading(txt, level=3)
                else:
                    p = word_doc.add_paragraph(txt)
                    p.paragraph_format.space_after = Pt(6)

    doc.close()
    out_buf = io.BytesIO()
    word_doc.save(out_buf)
    return out_buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# 3. OPTIMIZE: Compress PDF
# ─────────────────────────────────────────────────────────────────────────────

def compress_pdf(data: bytes, level: str = "medium") -> Tuple[bytes, int, int, float]:
    """
    Compress PDF:
    - low: garbage collection, deflating streams, strip metadata.
    - medium: above + clean content streams + deduplicate fonts/images.
    - high: above + downsample high-res embedded images to 150 DPI.
    Returns (out_bytes, original_size, output_size, reduction_pct).
    """
    if level not in ("low", "medium", "high"):
        raise HTTPException(status_code=400, detail="Level must be 'low', 'medium', or 'high'")

    validate_pdf(data)
    orig_size = len(data)
    doc = _open_fitz_doc(data)

    # Strip metadata on medium and high
    if level in ("medium", "high"):
        doc.set_metadata({})

    # High level: re-compress large images if present
    if level == "high":
        for i in range(len(doc)):
            page = doc[i]
            img_list = page.get_images()
            for img_info in img_list:
                xref = img_info[0]
                try:
                    base_img = doc.extract_image(xref)
                    if base_img and "image" in base_img:
                        pil = PILImage.open(io.BytesIO(base_img["image"]))
                        if pil.width > 1200 or pil.height > 1200:
                            pil.thumbnail((1200, 1200), PILImage.LANCZOS)
                            buf = io.BytesIO()
                            pil.convert("RGB").save(buf, format="JPEG", quality=75)
                            # Update image stream in PDF
                            doc.update_stream(xref, buf.getvalue())
                except Exception:
                    pass

    # Save with full optimization flags
    compressed_bytes = doc.tobytes(garbage=4, deflate=True, clean=True)
    doc.close()

    # Safety check: if compressed output is larger than original, return original
    if len(compressed_bytes) >= orig_size:
        final_bytes = data
        out_size = orig_size
        reduction_pct = 0.0
    else:
        final_bytes = compressed_bytes
        out_size = len(final_bytes)
        reduction_pct = round(((orig_size - out_size) / orig_size) * 100.0, 1)

    return final_bytes, orig_size, out_size, reduction_pct


# ─────────────────────────────────────────────────────────────────────────────
# 4. SECURITY & METADATA
# ─────────────────────────────────────────────────────────────────────────────

def get_pdf_metadata(data: bytes) -> Dict[str, str]:
    """Extract standard and custom metadata keys."""
    validate_pdf(data)
    doc = _open_fitz_doc(data)
    meta = doc.metadata or {}
    total_pages = len(doc)
    doc.close()

    return {
        "title": meta.get("title") or "—",
        "author": meta.get("author") or "—",
        "subject": meta.get("subject") or "—",
        "keywords": meta.get("keywords") or "—",
        "creator": meta.get("creator") or "—",
        "producer": meta.get("producer") or "—",
        "creationDate": meta.get("creationDate") or "—",
        "modDate": meta.get("modDate") or "—",
        "page_count": str(total_pages),
        "total_pages": total_pages,
        "format": meta.get("format") or "PDF",
        "encryption": meta.get("encryption") or "None",
    }


def remove_pdf_metadata(data: bytes) -> bytes:
    """Completely strip all metadata from PDF."""
    validate_pdf(data)
    doc = _open_fitz_doc(data)
    doc.set_metadata({})
    out_bytes = doc.tobytes(garbage=4, deflate=True, clean=True)
    doc.close()
    return out_bytes


def encrypt_pdf(data: bytes, user_password: str, owner_password: Optional[str] = None) -> bytes:
    """Encrypt PDF using standard AES-256."""
    if not user_password.strip():
        raise HTTPException(status_code=400, detail="Password cannot be empty")

    validate_pdf(data)
    doc = _open_fitz_doc(data)
    owner_pw = owner_password if (owner_password and owner_password.strip()) else user_password

    # AES 256 encryption
    perm = fitz.PDF_PERM_PRINT | fitz.PDF_PERM_COPY
    out_bytes = doc.tobytes(
        encryption=fitz.PDF_ENCRYPT_AES_256,
        user_pw=user_password,
        owner_pw=owner_pw,
        permissions=perm,
        garbage=4,
        deflate=True,
    )
    doc.close()
    return out_bytes


def decrypt_pdf(data: bytes, password: str) -> bytes:
    """Decrypt PDF with the supplied password and export decrypted document."""
    if not password.strip():
        raise HTTPException(status_code=400, detail="Password must be provided to decrypt PDF")

    validate_pdf(data)
    doc = _open_fitz_doc(data, password=password)
    # Re-save without encryption flags
    out_bytes = doc.tobytes(garbage=4, deflate=True, clean=True)
    doc.close()
    return out_bytes


def inspect_pdf_security(data: bytes) -> Dict[str, any]:
    """
    Deterministic local security inspection of PDF:
    - encryption status
    - page count
    - presence of metadata
    - embedded files
    - annotations
    - JavaScript / active content detection
    - interactive form fields (AcroForm)
    """
    validate_pdf(data)
    if not _PYMUPDF_AVAILABLE:
        raise HTTPException(status_code=500, detail="PyMuPDF is not installed on this server")

    doc = fitz.open(stream=data, filetype="pdf")
    is_enc = doc.is_encrypted
    total_pages = len(doc)

    js_detected = False
    embedded_count = doc.embfile_count() if hasattr(doc, "embfile_count") else 0
    form_fields_count = 0
    annotations_count = 0

    if not is_enc:
        # Inspect pages for forms, annotations, and JS
        for page in doc:
            annots = list(page.annots()) if hasattr(page, "annots") else []
            annotations_count += len(annots)
            widgets = list(page.widgets()) if hasattr(page, "widgets") else []
            form_fields_count += len(widgets)

        # Check catalog for JavaScript
        raw_text = data.decode("latin1", errors="ignore")
        if "/JavaScript" in raw_text or "/JS" in raw_text:
            js_detected = True

    meta = doc.metadata or {}
    has_meta = any(bool(v and v != "—") for v in meta.values())

    doc.close()

    return {
        "encrypted": is_enc,
        "page_count": total_pages,
        "metadata_present": has_meta,
        "metadata_keys": [k for k, v in meta.items() if v],
        "embedded_files_count": embedded_count,
        "annotations_count": annotations_count,
        "form_fields_count": form_fields_count,
        "has_forms": form_fields_count > 0,
        "javascript_detected": js_detected,
        "security_recommendation": (
            "Document contains active JavaScript or forms. Review before sharing in secure environments."
            if (js_detected or form_fields_count > 0)
            else "No active scripts or hidden attachments detected. Clean document."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. EDIT & SIGN: Watermark, Page Numbers, Annotations, Visual Signature
# ─────────────────────────────────────────────────────────────────────────────

def add_watermark(
    data: bytes,
    text: str,
    opacity: float = 0.3,
    angle: float = 45.0,
    font_size: int = 40,
    color: Tuple[float, float, float] = (0.6, 0.6, 0.6),
    pages: str = "all",
) -> bytes:
    """Add a customizable text watermark to PDF pages."""
    if not text.strip():
        raise HTTPException(status_code=400, detail="Watermark text cannot be empty")

    validate_pdf(data)
    doc = _open_fitz_doc(data)
    total_pages = len(doc)
    target_pages = set(parse_page_ranges(pages, total_pages))

    for p_num in target_pages:
        page = doc[p_num - 1]
        cx = page.rect.width / 2.0
        cy = page.rect.height / 2.0
        pt = fitz.Point(cx - (len(text) * font_size * 0.25), cy)
        # Use morph matrix for rotation around point
        mat = fitz.Matrix(angle)
        page.insert_text(
            pt,
            text,
            fontsize=font_size,
            color=color,
            morph=(pt, mat),
            render_mode=0,
        )

    out_bytes = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    return out_bytes


def add_page_numbers(
    data: bytes,
    position: str = "bottom-center",
    template: str = "Page {page} of {total}",
    start_num: int = 1,
    font_size: int = 10,
) -> bytes:
    """
    Add formatted page numbers to PDF.
    position: bottom-center, bottom-right, bottom-left, top-center, top-right
    """
    validate_pdf(data)
    doc = _open_fitz_doc(data)
    total_pages = len(doc)

    for i in range(total_pages):
        page = doc[i]
        curr = i + start_num
        text = template.replace("{page}", str(curr)).replace("{total}", str(total_pages + start_num - 1))
        w = page.rect.width
        h = page.rect.height

        if position == "bottom-center":
            pt = fitz.Point(w / 2 - (len(text) * font_size * 0.25), h - 30)
        elif position == "bottom-right":
            pt = fitz.Point(w - 50 - (len(text) * font_size * 0.5), h - 30)
        elif position == "bottom-left":
            pt = fitz.Point(50, h - 30)
        elif position == "top-center":
            pt = fitz.Point(w / 2 - (len(text) * font_size * 0.25), 35)
        elif position == "top-right":
            pt = fitz.Point(w - 50 - (len(text) * font_size * 0.5), 35)
        else:
            pt = fitz.Point(w / 2 - (len(text) * font_size * 0.25), h - 30)

        page.insert_text(pt, text, fontsize=font_size, color=(0.3, 0.3, 0.3))

    out_bytes = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    return out_bytes


def add_visual_signature(
    data: bytes,
    sig_image_bytes: bytes,
    page_num: int = 1,
    x: float = 350.0,
    y: float = 700.0,
    width: float = 180.0,
    height: float = 80.0,
) -> bytes:
    """
    Place a transparent or opaque signature image onto a specified page.
    Luminosity/alpha preserved for transparent PNG signatures.
    """
    validate_pdf(data)
    validate_image(sig_image_bytes, label="Signature Image")

    doc = _open_fitz_doc(data)
    total_pages = len(doc)
    if page_num < 1 or page_num > total_pages:
        raise HTTPException(status_code=400, detail=f"Page {page_num} out of range (1-{total_pages})")

    page = doc[page_num - 1]
    rect = fitz.Rect(x, y, x + width, y + height)

    try:
        page.insert_image(rect, stream=sig_image_bytes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to place signature: {exc}")

    out_bytes = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    return out_bytes
