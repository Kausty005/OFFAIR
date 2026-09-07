"""Local reranking for hybrid retrieval candidates."""

import re
from typing import Any


def _terms(text: str) -> set[str]:
    stop = {"the", "a", "an", "is", "in", "at", "of", "on", "and", "or", "for", "to", "what", "how", "this", "that", "it", "are", "was", "be", "has", "have", "do"}
    return set(re.findall(r"[a-zA-Z0-9_-]+", text.lower())) - stop


def rerank(query: str, results: list[dict[str, Any]], top_k: int = 5) -> list[dict[str, Any]]:
    """Rerank candidates using query-term coverage and hybrid_score (RRF-based).
    
    hybrid_score is always in a small range (1/(60+rank)) so it is consistent
    regardless of whether the result came from vector or keyword search.
    """
    query_terms = _terms(query)
    if not query_terms:
        return results[:top_k]

    ranked = []
    for result in results:
        document_terms = _terms(result.get("text", ""))
        # Coverage: fraction of query terms that appear in the document
        coverage = len(query_terms.intersection(document_terms)) / len(query_terms)
        
        # Always use hybrid_score (RRF-based, consistent range) — never raw BM25
        h_score = result.get("hybrid_score", 0.0)
        # Fall back to vector cosine similarity score (already 0-1) if no hybrid_score
        if h_score == 0.0:
            raw = result.get("score", 0.0)
            # Normalize: if it looks like a BM25 score (> 2.0), cap it
            h_score = min(raw, 1.0) if raw <= 2.0 else (1.0 / (1.0 + raw))
        
        result = dict(result)
        result["rerank_score"] = round(0.65 * coverage + 0.35 * (h_score * 100), 4)
        ranked.append(result)

    ranked.sort(key=lambda result: result["rerank_score"], reverse=True)
    return ranked[:top_k]