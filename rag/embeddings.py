"""
rag/embeddings.py
Local text embeddings via Ollama nomic-embed-text.
No sentence-transformers required (avoids Python 3.14 compat issues).
"""

import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

_base = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _base)

from security.audit import log
from models.model_registry import get_embedding_model
import models.ollama_client as ollama


# Max concurrent embedding requests — Ollama can handle several at once
_EMBED_WORKERS = 4


def embed_text(text: str, model: Optional[str] = None) -> list[float]:
    """
    Embed a single text string using the local embedding model.
    Returns a list of floats (embedding vector).
    """
    model_name = model or get_embedding_model()
    try:
        vec = ollama.embed(model_name, text)
        log("EMBEDDING", model=model_name, text_len=len(text), dims=len(vec))
        return vec
    except Exception as e:
        log("EMBEDDING_ERROR", model=model_name, error=str(e))
        # Return zero vector as fallback
        return [0.0] * 768


def embed_batch(texts: list[str], model: Optional[str] = None) -> list[list[float]]:
    """
    Embed a list of texts concurrently using ThreadPoolExecutor.
    Fires up to _EMBED_WORKERS parallel requests to Ollama.
    Returns list of embedding vectors in the same order as input texts.
    """
    if not texts:
        return []

    model_name = model or get_embedding_model()
    results: list[list[float]] = [None] * len(texts)  # type: ignore[list-item]

    def _embed_one(idx: int, text: str) -> tuple[int, list[float]]:
        return idx, embed_text(text, model=model_name)

    with ThreadPoolExecutor(max_workers=_EMBED_WORKERS) as pool:
        futures = {pool.submit(_embed_one, i, t): i for i, t in enumerate(texts)}
        for future in as_completed(futures):
            idx, vec = future.result()
            results[idx] = vec

    log("EMBED_BATCH", model=model_name, count=len(texts), workers=_EMBED_WORKERS)
    return results


def get_embedding_model_name() -> str:
    return get_embedding_model()
