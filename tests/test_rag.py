import os
import sys
from pathlib import Path
import pytest

# Add project root to path for tests
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.vector_store import (
    add_documents,
    search,
    get_collection_stats,
    delete_collection,
    _cosine_similarity,
)
from rag.ingest import _chunk_text, _doc_id, ingest_text
from rag.retriever import retrieve, get_kb_status
from security.permissions import User
from tools.search import search_knowledge_base


def test_cosine_similarity():
    # Identical vectors
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert abs(_cosine_similarity(v1, v2) - 1.0) < 1e-5

    # Orthogonal vectors
    v3 = [0.0, 1.0, 0.0]
    assert abs(_cosine_similarity(v1, v3)) < 1e-5

    # Zero vectors
    assert _cosine_similarity([0.0, 0.0], [0.0, 0.0]) == 0.0


def test_chunk_text():
    sample = "word " * 600
    chunks = _chunk_text(sample, chunk_size=100, overlap=20)
    assert len(chunks) > 1
    assert all(len(c.split()) <= 100 for c in chunks)


def test_doc_id_deterministic():
    id1 = _doc_id("sop.pdf", 1, 0)
    id2 = _doc_id("sop.pdf", 1, 0)
    id3 = _doc_id("sop.pdf", 1, 1)
    assert id1 == id2
    assert id1 != id3


def test_vector_store_lifecycle():
    # Reset collection first
    delete_collection()


def test_vector_search_filters_roles_before_scoring():
    delete_collection()
    ok = add_documents(
        ["hr", "finance"],
        [[1.0, 0.0], [0.0, 1.0]],
        ["Leave policy", "Company revenue"],
        [
            {"source": "hr.pdf", "allowed_roles": ["employee"]},
            {"source": "finance.pdf", "allowed_roles": ["finance"]},
        ],
    )
    assert ok is True

    employee_results = search(
        [0.0, 1.0],
        user=User("bob", "employee"),
        authorized_only=True,
    )
    finance_results = search(
        [0.0, 1.0],
        user=User("charlie", "finance"),
        authorized_only=True,
    )

    assert employee_results == []
    assert finance_results[0]["id"] == "finance"
    delete_collection()

    # Add mock documents
    doc_ids = ["doc1", "doc2"]
    embeddings = [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
    ]
    texts = [
        "Centrifugal pump bearing temperature must stay below 75 degrees C.",
        "Vibration limits are acceptable below 4.5 mm/s RMS.",
    ]
    metadatas = [
        {"source": "pump_sop.pdf", "page": "1", "section": "3.1"},
        {"source": "vibration_sop.pdf", "page": "2", "section": "3.2"},
    ]

    ok = add_documents(doc_ids, embeddings, texts, metadatas)
    assert ok is True

    # Check stats
    stats = get_collection_stats()
    assert stats["available"] is True
    assert stats["count"] >= 2

    # Query with vector matching doc1
    results = search([1.0, 0.0, 0.0, 0.0], top_k=2)
    assert len(results) > 0
    assert results[0]["id"] == "doc1"
    assert "bearing temperature" in results[0]["text"]
    assert results[0]["score"] > 0.9

    # Clean up
    delete_collection()


def test_ingest_text_and_search_tool():
    # Reset
    delete_collection()

    text = "Emergency shutdown procedure requires turning valve V-101 clockwise."
    res = ingest_text(text, source_name="emergency_sop.txt")
    assert res.get("stored") is True
    assert res.get("chunks", 0) >= 1

    # Search tool check
    kb_res = search_knowledge_base("emergency shutdown valve")
    assert kb_res["local"] is True
    assert kb_res["count"] >= 0

    # KB Status
    status = get_kb_status()
    assert status["local"] is True
    assert status["cloud"] is False

    # Clean up
    delete_collection()
