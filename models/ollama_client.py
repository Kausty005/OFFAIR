"""
models/ollama_client.py
Low-level wrapper around the Ollama HTTP REST API.
All calls are validated through network_guard before execution.
"""

import json
import os
import re
import sys
import time
from typing import Any, Generator, Optional

import requests
import yaml

# Path setup
_base = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _base)

from security.network_guard import assert_local_endpoint
from security.audit import log

_settings_path = os.path.join(_base, "config", "settings.yaml")
with open(_settings_path) as f:
    _cfg = yaml.safe_load(f)

OLLAMA_BASE = _cfg["ollama"]["base_url"]
TIMEOUT = _cfg["ollama"]["timeout"]
MAX_RETRIES = _cfg["ollama"]["max_retries"]

# GPU acceleration options — read from config
_ollama_cfg = _cfg.get("ollama", {})
_GPU_OPTIONS = {
    "num_gpu": _ollama_cfg.get("num_gpu", 99),      # offload all layers to VRAM
    "num_ctx": _ollama_cfg.get("num_ctx", 4096),    # context window
    "num_thread": _ollama_cfg.get("num_thread", 8), # CPU threads
    "num_batch": _ollama_cfg.get("num_batch", 512), # prefill batch size
}

# Validate at import time
assert_local_endpoint(OLLAMA_BASE, "Ollama base URL")


class OllamaError(Exception):
    """Raised when Ollama returns an error or is unreachable."""
    pass


def _strip_thinking(text: str) -> str:
    """
    qwen3 and other 'thinking' models wrap their chain-of-thought in
    <think>...</think> blocks. Strip those out so we only return the
    actual answer to the caller.
    """
    if not text:
        return text
    # Remove <think>...</think> blocks (including multiline)
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return cleaned.strip()


def _post(endpoint: str, payload: dict, stream: bool = False, timeout: int = TIMEOUT):
    url = f"{OLLAMA_BASE}{endpoint}"
    assert_local_endpoint(url, endpoint)
    if not ping():
        raise OllamaError(
            f"Cannot connect to Ollama at {OLLAMA_BASE}. "
            "Please start Ollama: run 'ollama serve' in a terminal."
        )
    try:
        resp = requests.post(url, json=payload, stream=stream, timeout=timeout)
        resp.raise_for_status()
        return resp
    except requests.exceptions.ConnectionError:
        raise OllamaError(
            f"Cannot connect to Ollama at {OLLAMA_BASE}. "
            "Please start Ollama: run 'ollama serve' in a terminal."
        )
    except requests.exceptions.Timeout:
        raise OllamaError(f"Ollama request timed out after {timeout}s.")
    except requests.exceptions.HTTPError as e:
        raise OllamaError(f"Ollama HTTP error: {e.response.status_code} — {e.response.text[:500]}")


def generate(
    model: str,
    prompt: str,
    system: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 2048,
    images: Optional[list[str]] = None,
) -> str:
    """
    Generate a completion using the Ollama /api/generate endpoint.
    Returns the full response string.
    images: list of base64-encoded image strings (for vision models).
    """
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            **_GPU_OPTIONS,           # GPU acceleration
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }
    if system:
        payload["system"] = system
    if images:
        payload["images"] = images

    log("LLM_CALL", model=model, endpoint="generate", prompt_len=len(prompt))
    t0 = time.time()
    resp = _post("/api/generate", payload)
    data = resp.json()
    elapsed = round(time.time() - t0, 2)
    raw = data.get("response", "")
    result = _strip_thinking(raw)
    log("LLM_RESPONSE", model=model, elapsed_s=elapsed, tokens=data.get("eval_count", -1), chars=len(result))
    return result


def chat(
    model: str,
    messages: list[dict],
    temperature: float = 0.1,
    max_tokens: int = 2048,
) -> str:
    """
    Chat completion using the Ollama /api/chat endpoint.
    messages: list of {"role": "user"|"assistant"|"system", "content": "..."}
    """
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            **_GPU_OPTIONS,           # GPU acceleration
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }
    log("LLM_CALL", model=model, endpoint="chat", messages=len(messages))
    t0 = time.time()
    resp = _post("/api/chat", payload)
    data = resp.json()
    elapsed = round(time.time() - t0, 2)
    raw = data.get("message", {}).get("content", "")
    result = _strip_thinking(raw)
    log("LLM_RESPONSE", model=model, elapsed_s=elapsed, chars=len(result))
    return result


def embed(model: str, text: str) -> list[float]:
    """
    Get text embeddings using the Ollama /api/embeddings endpoint.
    """
    payload = {"model": model, "prompt": text}
    log("EMBEDDING_CALL", model=model, text_len=len(text))
    resp = _post("/api/embeddings", payload)
    data = resp.json()
    return data.get("embedding", [])


def embed_batch(model: str, texts: list[str]) -> list[list[float]]:
    """Embed a list of texts, one by one (Ollama doesn't support batch natively)."""
    return [embed(model, t) for t in texts]


import socket
from urllib.parse import urlparse

_models_cache = {"ts": 0.0, "models": []}


def ping() -> bool:
    """Return True if Ollama is reachable."""
    try:
        parsed = urlparse(OLLAMA_BASE)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 11434
        with socket.create_connection((host, port), timeout=0.15):
            return True
    except Exception:
        return False


def list_models(force_refresh: bool = False) -> list[dict]:
    """Return a list of locally available models from Ollama with a short TTL cache."""
    now = time.time()
    if not force_refresh and (now - _models_cache["ts"] < 2.0):
        return _models_cache["models"]
    _models_cache["ts"] = now
    if not ping():
        _models_cache["models"] = []
        return []
    try:
        resp = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=1.0)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            _models_cache["models"] = models
            return models
    except Exception:
        pass
    _models_cache["models"] = []
    return []


def is_model_available(model_name: str) -> bool:
    """Check if a model is available locally in Ollama."""
    models = list_models()
    available = [m.get("name", "").split(":")[0] for m in models]
    available_full = [m.get("name", "") for m in models]
    check = model_name.split(":")[0]
    return model_name in available_full or check in available


def get_model_info(model_name: str) -> Optional[dict]:
    """Get details about a specific model."""
    try:
        resp = requests.post(
            f"{OLLAMA_BASE}/api/show",
            json={"name": model_name},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception:
        return None
