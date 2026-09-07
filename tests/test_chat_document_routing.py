"""
tests/test_chat_document_routing.py
Comprehensive test suite verifying:
1. Intent classification for all deterministic Document Tools.
2. Separation of DOCUMENT_OPERATION from VISION_ANALYSIS and DOCUMENT_ANALYSIS.
3. Attachment presence does NOT falsely trigger VISION_ANALYSIS.
4. Real end-to-end execution of merge_pdf and images_to_pdf without Ollama/Vision models.
5. Multi-step compound document pipeline execution (merge + compress).
"""

import io
from pathlib import Path
import pytest
import fitz
from PIL import Image

from agent.task_classifier import classify_task, TaskType
from router.model_router import classify as model_router_classify
from document_tools.chat_resolver import resolve_explicit_document_operation, is_explicit_vision_request
from agent.agent import Agent


def _create_dummy_pdf(num_pages: int = 1, text: str = "Test PDF Page") -> bytes:
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 100), f"{text} - Page {i+1}")
    b = doc.tobytes()
    doc.close()
    return b


def _create_dummy_png(color=(255, 0, 0)) -> bytes:
    img = Image.new("RGB", (100, 100), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ─── 1. Intent Table & Classification Tests ─────────────────────────────────

def test_intent_merge_pdf_variations():
    queries = [
        "merge these pdf",
        "merge these two pdf",
        "merge these 2 pdf",
        "merge these PDFs",
        "combine these pdf files",
        "join these PDFs",
        "merge 2 pdf",
        "combine decrypted.pdf and cropped.pdf",
    ]
    for q in queries:
        res = classify_task(query=q, uploaded_files=["decrypted.pdf", "cropped.pdf"])
        assert res.primary_task == TaskType.DOCUMENT_OPERATION, f"Failed for query: {q}"
        assert "merge_pdf" in res.selected_tools, f"Failed for query: {q}"
        assert res.selected_model == "NONE"


def test_intent_images_to_pdf():
    queries = [
        "make pdf",
        "make a pdf",
        "make PDF from these images",
        "convert these images to PDF",
        "combine these images into a PDF",
        "images to pdf",
    ]
    for q in queries:
        res = classify_task(query=q, uploaded_files=["6-Picsart-AI-ImageEnhancer.png", "6.png"])
        assert res.primary_task == TaskType.DOCUMENT_OPERATION, f"Failed for query: {q}"
        assert "images_to_pdf" in res.selected_tools, f"Failed for query: {q}"


def test_intent_other_document_tools():
    test_cases = [
        ("split this pdf", "split_pdf"),
        ("split PDF", "split_pdf"),
        ("split after page 5", "split_pdf"),
        ("extract pages 1, 3 and 5", "extract_pages"),
        ("extract page 4", "extract_pages"),
        ("take pages 2-6", "extract_pages"),
        ("delete page 3", "delete_pages"),
        ("remove pages 4 and 5", "delete_pages"),
        ("rotate this PDF", "rotate_pdf"),
        ("rotate page 2 by 90 degrees", "rotate_pdf"),
        ("crop this PDF", "crop_pdf"),
        ("resize this PDF", "resize_pdf"),
        ("add a blank page", "add_blank_page"),
        ("duplicate page 3", "duplicate_page"),
        ("compress this PDF", "compress_pdf"),
        ("reduce PDF size", "compress_pdf"),
        ("convert PDF to images", "pdf_to_images"),
        ("convert this PDF to PNG", "pdf_to_images"),
        ("turn this PDF into JPG", "pdf_to_images"),
        ("extract text from this PDF", "pdf_to_text"),
        ("OCR this PDF", "ocr_pdf"),
        ("OCR this scanned document", "ocr_pdf"),
        ("extract text using OCR", "ocr_pdf"),
        ("remove metadata", "strip_metadata"),
        ("strip PDF metadata", "strip_metadata"),
    ]
    for query, expected_tool in test_cases:
        res = classify_task(query=query, uploaded_files=["sample.pdf"])
        assert res.primary_task == TaskType.DOCUMENT_OPERATION, f"Failed for query: {query}"
        assert expected_tool in res.selected_tools, f"Expected {expected_tool} for '{query}', got {res.selected_tools}"


def test_intent_explicit_vision_request():
    queries = [
        "analyze this image and identify defects",
        "inspect this image",
        "what is shown in this image?",
        "detect objects in this image",
        "analyze the visual content",
    ]
    for q in queries:
        res = classify_task(query=q, uploaded_files=["image.png"])
        assert res.primary_task == TaskType.VISION_ANALYSIS, f"Failed for vision query: {q}"


def test_intent_document_analysis():
    queries = [
        "analyze this PDF for safety issues",
        "Analyze this inspection document and identify safety findings.",
        "Extract measurements and compare them with the SOP.",
        "inspect this report for safety defects",
    ]
    for q in queries:
        res = classify_task(query=q, uploaded_files=["inspection.pdf"])
        assert res.primary_task == TaskType.DOCUMENT_ANALYSIS, f"Failed for document analysis query: {q}"


def test_general_chat_with_attachments_not_hijacked():
    # PDF attachment with general question must NOT become DOCUMENT_ANALYSIS or VISION_ANALYSIS
    res_pdf = classify_task(query="What is an operating system?", uploaded_files=["document.pdf"])
    assert res_pdf.primary_task == TaskType.GENERAL_CHAT

    # Image attachment with general question must NOT become VISION_ANALYSIS
    res_img = classify_task(query="Explain the concept of entropy.", uploaded_files=["picture.png"])
    assert res_img.primary_task == TaskType.GENERAL_CHAT


def test_compound_document_pipeline_intent():
    res = classify_task(
        query="Merge these two PDFs and then compress the result.",
        uploaded_files=["a.pdf", "b.pdf"],
    )
    assert res.primary_task == TaskType.DOCUMENT_OPERATION
    assert res.is_multi_step is True
    assert res.selected_tools == ["merge_pdf", "compress_pdf"]


# ─── 2. Model Router Classify Function Tests ─────────────────────────────────

def test_model_router_classify_document_operation():
    dec = model_router_classify("merge these 2 pdf", has_pdf=True)
    assert dec.task_type == "document_operation"
    assert dec.selected_model == "NONE"
    assert dec.selected_role == "document_tools"


def test_model_router_classify_images_to_pdf():
    dec = model_router_classify("make pdf", has_image=True)
    assert dec.task_type == "document_operation"
    assert dec.selected_model == "NONE"


def test_model_router_classify_image_attachment_without_vision_intent():
    # Having an image attached without vision keywords must NOT route to vision
    dec = model_router_classify("Write python code to sort an array", has_image=True)
    assert dec.task_type == "coding"


# ─── 3. End-to-End Real Execution Tests ──────────────────────────────────────

def test_e2e_merge_pdf_real_execution(tmp_path):
    # Setup test PDFs in workspace/uploads
    uploads_dir = Path("workspace/uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)

    pdf1_bytes = _create_dummy_pdf(num_pages=2, text="Doc One")
    pdf2_bytes = _create_dummy_pdf(num_pages=3, text="Doc Two")

    file1 = uploads_dir / "decrypted.pdf"
    file2 = uploads_dir / "cropped.pdf"

    file1.write_bytes(pdf1_bytes)
    file2.write_bytes(pdf2_bytes)

    agent = Agent()
    state = agent.run("merge these 2 pdf", uploaded_files=[str(file1), str(file2)])

    assert state.task_type == TaskType.DOCUMENT_OPERATION
    assert state.selected_model == "NONE"
    assert state.verified is True

    # Output file verification
    assert len(state.output_files) >= 1
    out_file = Path(state.output_files[-1])
    assert out_file.exists()
    assert out_file.stat().st_size > 0

    # Verify merged PDF validity and exact page count (2 + 3 = 5 pages)
    doc = fitz.open(str(out_file))
    assert len(doc) == 5
    doc.close()

    # Verify chat output format
    assert "✓ PDFs merged successfully." in state.final_output
    assert "decrypted.pdf" in state.final_output
    assert "cropped.pdf" in state.final_output
    assert "Multi-Step Execution Summary" not in state.final_output
    assert "SOP Grounding" not in state.final_output


def test_e2e_images_to_pdf_real_execution():
    uploads_dir = Path("workspace/uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)

    img1_bytes = _create_dummy_png(color=(255, 0, 0))
    img2_bytes = _create_dummy_png(color=(0, 255, 0))

    img1 = uploads_dir / "6-Picsart-AI-ImageEnhancer.png"
    img2 = uploads_dir / "6.png"

    img1.write_bytes(img1_bytes)
    img2.write_bytes(img2_bytes)

    agent = Agent()
    state = agent.run("make pdf", uploaded_files=[str(img1), str(img2)])

    assert state.task_type == TaskType.DOCUMENT_OPERATION
    assert state.verified is True
    assert len(state.output_files) >= 1

    out_file = Path(state.output_files[-1])
    assert out_file.exists()

    doc = fitz.open(str(out_file))
    assert len(doc) == 2
    doc.close()

    assert "✓ PDF created successfully." in state.final_output
    assert "6-Picsart-AI-ImageEnhancer.png" in state.final_output
    assert "6.png" in state.final_output


# ─── 4. User Test Matrix Verification ────────────────────────────────────────

def test_matrix_all_14_scenarios():
    matrix = [
        # 1. merge two PDFs
        ("merge two PDFs", ["a.pdf", "b.pdf"], TaskType.DOCUMENT_OPERATION, "merge_pdf"),
        # 2. merge three PDFs
        ("merge three PDFs", ["a.pdf", "b.pdf", "c.pdf"], TaskType.DOCUMENT_OPERATION, "merge_pdf"),
        # 3. images → PDF
        ("convert these images to PDF", ["1.png", "2.png"], TaskType.DOCUMENT_OPERATION, "images_to_pdf"),
        # 4. PDF → PNG
        ("convert this PDF to PNG", ["doc.pdf"], TaskType.DOCUMENT_OPERATION, "pdf_to_images"),
        # 5. PDF → JPG
        ("turn this PDF into JPG", ["doc.pdf"], TaskType.DOCUMENT_OPERATION, "pdf_to_images"),
        # 6. split PDF
        ("split this PDF", ["doc.pdf"], TaskType.DOCUMENT_OPERATION, "split_pdf"),
        # 7. extract pages
        ("extract pages 1, 3 and 5", ["doc.pdf"], TaskType.DOCUMENT_OPERATION, "extract_pages"),
        # 8. rotate PDF
        ("rotate this PDF", ["doc.pdf"], TaskType.DOCUMENT_OPERATION, "rotate_pdf"),
        # 9. compress PDF
        ("compress this PDF", ["doc.pdf"], TaskType.DOCUMENT_OPERATION, "compress_pdf"),
        # 10. OCR scanned PDF
        ("OCR this scanned PDF", ["scanned.pdf"], TaskType.DOCUMENT_OPERATION, "ocr_pdf"),
        # 11. analyze image
        ("analyze this image and identify defects", ["photo.png"], TaskType.VISION_ANALYSIS, None),
        # 12. analyze PDF
        ("analyze this PDF for safety issues", ["report.pdf"], TaskType.DOCUMENT_ANALYSIS, None),
        # 13. general chat with PDF attachment
        ("what is the capital of France?", ["manual.pdf"], TaskType.GENERAL_CHAT, None),
        # 14. general chat with image attachment
        ("explain quantum computing", ["diagram.png"], TaskType.GENERAL_CHAT, None),
    ]

    for idx, (query, files, expected_task, expected_tool) in enumerate(matrix, 1):
        res = classify_task(query=query, uploaded_files=files)
        assert res.primary_task == expected_task, (
            f"Matrix test #{idx} failed: query '{query}' got task '{res.primary_task}', expected '{expected_task}'"
        )
        if expected_tool:
            assert expected_tool in res.selected_tools, (
                f"Matrix test #{idx} failed: query '{query}' got tools '{res.selected_tools}', expected '{expected_tool}'"
            )

