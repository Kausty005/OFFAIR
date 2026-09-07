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
import re
from pathlib import Path
from typing import Optional

try:
    import numpy as np
    _NUMPY_AVAILABLE = True
except ImportError:
    _NUMPY_AVAILABLE = False

_base = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _base)

from security.audit import log
from security.permissions import User, can_user_access

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
    """Single-pair cosine similarity fallback (used only when numpy unavailable)."""
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm_a = math.sqrt(sum(a * a for a in vec1))
    norm_b = math.sqrt(sum(b * b for b in vec2))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)


def _cosine_similarity_batch(query: list[float], matrix: list[list[float]]) -> list[float]:
    """
    Compute cosine similarity between a query vector and ALL stored vectors
    in a single vectorized NumPy call — 50-100x faster than a Python loop.
    Falls back to pure Python if numpy is unavailable.
    """
    if not matrix:
        return []
    if _NUMPY_AVAILABLE:
        q = np.array(query, dtype=np.float32)
        m = np.array(matrix, dtype=np.float32)          # shape: (N, dims)
        # Dot products: (N,)
        dots = m @ q
        # Norms
        q_norm = np.linalg.norm(q)
        m_norms = np.linalg.norm(m, axis=1)             # (N,)
        # Avoid division by zero
        denom = m_norms * q_norm
        denom[denom == 0] = 1e-9
        scores = dots / denom
        return scores.tolist()
    else:
        return [_cosine_similarity(query, row) for row in matrix]


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
    user: Optional[User] = None,
    authorized_only: bool = False,
) -> list[dict]:
    """
    Semantic search using a query embedding with lexical fallback.
    Uses NumPy batch cosine similarity for speed.
    Returns list of {id, text, metadata, score, document, page, section}.
    """
    try:
        store = _load_store()
        if not store["ids"]:
            return []

        is_zero_vector = not query_embedding or all(v == 0.0 for v in query_embedding)

        # --- Apply metadata and authorization filters first ---
        if where:
            indices = [
                i for i in range(len(store["ids"]))
                if all(store["metadatas"][i].get(k) == v for k, v in where.items())
            ]
        else:
            indices = list(range(len(store["ids"])))

        if authorized_only:
            if user is None:
                return []
            denied_sources = sorted({
                store["metadatas"][i].get("source", "unknown")
                for i in indices
                if not can_user_access(user, store["metadatas"][i])
            })
            log(
                "RAG_ACCESS_FILTER",
                user_id=user.user_id,
                role=user.normalized_role,
                denied_documents=denied_sources,
                candidates_before_filter=len(indices),
            )
            indices = [
                i for i in indices
                if can_user_access(user, store["metadatas"][i])
            ]

        if not indices:
            return []

        # --- Compute scores ---
        if not is_zero_vector:
            # Batch NumPy cosine similarity over all (filtered) vectors
            filtered_embeddings = [store["embeddings"][i] for i in indices]
            # Remove entries with zero/missing embeddings
            valid_mask = [bool(emb and any(v != 0.0 for v in emb)) for emb in filtered_embeddings]
            valid_indices = [indices[j] for j, ok in enumerate(valid_mask) if ok]
            valid_embeddings = [filtered_embeddings[j] for j, ok in enumerate(valid_mask) if ok]

            if valid_embeddings:
                scores_arr = _cosine_similarity_batch(query_embedding, valid_embeddings)
            else:
                scores_arr = []

            score_map = {valid_indices[j]: scores_arr[j] for j in range(len(valid_indices))}

            # Fallback to text overlap for zero-embedding entries
            for i in indices:
                if i not in score_map:
                    score_map[i] = (
                        _text_overlap_similarity(query_text, store["documents"][i])
                        if query_text else 0.0
                    )
        else:
            # Zero query vector — use text overlap for everything
            score_map = {
                i: (_text_overlap_similarity(query_text, store["documents"][i]) if query_text else 0.0)
                for i in indices
            }

        # --- Filter by threshold and build results ---
        results = []
        for i in indices:
            score = score_map.get(i, 0.0)
            if score >= _SIM_THRESHOLD:
                meta = store["metadatas"][i]
                results.append({
                    "id": store["ids"][i],
                    "text": store["documents"][i],
                    "metadata": meta,
                    "score": round(float(score), 4),
                    "document": meta.get("source", "unknown"),
                    "page": meta.get("page", ""),
                    "section": meta.get("section", ""),
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        results = results[:top_k]

        log(
            "RAG_SEARCH",
            results=len(results),
            collection=_COLLECTION_NAME,
            backend="numpy" if _NUMPY_AVAILABLE else "python",
            authorized_only=authorized_only,
            user_id=user.user_id if user else None,
            role=user.normalized_role if user else None,
        )
        return results
    except Exception as e:
        log("VECTOR_SEARCH_ERROR", error=str(e))
        return []


def keyword_search(
    query: str,
    top_k: int = _TOP_K,
    user: Optional[User] = None,
    authorized_only: bool = False,
) -> list[dict]:
    """Search authorized chunks with a local BM25-style keyword scorer."""
    try:
        store = _load_store()
        if not store["ids"] or not query.strip():
            return []

        query_terms = re.findall(r"[a-zA-Z0-9_-]+", query.lower())
        if not query_terms:
            return []

        tokenized_documents = [
            re.findall(r"[a-zA-Z0-9_-]+", text.lower())
            for text in store["documents"]
        ]
        average_length = sum(len(tokens) for tokens in tokenized_documents) / max(len(tokenized_documents), 1)
        document_frequency = {
            term: sum(term in set(tokens) for tokens in tokenized_documents)
            for term in set(query_terms)
        }
        total_documents = len(tokenized_documents)
        candidates = []
        for index, terms in enumerate(tokenized_documents):
            metadata = store["metadatas"][index]
            if authorized_only and (user is None or not can_user_access(user, metadata)):
                continue
            if not terms:
                continue
            term_counts = {term: terms.count(term) for term in set(terms)}
            document_length_factor = 1 - 0.75 + 0.75 * len(terms) / max(average_length, 1)
            score = 0.0
            for term in query_terms:
                frequency = term_counts.get(term, 0)
                if not frequency:
                    continue
                inverse_document_frequency = math.log(
                    1 + (total_documents - document_frequency.get(term, 0) + 0.5)
                    / (document_frequency.get(term, 0) + 0.5)
                )
                score += inverse_document_frequency * (
                    frequency * 2.0
                    / (frequency + 2.0 * document_length_factor)
                )
            if score <= 0:
                continue
            candidates.append((score, index))

        results = []
        for score, index in sorted(candidates, reverse=True)[:top_k]:
            metadata = store["metadatas"][index]
            results.append({
                "id": store["ids"][index],
                "text": store["documents"][index],
                "metadata": metadata,
                "score": round(float(score), 4),
                "document": metadata.get("source", "unknown"),
                "page": metadata.get("page", ""),
                "section": metadata.get("section", ""),
            })
        log(
            "RAG_KEYWORD_SEARCH",
            results=len(results),
            authorized_only=authorized_only,
            user_id=user.user_id if user else None,
        )
        return results
    except Exception as e:
        log("KEYWORD_SEARCH_ERROR", error=str(e))
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
