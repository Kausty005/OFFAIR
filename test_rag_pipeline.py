"""
Quick diagnostic test for the RAG pipeline and document generation.
"""
import sys
sys.path.insert(0, '.')

def test_rag():
    print("=" * 60)
    print("TEST 1: RAG Retrieval")
    print("=" * 60)
    from rag.vector_store import get_collection_stats
    stats = get_collection_stats()
    print(f"KB stats: {stats}")

    from rag.retriever import retrieve
    q = "what is the maintenance procedure for pump"
    results = retrieve(q)
    print(f"Query: {q!r}")
    print(f"Results count: {len(results)}")
    for r in results:
        print(f"  doc={r.get('document')}, score={r.get('score')}, rerank={r.get('rerank_score')}")
        print(f"  text={r.get('text', '')[:80]}")


def test_rag_general_query():
    print("=" * 60)
    print("TEST 2: General Chat RAG Flow")
    print("=" * 60)
    from rag.interface import retrieve_context
    q = "What is an SOP?"
    chunks = retrieve_context(q, user_context=None, top_k=5)
    print(f"Query: {q!r}")
    print(f"Chunks returned: {len(chunks)}")
    for c in chunks:
        print(f"  score={c.get('score')}, rerank={c.get('rerank_score')}, doc={c.get('document')}")


def test_docx():
    print("=" * 60)
    print("TEST 3: Word Document Generation")
    print("=" * 60)
    from tools.docx_generator import create_document_from_markdown, docx_available
    print(f"DOCX available: {docx_available()}")
    if docx_available():
        result = create_document_from_markdown(
            "# Test Report\n\nThis is a test document.\n\n## Section 1\n\nContent here.",
            "Test Document",
            "workspace/outputs/test_doc.docx"
        )
        print(f"Result: {result}")


def test_pdf():
    print("=" * 60)
    print("TEST 4: PDF Generation")
    print("=" * 60)
    from tools.pdf_generator import create_pdf_from_markdown, pdf_available
    print(f"PDF available: {pdf_available()}")
    if pdf_available():
        result = create_pdf_from_markdown(
            "# Test PDF\n\nThis is a test PDF.\n\n## Section 1\n\nContent here.",
            "Test PDF",
            "workspace/outputs/test_doc.pdf"
        )
        print(f"Result: {result}")


def test_pptx():
    print("=" * 60)
    print("TEST 5: PowerPoint Generation")
    print("=" * 60)
    from tools.pptx_generator import create_presentation_from_markdown, pptx_available
    print(f"PPTX available: {pptx_available()}")
    if pptx_available():
        content = """### Test Presentation
*OffAir AI Test*

---

#### Slide 1: Introduction
- Point 1
- Point 2
- Point 3

---

#### Slide 2: Details
- Detail 1
- Detail 2
- Detail 3
"""
        result = create_presentation_from_markdown(
            content,
            default_title="Test Presentation",
            output_path="workspace/outputs/test_pptx.pptx"
        )
        print(f"Result: {result}")


def test_embeddings():
    print("=" * 60)
    print("TEST 6: Embedding Model")
    print("=" * 60)
    from rag.embeddings import embed_text, get_embedding_model_name
    model = get_embedding_model_name()
    print(f"Embedding model: {model}")
    try:
        vec = embed_text("test text for embeddings")
        print(f"Embedding dims: {len(vec)}, non-zero: {sum(1 for v in vec if v != 0.0)}")
    except Exception as e:
        print(f"Embedding error: {e}")


def test_ingest():
    print("=" * 60)
    print("TEST 7: Re-ingest knowledge_base")
    print("=" * 60)
    from rag.ingest import ingest_directory
    result = ingest_directory("knowledge_base", progress_callback=print)
    print(f"Ingest result: {result}")


if __name__ == "__main__":
    test_rag()
    test_rag_general_query()
    test_embeddings()
    test_docx()
    test_pdf()
    test_pptx()
