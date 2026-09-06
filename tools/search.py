"""
tools/search.py
Knowledge base search tool — the agent's interface to RAG retrieval.
Wraps retriever.py with structured output for agent consumption.
"""

import os
import sys
from typing import Optional

_base = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _base)

from rag.retriever import retrieve, answer_with_rag
from security.audit import log


def search_knowledge_base(query: str, top_k: int = 5) -> dict:
    """
    Search the local knowledge base for passages relevant to a query.

    Returns:
        {
            "query": str,
            "results": [{text, document, page, score}, ...],
            "count": int,
            "local": True,
        }
    """
    log("TOOL_CALL", tool="search_knowledge_base", query=query[:100])
    results = retrieve(query, top_k=top_k)
    return {
        "query": query,
        "results": results,
        "count": len(results),
        "local": True,
        "cloud": False,
    }


def ask_knowledge_base(query: str, model: Optional[str] = None) -> dict:
    """
    Ask a question and get a grounded answer from the knowledge base.
    Combines retrieval + LLM generation with source citations.

    Returns:
        {
            "answer": str,
            "sources": [...],
            "model": str,
            "rag_used": bool,
        }
    """
    log("TOOL_CALL", tool="ask_knowledge_base", query=query[:100])
    return answer_with_rag(query, model=model)
