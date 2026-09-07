"""
document_tools/chat_resolver.py
Dedicated deterministic pre-router for chat document operations.

Strictly local, air-gap compatible, zero LLM / Ollama dependency for deterministic ops.
Resolves natural-language chat requests into explicit Document Tool operations
before any AI routing or vision analysis can intercept them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class DocumentStep:
    tool_name: str
    params: Dict[str, Any]
    description: str


@dataclass
class DocumentOperationIntent:
    tool_name: str
    params: Dict[str, Any]
    description: str
    is_compound: bool = False
    pipeline: List[DocumentStep] = field(default_factory=list)

    @property
    def tools(self) -> List[str]:
        if self.is_compound and self.pipeline:
            return [s.tool_name for s in self.pipeline]
        return [self.tool_name]


def _parse_pages_param(q: str) -> Optional[str]:
    """Extract page specifications like '1, 3 and 5', 'page 4', 'pages 2-6'."""
    m = re.search(r"\bpages?\s+((?:\d+|\s+|,|and|to|-)+)", q)
    if m:
        raw = m.group(1).replace("and", ",").replace("to", "-").strip()
        tokens = [t.strip() for t in raw.split(",") if t.strip()]
        cleaned = ",".join(tokens)
        cleaned = re.sub(r"\s+", "", cleaned)
        if cleaned:
            return cleaned

    m_range = re.search(r"\b(\d+)\s*(?:-|to)\s*(\d+)\b", q)
    if m_range:
        return f"{m_range.group(1)}-{m_range.group(2)}"

    m_single = re.search(r"\bpage\s+(\d+)\b", q)
    if m_single:
        return m_single.group(1)

    return None


def _parse_angle_param(q: str) -> int:
    """Extract rotation angle."""
    if "180" in q:
        return 180
    if "270" in q or "counter" in q or "left" in q:
        return 270
    return 90


def _parse_compression_level(q: str) -> str:
    """Extract compression level: low, medium, high."""
    if "high" in q or "maximum" in q or "smallest" in q or "extreme" in q:
        return "high"
    if "low" in q or "slight" in q or "minimal" in q or "fast" in q:
        return "low"
    return "medium"


def _parse_image_format(q: str) -> str:
    """Extract image format: png or jpg."""
    if "jpg" in q or "jpeg" in q:
        return "jpg"
    return "png"


def _parse_language(q: str) -> str:
    """Extract language code for OCR."""
    if "hindi" in q or "hin" in q:
        return "hin"
    if "spanish" in q or "spa" in q:
        return "spa"
    if "french" in q or "fra" in q:
        return "fra"
    if "german" in q or "deu" in q:
        return "deu"
    return "eng"


_EXPLICIT_VISION_PATTERNS = [
    r"\banalyze\s+(?:this\s+)?(?:image|photo|photograph|picture|graphic)\b",
    r"\binspect\s+(?:this\s+)?(?:image|photo|photograph|picture)\b",
    r"\bidentify\s+defects\b",
    r"\bfind\s+defects\b",
    r"\bwhat\s+(?:is\s+)?(?:shown|visible|in)\s+(?:in\s+)?(?:this\s+)?(?:image|photo|picture)\b",
    r"\bdetect\s+objects\b",
    r"\banalyze\s+(?:the\s+)?visual\s+content\b",
    r"\blook\s+at\s+(?:this\s+)?(?:image|photo|picture)\b",
    r"\bp&id\b",
    r"\bpiping\s+and\s+instrumentation\b",
]


def is_explicit_vision_request(query: str) -> bool:
    """Check if query explicitly requests visual understanding/inspection."""
    q_lower = query.strip().lower()
    return any(re.search(p, q_lower) for p in _EXPLICIT_VISION_PATTERNS)


def resolve_explicit_document_operation(
    query: str,
    uploaded_files: Optional[List[str]] = None,
) -> Optional[DocumentOperationIntent]:
    """
    Deterministically resolve explicit document operations from user query and attachments.
    Returns DocumentOperationIntent or None if the request is not a deterministic document tool.
    """
    q = query.strip().lower()
    files = uploaded_files or []

    has_pdf = any(f.lower().endswith(".pdf") for f in files)
    has_image = any(f.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff")) for f in files)
    has_docx = any(f.lower().endswith((".docx", ".doc")) for f in files)

    # ─────────────────────────────────────────────────────────────
    # Check for Compound Multi-Step Pipeline
    # Example: "Merge these two PDFs and then compress the result."
    # ─────────────────────────────────────────────────────────────
    is_merge = bool(
        re.search(r"\b(?:merge|combine|join|stitch|concatenate)\b", q)
        and ("pdf" in q or has_pdf or re.search(r"\b(?:these|files|documents|two|2)\b", q))
    )
    is_compress = bool(
        re.search(r"\b(?:compress|reduce\s+(?:the\s+)?(?:pdf\s+)?size|make\s+(?:it\s+)?smaller)\b", q)
    )

    if is_merge and is_compress and ("and" in q or "then" in q or "after" in q):
        comp_level = _parse_compression_level(q)
        return DocumentOperationIntent(
            tool_name="merge_pdf",
            params={"level": comp_level},
            description="Merge PDF files and compress the result",
            is_compound=True,
            pipeline=[
                DocumentStep("merge_pdf", {}, "Merge input PDF files"),
                DocumentStep("compress_pdf", {"level": comp_level}, "Compress merged PDF file"),
            ],
        )

    # ─────────────────────────────────────────────────────────────
    # 1. IMAGES TO PDF ("make pdf" with images attached, or explicit image conversion)
    # ─────────────────────────────────────────────────────────────
    if (
        re.search(r"\b(?:make|create|generate|convert|turn)\s+(?:a\s+)?pdf\s+(?:from\s+)?(?:these\s+)?images?\b", q)
        or re.search(r"\bimages?\s+(?:to|into)\s+pdf\b", q)
        or re.search(r"\bconvert\s+(?:these\s+)?images?\s+to\s+pdf\b", q)
        or re.search(r"\bcombine\s+(?:these\s+)?images?\s+(?:into\s+a\s+|to\s+)?pdf\b", q)
        or re.search(r"\bjoin\s+(?:these\s+)?images?\s+(?:into\s+a\s+|to\s+)?pdf\b", q)
        or re.search(r"\bmerge\s+(?:these\s+)?images?\s+(?:into\s+a\s+|to\s+)?pdf\b", q)
        or (has_image and re.search(r"^\s*(?:make|create|generate|turn\s+into)\s+(?:a\s+)?pdf\s*$", q))
        or (has_image and q in ("make pdf", "create pdf", "pdf please", "convert to pdf", "convert to pdf please"))
        or (has_image and "to pdf" in q and not has_pdf)
    ):
        return DocumentOperationIntent(
            tool_name="images_to_pdf",
            params={},
            description="Convert input image(s) into a unified PDF document",
        )

    # ─────────────────────────────────────────────────────────────
    # 2. MERGE PDF
    # ─────────────────────────────────────────────────────────────
    is_image_conversion = bool(re.search(r"\b(?:images?|photos?|pictures?)\b", q) and ("to pdf" in q or "into a pdf" in q or "into pdf" in q))
    if not is_image_conversion and (
        re.search(r"\b(?:merge|combine|join|stitch|concatenate)\s+(?:these\s+|the\s+)?(?:\d+|two|three|all)?\s*(?:pdf|pdfs|documents|files)\b", q)
        or re.search(r"\bmerge\s+(?:these\s+)?(?:\d+|two|three)?\s*pdfs?\b", q)
        or re.search(r"\bmerge\s+pdf\b", q)
        or re.search(r"\bcombine\s+.*\.pdf\b", q)
        or (("merge" in q or "combine" in q or "join" in q) and ("pdf" in q or has_pdf) and not ("analyze" in q or "inspect" in q))
    ):
        return DocumentOperationIntent(
            tool_name="merge_pdf",
            params={},
            description="Merge PDF documents into a single sequential PDF",
        )

    # ─────────────────────────────────────────────────────────────
    # 3. COMPRESS PDF
    # ─────────────────────────────────────────────────────────────
    if (
        re.search(r"\bcompress\s+(?:this\s+|the\s+)?pdf\b", q)
        or re.search(r"\breduce\s+(?:the\s+)?(?:pdf\s+)?size\b", q)
        or re.search(r"\bmake\s+(?:this\s+)?pdf\s+(?:smaller|less\s+size)\b", q)
        or re.search(r"\boptimize\s+pdf\b", q)
        or ("compress" in q and ("pdf" in q or has_pdf))
    ):
        level = _parse_compression_level(q)
        return DocumentOperationIntent(
            tool_name="compress_pdf",
            params={"level": level},
            description=f"Compress PDF document (level: {level})",
        )

    # ─────────────────────────────────────────────────────────────
    # 4. SPLIT PDF
    # ─────────────────────────────────────────────────────────────
    if (
        re.search(r"\bsplit\s+(?:this\s+|the\s+)?(?:pdf|document|file)\b", q)
        or re.search(r"\bsplit\s+pdf\b", q)
        or ("split" in q and ("pdf" in q or has_pdf))
    ):
        pages = _parse_pages_param(q)
        mode = "ranges" if pages else ("all" if "every page" in q or "each page" in q else "ranges")
        return DocumentOperationIntent(
            tool_name="split_pdf",
            params={"mode": mode, "ranges": pages or ""},
            description="Split PDF document into parts",
        )

    # ─────────────────────────────────────────────────────────────
    # 5. EXTRACT PAGES
    # ─────────────────────────────────────────────────────────────
    if (
        (re.search(r"\bextract\s+(?:the\s+)?pages?\b", q) and not ("text" in q))
        or re.search(r"\btake\s+pages?\b", q)
        or re.search(r"\bgive\s+me\s+pages?\b", q)
        or re.search(r"\bpull\s+out\s+pages?\b", q)
        or (("extract" in q or "get" in q) and "page" in q and ("pdf" in q or has_pdf) and not ("text" in q))
    ):
        pages = _parse_pages_param(q)
        return DocumentOperationIntent(
            tool_name="extract_pages",
            params={"pages": pages or ""},
            description=f"Extract page(s) {pages or ''} from PDF",
        )

    # ─────────────────────────────────────────────────────────────
    # 6. DELETE PAGES
    # ─────────────────────────────────────────────────────────────
    if (
        re.search(r"\b(?:delete|remove)\s+(?:the\s+)?pages?\b", q)
        or ("delete" in q or "remove" in q) and "page" in q and ("pdf" in q or has_pdf)
    ):
        pages = _parse_pages_param(q)
        return DocumentOperationIntent(
            tool_name="delete_pages",
            params={"pages": pages or ""},
            description=f"Remove designated page(s) {pages or ''} from PDF",
        )

    # ─────────────────────────────────────────────────────────────
    # 7. ROTATE PDF
    # ─────────────────────────────────────────────────────────────
    if (
        re.search(r"\brotate\s+(?:the\s+|this\s+)?(?:pdf|pages?|document)\b", q)
        or "rotate" in q and ("pdf" in q or "page" in q or has_pdf)
    ):
        pages = _parse_pages_param(q) or "all"
        angle = _parse_angle_param(q)
        return DocumentOperationIntent(
            tool_name="rotate_pdf",
            params={"angle": angle, "pages": pages},
            description=f"Rotate PDF page(s) by {angle}°",
        )

    # ─────────────────────────────────────────────────────────────
    # 8. CROP PDF
    # ─────────────────────────────────────────────────────────────
    if re.search(r"\bcrop\s+(?:this\s+|the\s+)?(?:pdf|document)\b", q) or ("crop" in q and ("pdf" in q or has_pdf)):
        pages = _parse_pages_param(q) or "all"
        return DocumentOperationIntent(
            tool_name="crop_pdf",
            params={"pages": pages, "left": 20, "top": 20, "right": 20, "bottom": 20},
            description="Crop margins of PDF document",
        )

    # ─────────────────────────────────────────────────────────────
    # 9. RESIZE PDF
    # ─────────────────────────────────────────────────────────────
    if re.search(r"\bresize\s+(?:this\s+|the\s+)?(?:pdf|document)\b", q) or ("resize" in q and ("pdf" in q or has_pdf)):
        target_size = "A3" if "a3" in q else ("letter" if "letter" in q else "A4")
        return DocumentOperationIntent(
            tool_name="resize_pdf",
            params={"target_size": target_size},
            description=f"Resize PDF pages to standard {target_size}",
        )

    # ─────────────────────────────────────────────────────────────
    # 10. ADD BLANK PAGE
    # ─────────────────────────────────────────────────────────────
    if re.search(r"\b(?:add|insert)\s+(?:a\s+)?blank\s+page\b", q):
        position = "start" if "beginning" in q or "start" in q else "end"
        return DocumentOperationIntent(
            tool_name="add_blank_page",
            params={"position": position},
            description="Insert a blank page into PDF",
        )

    # ─────────────────────────────────────────────────────────────
    # 11. DUPLICATE PAGE
    # ─────────────────────────────────────────────────────────────
    if re.search(r"\bduplicate\s+page\b", q):
        page_num = _parse_pages_param(q) or "1"
        try:
            p_int = int(page_num)
        except ValueError:
            p_int = 1
        return DocumentOperationIntent(
            tool_name="duplicate_page",
            params={"target_page": p_int},
            description=f"Duplicate page {p_int} in PDF",
        )

    # ─────────────────────────────────────────────────────────────
    # 12. PDF TO IMAGES
    # ─────────────────────────────────────────────────────────────
    if (
        re.search(r"\bpdf\s+(?:to|into)\s+(?:png|jpg|jpeg|images?)\b", q)
        or re.search(r"\bconvert\s+(?:this\s+)?pdf\s+to\s+(?:png|jpg|jpeg|images?)\b", q)
        or re.search(r"\bturn\s+(?:this\s+)?pdf\s+into\s+(?:png|jpg|jpeg|images?)\b", q)
        or re.search(r"\brender\s+(?:this\s+)?pdf\s+to\s+(?:png|jpg|jpeg|images?)\b", q)
        or (("image" in q or "png" in q or "jpg" in q or "jpeg" in q) and "pdf" in q and ("convert" in q or "turn" in q or "render" in q))
    ):
        fmt = _parse_image_format(q)
        pages = _parse_pages_param(q) or "all"
        return DocumentOperationIntent(
            tool_name="pdf_to_images",
            params={"format": fmt, "pages": pages},
            description=f"Render PDF pages to {fmt.upper()} images in archive",
        )

    # ─────────────────────────────────────────────────────────────
    # 13. PDF TO TEXT (Native extraction)
    # ─────────────────────────────────────────────────────────────
    if not ("ocr" in q) and (
        re.search(r"\bextract\s+(?:all\s+)?(?:the\s+)?text\s+from\s+(?:this\s+)?pdf\b", q)
        or re.search(r"\bpdf\s+(?:to|into)\s+text\b", q)
        or re.search(r"\bget\s+text\s+from\s+(?:this\s+)?pdf\b", q)
        or re.search(r"\bextract\s+text\s+from\s+(?:this\s+)?pdf\b", q)
        or (has_pdf and ("extract text" in q or "text from pdf" in q or "convert to text" in q))
    ):
        return DocumentOperationIntent(
            tool_name="pdf_to_text",
            params={},
            description="Extract digital text content from PDF",
        )

    # ─────────────────────────────────────────────────────────────
    # 14. OCR (Scanned PDF or Image)
    # ─────────────────────────────────────────────────────────────
    if (
        re.search(r"\bocr\s+(?:this\s+|the\s+)?(?:scanned\s+)?(?:pdf|document|image|file)\b", q)
        or re.search(r"\bextract\s+text\s+using\s+ocr\b", q)
        or ("ocr" in q and (has_pdf or has_image or "pdf" in q or "scanned" in q or "image" in q))
    ):
        lang = _parse_language(q)
        pages = _parse_pages_param(q) or "all"
        if has_image and not has_pdf:
            return DocumentOperationIntent(
                tool_name="ocr_image",
                params={"language": lang},
                description=f"Extract text from image using local OCR ({lang})",
            )
        return DocumentOperationIntent(
            tool_name="ocr_pdf",
            params={"language": lang, "pages": pages},
            description=f"Extract text from scanned PDF using local OCR ({lang})",
        )

    # ─────────────────────────────────────────────────────────────
    # 15. STRIP METADATA
    # ─────────────────────────────────────────────────────────────
    if (
        re.search(r"\bstrip\s+(?:pdf\s+)?metadata\b", q)
        or re.search(r"\bremove\s+(?:pdf\s+)?metadata\b", q)
        or re.search(r"\bclean\s+metadata\b", q)
        or re.search(r"\bsanitize\s+pdf\b", q)
    ):
        return DocumentOperationIntent(
            tool_name="strip_metadata",
            params={},
            description="Sanitize and remove metadata from PDF",
        )

    return None
