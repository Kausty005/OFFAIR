"""
models/model_registry.py
Loads model configuration from config/models.yaml.
Provides lookup by task type and model role.
Adding a new model requires only a config change — no code changes.
"""

import os
import sys
from dataclasses import dataclass, field
from typing import Optional

import yaml

_base = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _base)

from models.ollama_client import is_model_available, list_models

_models_path = os.path.join(_base, "config", "models.yaml")
with open(_models_path) as f:
    _raw = yaml.safe_load(f)


@dataclass
class ModelConfig:
    role: str
    provider: str
    name: str
    description: str
    task_types: list[str]
    context_length: int = 4096
    fallback: Optional[str] = None


def _load_registry() -> dict[str, ModelConfig]:
    registry: dict[str, ModelConfig] = {}
    for role, cfg in _raw["models"].items():
        registry[role] = ModelConfig(
            role=role,
            provider=cfg.get("provider", "ollama"),
            name=cfg["name"],
            description=cfg.get("description", ""),
            task_types=cfg.get("task_types", []),
            context_length=cfg.get("context_length", 4096),
            fallback=cfg.get("fallback"),
        )
    return registry


_registry: dict[str, ModelConfig] = _load_registry()


def get_model(role: str) -> Optional[ModelConfig]:
    """Get model config by role (general, coding, vision, embedding)."""
    return _registry.get(role)


def get_model_for_task(task_type: str) -> Optional[ModelConfig]:
    """Find the best model for a given task type."""
    for model in _registry.values():
        if task_type in model.task_types:
            return model
    # Default to general
    return _registry.get("general")


def get_available_model(role: str) -> Optional[str]:
    """
    Return the model name to use for a role, checking availability.
    Falls back to the configured fallback if the primary isn't pulled.
    """
    model = _registry.get(role)
    if not model:
        return None

    if is_model_available(model.name):
        return model.name

    # Try fallback
    if model.fallback and is_model_available(model.fallback):
        return model.fallback

    # Last resort: general model
    general = _registry.get("general")
    if general and is_model_available(general.name):
        return general.name

    return None


def get_embedding_model() -> str:
    """Return the embedding model name."""
    emb = _registry.get("embedding")
    return emb.name if emb else "nomic-embed-text:latest"


def get_all_models() -> dict[str, dict]:
    """Return all model configs as plain dicts (JSON-serializable)."""
    result = {}
    for role, model in _registry.items():
        result[role] = {
            "role": model.role,
            "provider": model.provider,
            "name": model.name,
            "description": model.description,
            "task_types": model.task_types,
            "context_length": model.context_length,
            "fallback": model.fallback,
        }
    return result



def get_model_status() -> list[dict]:
    """
    Return status of all configured models for health check display.
    Checks if each is available in Ollama.
    """
    available_in_ollama = {m.get("name", "") for m in list_models()}
    status = []
    for role, model in _registry.items():
        available = model.name in available_in_ollama
        fallback_available = (
            model.fallback in available_in_ollama if model.fallback else False
        )
        status.append(
            {
                "role": role,
                "name": model.name,
                "description": model.description,
                "available": available,
                "fallback": model.fallback,
                "fallback_available": fallback_available,
                "task_types": model.task_types,
            }
        )
    return status
