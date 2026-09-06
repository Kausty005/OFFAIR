"""
document_tools/router.py
FastAPI router for the OFFAIR Document Tools Suite.
Zero AI, zero Ollama, zero Docker, zero external API calls.
Sandboxed within workspace/outputs/.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from document_tools.batch_ops import batch_process
from document_tools.common import (
    create_zip_archive,
    get_output_path,
    safe_filename,
    save_output_bytes,
)
from document_tools.compare_ops import compare_documents
from document_tools.image_ops import (
    batch_convert_images,
    compress_image,
    convert_image,
    crop_image,
    resize_image,
    rotate_flip_image,
)
from document_tools.inspector_ops import inspect_document
from document_tools.ocr_ops import (
    create_searchable_pdf,
    get_ocr_engine_status,
    ocr_pdf_document,
    ocr_single_image,
)
from document_tools.office_ops import (
    csv_to_xlsx,
    docx_extract_tables,
    docx_get_stats,
    docx_to_markdown,
    docx_to_pdf,
    docx_to_text,
    pptx_extract_text,
    pptx_get_stats,
    spreadsheet_preview,
    txt_to_docx,
    txt_to_pdf,
    xlsx_to_csv,
)
from document_tools.pdf_ops import (
    add_blank_page,
    add_page_numbers,
    add_visual_signature,
    add_watermark,
    compress_pdf,
    crop_pdf,
    decrypt_pdf,
    delete_pages,
    duplicate_page,
    encrypt_pdf,
    extract_pages,
    extract_text_from_pdf,
    get_pdf_metadata,
    images_to_pdf,
    inspect_pdf_security,
    merge_pdfs,
    pdf_to_docx,
    pdf_to_markdown,
    remove_pdf_metadata,
    render_pdf_to_images,
    reorder_pages,
    resize_pdf,
    rotate_pdf,
    split_pdf,
)

from document_tools import common, pdf_ops

router = APIRouter(prefix="/api/document-tools", tags=["document-tools"])

# ── Backward-compatible helper aliases ──────────────────────────────────────
import io

_MAX_FILE_BYTES = 50 * 1024 * 1024

def _validate_pdf(data: bytes, label: str = "PDF file"):
    if len(data) > _MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail=f"{label}: file too large (max {_MAX_FILE_BYTES} bytes)")
    common.validate_pdf(data, label=label)


_validate_image = common.validate_image
_parse_page_ranges = common.parse_page_ranges
_safe_name = common.safe_filename


def _open_reader(data: bytes):
    import PyPDF2
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise HTTPException(status_code=400, detail="Password-protected PDFs are not supported")
        return reader
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Cannot read PDF: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# 1. ORGANIZE: Merge, Split, Extract, Delete, Reorder, Rotate, Crop, Resize, Add Blank, Duplicate
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/merge")
async def api_merge(files: List[UploadFile] = File(...)):
    """Merge 2 or more PDF files into a single PDF in upload order."""
    file_tuples = []
    for f in files:
        data = await f.read()
        file_tuples.append((data, f.filename or "file.pdf"))

    out_bytes = merge_pdfs(file_tuples)
    path = save_output_bytes(out_bytes, "merged.pdf")
    return FileResponse(path=str(path), filename="merged.pdf", media_type="application/pdf")


@router.post("/split")
async def api_split(
    file: UploadFile = File(...),
    mode: str = Form("all"),     # "all" or "ranges"
    ranges: str = Form(""),      # e.g. "1-2, 3-4"
):
    """Split a PDF into individual pages or custom ranges."""
    data = await file.read()
    parts = split_pdf(data, mode=mode, ranges=ranges)

    if len(parts) == 1:
        name, content = next(iter(parts.items()))
        path = save_output_bytes(content, name)
        return FileResponse(path=str(path), filename=name, media_type="application/pdf")

    zip_path = create_zip_archive(parts, "split_pages.zip")
    return FileResponse(path=str(zip_path), filename="split_pages.zip", media_type="application/zip")


@router.post("/extract")
@router.post("/extract-pages")
async def api_extract(
    file: UploadFile = File(...),
    pages: str = Form(...),      # e.g. "1-3, 5"
):
    """Extract specified pages into a new PDF."""
    data = await file.read()
    out_bytes = extract_pages(data, page_spec=pages)
    path = save_output_bytes(out_bytes, "extracted_pages.pdf")
    return FileResponse(path=str(path), filename="extracted_pages.pdf", media_type="application/pdf")


@router.post("/delete-pages")
async def api_delete_pages(
    file: UploadFile = File(...),
    pages: str = Form(...),      # e.g. "2, 4"
):
    """Delete specified pages from a PDF."""
    data = await file.read()
    out_bytes = delete_pages(data, page_spec=pages)
    path = save_output_bytes(out_bytes, "pages_deleted.pdf")
    return FileResponse(path=str(path), filename="pages_deleted.pdf", media_type="application/pdf")


@router.post("/reorder-pages")
async def api_reorder_pages(
    file: UploadFile = File(...),
    order: str = Form(...),       # comma-separated 1-based indices, e.g. "3,1,2,4"
):
    """Reorder pages according to custom sequence."""
    data = await file.read()
    try:
        page_order = [int(p.strip()) for p in order.split(",") if p.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Page order must be a comma-separated list of integers")

    out_bytes = reorder_pages(data, page_order)
    path = save_output_bytes(out_bytes, "reordered.pdf")
    return FileResponse(path=str(path), filename="reordered.pdf", media_type="application/pdf")


@router.post("/rotate")
@router.post("/rotate-pdf")
async def api_rotate(
    file: UploadFile = File(...),
    angle: int = Form(90),        # 90, 180, 270
    pages: str = Form("all"),     # "all" or "1,3-5"
):
    """Rotate selected or all pages by 90, 180, or 270 degrees."""
    data = await file.read()
    out_bytes = rotate_pdf(data, angle=angle, page_spec=pages)
    path = save_output_bytes(out_bytes, "rotated.pdf")
    return FileResponse(path=str(path), filename="rotated.pdf", media_type="application/pdf")


@router.post("/crop-pdf")
async def api_crop_pdf(
    file: UploadFile = File(...),
    left: float = Form(0.0),
    top: float = Form(0.0),
    right: float = Form(0.0),
    bottom: float = Form(0.0),
    pages: str = Form("all"),
):
    """Crop margins off PDF pages."""
    data = await file.read()
    out_bytes = crop_pdf(data, left, top, right, bottom, page_spec=pages)
    path = save_output_bytes(out_bytes, "cropped.pdf")
    return FileResponse(path=str(path), filename="cropped.pdf", media_type="application/pdf")


@router.post("/resize-pdf")
async def api_resize_pdf(
    file: UploadFile = File(...),
    target_size: str = Form("A4"),
    pages: str = Form("all"),
):
    """Resize PDF pages to standard paper size (A4, Letter, A3, Legal)."""
    data = await file.read()
    out_bytes = resize_pdf(data, target_size=target_size, page_spec=pages)
    path = save_output_bytes(out_bytes, f"resized_{target_size.lower()}.pdf")
    return FileResponse(path=str(path), filename=f"resized_{target_size.lower()}.pdf", media_type="application/pdf")


@router.post("/add-blank-page")
async def api_add_blank_page(
    file: UploadFile = File(...),
    position: str = Form("end"),    # start, end, after
    target_page: int = Form(1),
    page_size: str = Form("A4"),
):
    """Insert a blank page at start, end, or after specific page."""
    data = await file.read()
    out_bytes = add_blank_page(data, position=position, target_page=target_page, page_size=page_size)
    path = save_output_bytes(out_bytes, "with_blank_page.pdf")
    return FileResponse(path=str(path), filename="with_blank_page.pdf", media_type="application/pdf")


@router.post("/duplicate-page")
async def api_duplicate_page(
    file: UploadFile = File(...),
    page_num: int = Form(1),
    count: int = Form(1),
):
    """Duplicate a specific page in a PDF."""
    data = await file.read()
    out_bytes = duplicate_page(data, page_num=page_num, count=count)
    path = save_output_bytes(out_bytes, "page_duplicated.pdf")
    return FileResponse(path=str(path), filename="page_duplicated.pdf", media_type="application/pdf")


# ─────────────────────────────────────────────────────────────────────────────
# 2. CONVERT: PDF ↔ Images, Text, Markdown, DOCX, TXT
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/pdf-to-images")
async def api_pdf_to_images(
    file: UploadFile = File(...),
    fmt: str = Form("PNG"),
    pages: str = Form("all"),
    dpi: int = Form(150),
):
    """Convert PDF pages to PNG or JPG images."""
    data = await file.read()
    results = render_pdf_to_images(data, fmt=fmt, pages=pages, dpi=dpi)

    if len(results) == 1:
        name, img_bytes = next(iter(results.items()))
        path = save_output_bytes(img_bytes, name)
        media_type = "image/jpeg" if fmt.upper() in ("JPG", "JPEG") else "image/png"
        return FileResponse(path=str(path), filename=name, media_type=media_type)

    zip_path = create_zip_archive(results, "pdf_images.zip")
    return FileResponse(path=str(zip_path), filename="pdf_images.zip", media_type="application/zip")


@router.post("/images-to-pdf")
async def api_images_to_pdf(files: List[UploadFile] = File(...)):
    """Combine multiple images into a single A4 PDF."""
    imgs = []
    for f in files:
        data = await f.read()
        imgs.append((data, f.filename or "image"))

    out_bytes = images_to_pdf(imgs)
    path = save_output_bytes(out_bytes, "images_combined.pdf")
    return FileResponse(path=str(path), filename="images_combined.pdf", media_type="application/pdf")


@router.post("/pdf-to-text")
async def api_pdf_to_text(file: UploadFile = File(...)):
    """Extract digital text from PDF into a .txt file."""
    data = await file.read()
    full_text, is_scanned = extract_text_from_pdf(data)
    if is_scanned:
        full_text += (
            "\n\n[WARNING] Little or no machine-readable text was extracted from this PDF. "
            "It may be a scanned document. Use the OCR tool for scanned documents."
        )

    out_bytes = full_text.encode("utf-8")
    path = save_output_bytes(out_bytes, "extracted_text.txt")
    return FileResponse(path=str(path), filename="extracted_text.txt", media_type="text/plain; charset=utf-8")


@router.post("/pdf-to-markdown")
async def api_pdf_to_markdown(file: UploadFile = File(...)):
    """Convert PDF layout and text into structured Markdown."""
    data = await file.read()
    md_content = pdf_to_markdown(data)
    out_bytes = md_content.encode("utf-8")
    path = save_output_bytes(out_bytes, "document.md")
    return FileResponse(path=str(path), filename="document.md", media_type="text/markdown; charset=utf-8")


@router.post("/pdf-to-docx")
async def api_pdf_to_docx(file: UploadFile = File(...)):
    """Convert PDF text and structure into an editable Word (.docx) document."""
    data = await file.read()
    docx_bytes = pdf_to_docx(data)
    path = save_output_bytes(docx_bytes, "converted_document.docx")
    return FileResponse(
        path=str(path),
        filename="converted_document.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.post("/docx-to-pdf")
async def api_docx_to_pdf(file: UploadFile = File(...)):
    """Convert Word (.docx) into a clean formatted A4 PDF."""
    data = await file.read()
    pdf_bytes = docx_to_pdf(data)
    path = save_output_bytes(pdf_bytes, "converted_document.pdf")
    return FileResponse(path=str(path), filename="converted_document.pdf", media_type="application/pdf")


@router.post("/docx-to-text")
async def api_docx_to_text(file: UploadFile = File(...)):
    """Extract plain text from Word (.docx) file."""
    data = await file.read()
    text = docx_to_text(data)
    path = save_output_bytes(text.encode("utf-8"), "extracted_text.txt")
    return FileResponse(path=str(path), filename="extracted_text.txt", media_type="text/plain; charset=utf-8")


@router.post("/docx-to-markdown")
async def api_docx_to_markdown(file: UploadFile = File(...)):
    """Convert Word (.docx) into structured Markdown."""
    data = await file.read()
    md_text = docx_to_markdown(data)
    path = save_output_bytes(md_text.encode("utf-8"), "extracted.md")
    return FileResponse(path=str(path), filename="extracted.md", media_type="text/markdown; charset=utf-8")


@router.post("/txt-to-pdf")
async def api_txt_to_pdf(
    file: UploadFile = File(...),
    title: str = Form("Document"),
):
    """Convert plain text file into formatted A4 PDF."""
    data = await file.read()
    text = data.decode("utf-8", errors="replace")
    pdf_bytes = txt_to_pdf(text, title=title)
    path = save_output_bytes(pdf_bytes, "document.pdf")
    return FileResponse(path=str(path), filename="document.pdf", media_type="application/pdf")


@router.post("/txt-to-docx")
async def api_txt_to_docx(
    file: UploadFile = File(...),
    title: str = Form("Document"),
):
    """Convert plain text file into editable Word (.docx)."""
    data = await file.read()
    text = data.decode("utf-8", errors="replace")
    docx_bytes = txt_to_docx(text, title=title)
    path = save_output_bytes(docx_bytes, "document.docx")
    return FileResponse(
        path=str(path),
        filename="document.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. OPTIMIZE: Compress PDF, Compress Image, Resize Image
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/compress")
async def api_compress_pdf(
    file: UploadFile = File(...),
    level: str = Form("medium"),    # low | medium | high
):
    """
    Compress PDF: strips metadata, cleans stream objects, optimizes images.
    Returns compressed file with X-Original-Size, X-Output-Size, and X-Reduction-Pct headers.
    """
    data = await file.read()
    out_bytes, orig_size, out_size, pct = compress_pdf(data, level=level)
    path = save_output_bytes(out_bytes, "compressed.pdf")

    return FileResponse(
        path=str(path),
        filename="compressed.pdf",
        media_type="application/pdf",
        headers={
            "X-Original-Size": str(orig_size),
            "X-Output-Size": str(out_size),
            "X-Reduction-Pct": str(pct),
        },
    )


@router.post("/compress-image")
async def api_compress_image(
    file: UploadFile = File(...),
    quality: int = Form(70),
):
    """Compress image by re-encoding with optimized quality factor."""
    data = await file.read()
    out_bytes, stats = compress_image(data, quality=quality)
    path = save_output_bytes(out_bytes, "compressed_image.jpg")

    return FileResponse(
        path=str(path),
        filename="compressed_image.jpg",
        media_type="image/jpeg",
        headers={
            "X-Original-Size": str(stats["original_size"]),
            "X-Output-Size": str(stats["output_size"]),
            "X-Reduction-Pct": str(stats["reduction_pct"]),
        },
    )


@router.post("/resize-image")
async def api_resize_image(
    file: UploadFile = File(...),
    width: Optional[int] = Form(None),
    height: Optional[int] = Form(None),
    scale_pct: Optional[float] = Form(None),
    keep_aspect: bool = Form(True),
):
    """Resize an image to specific dimensions or percentage scale."""
    data = await file.read()
    out_bytes, stats = resize_image(data, width=width, height=height, scale_pct=scale_pct, keep_aspect=keep_aspect)
    path = save_output_bytes(out_bytes, "resized_image.png")
    return FileResponse(path=str(path), filename="resized_image.png", media_type="image/png")


# ─────────────────────────────────────────────────────────────────────────────
# 4. SECURITY & METADATA
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/metadata")
@router.post("/view-metadata")
async def api_view_metadata(file: UploadFile = File(...)):
    """View PDF metadata properties and attributes."""
    data = await file.read()
    meta = get_pdf_metadata(data)
    return JSONResponse(content=meta)


@router.post("/remove-metadata")
async def api_remove_metadata(file: UploadFile = File(...)):
    """Strip all metadata and author information from PDF."""
    data = await file.read()
    clean_bytes = remove_pdf_metadata(data)
    path = save_output_bytes(clean_bytes, "clean.pdf")
    return FileResponse(path=str(path), filename="clean.pdf", media_type="application/pdf")


@router.post("/encrypt")
async def api_encrypt(
    file: UploadFile = File(...),
    password: str = Form(...),
    owner_password: Optional[str] = Form(None),
):
    """Encrypt PDF using AES-256 standard encryption."""
    data = await file.read()
    enc_bytes = encrypt_pdf(data, user_password=password, owner_password=owner_password)
    path = save_output_bytes(enc_bytes, "encrypted.pdf")
    return FileResponse(path=str(path), filename="encrypted.pdf", media_type="application/pdf")


@router.post("/remove-password")
async def api_remove_password(
    file: UploadFile = File(...),
    password: str = Form(...),
):
    """Decrypt PDF with provided password and save unencrypted copy."""
    data = await file.read()
    dec_bytes = decrypt_pdf(data, password=password)
    path = save_output_bytes(dec_bytes, "decrypted.pdf")
    return FileResponse(path=str(path), filename="decrypted.pdf", media_type="application/pdf")


@router.post("/security-info")
async def api_security_info(file: UploadFile = File(...)):
    """Inspect PDF security, encryption, forms, JavaScript, and embedded files."""
    data = await file.read()
    sec = inspect_pdf_security(data)
    return JSONResponse(content=sec)


# ─────────────────────────────────────────────────────────────────────────────
# 5. EDIT & SIGN: Watermark, Page Numbers, Visual Signature
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/watermark")
async def api_watermark(
    file: UploadFile = File(...),
    text: str = Form("CONFIDENTIAL"),
    opacity: float = Form(0.3),
    angle: float = Form(45.0),
    font_size: int = Form(40),
    pages: str = Form("all"),
):
    """Add customizable diagonal or horizontal watermark to PDF pages."""
    data = await file.read()
    out_bytes = add_watermark(
        data,
        text=text,
        opacity=opacity,
        angle=angle,
        font_size=font_size,
        pages=pages,
    )
    path = save_output_bytes(out_bytes, "watermarked.pdf")
    return FileResponse(path=str(path), filename="watermarked.pdf", media_type="application/pdf")


@router.post("/page-numbers")
async def api_page_numbers(
    file: UploadFile = File(...),
    position: str = Form("bottom-center"),
    template: str = Form("Page {page} of {total}"),
    start_num: int = Form(1),
    font_size: int = Form(10),
):
    """Stamp formatted page numbers onto PDF pages."""
    data = await file.read()
    out_bytes = add_page_numbers(
        data,
        position=position,
        template=template,
        start_num=start_num,
        font_size=font_size,
    )
    path = save_output_bytes(out_bytes, "numbered.pdf")
    return FileResponse(path=str(path), filename="numbered.pdf", media_type="application/pdf")


@router.post("/visual-signature")
async def api_visual_signature(
    file: UploadFile = File(...),
    signature: UploadFile = File(...),
    page_num: int = Form(1),
    x: float = Form(350.0),
    y: float = Form(700.0),
    width: float = Form(180.0),
    height: float = Form(80.0),
):
    """Place drawn or uploaded visual signature image onto specified PDF page."""
    data = await file.read()
    sig_data = await signature.read()
    out_bytes = add_visual_signature(
        data,
        sig_image_bytes=sig_data,
        page_num=page_num,
        x=x,
        y=y,
        width=width,
        height=height,
    )
    path = save_output_bytes(out_bytes, "signed.pdf")
    return FileResponse(path=str(path), filename="signed.pdf", media_type="application/pdf")


# ─────────────────────────────────────────────────────────────────────────────
# 6. OFFICE: Word, PowerPoint, Spreadsheets
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/docx-extract-tables")
async def api_docx_extract_tables(file: UploadFile = File(...)):
    """Extract all tables from Word (.docx) file."""
    data = await file.read()
    tables = docx_extract_tables(data)
    return JSONResponse(content={"table_count": len(tables), "tables": tables})


@router.post("/docx-stats")
async def api_docx_stats(file: UploadFile = File(...)):
    """Calculate word, character, paragraph, and table statistics for DOCX."""
    data = await file.read()
    stats = docx_get_stats(data)
    return JSONResponse(content=stats)


@router.post("/pptx-extract-text")
async def api_pptx_extract_text(file: UploadFile = File(...)):
    """Extract slide text and speaker notes from PowerPoint (.pptx)."""
    data = await file.read()
    res = pptx_extract_text(data)
    return JSONResponse(content=res)


@router.post("/pptx-stats")
async def api_pptx_stats(file: UploadFile = File(...)):
    """Calculate PowerPoint presentation statistics."""
    data = await file.read()
    res = pptx_get_stats(data)
    return JSONResponse(content=res)


@router.post("/xlsx-to-csv")
async def api_xlsx_to_csv(
    file: UploadFile = File(...),
    sheet_name: Optional[str] = Form(None),
):
    """Convert Excel worksheet(s) to CSV."""
    data = await file.read()
    sheets_csv = xlsx_to_csv(data, sheet_name=sheet_name)

    if len(sheets_csv) == 1:
        name, csv_bytes = next(iter(sheets_csv.items()))
        path = save_output_bytes(csv_bytes, name)
        return FileResponse(path=str(path), filename=name, media_type="text/csv")

    zip_path = create_zip_archive(sheets_csv, "excel_sheets_csv.zip")
    return FileResponse(path=str(zip_path), filename="excel_sheets_csv.zip", media_type="application/zip")


@router.post("/csv-to-xlsx")
async def api_csv_to_xlsx(
    file: UploadFile = File(...),
    sheet_name: str = Form("Data"),
):
    """Convert CSV file into a styled Excel workbook."""
    data = await file.read()
    csv_text = data.decode("utf-8", errors="replace")
    xlsx_bytes = csv_to_xlsx(csv_text, sheet_name=sheet_name)
    path = save_output_bytes(xlsx_bytes, "spreadsheet.xlsx")
    return FileResponse(
        path=str(path),
        filename="spreadsheet.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.post("/spreadsheet-preview")
async def api_spreadsheet_preview(file: UploadFile = File(...)):
    """Inspect Excel workbook sheets, rows, and preview first 10 rows."""
    data = await file.read()
    res = spreadsheet_preview(data)
    return JSONResponse(content=res)


# ─────────────────────────────────────────────────────────────────────────────
# 7. IMAGE TOOLS: Convert, Crop, Rotate, Flip, Batch
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/convert-image")
async def api_convert_image(
    file: UploadFile = File(...),
    target_fmt: str = Form("PNG"),
    quality: int = Form(85),
):
    """Convert image between PNG, JPG, and WebP formats."""
    data = await file.read()
    out_bytes, ext, stats = convert_image(data, target_fmt=target_fmt, quality=quality)
    out_name = f"converted_image.{ext}"
    path = save_output_bytes(out_bytes, out_name)
    media_type = f"image/{ext}" if ext != "jpg" else "image/jpeg"
    return FileResponse(path=str(path), filename=out_name, media_type=media_type)


@router.post("/crop-image")
async def api_crop_image(
    file: UploadFile = File(...),
    left: int = Form(...),
    top: int = Form(...),
    right: int = Form(...),
    bottom: int = Form(...),
):
    """Crop image with bounding box coordinates."""
    data = await file.read()
    out_bytes, stats = crop_image(data, left=left, top=top, right=right, bottom=bottom)
    path = save_output_bytes(out_bytes, "cropped_image.png")
    return FileResponse(path=str(path), filename="cropped_image.png", media_type="image/png")


@router.post("/rotate-flip-image")
async def api_rotate_flip_image(
    file: UploadFile = File(...),
    angle: int = Form(0),
    flip_h: bool = Form(False),
    flip_v: bool = Form(False),
):
    """Rotate image by 90/180/270 degrees and/or mirror horizontally/vertically."""
    data = await file.read()
    out_bytes, stats = rotate_flip_image(data, angle=angle, flip_h=flip_h, flip_v=flip_v)
    path = save_output_bytes(out_bytes, "transformed_image.png")
    return FileResponse(path=str(path), filename="transformed_image.png", media_type="image/png")


@router.post("/batch-convert-images")
async def api_batch_convert_images(
    files: List[UploadFile] = File(...),
    target_fmt: str = Form("PNG"),
    quality: int = Form(85),
):
    """Convert multiple images into target format and return ZIP."""
    img_tuples = []
    for f in files:
        data = await f.read()
        img_tuples.append((data, f.filename or "image"))

    results = batch_convert_images(img_tuples, target_fmt=target_fmt, quality=quality)
    zip_path = create_zip_archive(results, "converted_images.zip")
    return FileResponse(path=str(zip_path), filename="converted_images.zip", media_type="application/zip")


# ─────────────────────────────────────────────────────────────────────────────
# 8. OCR TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/ocr-status")
async def api_ocr_status():
    """Check local Tesseract OCR engine status."""
    return JSONResponse(content=get_ocr_engine_status())


@router.post("/ocr-image")
async def api_ocr_image(
    file: UploadFile = File(...),
    lang: Optional[str] = Form(None),
):
    """Extract text from an image using local Tesseract OCR."""
    data = await file.read()
    text = ocr_single_image(data, lang=lang)
    return JSONResponse(content={"text": text, "char_count": len(text)})


@router.post("/ocr-pdf")
async def api_ocr_pdf(
    file: UploadFile = File(...),
    pages: str = Form("all"),
    lang: Optional[str] = Form(None),
):
    """Extract text from scanned PDF pages using local Tesseract OCR."""
    data = await file.read()
    res = ocr_pdf_document(data, pages=pages, lang=lang)
    return JSONResponse(content=res)


@router.post("/searchable-pdf")
async def api_searchable_pdf(
    file: UploadFile = File(...),
    pages: str = Form("all"),
    lang: Optional[str] = Form(None),
):
    """Create a searchable PDF with embedded invisible text layer from OCR."""
    data = await file.read()
    out_bytes = create_searchable_pdf(data, pages=pages, lang=lang)
    path = save_output_bytes(out_bytes, "searchable.pdf")
    return FileResponse(path=str(path), filename="searchable.pdf", media_type="application/pdf")



# ─────────────────────────────────────────────────────────────────────────────
# 9. INSPECTOR & COMPARE
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/inspect")
async def api_inspect(file: UploadFile = File(...)):
    """Deterministic offline inspection for PDF, Office, Image, and Text files."""
    data = await file.read()
    res = inspect_document(file.filename or "document", data)
    return JSONResponse(content=res)


@router.post("/compare")
async def api_compare(
    file1: UploadFile = File(...),
    file2: UploadFile = File(...),
):
    """Compare two documents line-by-line using difflib."""
    data1 = await file1.read()
    data2 = await file2.read()
    res = compare_documents(data1, file1.filename or "file1", data2, file2.filename or "file2")
    return JSONResponse(content=res)


# ─────────────────────────────────────────────────────────────────────────────
# 10. BATCH PROCESSING
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/batch")
async def api_batch(
    files: List[UploadFile] = File(...),
    operation: str = Form(...),      # pdf-to-txt, compress-pdf, pdf-to-images, remove-metadata, convert-images, docx-to-txt
    options: str = Form("{}"),       # JSON string of options
):
    """
    Batch process multiple documents in parallel with isolated error recovery.
    Returns ZIP of successful outputs with summary headers.
    """
    try:
        opts = json.loads(options) if options else {}
    except Exception:
        opts = {}

    file_tuples = []
    for f in files:
        data = await f.read()
        file_tuples.append((data, f.filename or "file"))

    output_files, summary = batch_process(file_tuples, operation=operation, options=opts)

    if not output_files:
        raise HTTPException(
            status_code=400,
            detail=f"Batch processing failed for all {len(file_tuples)} file(s). Errors: {summary.get('errors')}",
        )

    zip_path = create_zip_archive(output_files, "batch_results.zip")
    return FileResponse(
        path=str(zip_path),
        filename="batch_results.zip",
        media_type="application/zip",
        headers={
            "X-Total-Files": str(summary["total_files"]),
            "X-Completed-Files": str(summary["completed"]),
            "X-Failed-Files": str(summary["failed"]),
        },
    )
