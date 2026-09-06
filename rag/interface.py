"""
rag/interface.py
Modular RAG Boundary Interface.

This module provides a clean abstraction layer between the Agent / Orchestration
system and the Knowledge Retrieval pipeline.

NOTE FOR OTHER TEAMS:
This interface is the agreed-upon contract for RAG retrieval.
The underlying implementation may be upgraded to Qdrant, hybrid search (dense + BM25),
reranking, or fine-grained RBAC/permission filtering without modifying any agent code.
"""

from typing import Any, Optional
from security.audit import log
from rag.retriever import retrieve as _default_retrieve


def retrieve_context(
    query: str,
    user_context: Optional[dict[str, Any]] = None,
    filters: Optional[dict[str, Any]] = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    Retrieve authorized, ranked knowledge chunks for a query.

    Args:
        query: The user or agent search query string.
        user_context: Optional security/RBAC context (e.g., {"user_id": ..., "role": ..., "permissions": [...]}).
        filters: Optional metadata filters (e.g., {"document_type": "sop", "tags": [...]}).
        top_k: Maximum number of relevant chunks to return.

    Returns:
        List of chunks, each structured as:
        {
            "text": str,
            "document": str,
            "page": int | str,
            "score": float,
            "metadata": dict (optional)
        }
    """
    log(
        "RAG_INTERFACE_QUERY",
        query=query[:100],
        top_k=top_k,
        has_user_context=bool(user_context),
        has_filters=bool(filters),
    )

    # Future team integration point:
    # 1. Enforce RBAC / document authorization against user_context
    # 2. Apply metadata filters
    # 3. Perform hybrid dense + sparse retrieval (Qdrant / BM25)
    # 4. Apply cross-encoder reranking
    # For now, calls the validated local vector retriever:
    chunks = _default_retrieve(query=query, top_k=top_k)

    return chunks
