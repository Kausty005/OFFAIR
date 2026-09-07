"""
rag/vector_store.py
Pure Python local vector store for RAG.
All data stored locally in a JSON file — no cloud vector database, 
and fully compatible with Python 3.14 (avoids Pydantic/Chroma issues).
"""

import os
import sys
import json
import math
from pathlib import Path
from typing import Optional

_base = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _base)

from security.audit import log

import yaml
_cfg_path = os.path.join(_base, "config", "settings.yaml")
with open(_cfg_path) as f:
    _settings = yaml.safe_load(f)

_CHROMA_PATH = Path(_settings["paths"]["chroma_db"])
_COLLECTION_NAME = _settings["rag"]["collection_name"]
_TOP_K = _settings["rag"]["top_k"]
_SIM_THRESHOLD = _settings["rag"]["similarity_threshold"]

_CHROMA_PATH.mkdir(parents=True, exist_ok=True)
_STORE_FILE = _CHROMA_PATH / f"{_COLLECTION_NAME}.json"

def _load_store() -> dict:
    if _STORE_FILE.exists():
        try:
            with open(_STORE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log("VECTOR_STORE_ERROR", error=f"Failed to load: {e}")
    return {"ids": [], "embeddings": [], "documents": [], "metadatas": []}

def _save_store(data: dict):
    with open(_STORE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm_a = math.sqrt(sum(a * a for a in vec1))
    norm_b = math.sqrt(sum(b * b for b in vec2))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)


def add_documents(
    ids: list[str],
    embeddings: list[list[float]],
    texts: list[str],
    metadatas: list[dict],
) -> bool:
    """
    Add document chunks to the pure python vector store.
    """
    try:
        store = _load_store()
        
        # Upsert logic (replace if ID exists)
        for i, doc_id in enumerate(ids):
            if doc_id in store["ids"]:
                idx = store["ids"].index(doc_id)
                store["embeddings"][idx] = embeddings[i]
                store["documents"][idx] = texts[i]
                store["metadatas"][idx] = metadatas[i]
            else:
                store["ids"].append(doc_id)
                store["embeddings"].append(embeddings[i])
                store["documents"].append(texts[i])
                store["metadatas"].append(metadatas[i])
                
        _save_store(store)
        log("VECTOR_STORE_ADD", count=len(ids), collection=_COLLECTION_NAME)
        return True
    except Exception as e:
        log("VECTOR_STORE_ERROR", error=str(e))
        return False


def _text_overlap_similarity(query_text: str, doc_text: str) -> float:
    if not query_text or not doc_text:
        return 0.0
    import re
    q_words = set(re.findall(r"[a-zA-Z0-9]+", query_text.lower()))
    d_words = set(re.findall(r"[a-zA-Z0-9]+", doc_text.lower()))
    if not q_words or not d_words:
        return 0.0
    # Filter common stopwords
    stop = {"the", "a", "an", "is", "in", "at", "of", "on", "and", "or", "for", "to", "what", "how", "this", "that"}
    q_meaningful = q_words - stop
    if not q_meaningful:
        q_meaningful = q_words
    overlap = len(q_meaningful.intersection(d_words))
    if overlap == 0:
        return 0.0
    return min(0.3 + (overlap / len(q_meaningful)) * 0.65, 0.98)


def search(
    query_embedding: list[float],
    top_k: int = _TOP_K,
    where: Optional[dict] = None,
    query_text: Optional[str] = None,
) -> list[dict]:
    """
    Semantic search using a query embedding with lexical fallback.
    Returns list of {id, text, metadata, score, document, page, section}.
    """
    try:
        store = _load_store()
        if not store["ids"]:
            return []

        results = []
        is_zero_vector = not query_embedding or all(v == 0.0 for v in query_embedding)

        for i in range(len(store["ids"])):
            meta = store["metadatas"][i]
            doc_text = store["documents"][i]
            
            # Simple metadata filtering if 'where' is provided
            if where:
                skip = False
                for k, v in where.items():
                    if meta.get(k) != v:
                        skip = True
                        break
                if skip:
                    continue

            if not is_zero_vector and store["embeddings"][i] and any(v != 0.0 for v in store["embeddings"][i]):
                score = _cosine_similarity(query_embedding, store["embeddings"][i])
            elif query_text:
                score = _text_overlap_similarity(query_text, doc_text)
            else:
                score = 0.0

            if score >= _SIM_THRESHOLD:
                results.append({
                    "id": store["ids"][i],
                    "text": doc_text,
                    "metadata": meta,
                    "score": round(score, 4),
                    "document": meta.get("source", "unknown"),
                    "page": meta.get("page", ""),
                    "section": meta.get("section", ""),
                })
                
        # Sort by highest score
        results.sort(key=lambda x: x["score"], reverse=True)
        results = results[:top_k]

        log("RAG_SEARCH", results=len(results), collection=_COLLECTION_NAME)
        return results
    except Exception as e:
        log("VECTOR_SEARCH_ERROR", error=str(e))
        return []


def get_collection_stats() -> dict:
    """Return stats about the current collection."""
    try:
        store = _load_store()
        return {
            "available": True,
            "collection": _COLLECTION_NAME,
            "count": len(store["ids"]),
            "path": str(_STORE_FILE),
            "cloud": False,
        }
    except Exception as e:
        return {"available": False, "error": str(e), "count": 0}


def delete_document(source_name: str) -> int:
    """Remove all chunks belonging to a specific source document from the store.
    
    Args:
        source_name: The filename (e.g. 'maintenance_sop.pdf') stored in chunk metadata.
    
    Returns:
        Number of chunks removed.
    """
    try:
        store = _load_store()
        original_count = len(store["ids"])

        # Keep only chunks whose metadata source does NOT match the target
        keep_indices = [
            i for i, meta in enumerate(store["metadatas"])
            if meta.get("source", "") != source_name
        ]

        store["ids"]        = [store["ids"][i]        for i in keep_indices]
        store["embeddings"] = [store["embeddings"][i] for i in keep_indices]
        store["documents"]  = [store["documents"][i]  for i in keep_indices]
        store["metadatas"]  = [store["metadatas"][i]  for i in keep_indices]

        removed = original_count - len(store["ids"])
        _save_store(store)
        log("VECTOR_STORE_DELETE_DOC", source=source_name, removed=removed)
        return removed
    except Exception as e:
        log("VECTOR_STORE_DELETE_DOC_ERROR", error=str(e))
        return 0


def delete_collection() -> bool:
    """Delete and recreate the collection (for re-ingestion)."""
    try:
        if _STORE_FILE.exists():
            _STORE_FILE.unlink()
        log("VECTOR_STORE_RESET", collection=_COLLECTION_NAME)
        return True
    except Exception as e:
        log("VECTOR_STORE_RESET_ERROR", error=str(e))
        return False


def chroma_available() -> bool:
    # We return True to pretend the store is available even though it's pure Python now
    return True
