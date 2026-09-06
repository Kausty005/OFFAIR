"""
rag/embeddings.py
Local text embeddings via Ollama nomic-embed-text.
No sentence-transformers required (avoids Python 3.14 compat issues).
"""

import os
import sys
from typing import Optional

_base = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _base)

from security.audit import log
from models.model_registry import get_embedding_model
import models.ollama_client as ollama


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
    Embed a list of texts. Returns list of embedding vectors.
    Shows progress for large batches.
    """
    model_name = model or get_embedding_model()
    results = []
    for i, text in enumerate(texts):
        vec = embed_text(text, model=model_name)
        results.append(vec)
    return results


def get_embedding_model_name() -> str:
    return get_embedding_model()
