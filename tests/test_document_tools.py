"""
tests/test_document_tools.py
Isolated tests for the Document Tools module.
No Ollama, Docker, or AI stack required.

Requires: pytest, PyPDF2, Pillow, anyio, httpx (all already installed)
Run from project root: python -m pytest tests/test_document_tools.py -v
"""

import io
import sys
import zipfile
from pathlib import Path

import pytest

# ── path setup ─────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))

# ── helpers to create synthetic PDFs / images in-memory ──────────────────

def _make_pdf(num_pages: int = 1) -> bytes:
    """Create a minimal valid PDF with n blank pages using PyPDF2."""
    import PyPDF2
    writer = PyPDF2.PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=595, height=842)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _make_pdf_with_meta(title="Test Title", author="Test Author") -> bytes:
    import PyPDF2
    writer = PyPDF2.PdfWriter()
    writer.add_blank_page(width=595, height=842)
    writer.add_metadata({"/Title": title, "/Author": author})
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _make_image_bytes(fmt: str = "PNG", size=(100, 100)) -> bytes:
    """Create a tiny solid-colour image as bytes."""
    from PIL import Image
    img = Image.new("RGB", size, color=(200, 100, 50))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


# ── import router helpers directly ─────────────────────────────────────────
from document_tools.router import (
    _validate_pdf,
    _validate_image,
    _open_reader,
    _parse_page_ranges,
    _safe_name,
)


# ═══════════════════════════════════════════════════════════════════════════
# Unit tests — pure helper functions (no HTTP, no async)
# ═══════════════════════════════════════════════════════════════════════════

class TestSafeName:
    def test_normal(self):
        assert _safe_name("hello.pdf") == "hello.pdf"

    def test_path_traversal_stripped(self):
        result = _safe_name("../../etc/passwd")
        assert ".." not in result
        assert "/" not in result

    def test_special_chars_replaced(self):
        result = _safe_name("my file (v2).pdf")
        assert "(" not in result
        assert " " not in result


class TestValidatePDF:
    def test_valid_pdf(self):
        data = _make_pdf(1)
        _validate_pdf(data)  # should not raise

    def test_invalid_magic_bytes(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            _validate_pdf(b"not a pdf at all")
        assert exc_info.value.status_code == 400

    def test_too_large(self, monkeypatch):
        from fastapi import HTTPException
        import document_tools.router as rt
        monkeypatch.setattr(rt, "_MAX_FILE_BYTES", 10)
        with pytest.raises(HTTPException) as exc_info:
            _validate_pdf(_make_pdf(1))
        assert exc_info.value.status_code == 413


class TestValidateImage:
    def test_valid_png(self):
        data = _make_image_bytes("PNG")
        _validate_image(data)  # should not raise

    def test_valid_jpeg(self):
        data = _make_image_bytes("JPEG")
        _validate_image(data)  # should not raise

    def test_invalid_image(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            _validate_image(b"not an image")
        assert exc_info.value.status_code == 400


class TestOpenReader:
    def test_valid_pdf(self):
        data = _make_pdf(3)
        reader = _open_reader(data)
        assert len(reader.pages) == 3

    def test_corrupt_pdf(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            _open_reader(b"%PDF-corrupted-garbage")
        assert exc_info.value.status_code == 400


class TestParsePageRanges:
    def test_single_page(self):
        assert _parse_page_ranges("3", 10) == [3]

    def test_range(self):
        assert _parse_page_ranges("1-3", 10) == [1, 2, 3]

    def test_mixed(self):
        assert _parse_page_ranges("1-3,5,7-8", 10) == [1, 2, 3, 5, 7, 8]

    def test_out_of_bounds_high(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            _parse_page_ranges("1-20", 10)
        assert exc_info.value.status_code == 400

    def test_out_of_bounds_low(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            _parse_page_ranges("0", 10)
        assert exc_info.value.status_code == 400

    def test_invalid_string(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            _parse_page_ranges("abc", 10)

    def test_empty_spec(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            _parse_page_ranges("", 10)


# ═══════════════════════════════════════════════════════════════════════════
# Integration tests — async httpx.AsyncClient via anyio
# anyio + httpx are already installed (via chromadb dependency)
# ═══════════════════════════════════════════════════════════════════════════

try:
    import httpx
    from fastapi import FastAPI
    from document_tools.router import router as _dt_router

    _int_app = FastAPI()
    _int_app.include_router(_dt_router)
    _transport = httpx.ASGITransport(app=_int_app)
    _INTEG_AVAILABLE = True
except Exception as _setup_err:
    _INTEG_AVAILABLE = False
    _transport = None
    print(f"Integration setup failed: {_setup_err}")


def _pdf_file(data: bytes, filename: str = "test.pdf"):
    return ("file", (filename, io.BytesIO(data), "application/pdf"))


def _multi_pdf_files(datasets: list):
    return [("files", (name, io.BytesIO(data), "application/pdf")) for data, name in datasets]


async def _post(path: str, files=None, data=None):
    import httpx
    async with httpx.AsyncClient(transport=_transport, base_url="http://testserver") as c:
        return await c.post(path, files=files, data=data)


# ── Merge ──────────────────────────────────────────────────────────────────

@pytest.mark.anyio
@pytest.mark.skipif(not _INTEG_AVAILABLE, reason="Integration setup failed")
async def test_merge_two_pdfs():
    p1, p2 = _make_pdf(2), _make_pdf(3)
    r = await _post("/api/document-tools/merge",
                    files=_multi_pdf_files([(p1, "a.pdf"), (p2, "b.pdf")]))
    assert r.status_code == 200
    import PyPDF2
    assert len(PyPDF2.PdfReader(io.BytesIO(r.content)).pages) == 5


@pytest.mark.anyio
@pytest.mark.skipif(not _INTEG_AVAILABLE, reason="Integration setup failed")
async def test_merge_three_pdfs():
    files = _multi_pdf_files([(_make_pdf(1), f"{i}.pdf") for i in range(3)])
    r = await _post("/api/document-tools/merge", files=files)
    assert r.status_code == 200
    import PyPDF2
    assert len(PyPDF2.PdfReader(io.BytesIO(r.content)).pages) == 3


@pytest.mark.anyio
@pytest.mark.skipif(not _INTEG_AVAILABLE, reason="Integration setup failed")
async def test_merge_single_file_rejected():
    r = await _post("/api/document-tools/merge",
                    files=_multi_pdf_files([(_make_pdf(1), "a.pdf")]))
    assert r.status_code == 400


@pytest.mark.anyio
@pytest.mark.skipif(not _INTEG_AVAILABLE, reason="Integration setup failed")
async def test_merge_invalid_file():
    r = await _post("/api/document-tools/merge",
                    files=[("files", ("bad.pdf", io.BytesIO(b"not a pdf"), "application/pdf"))])
    assert r.status_code == 400


# ── Split ──────────────────────────────────────────────────────────────────

@pytest.mark.anyio
@pytest.mark.skipif(not _INTEG_AVAILABLE, reason="Integration setup failed")
async def test_split_every_page():
    r = await _post("/api/document-tools/split",
                    files=[_pdf_file(_make_pdf(3))], data={"mode": "every"})
    assert r.status_code == 200
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        assert len(zf.namelist()) == 3


@pytest.mark.anyio
@pytest.mark.skipif(not _INTEG_AVAILABLE, reason="Integration setup failed")
async def test_split_by_ranges():
    r = await _post("/api/document-tools/split",
                    files=[_pdf_file(_make_pdf(6))],
                    data={"mode": "ranges", "ranges": "1-2,3-4,5-6"})
    assert r.status_code == 200
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        assert len(zf.namelist()) == 3


@pytest.mark.anyio
@pytest.mark.skipif(not _INTEG_AVAILABLE, reason="Integration setup failed")
async def test_split_invalid_mode():
    r = await _post("/api/document-tools/split",
                    files=[_pdf_file(_make_pdf(2))], data={"mode": "invalid"})
    assert r.status_code == 400


# ── Extract ────────────────────────────────────────────────────────────────

@pytest.mark.anyio
@pytest.mark.skipif(not _INTEG_AVAILABLE, reason="Integration setup failed")
async def test_extract_pages():
    r = await _post("/api/document-tools/extract",
                    files=[_pdf_file(_make_pdf(5))], data={"pages": "1,3,5"})
    assert r.status_code == 200
    import PyPDF2
    assert len(PyPDF2.PdfReader(io.BytesIO(r.content)).pages) == 3


@pytest.mark.anyio
@pytest.mark.skipif(not _INTEG_AVAILABLE, reason="Integration setup failed")
async def test_extract_out_of_bounds():
    r = await _post("/api/document-tools/extract",
                    files=[_pdf_file(_make_pdf(3))], data={"pages": "1-10"})
    assert r.status_code == 400


# ── Delete Pages ───────────────────────────────────────────────────────────

@pytest.mark.anyio
@pytest.mark.skipif(not _INTEG_AVAILABLE, reason="Integration setup failed")
async def test_delete_pages():
    r = await _post("/api/document-tools/delete-pages",
                    files=[_pdf_file(_make_pdf(4))], data={"pages": "2,4"})
    assert r.status_code == 200
    import PyPDF2
    assert len(PyPDF2.PdfReader(io.BytesIO(r.content)).pages) == 2


@pytest.mark.anyio
@pytest.mark.skipif(not _INTEG_AVAILABLE, reason="Integration setup failed")
async def test_delete_all_pages_rejected():
    r = await _post("/api/document-tools/delete-pages",
                    files=[_pdf_file(_make_pdf(2))], data={"pages": "1-2"})
    assert r.status_code == 400


# ── Rotate ─────────────────────────────────────────────────────────────────

@pytest.mark.anyio
@pytest.mark.skipif(not _INTEG_AVAILABLE, reason="Integration setup failed")
async def test_rotate_all():
    r = await _post("/api/document-tools/rotate",
                    files=[_pdf_file(_make_pdf(2))], data={"angle": "90", "pages": "all"})
    assert r.status_code == 200
    assert "application/pdf" in r.headers["content-type"]


@pytest.mark.anyio
@pytest.mark.skipif(not _INTEG_AVAILABLE, reason="Integration setup failed")
async def test_rotate_specific_pages():
    r = await _post("/api/document-tools/rotate",
                    files=[_pdf_file(_make_pdf(3))], data={"angle": "180", "pages": "1,3"})
    assert r.status_code == 200


@pytest.mark.anyio
@pytest.mark.skipif(not _INTEG_AVAILABLE, reason="Integration setup failed")
async def test_rotate_invalid_angle():
    r = await _post("/api/document-tools/rotate",
                    files=[_pdf_file(_make_pdf(1))], data={"angle": "45", "pages": "all"})
    assert r.status_code == 400


# ── PDF → Text ─────────────────────────────────────────────────────────────

@pytest.mark.anyio
@pytest.mark.skipif(not _INTEG_AVAILABLE, reason="Integration setup failed")
async def test_pdf_to_text():
    r = await _post("/api/document-tools/pdf-to-text", files=[_pdf_file(_make_pdf(2))])
    assert r.status_code == 200
    assert "text/plain" in r.headers["content-type"]
    assert "Page 1" in r.content.decode("utf-8")


@pytest.mark.anyio
@pytest.mark.skipif(not _INTEG_AVAILABLE, reason="Integration setup failed")
async def test_pdf_to_text_invalid_rejected():
    r = await _post("/api/document-tools/pdf-to-text",
                    files=[("file", ("bad.pdf", io.BytesIO(b"garbage"), "application/pdf"))])
    assert r.status_code == 400


# ── Images → PDF ───────────────────────────────────────────────────────────

@pytest.mark.anyio
@pytest.mark.skipif(not _INTEG_AVAILABLE, reason="Integration setup failed")
async def test_images_to_pdf():
    files = [
        ("files", ("a.png", io.BytesIO(_make_image_bytes("PNG")), "image/png")),
        ("files", ("b.jpg", io.BytesIO(_make_image_bytes("JPEG")), "image/jpeg")),
    ]
    r = await _post("/api/document-tools/images-to-pdf", files=files)
    assert r.status_code == 200
    import PyPDF2
    assert len(PyPDF2.PdfReader(io.BytesIO(r.content)).pages) == 2


@pytest.mark.anyio
@pytest.mark.skipif(not _INTEG_AVAILABLE, reason="Integration setup failed")
async def test_images_to_pdf_invalid_rejected():
    r = await _post("/api/document-tools/images-to-pdf",
                    files=[("files", ("bad.png", io.BytesIO(b"not an image"), "image/png"))])
    assert r.status_code == 400


# ── Compress ───────────────────────────────────────────────────────────────

@pytest.mark.anyio
@pytest.mark.skipif(not _INTEG_AVAILABLE, reason="Integration setup failed")
async def test_compress_low():
    r = await _post("/api/document-tools/compress",
                    files=[_pdf_file(_make_pdf(2))], data={"level": "low"})
    assert r.status_code == 200
    assert "x-original-size" in r.headers
    assert "x-output-size" in r.headers
    assert "x-reduction-pct" in r.headers


@pytest.mark.anyio
@pytest.mark.skipif(not _INTEG_AVAILABLE, reason="Integration setup failed")
async def test_compress_medium():
    r = await _post("/api/document-tools/compress",
                    files=[_pdf_file(_make_pdf_with_meta())], data={"level": "medium"})
    assert r.status_code == 200


@pytest.mark.anyio
@pytest.mark.skipif(not _INTEG_AVAILABLE, reason="Integration setup failed")
async def test_compress_high():
    r = await _post("/api/document-tools/compress",
                    files=[_pdf_file(_make_pdf(3))], data={"level": "high"})
    assert r.status_code == 200


@pytest.mark.anyio
@pytest.mark.skipif(not _INTEG_AVAILABLE, reason="Integration setup failed")
async def test_compress_invalid_level():
    r = await _post("/api/document-tools/compress",
                    files=[_pdf_file(_make_pdf(1))], data={"level": "extreme"})
    assert r.status_code == 400


# ── Metadata ───────────────────────────────────────────────────────────────

@pytest.mark.anyio
@pytest.mark.skipif(not _INTEG_AVAILABLE, reason="Integration setup failed")
async def test_view_metadata():
    r = await _post("/api/document-tools/metadata",
                    files=[_pdf_file(_make_pdf_with_meta(title="MyDoc", author="Alice"))])
    assert r.status_code == 200
    j = r.json()
    assert j["title"] == "MyDoc"
    assert j["author"] == "Alice"
    assert "total_pages" in j


@pytest.mark.anyio
@pytest.mark.skipif(not _INTEG_AVAILABLE, reason="Integration setup failed")
async def test_remove_metadata():
    r = await _post("/api/document-tools/remove-metadata",
                    files=[_pdf_file(_make_pdf_with_meta(title="Remove Me"))])
    assert r.status_code == 200
    assert "application/pdf" in r.headers["content-type"]
    import PyPDF2
    raw = PyPDF2.PdfReader(io.BytesIO(r.content)).metadata or {}
    assert not raw.get("/Title")


@pytest.mark.anyio
@pytest.mark.skipif(not _INTEG_AVAILABLE, reason="Integration setup failed")
async def test_metadata_invalid_pdf():
    r = await _post("/api/document-tools/metadata",
                    files=[("file", ("x.pdf", io.BytesIO(b"not pdf"), "application/pdf"))])
    assert r.status_code == 400
