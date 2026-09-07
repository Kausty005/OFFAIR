"""
rag/ingest.py
Document ingestion pipeline for the local knowledge base.
Parses documents, chunks text, generates embeddings, stores in ChromaDB.
"""

import hashlib
import os
import sys
from pathlib import Path
from typing import Optional, Callable

_base = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _base)

from security.audit import log
from security.permissions import access_metadata
from document.pdf_processor import process_pdf, extract_pages_digital
from document.ocr import ocr_pdf_pages
from document.cleaner import clean_text, detect_section
from rag.embeddings import embed_batch
from rag.vector_store import add_documents, get_collection_stats


import yaml
_cfg_path = os.path.join(_base, "config", "settings.yaml")
with open(_cfg_path) as f:
    _settings = yaml.safe_load(f)

CHUNK_SIZE = _settings["document"]["chunk_size"]
CHUNK_OVERLAP = _settings["document"]["chunk_overlap"]


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks."""
    if not text.strip():
        return []
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def _doc_id(source: str, page: int, chunk_idx: int) -> str:
    """Generate a unique, stable document chunk ID."""
    raw = f"{source}:{page}:{chunk_idx}"
    return hashlib.md5(raw.encode()).hexdigest()


def ingest_pdf(
    pdf_path: str | Path,
    progress_callback: Optional[Callable[[str], None]] = None,
    security_metadata: Optional[dict] = None,
) -> dict:
    """
    Full ingestion pipeline for a PDF file.
    1. Parse PDF
    2. OCR scanned pages
    3. Chunk text
    4. Embed chunks
    5. Store in vector DB

    Returns ingestion summary.
    """
    pdf_path = Path(pdf_path)
    source_name = pdf_path.name
    sm = security_metadata or {}
    sec_meta = access_metadata(
        department=sm.get("department", ""),
        classification=sm.get("classification", "internal"),
        allowed_roles=sm.get("allowed_roles", ["admin", "engineer", "employee"]),
        uploaded_by=sm.get("uploaded_by", ""),
        min_role_level=sm.get("min_role_level"),
        uploaded_at=sm.get("uploaded_at", ""),
    )
    log("INGEST_START", source=source_name, uploaded_by=sec_meta.get("uploaded_by"))

    def _progress(msg: str):
        if progress_callback:
            progress_callback(msg)
        log("INGEST_PROGRESS", msg=msg)

    _progress(f"Parsing {source_name}...")
    pdf_data = process_pdf(pdf_path)

    if pdf_data.get("error"):
        return {"error": pdf_data["error"], "chunks": 0}

    pages = pdf_data["pages"]

    # Run OCR on scanned pages
    if pdf_data.get("needs_ocr"):
        _progress(f"Running OCR on {len(pages)} pages...")
        pages = ocr_pdf_pages(pages)

    # Collect all text with page metadata
    _progress("Chunking text...")
    all_chunks = []
    for page in pages:
        text = clean_text(page.get("text", "") or page.get("ocr_text", ""))
        if not text.strip():
            continue
        chunks = _chunk_text(text)
        section = detect_section(text)
        for ci, chunk in enumerate(chunks):
            all_chunks.append({
                "id": _doc_id(source_name, page["page_num"], ci),
                "text": chunk,
                "metadata": {
                    "source": source_name,
                    "page": str(page["page_num"]),
                    "chunk_idx": ci,
                    "path": str(pdf_path),
                    "type": "pdf",
                    "section": section,
                    **sec_meta,
                },
            })

    if not all_chunks:
        _progress("No text content extracted from PDF.")
        return {"error": "No text content found", "chunks": 0}

    _progress(f"Embedding {len(all_chunks)} chunks (this may take a moment)...")
    texts = [c["text"] for c in all_chunks]
    embeddings = embed_batch(texts)

    _progress("Storing in local vector database...")
    ok = add_documents(
        ids=[c["id"] for c in all_chunks],
        embeddings=embeddings,
        texts=texts,
        metadatas=[c["metadata"] for c in all_chunks],
    )

    summary = {
        "source": source_name,
        "pages": len(pages),
        "chunks": len(all_chunks),
        "is_scanned": pdf_data.get("is_scanned", False),
        "stored": ok,
        "uploaded_by": sec_meta.get("uploaded_by", ""),
        "allowed_roles": sec_meta.get("allowed_roles", []),
    }
    log("INGEST_DONE", **summary)
    _progress(f"Ingested {len(all_chunks)} chunks from {source_name}")
    return summary


def ingest_text(
    text: str,
    source_name: str,
    progress_callback: Optional[Callable[[str], None]] = None,
    security_metadata: Optional[dict] = None,
) -> dict:
    """Ingest plain text content into the knowledge base."""
    def _progress(msg: str):
        if progress_callback:
            progress_callback(msg)

    _progress(f"Chunking text from {source_name}...")
    sm = security_metadata or {}
    sec_meta = access_metadata(
        department=sm.get("department", ""),
        classification=sm.get("classification", "internal"),
        allowed_roles=sm.get("allowed_roles", ["admin", "engineer", "employee"]),
        uploaded_by=sm.get("uploaded_by", ""),
        min_role_level=sm.get("min_role_level"),
        uploaded_at=sm.get("uploaded_at", ""),
    )
    chunks_text = _chunk_text(clean_text(text))
    if not chunks_text:
        return {"error": "Empty text", "chunks": 0}

    all_chunks = []
    for ci, chunk in enumerate(chunks_text):
        all_chunks.append({
            "id": _doc_id(source_name, 0, ci),
            "text": chunk,
            "metadata": {
                "source": source_name,
                "page": "1",
                "chunk_idx": ci,
                "type": "text",
                **sec_meta,
            },
        })

    _progress(f"Embedding {len(all_chunks)} chunks...")
    texts = [c["text"] for c in all_chunks]
    embeddings = embed_batch(texts)

    ok = add_documents(
        ids=[c["id"] for c in all_chunks],
        embeddings=embeddings,
        texts=texts,
        metadatas=[c["metadata"] for c in all_chunks],
    )
    return {"source": source_name, "chunks": len(all_chunks), "stored": ok}


def ingest_docx(
    docx_path: str | Path,
    progress_callback: Optional[Callable[[str], None]] = None,
    security_metadata: Optional[dict] = None,
) -> dict:
    """Ingest a DOCX file."""
    try:
        from docx import Document
        doc = Document(str(docx_path))
        text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        return ingest_text(
            text,
            Path(docx_path).name,
            progress_callback,
            security_metadata=security_metadata,
        )
    except Exception as e:
        return {"error": str(e), "chunks": 0}


def ingest_file(
    file_path: str | Path,
    progress_callback: Optional[Callable[[str], None]] = None,
    security_metadata: Optional[dict] = None,
) -> dict:
    """
    Ingest a single file (.pdf, .docx, .txt, .md, .csv, .json) into the knowledge base.
    """
    p = Path(file_path)
    if not p.exists():
        return {"error": f"File not found: {p}", "chunks": 0}

    ext = p.suffix.lower()
    if ext == ".pdf":
        return ingest_pdf(
            p,
            progress_callback=progress_callback,
            security_metadata=security_metadata,
        )
    elif ext == ".docx":
        return ingest_docx(
            p,
            progress_callback=progress_callback,
            security_metadata=security_metadata,
        )
    elif ext in (".txt", ".md", ".csv", ".json", ".log"):
        text = p.read_text(encoding="utf-8", errors="replace")
        return ingest_text(
            text,
            p.name,
            progress_callback=progress_callback,
            security_metadata=security_metadata,
        )
    else:
        return {"error": f"Unsupported file type: {ext}", "chunks": 0}


def ingest_directory(
    directory_path: str | Path,
    progress_callback: Optional[Callable[[str], None]] = None,
    security_metadata: Optional[dict] = None,
) -> dict:
    """
    Scan a directory and ingest all supported document files into the knowledge base.
    Returns summary of total files processed and chunks stored.
    """
    d = Path(directory_path)
    if not d.exists() or not d.is_dir():
        return {"error": f"Directory not found: {d}", "total_files": 0, "total_chunks": 0}

    valid_extensions = {".pdf", ".docx", ".txt", ".md", ".csv", ".json", ".log"}
    files = [f for f in d.iterdir() if f.is_file() and f.suffix.lower() in valid_extensions]

    results = []
    total_chunks = 0

    def _prog(msg: str):
        if progress_callback:
            progress_callback(msg)
        log("INGEST_DIR_PROGRESS", msg=msg)

    _prog(f"Starting ingestion of {len(files)} documents in {d.name}...")

    for f in files:
        _prog(f"Processing {f.name}...")
        res = ingest_file(
            f,
            progress_callback=progress_callback,
            security_metadata=security_metadata,
        )
        chunks = res.get("chunks", 0)
        total_chunks += chunks
        results.append({
            "file": f.name,
            "chunks": chunks,
            "stored": res.get("stored", False),
            "error": res.get("error"),
        })

    summary = {
        "directory": str(d),
        "total_files": len(files),
        "total_chunks": total_chunks,
        "files": results,
    }
    log("INGEST_DIR_DONE", **summary)
    _prog(f"Directory ingestion complete: {len(files)} files, {total_chunks} total chunks.")
    return summary
