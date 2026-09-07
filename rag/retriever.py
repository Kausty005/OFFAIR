"""
rag/retriever.py
RAG retrieval — semantic search + LLM answer generation with source citations.
"""

import os
import sys
from typing import Optional

_base = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _base)

from security.audit import log
from security.permissions import User
from rag.embeddings import embed_text
from rag.vector_store import search, keyword_search, get_collection_stats
from rag.reranker import rerank
from models.model_registry import get_available_model
import models.ollama_client as ollama


def retrieve(
    query: str,
    top_k: int = 5,
    user: Optional[User] = None,
    authorized_only: bool = False,
) -> list[dict]:
    """
    Retrieve relevant chunks from the knowledge base for a query.
    Returns list of {text, document, page, score} dicts.
    """
    log("RAG_SEARCH", query=query[:100], top_k=top_k)
    query_vec = embed_text(query)
    vector_results = search(
        query_vec,
        top_k=top_k,
        query_text=query,
        user=user,
        authorized_only=authorized_only,
    )
    keyword_results = keyword_search(
        query,
        top_k=max(top_k, 10),
        user=user,
        authorized_only=authorized_only,
    )

    # Reciprocal rank fusion makes semantic and exact identifier matches
    # contribute without requiring either score scale to match.
    fused: dict[str, dict] = {}
    for rank, result in enumerate(vector_results + keyword_results, start=1):
        item = fused.setdefault(result["id"], dict(result))
        item["hybrid_score"] = item.get("hybrid_score", 0.0) + 1.0 / (60 + rank)
        item["vector_score"] = item.get("vector_score", result.get("score", 0.0))
        item["keyword_score"] = max(item.get("keyword_score", 0.0), result.get("score", 0.0))

    results = sorted(fused.values(), key=lambda item: item["hybrid_score"], reverse=True)
    return rerank(query, results, top_k=top_k)


def answer_with_rag(
    query: str,
    top_k: int = 5,
    model: Optional[str] = None,
    user: Optional[User] = None,
    authorized_only: bool = False,
) -> dict:
    """
    Full RAG pipeline: retrieve relevant chunks + generate grounded answer.

    Returns:
        {
            "answer": str,
            "sources": [...],
            "retrieved_chunks": [...],
            "model": str,
            "rag_used": bool,
        }
    """
    model_name = model or get_available_model("general") or "llama3.1:8b"

    # Step 1: Retrieve
    chunks = retrieve(
        query,
        top_k=top_k,
        user=user,
        authorized_only=authorized_only,
    )

    if not chunks:
        # Never allow the model to answer from its pretrained knowledge.
        log(
            "RAG_NO_RESULTS",
            query=query[:100],
            user_id=user.user_id if user else None,
            role=user.normalized_role if user else None,
            authorized_only=authorized_only,
        )
        return {
            "answer": "I couldn't find this information in the authorized knowledge base.",
            "sources": [],
            "retrieved_chunks": [],
            "model": model_name,
            "rag_used": False,
            "abstained": True,
            "warning": "No sufficiently relevant authorized context was found.",
        }

    # Step 2: Build context from retrieved chunks
    context_parts = []
    sources = []
    for i, chunk in enumerate(chunks):
        src = chunk.get("document", "Document")
        page = chunk.get("page", "")
        context_parts.append(
            f"[Source {i+1}: {src}{f' — Page {page}' if page else ''}]\n{chunk['text']}"
        )
        sources.append({
            "index": i + 1,
            "document": src,
            "page": page,
            "score": chunk.get("score", 0),
            "text": chunk["text"][:300],
        })

    context = "\n\n".join(context_parts)

    # Step 3: Generate grounded answer
    prompt = f"""Using ONLY the information from the provided context, answer the following question.
If the context does not contain sufficient information, say so clearly.
Always cite your sources using [Source N] notation.

CONTEXT:
{context}

QUESTION:
{query}

ANSWER:"""

    system = """You are an expert industrial knowledge assistant. 
Your answers must be grounded in the provided document context.
Always cite sources. Do not fabricate information."""

    log("RAG_GENERATE", model=model_name, chunks=len(chunks))
    answer = ollama.generate(
        model=model_name,
        prompt=prompt,
        system=system,
        temperature=0.05,
        max_tokens=1024,
    )

    return {
        "answer": answer,
        "sources": sources,
        "retrieved_chunks": chunks,
        "model": model_name,
        "rag_used": True,
        "abstained": False,
    }


def get_kb_status() -> dict:
    """Return knowledge base status for health check."""
    stats = get_collection_stats()
    return {
        "available": stats.get("available", False),
        "document_chunks": stats.get("count", 0),
        "local": True,
        "cloud": False,
        "collection": stats.get("collection", ""),
    }
