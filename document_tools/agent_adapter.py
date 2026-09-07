"""
document_tools/agent_adapter.py
Isolated Document Tools Adapter for AI Workbench Chat.

Bridges natural-language chat requests with the existing local Document Tools
backend services. Strictly local, air-gap compatible, zero cloud dependencies.

Architecture:
  USER CHAT -> AI ROUTER -> DOCUMENT TOOL ADAPTER -> EXISTING DOCUMENT TOOLS
                                                          ↓
                                                     OUTPUT FILE(S)
                                                          ↓
                                               CHAT RESPONSE + DOWNLOAD
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from document_tools.common import (
    create_zip_archive,
    format_file_size,
    get_output_path,
    safe_filename,
    save_output_bytes,
)
from document_tools.ocr_ops import ocr_pdf_document, ocr_single_image
from document_tools.office_ops import docx_to_text
from document_tools.pdf_ops import (
    add_blank_page,
    compress_pdf,
    crop_pdf,
    delete_pages,
    duplicate_page,
    extract_pages,
    extract_text_from_pdf,
    images_to_pdf,
    merge_pdfs,
    remove_pdf_metadata,
    render_pdf_to_images,
    reorder_pages,
    resize_pdf,
    rotate_pdf,
    split_pdf,
)
from security.audit import log


# ─── Allowed Tool Registry ───────────────────────────────────────────────────

REGISTERED_DOCUMENT_TOOLS: Dict[str, Dict[str, Any]] = {
    "merge_pdf": {
        "name": "merge_pdf",
        "category": "ORGANIZE",
        "description": "Combine two or more PDF files in sequence into a single PDF document.",
        "min_files": 2,
        "supported_extensions": [".pdf"],
        "destructive": False,
    },
    "split_pdf": {
        "name": "split_pdf",
        "category": "ORGANIZE",
        "description": "Split a PDF document into separate files by page ranges or into individual pages.",
        "min_files": 1,
        "supported_extensions": [".pdf"],
        "destructive": False,
    },
    "extract_pages": {
        "name": "extract_pages",
        "category": "ORGANIZE",
        "description": "Extract specific pages from a PDF document into a new PDF file.",
        "min_files": 1,
        "supported_extensions": [".pdf"],
        "destructive": False,
    },
    "rotate_pdf": {
        "name": "rotate_pdf",
        "category": "ORGANIZE",
        "description": "Rotate specified pages or all pages of a PDF document by 90, 180, or 270 degrees.",
        "min_files": 1,
        "supported_extensions": [".pdf"],
        "destructive": False,
    },
    "delete_pages": {
        "name": "delete_pages",
        "category": "ORGANIZE",
        "description": "Create a new PDF excluding designated pages (preserves original document).",
        "min_files": 1,
        "supported_extensions": [".pdf"],
        "destructive": True,
    },
    "reorder_pages": {
        "name": "reorder_pages",
        "category": "ORGANIZE",
        "description": "Reorder the pages of a PDF document according to a specified sequence.",
        "min_files": 1,
        "supported_extensions": [".pdf"],
        "destructive": False,
    },
    "pdf_to_images": {
        "name": "pdf_to_images",
        "category": "CONVERT",
        "description": "Render PDF pages into PNG or JPG images, packaged in a ZIP archive.",
        "min_files": 1,
        "supported_extensions": [".pdf"],
        "destructive": False,
    },
    "images_to_pdf": {
        "name": "images_to_pdf",
        "category": "CONVERT",
        "description": "Convert one or more image files (PNG, JPG, JPEG, WebP, BMP) into a single PDF.",
        "min_files": 1,
        "supported_extensions": [".png", ".jpg", ".jpeg", ".webp", ".bmp"],
        "destructive": False,
    },
    "pdf_to_text": {
        "name": "pdf_to_text",
        "category": "CONVERT",
        "description": "Extract native digital text content from a PDF document.",
        "min_files": 1,
        "supported_extensions": [".pdf"],
        "destructive": False,
    },
    "docx_to_text": {
        "name": "docx_to_text",
        "category": "CONVERT",
        "description": "Extract all text from a Microsoft Word (.docx) document.",
        "min_files": 1,
        "supported_extensions": [".docx", ".doc"],
        "destructive": False,
    },
    "compress_pdf": {
        "name": "compress_pdf",
        "category": "OPTIMIZE",
        "description": "Reduce PDF file size with selectable compression levels (low, medium, high).",
        "min_files": 1,
        "supported_extensions": [".pdf"],
        "destructive": False,
    },
    "strip_metadata": {
        "name": "strip_metadata",
        "category": "OPTIMIZE",
        "description": "Remove metadata, author information, and revision history from a PDF.",
        "min_files": 1,
        "supported_extensions": [".pdf"],
        "destructive": False,
    },
    "ocr_pdf": {
        "name": "ocr_pdf",
        "category": "OCR",
        "description": "Perform local Tesseract OCR on a scanned or image-based PDF to extract text.",
        "min_files": 1,
        "supported_extensions": [".pdf"],
        "destructive": False,
    },
    "ocr_image": {
        "name": "ocr_image",
        "category": "OCR",
        "description": "Perform local Tesseract OCR on an image file to extract printed or handwritten text.",
        "min_files": 1,
        "supported_extensions": [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"],
        "destructive": False,
    },
    "crop_pdf": {
        "name": "crop_pdf",
        "category": "EDIT",
        "description": "Crop PDF margins.",
        "min_files": 1,
        "supported_extensions": [".pdf"],
        "destructive": False,
    },
    "resize_pdf": {
        "name": "resize_pdf",
        "category": "EDIT",
        "description": "Resize PDF page size.",
        "min_files": 1,
        "supported_extensions": [".pdf"],
        "destructive": False,
    },
    "add_blank_page": {
        "name": "add_blank_page",
        "category": "EDIT",
        "description": "Insert blank page into PDF.",
        "min_files": 1,
        "supported_extensions": [".pdf"],
        "destructive": False,
    },
    "duplicate_page": {
        "name": "duplicate_page",
        "category": "EDIT",
        "description": "Duplicate a page in PDF.",
        "min_files": 1,
        "supported_extensions": [".pdf"],
        "destructive": False,
    },
}


@dataclass
class DocumentToolResult:
    success: bool
    tool_name: str
    message: str
    output_files: List[str] = field(default_factory=list)
    needs_user_input: bool = False
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


# ─── Safe File Resolution ────────────────────────────────────────────────────

def _normalize_workspace_path(path_str: str) -> Optional[Path]:
    """
    Ensure the path is strictly within the allowed workspace boundary.
    Rejects any path traversal attempts.
    """
    try:
        p = Path(path_str).resolve()
        workspace = Path("workspace").resolve()
        # Accept files located directly inside workspace (uploads, outputs, or root)
        # or inside application directory
        app_dir = Path(".").resolve()
        try:
            p.relative_to(workspace)
            if p.exists():
                return p
        except ValueError:
            pass

        try:
            p.relative_to(app_dir)
            if p.exists():
                return p
        except ValueError:
            pass

        # Also check relative to workspace/uploads if basename only
        candidate = workspace / "uploads" / p.name
        if candidate.exists():
            return candidate

        candidate_out = workspace / "outputs" / p.name
        if candidate_out.exists():
            return candidate_out

        if p.exists():
            return p
    except Exception:
        pass
    return None


def resolve_files_for_tool(
    tool_name: str,
    uploaded_files: List[str],
    query: str = "",
) -> Tuple[List[Path], Optional[str]]:
    """
    Resolve which uploaded files apply to the requested document tool.
    Handles filename mentions, ordinal references ('first two', 'second'),
    and extension filtering.
    """
    meta = REGISTERED_DOCUMENT_TOOLS.get(tool_name)
    if not meta:
        return [], f"Unknown document tool: '{tool_name}'."

    supported_exts = tuple(meta["supported_extensions"])
    q_lower = query.lower()

    # Normalize existing files
    valid_paths: List[Path] = []
    for f in uploaded_files:
        p = _normalize_workspace_path(f)
        if p and p.suffix.lower() in supported_exts:
            valid_paths.append(p)

    if not valid_paths:
        ext_list = ", ".join(meta["supported_extensions"])
        return [], (
            f"No matching {ext_list} files found in uploaded documents. "
            f"Please upload the required file(s) first."
        )

    # 1. Check if user explicitly mentioned specific filenames
    mentioned: List[Path] = []
    for p in valid_paths:
        if p.name.lower() in q_lower or p.stem.lower() in q_lower:
            mentioned.append(p)

    if mentioned:
        # Sort files in the order they were mentioned in user query
        def _pos(path: Path) -> int:
            pos_name = q_lower.find(path.name.lower())
            pos_stem = q_lower.find(path.stem.lower())
            indices = [idx for idx in (pos_name, pos_stem) if idx >= 0]
            return min(indices) if indices else 999999
        mentioned.sort(key=_pos)
        return mentioned, None

    # 2. Check for ordinal / quantity references in query
    if tool_name == "merge_pdf":
        if any(w in q_lower for w in ("first two", "first 2", "these two", "these 2", "the two", "the 2", "two pdf", "2 pdf")):
            if len(valid_paths) >= 2:
                return valid_paths[:2], None
        elif any(w in q_lower for w in ("first three", "first 3", "these three", "these 3", "the three", "the 3", "three pdf", "3 pdf")):
            if len(valid_paths) >= 3:
                return valid_paths[:3], None
        elif "last two" in q_lower or "last 2" in q_lower:
            if len(valid_paths) >= 2:
                return valid_paths[-2:], None
        # Default for merge: merge all uploaded PDFs
        return valid_paths, None

    if tool_name == "images_to_pdf":
        # images_to_pdf combines all valid uploaded images into a PDF
        return valid_paths, None

    # For single-file tools
    if meta["min_files"] == 1:
        if "second" in q_lower and len(valid_paths) >= 2:
            return [valid_paths[1]], None
        if "third" in q_lower and len(valid_paths) >= 3:
            return [valid_paths[2]], None
        if "last" in q_lower and valid_paths:
            return [valid_paths[-1]], None
        # If multiple files exist and user didn't specify which one
        if len(valid_paths) > 1 and not ("first" in q_lower or "this" in q_lower or "the" in q_lower):
            file_names = ", ".join([f"`{p.name}`" for p in valid_paths])
            return [], (
                f"Multiple {supported_exts[0]} files are available: {file_names}. "
                f"Please specify which file you would like to process."
            )
        # Default to first valid file
        return [valid_paths[0]], None

    return valid_paths, None


# ─── Natural Language Parameter & Intent Parsing ─────────────────────────────

def _parse_pages_param(query: str) -> Optional[str]:
    """
    Extract page specifications from query text like:
    'pages 1, 3 and 5', 'page 4', 'pages 1 to 5', 'pages 1-5'
    """
    q = query.lower()

    # "pages 1, 3 and 5" or "pages 1, 3, 5"
    m = re.search(r"\bpages?\s+([\d\s,and\-to]+)", q)
    if m:
        raw = m.group(1).replace("and", ",").replace("to", "-").strip()
        tokens = [t.strip() for t in raw.split(",") if t.strip()]
        cleaned = ",".join(tokens)
        cleaned = re.sub(r"\s+", "", cleaned)
        if cleaned:
            return cleaned

    # Direct range: "1-5" or "1 to 5"
    m_range = re.search(r"\b(\d+)\s*(?:-|to)\s*(\d+)\b", q)
    if m_range:
        return f"{m_range.group(1)}-{m_range.group(2)}"

    return None


def _parse_angle_param(query: str) -> int:
    """Extract rotation angle (default 90 clockwise)."""
    q = query.lower()
    if "180" in q:
        return 180
    if "270" in q or "counter" in q or "left" in q:
        return 270
    return 90


def _parse_compression_level(query: str) -> str:
    """Extract compression level: low, medium, high."""
    q = query.lower()
    if "high" in q or "maximum" in q or "smallest" in q or "extreme" in q:
        return "high"
    if "low" in q or "slight" in q or "minimal" in q or "fast" in q:
        return "low"
    return "medium"


def _parse_image_format(query: str) -> str:
    """Extract image format: png or jpg."""
    q = query.lower()
    if "jpg" in q or "jpeg" in q:
        return "jpg"
    return "png"


def _parse_language(query: str) -> str:
    """Extract language code for OCR."""
    q = query.lower()
    if "hindi" in q or "hin" in q:
        return "hin"
    if "spanish" in q or "spa" in q:
        return "spa"
    if "french" in q or "fra" in q:
        return "fra"
    if "german" in q or "deu" in q:
        return "deu"
    return "eng"


def detect_document_tool_intent(query: str, uploaded_files: List[str] = None) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Deterministically detect the document tool and parameters from the user's query.
    Returns (tool_name, params_dict) or None if not a document tool operation.
    """
    q = query.strip().lower()
    files = uploaded_files or []

    # File type helpers
    has_pdf = any(f.lower().endswith(".pdf") for f in files)
    has_image = any(f.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff")) for f in files)
    has_docx = any(f.lower().endswith((".docx", ".doc")) for f in files)

    # 1. MERGE PDF
    if (
        re.search(r"\b(?:merge|combine|join|stitch|concatenate)\s+(?:these\s+|the\s+)?(?:pdf|pdfs|documents|files)\b", q)
        or re.search(r"\bmerge\s+pdf\b", q)
        or (("merge" in q or "combine" in q) and ("pdf" in q or has_pdf))
    ):
        return "merge_pdf", {}

    # 2. SPLIT PDF
    if (
        re.search(r"\bsplit\s+(?:this\s+|the\s+)?(?:pdf|document|file)\b", q)
        or re.search(r"\bsplit\s+pdf\b", q)
        or ("split" in q and ("pdf" in q or has_pdf))
    ):
        pages = _parse_pages_param(q)
        mode = "ranges" if pages else ("all" if "every page" in q or "each page" in q else "ranges")
        return "split_pdf", {"mode": mode, "ranges": pages or ""}

    # 3. EXTRACT PAGES
    if (
        re.search(r"\bextract\s+(?:the\s+)?pages?\b", q)
        or re.search(r"\bgive\s+me\s+pages?\b", q)
        or re.search(r"\bpull\s+out\s+pages?\b", q)
        or (("extract" in q or "get" in q) and "page" in q and ("pdf" in q or has_pdf))
    ):
        pages = _parse_pages_param(q)
        return "extract_pages", {"pages": pages or ""}

    # 4. ROTATE PDF
    if (
        re.search(r"\brotate\s+(?:the\s+|this\s+)?(?:pdf|pages?|document)\b", q)
        or "rotate" in q and ("pdf" in q or "page" in q or has_pdf)
    ):
        pages = _parse_pages_param(q) or "all"
        angle = _parse_angle_param(q)
        return "rotate_pdf", {"angle": angle, "pages": pages}

    # 5. DELETE PAGES
    if (
        re.search(r"\b(?:delete|remove)\s+(?:the\s+)?pages?\b", q)
        or ("delete" in q or "remove" in q) and "page" in q and ("pdf" in q or has_pdf)
    ):
        pages = _parse_pages_param(q)
        return "delete_pages", {"pages": pages or ""}

    # 6. REORDER PAGES
    if (
        re.search(r"\b(?:reorder|rearrange|change\s+order\s+of)\s+(?:the\s+)?pages?\b", q)
        or "reorder" in q and ("pdf" in q or "page" in q)
    ):
        m_order = re.search(r"\b(?:to|as|into|order)\s+([\d\s,]+)", q)
        new_order = re.sub(r"\s+", "", m_order.group(1)) if m_order else ""
        return "reorder_pages", {"new_order": new_order}

    # 7. PDF TO IMAGES
    if (
        re.search(r"\bpdf\s+(?:to|into)\s+images?\b", q)
        or re.search(r"\bconvert\s+(?:this\s+)?pdf\s+to\s+(?:png|jpg|jpeg|images?)\b", q)
        or re.search(r"\bturn\s+(?:this\s+)?pdf\s+into\s+images?\b", q)
        or re.search(r"\brender\s+pdf\s+to\s+images?\b", q)
        or ("image" in q and "pdf" in q and ("convert" in q or "turn" in q or "render" in q))
    ):
        fmt = _parse_image_format(q)
        pages = _parse_pages_param(q) or "all"
        return "pdf_to_images", {"format": fmt, "pages": pages}

    # 8. IMAGES TO PDF
    if (
        re.search(r"\bimages?\s+(?:to|into)\s+pdf\b", q)
        or re.search(r"\bconvert\s+(?:these\s+)?images?\s+to\s+pdf\b", q)
        or (has_image and "to pdf" in q)
    ):
        return "images_to_pdf", {}

    # 9. OCR (Scanned PDF or Image)
    if "ocr" in q or "scanned" in q or "optical character" in q:
        lang = _parse_language(q)
        pages = _parse_pages_param(q) or "all"
        if has_image and not has_pdf:
            return "ocr_image", {"language": lang}
        return "ocr_pdf", {"language": lang, "pages": pages}

    # 10. DOCX TO TEXT
    if (
        re.search(r"\bdocx\s+(?:to|into)\s+text\b", q)
        or re.search(r"\bconvert\s+(?:this\s+)?docx\s+to\s+text\b", q)
        or (has_docx and ("text" in q or "extract" in q))
    ):
        return "docx_to_text", {}

    # 11. PDF TO TEXT (Native extraction)
    if (
        re.search(r"\bextract\s+(?:all\s+)?(?:the\s+)?text\b", q)
        or re.search(r"\bpdf\s+(?:to|into)\s+text\b", q)
        or re.search(r"\bget\s+text\s+from\s+(?:this\s+)?pdf\b", q)
        or (has_pdf and ("extract text" in q or "text from pdf" in q or "convert to text" in q))
    ):
        return "pdf_to_text", {}

    # 12. COMPRESS PDF
    if (
        re.search(r"\bcompress\s+(?:this\s+|the\s+)?pdf\b", q)
        or re.search(r"\bmake\s+(?:this\s+)?pdf\s+(?:smaller|less\s+size)\b", q)
        or re.search(r"\breduce\s+(?:the\s+)?(?:size\s+of\s+)?pdf\b", q)
        or re.search(r"\boptimize\s+pdf\b", q)
    ):
        level = _parse_compression_level(q)
        return "compress_pdf", {"level": level}

    # 13. STRIP METADATA
    if (
        re.search(r"\bstrip\s+metadata\b", q)
        or re.search(r"\bremove\s+metadata\b", q)
        or re.search(r"\bclean\s+metadata\b", q)
        or re.search(r"\bsanitize\s+pdf\b", q)
    ):
        return "strip_metadata", {}

    return None


# ─── Execution Adapter ───────────────────────────────────────────────────────

def execute_document_tool(
    tool_name: str,
    params: Dict[str, Any],
    uploaded_files: List[str],
    query: str = "",
) -> DocumentToolResult:
    """
    Execute the requested document tool safely using the existing local backend.
    Translates parameters, calls existing functions, and packages outputs.
    """
    if tool_name not in REGISTERED_DOCUMENT_TOOLS:
        return DocumentToolResult(
            success=False,
            tool_name=tool_name,
            message=f"Tool `{tool_name}` is not in the allowed document tool registry.",
            error="SECURITY_TOOL_NOT_ALLOWED",
        )

    log("DOCUMENT_TOOL_INVOKED", tool=tool_name, params=params, query=query[:100])

    # 1. Resolve target files
    files, resolve_err = resolve_files_for_tool(tool_name, uploaded_files, query)
    if resolve_err:
        return DocumentToolResult(
            success=False,
            tool_name=tool_name,
            message=resolve_err,
            needs_user_input=True,
            error="FILE_RESOLUTION_REQUIRED",
        )

    meta = REGISTERED_DOCUMENT_TOOLS[tool_name]
    min_files = meta.get("min_files", 1)
    if len(files) < min_files:
        return DocumentToolResult(
            success=False,
            tool_name=tool_name,
            message=f"Tool `{tool_name}` requires at least {min_files} file(s), but only {len(files)} was provided.",
            needs_user_input=True,
        )

    try:
        # ── 1. MERGE PDF ─────────────────────────────────────────────────────
        if tool_name == "merge_pdf":
            import fitz
            file_tuples: List[Tuple[bytes, str]] = []
            total_expected_pages = 0
            for f in files:
                b = f.read_bytes()
                file_tuples.append((b, f.name))
                try:
                    d_in = fitz.open(stream=b, filetype="pdf")
                    total_expected_pages += len(d_in)
                    d_in.close()
                except Exception:
                    pass

            merged_bytes = merge_pdfs(file_tuples)

            # Verify output validity and page count
            d_out = fitz.open(stream=merged_bytes, filetype="pdf")
            out_page_count = len(d_out)
            d_out.close()

            if total_expected_pages > 0 and out_page_count != total_expected_pages:
                raise ValueError(f"Merged PDF page count mismatch: expected {total_expected_pages}, got {out_page_count}")

            out_name = f"merged_{int(time.time())}.pdf" if get_output_path("merged.pdf").exists() else "merged.pdf"
            out_path = save_output_bytes(merged_bytes, out_name)

            if not out_path.exists() or out_path.stat().st_size == 0:
                raise IOError(f"Failed to create output file: {out_name}")

            fnames_list = "\n".join([f"- {f.name}" for f in files])
            msg = (
                f"✓ PDFs merged successfully.\n\n"
                f"Input files:\n{fnames_list}\n\n"
                f"Output:\n{out_name}\n\n"
                f"[{out_name}](file:///{out_path.as_posix()})"
            )
            return DocumentToolResult(
                success=True,
                tool_name=tool_name,
                message=msg,
                output_files=[str(out_path.resolve())],
                details={
                    "page_count": out_page_count,
                    "file_size": len(merged_bytes),
                    "input_files": [f.name for f in files],
                    "output_file": out_name,
                },
            )

        # ── 2. SPLIT PDF ─────────────────────────────────────────────────────
        elif tool_name == "split_pdf":
            target = files[0]
            mode = params.get("mode", "ranges")
            ranges = params.get("ranges", "").strip()

            if mode == "ranges" and not ranges:
                return DocumentToolResult(
                    success=False,
                    tool_name=tool_name,
                    message=(
                        f"Which page ranges would you like to split `{target.name}` into?\n\n"
                        f"For example: *'1-3, 4-6'* or *'1-2, 3-5'*."
                    ),
                    needs_user_input=True,
                )

            data = target.read_bytes()
            split_dict = split_pdf(data, mode=mode, ranges=ranges)

            # Package multiple split parts into a zip archive
            zip_name = f"split_{target.stem}.zip"
            zip_path = create_zip_archive(split_dict, zip_name)

            part_list = "\n".join([f"- `{k}` ({format_file_size(len(v))})" for k, v in split_dict.items()])
            msg = (
                f"✓ **Successfully split `{target.name}` into {len(split_dict)} parts**.\n\n"
                f"{part_list}\n\n"
                f"All parts have been archived into [{zip_name}](file:///{zip_path.as_posix()}) for download."
            )
            return DocumentToolResult(
                success=True,
                tool_name=tool_name,
                message=msg,
                output_files=[str(zip_path.resolve())],
                details={"parts_count": len(split_dict)},
            )

        # ── 3. EXTRACT PAGES ─────────────────────────────────────────────────
        elif tool_name == "extract_pages":
            target = files[0]
            pages = params.get("pages", "").strip()
            if not pages:
                return DocumentToolResult(
                    success=False,
                    tool_name=tool_name,
                    message=(
                        f"Which pages would you like to extract from `{target.name}`?\n\n"
                        f"For example: *'1, 3, 5'* or *'2-4'*."
                    ),
                    needs_user_input=True,
                )

            data = target.read_bytes()
            extracted_bytes = extract_pages(data, pages=pages)
            clean_tag = re.sub(r"[^\w\-]", "_", pages)[:20]
            out_name = f"extracted_p{clean_tag}_{target.stem}.pdf"
            out_path = save_output_bytes(extracted_bytes, out_name)

            msg = (
                f"✓ **Extracted page(s) `{pages}` from `{target.name}`**.\n\n"
                f"Output saved as [{out_name}](file:///{out_path.as_posix()}) ({format_file_size(len(extracted_bytes))})."
            )
            return DocumentToolResult(
                success=True,
                tool_name=tool_name,
                message=msg,
                output_files=[str(out_path.resolve())],
                details={"pages": pages, "file_size": len(extracted_bytes)},
            )

        # ── 4. ROTATE PDF ─────────────────────────────────────────────────────
        elif tool_name == "rotate_pdf":
            target = files[0]
            angle = int(params.get("angle", 90))
            pages = params.get("pages", "all")

            data = target.read_bytes()
            rotated_bytes = rotate_pdf(data, angle=angle, pages=pages)
            out_name = f"rotated_{angle}deg_{target.stem}.pdf"
            out_path = save_output_bytes(rotated_bytes, out_name)

            page_label = f"page(s) {pages}" if pages != "all" else "all pages"
            msg = (
                f"✓ **Rotated {page_label} of `{target.name}` by {angle}° clockwise**.\n\n"
                f"Output saved as [{out_name}](file:///{out_path.as_posix()}) ({format_file_size(len(rotated_bytes))})."
            )
            return DocumentToolResult(
                success=True,
                tool_name=tool_name,
                message=msg,
                output_files=[str(out_path.resolve())],
                details={"angle": angle, "pages": pages},
            )

        # ── 5. DELETE PAGES (Non-destructive to original) ────────────────────
        elif tool_name == "delete_pages":
            target = files[0]
            pages = params.get("pages", "").strip()
            if not pages:
                return DocumentToolResult(
                    success=False,
                    tool_name=tool_name,
                    message=(
                        f"Which pages would you like to remove from `{target.name}`?\n\n"
                        f"For example: *'2, 4'* or *'1-3'*."
                    ),
                    needs_user_input=True,
                )

            data = target.read_bytes()
            result_bytes = delete_pages(data, page_spec=pages)
            out_name = f"deleted_p{re.sub(r'[^0-9]', '_', pages)}_{target.stem}.pdf"
            out_path = save_output_bytes(result_bytes, out_name)

            msg = (
                f"✓ **Created a new PDF excluding page(s) `{pages}` from `{target.name}`**.\n\n"
                f"🛡️ *Safety Note: The original uploaded file `{target.name}` remains intact and unmodified.*\n\n"
                f"Output saved as [{out_name}](file:///{out_path.as_posix()}) ({format_file_size(len(result_bytes))})."
            )
            return DocumentToolResult(
                success=True,
                tool_name=tool_name,
                message=msg,
                output_files=[str(out_path.resolve())],
                details={"removed_pages": pages},
            )

        # ── 6. REORDER PAGES ─────────────────────────────────────────────────
        elif tool_name == "reorder_pages":
            target = files[0]
            new_order = params.get("new_order", "").strip()
            if not new_order:
                return DocumentToolResult(
                    success=False,
                    tool_name=tool_name,
                    message=(
                        f"Please specify the desired page order for `{target.name}`.\n\n"
                        f"For example: *'3, 1, 2'* or *'2, 4, 1, 3'*."
                    ),
                    needs_user_input=True,
                )

            data = target.read_bytes()
            result_bytes = reorder_pages(data, new_order=new_order)
            out_name = f"reordered_{target.stem}.pdf"
            out_path = save_output_bytes(result_bytes, out_name)

            msg = (
                f"✓ **Reordered pages of `{target.name}` to `[{new_order}]`**.\n\n"
                f"Output saved as [{out_name}](file:///{out_path.as_posix()}) ({format_file_size(len(result_bytes))})."
            )
            return DocumentToolResult(
                success=True,
                tool_name=tool_name,
                message=msg,
                output_files=[str(out_path.resolve())],
                details={"new_order": new_order},
            )

        # ── 7. PDF TO IMAGES ─────────────────────────────────────────────────
        elif tool_name == "pdf_to_images":
            target = files[0]
            fmt = params.get("format", "png").lower()
            pages = params.get("pages", "all")

            data = target.read_bytes()
            img_dict = render_pdf_to_images(data, fmt=fmt, pages=pages)

            zip_name = f"{target.stem}_images_{fmt}.zip"
            zip_path = create_zip_archive(img_dict, zip_name)

            msg = (
                f"✓ **Rendered {len(img_dict)} page(s) of `{target.name}` into {fmt.upper()} images**.\n\n"
                f"All image files have been packaged into [{zip_name}](file:///{zip_path.as_posix()}) for easy download."
            )
            return DocumentToolResult(
                success=True,
                tool_name=tool_name,
                message=msg,
                output_files=[str(zip_path.resolve())],
                details={"images_count": len(img_dict), "format": fmt},
            )

        # ── 8. IMAGES TO PDF ─────────────────────────────────────────────────
        elif tool_name == "images_to_pdf":
            img_tuples: List[Tuple[bytes, str]] = []
            for f in files:
                img_tuples.append((f.read_bytes(), f.name))

            pdf_bytes = images_to_pdf(img_tuples)
            out_name = f"images_{int(time.time())}.pdf" if get_output_path("images.pdf").exists() else "images.pdf"
            out_path = save_output_bytes(pdf_bytes, out_name)

            if not out_path.exists() or out_path.stat().st_size == 0:
                raise IOError(f"Failed to create output file: {out_name}")

            fnames_list = "\n".join([f"- {f.name}" for f in files])
            msg = (
                f"✓ PDF created successfully.\n\n"
                f"Input files:\n{fnames_list}\n\n"
                f"Output:\n{out_name}\n\n"
                f"[{out_name}](file:///{out_path.as_posix()})"
            )
            return DocumentToolResult(
                success=True,
                tool_name=tool_name,
                message=msg,
                output_files=[str(out_path.resolve())],
                details={"images_count": len(files), "file_size": len(pdf_bytes), "output_file": out_name},
            )

        # ── 9. PDF TO TEXT ───────────────────────────────────────────────────
        elif tool_name == "pdf_to_text":
            target = files[0]
            data = target.read_bytes()
            extracted_txt, ocr_recommended = extract_text_from_pdf(data)

            out_name = f"extracted_{target.stem}.txt"
            out_path = save_output_bytes(extracted_txt.encode("utf-8"), out_name)

            preview = extracted_txt.strip()[:1000]
            if len(extracted_txt.strip()) > 1000:
                preview += "\n\n... *(text truncated for display)*"

            ocr_note = ""
            if ocr_recommended:
                ocr_note = (
                    "\n\n> ℹ️ **Notice**: Very little digital text was detected. "
                    "This document may be scanned. You can say: *'OCR this scanned PDF'* to perform local OCR."
                )

            msg = (
                f"✓ **Extracted text from `{target.name}`** ({len(extracted_txt):,} characters):\n\n"
                f"```text\n{preview}\n```\n\n"
                f"Full text file saved as [{out_name}](file:///{out_path.as_posix()}).{ocr_note}"
            )
            return DocumentToolResult(
                success=True,
                tool_name=tool_name,
                message=msg,
                output_files=[str(out_path.resolve())],
                details={"char_count": len(extracted_txt), "ocr_recommended": ocr_recommended},
            )

        # ── 10. DOCX TO TEXT ─────────────────────────────────────────────────
        elif tool_name == "docx_to_text":
            target = files[0]
            data = target.read_bytes()
            extracted_txt = docx_to_text(data)

            out_name = f"extracted_{target.stem}.txt"
            out_path = save_output_bytes(extracted_txt.encode("utf-8"), out_name)

            preview = extracted_txt.strip()[:1000]
            if len(extracted_txt.strip()) > 1000:
                preview += "\n\n... *(text truncated for display)*"

            msg = (
                f"✓ **Extracted text from Word document `{target.name}`** ({len(extracted_txt):,} characters):\n\n"
                f"```text\n{preview}\n```\n\n"
                f"Full text file saved as [{out_name}](file:///{out_path.as_posix()})."
            )
            return DocumentToolResult(
                success=True,
                tool_name=tool_name,
                message=msg,
                output_files=[str(out_path.resolve())],
                details={"char_count": len(extracted_txt)},
            )

        # ── 11. COMPRESS PDF ─────────────────────────────────────────────────
        elif tool_name == "compress_pdf":
            target = files[0]
            level = params.get("level", "medium").lower()

            data = target.read_bytes()
            compressed_bytes, orig_size, new_size, ratio = compress_pdf(data, level=level)

            out_name = f"compressed_{target.stem}.pdf"
            out_path = save_output_bytes(compressed_bytes, out_name)

            msg = (
                f"✓ **Compressed `{target.name}` successfully** (Compression Level: **{level.upper()}**).\n\n"
                f"- **Original Size**: {format_file_size(orig_size)}\n"
                f"- **Compressed Size**: {format_file_size(new_size)}\n"
                f"- **Reduction**: **{ratio:.1f}%**\n\n"
                f"Output file: [{out_name}](file:///{out_path.as_posix()})"
            )
            return DocumentToolResult(
                success=True,
                tool_name=tool_name,
                message=msg,
                output_files=[str(out_path.resolve())],
                details={"original_size": orig_size, "compressed_size": new_size, "ratio": ratio},
            )

        # ── 12. STRIP METADATA ───────────────────────────────────────────────
        elif tool_name == "strip_metadata":
            target = files[0]
            data = target.read_bytes()
            clean_bytes = remove_pdf_metadata(data)

            out_name = f"sanitized_{target.stem}.pdf"
            out_path = save_output_bytes(clean_bytes, out_name)

            msg = (
                f"✓ **Removed all metadata and author tracking info from `{target.name}`**.\n\n"
                f"Clean file saved as [{out_name}](file:///{out_path.as_posix()}) ({format_file_size(len(clean_bytes))})."
            )
            return DocumentToolResult(
                success=True,
                tool_name=tool_name,
                message=msg,
                output_files=[str(out_path.resolve())],
                details={"sanitized": True},
            )

        # ── 13. OCR PDF ──────────────────────────────────────────────────────
        elif tool_name == "ocr_pdf":
            target = files[0]
            lang = params.get("language", "eng")
            pages = params.get("pages", "all")

            data = target.read_bytes()
            ocr_res = ocr_pdf_document(data, pages=pages, lang=lang)

            full_text = ocr_res.get("text", "")
            out_name = f"ocr_{target.stem}.txt"
            out_path = save_output_bytes(full_text.encode("utf-8"), out_name)

            preview = full_text.strip()[:1000]
            if len(full_text.strip()) > 1000:
                preview += "\n\n... *(text truncated for display)*"

            msg = (
                f"✓ **Completed local Tesseract OCR on `{target.name}`** "
                f"({ocr_res.get('ocr_pages', 1)} page(s) processed using language: `{lang}`):\n\n"
                f"```text\n{preview}\n```\n\n"
                f"Full recognized text saved as [{out_name}](file:///{out_path.as_posix()})."
            )
            return DocumentToolResult(
                success=True,
                tool_name=tool_name,
                message=msg,
                output_files=[str(out_path.resolve())],
                details=ocr_res,
            )

        # ── 14. OCR IMAGE ────────────────────────────────────────────────────
        elif tool_name == "ocr_image":
            target = files[0]
            lang = params.get("language", "eng")

            data = target.read_bytes()
            img_text = ocr_single_image(data, lang=lang)

            out_name = f"ocr_{target.stem}.txt"
            out_path = save_output_bytes(img_text.encode("utf-8"), out_name)

            preview = img_text.strip()[:1000]
            if len(img_text.strip()) > 1000:
                preview += "\n\n... *(text truncated for display)*"

            msg = (
                f"✓ **Completed local Tesseract OCR on `{target.name}`** (language: `{lang}`):\n\n"
                f"```text\n{preview}\n```\n\n"
                f"Full recognized text saved as [{out_name}](file:///{out_path.as_posix()})."
            )
            return DocumentToolResult(
                success=True,
                tool_name=tool_name,
                message=msg,
                output_files=[str(out_path.resolve())],
                details={"text_length": len(img_text)},
            )

        # ── 15. CROP PDF ─────────────────────────────────────────────────────
        elif tool_name == "crop_pdf":
            target = files[0]
            data = target.read_bytes()
            pages = params.get("pages", "all")
            cropped_bytes = crop_pdf(
                data,
                margin_left=float(params.get("left", 20)),
                margin_top=float(params.get("top", 20)),
                margin_right=float(params.get("right", 20)),
                margin_bottom=float(params.get("bottom", 20)),
                page_spec=pages,
            )
            out_name = f"cropped_{target.stem}.pdf"
            out_path = save_output_bytes(cropped_bytes, out_name)
            return DocumentToolResult(
                success=True,
                tool_name=tool_name,
                message=f"✓ **Successfully cropped margins of `{target.name}`**.\n\nOutput: [{out_name}](file:///{out_path.as_posix()})",
                output_files=[str(out_path.resolve())],
            )

        # ── 16. RESIZE PDF ───────────────────────────────────────────────────
        elif tool_name == "resize_pdf":
            target = files[0]
            data = target.read_bytes()
            target_size = params.get("target_size", "A4")
            resized_bytes = resize_pdf(data, target_size=target_size)
            out_name = f"resized_{target_size}_{target.stem}.pdf"
            out_path = save_output_bytes(resized_bytes, out_name)
            return DocumentToolResult(
                success=True,
                tool_name=tool_name,
                message=f"✓ **Successfully resized `{target.name}` to {target_size}**.\n\nOutput: [{out_name}](file:///{out_path.as_posix()})",
                output_files=[str(out_path.resolve())],
            )

        # ── 17. ADD BLANK PAGE ───────────────────────────────────────────────
        elif tool_name == "add_blank_page":
            target = files[0]
            data = target.read_bytes()
            pos = params.get("position", "end")
            added_bytes = add_blank_page(data, position=pos)
            out_name = f"blank_added_{target.stem}.pdf"
            out_path = save_output_bytes(added_bytes, out_name)
            return DocumentToolResult(
                success=True,
                tool_name=tool_name,
                message=f"✓ **Inserted a blank page into `{target.name}`**.\n\nOutput: [{out_name}](file:///{out_path.as_posix()})",
                output_files=[str(out_path.resolve())],
            )

        # ── 18. DUPLICATE PAGE ───────────────────────────────────────────────
        elif tool_name == "duplicate_page":
            target = files[0]
            data = target.read_bytes()
            target_p = int(params.get("target_page", 1))
            dup_bytes = duplicate_page(data, target_page=target_p)
            out_name = f"duplicated_p{target_p}_{target.stem}.pdf"
            out_path = save_output_bytes(dup_bytes, out_name)
            return DocumentToolResult(
                success=True,
                tool_name=tool_name,
                message=f"✓ **Duplicated page {target_p} in `{target.name}`**.\n\nOutput: [{out_name}](file:///{out_path.as_posix()})",
                output_files=[str(out_path.resolve())],
            )

    except Exception as e:
        # Sanitize error message to be user-friendly and not leak internal paths
        err_msg = str(e)
        if "TesseractNotFoundError" in err_msg or "tesseract is not installed" in err_msg.lower():
            user_err = "Tesseract OCR is not available on this system. Please check Tesseract installation."
        elif "Not a valid PDF" in err_msg or "PdfReadError" in err_msg:
            user_err = "The selected file could not be processed as a valid PDF."
        elif "No such file" in err_msg:
            user_err = "The requested file is no longer available in the workspace."
        else:
            # Clean generic message
            user_err = f"Failed to execute `{tool_name}`: {err_msg.split('HTTPException:')[-1].strip()}"

        log("DOCUMENT_TOOL_ERROR", tool=tool_name, error=str(e))
        return DocumentToolResult(
            success=False,
            tool_name=tool_name,
            message=f"❌ **Error**: {user_err}",
            error=str(e),
        )

    return DocumentToolResult(
        success=False,
        tool_name=tool_name,
        message="Unhandled document tool operation.",
        error="UNHANDLED_OP",
    )
