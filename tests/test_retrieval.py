import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.reranker import rerank


def test_reranker_prefers_query_term_coverage():
    results = rerank(
        "P-104 overheating limit",
        [
            {"id": "broad", "text": "Pump operating guidance", "hybrid_score": 0.02},
            {
                "id": "exact",
                "text": "P-104 overheating limit is 80 C",
                "hybrid_score": 0.01,
            },
        ],
        top_k=2,
    )
    assert results[0]["id"] == "exact"