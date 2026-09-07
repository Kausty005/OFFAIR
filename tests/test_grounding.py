import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rag import retriever
from security.permissions import User


def test_no_authorized_context_abstains_without_llm_call(monkeypatch):
    calls = []

    monkeypatch.setattr(retriever, "retrieve", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        retriever.ollama,
        "generate",
        lambda **kwargs: calls.append(kwargs),
    )

    result = retriever.answer_with_rag(
        "What is the company revenue?",
        user=User("bob", "employee"),
        authorized_only=True,
    )

    assert result["abstained"] is True
    assert result["sources"] == []
    assert calls == []