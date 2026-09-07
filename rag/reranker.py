"""Local reranking for hybrid retrieval candidates."""

import re
from typing import Any


def _terms(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9_-]+", text.lower()))


def rerank(query: str, results: list[dict[str, Any]], top_k: int = 5) -> list[dict[str, Any]]:
    """Rerank candidates using query-term coverage and hybrid rank score."""
    query_terms = _terms(query)
    if not query_terms:
        return results[:top_k]

    ranked = []
    for result in results:
        document_terms = _terms(result.get("text", ""))
        coverage = len(query_terms.intersection(document_terms)) / len(query_terms)
        result = dict(result)
        result["rerank_score"] = round(
            0.7 * coverage + 0.3 * result.get("hybrid_score", result.get("score", 0.0)),
            4,
        )
        ranked.append(result)
    ranked.sort(key=lambda result: result["rerank_score"], reverse=True)
    return ranked[:top_k]