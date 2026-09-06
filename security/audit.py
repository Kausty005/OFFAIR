"""
security/audit.py
JSONL audit logger — every important operation is recorded with a timestamp.
Provides counters for external API calls (should always be 0).
"""

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

_settings_path = os.path.join(os.path.dirname(__file__), "..", "config", "settings.yaml")
with open(_settings_path, "r") as f:
    _settings = yaml.safe_load(f)

_LOG_PATH = Path(_settings["paths"]["audit_log"])
_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

_lock = threading.Lock()

# Runtime counters (reset on each application start)
_counters: dict[str, int] = {
    "external_api_calls": 0,
    "cloud_uploads": 0,
    "local_llm_calls": 0,
    "ocr_operations": 0,
    "rag_searches": 0,
    "sandbox_executions": 0,
    "docx_generated": 0,
    "files_written": 0,
    "tasks_completed": 0,
}

# In-memory event buffer (last N events for UI display)
_event_buffer: list[dict] = []
_MAX_BUFFER = 200


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(event: str, **kwargs: Any) -> dict:
    """
    Write a structured audit event to logs/audit.jsonl.
    Also maintains in-memory buffer for UI display.
    """
    ts = _now()
    record = {
        "time": ts,
        "timestamp": ts,
        "action": event,
        "event": event,
        "details": kwargs,
        **kwargs,
    }
    with _lock:
        # Append to file
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        # Update counters
        if event == "EXTERNAL_API_CALL":
            _counters["external_api_calls"] += 1
        elif event == "CLOUD_UPLOAD":
            _counters["cloud_uploads"] += 1
        elif event in ("LLM_CALL", "EMBEDDING_CALL"):
            _counters["local_llm_calls"] += 1
        elif event == "OCR_EXECUTED":
            _counters["ocr_operations"] += 1
        elif event == "RAG_SEARCH":
            _counters["rag_searches"] += 1
        elif event == "SANDBOX_EXECUTION":
            _counters["sandbox_executions"] += 1
        elif event == "DOCX_GENERATED":
            _counters["docx_generated"] += 1
        elif event == "FILE_WRITTEN":
            _counters["files_written"] += 1
        elif event == "TASK_COMPLETED":
            _counters["tasks_completed"] += 1

        # Update in-memory buffer
        _event_buffer.append(record)
        if len(_event_buffer) > _MAX_BUFFER:
            _event_buffer.pop(0)

    return record


def get_counters() -> dict[str, int]:
    """Return a copy of runtime counters."""
    with _lock:
        return dict(_counters)


def get_recent_events(n: int = 50) -> list[dict]:
    """Return the last N audit events for UI display."""
    with _lock:
        return list(_event_buffer[-n:])


def get_recent_logs(limit: int = 50) -> list[dict]:
    """Alias for get_recent_events — used by the FastAPI endpoint."""
    return get_recent_events(n=limit)


def get_security_status() -> dict:
    """Return a security status summary for the UI."""
    counters = get_counters()
    return {
        "llm_inference": "LOCAL",
        "ocr": "LOCAL",
        "embeddings": "LOCAL",
        "rag": "LOCAL",
        "file_processing": "LOCAL",
        "code_execution": "DOCKER",
        "external_ai_apis": counters["external_api_calls"],
        "cloud_uploads": counters["cloud_uploads"],
        "internet_dependency": "NONE",
        "local_llm_calls": counters["local_llm_calls"],
        "ocr_operations": counters["ocr_operations"],
        "rag_searches": counters["rag_searches"],
        "sandbox_executions": counters["sandbox_executions"],
    }


# Log application start
log("APP_START", version="2.0.0", project="SIH26117", ui="React+FastAPI")
