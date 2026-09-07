import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.graph import node_execute_document_analysis, node_execute_multi_step, node_execute_vision_analysis


def test_non_inspection_document_does_not_create_maintenance_report(monkeypatch, tmp_path):
    resume = tmp_path / "resume.txt"
    resume.write_text("Jane Doe\nPython developer\nExperience at Example Corp", encoding="utf-8")

    monkeypatch.setattr("agent.graph.retrieve_context", lambda *args, **kwargs: [])
    monkeypatch.setattr("agent.graph.ollama.generate", lambda **kwargs: (_ for _ in ()).throw(AssertionError("LLM must not be called")))
    result = node_execute_document_analysis({
        "uploaded_files": [str(resume)],
        "user_query": "Summarize this resume",
        "selected_model": "local-test",
        "output_files": [],
    })

    assert result["output_files"] == []
    assert "no related authorized source" in result["generated_response"].lower()
    assert result["retrieved_context"] == []


def test_multi_step_generic_upload_does_not_use_p104_fallback(monkeypatch, tmp_path):
    resume = tmp_path / "resume.txt"
    resume.write_text("Jane Doe\nPython developer\nExperience at Example Corp", encoding="utf-8")
    monkeypatch.setattr("agent.graph.ollama.generate", lambda **kwargs: "Resume summary: Python developer.")

    result = node_execute_multi_step({
        "uploaded_files": [str(resume)],
        "user_query": "Analyse document",
        "execution_plan": [{"tool": "pdf_processor"}],
        "selected_model": "local-test",
        "output_files": [],
    })

    assert result["output_files"] == []
    assert "p_104" not in result["generated_response"].lower()


def test_related_source_is_shown_when_ollama_is_offline(monkeypatch, tmp_path):
    document = tmp_path / "retrieval.txt"
    document.write_text("RAG retrieves external knowledge before answering.", encoding="utf-8")
    monkeypatch.setattr(
        "agent.graph.retrieve_context",
        lambda *args, **kwargs: [{
            "document": "Retrieval.docx",
            "page": "1",
            "text": "RAG retrieves and incorporates information from external data sources.",
            "score": 0.9,
        }],
    )
    monkeypatch.setattr("agent.graph.ollama.generate", lambda **kwargs: "")

    result = node_execute_document_analysis({
        "uploaded_files": [str(document)],
        "user_query": "Analyse document",
        "selected_model": "",
        "output_files": [],
    })

    assert "Retrieval.docx" in result["generated_response"]
    assert "RAG retrieves" in result["generated_response"]


def test_unrelated_image_is_rejected_before_vision_model(monkeypatch, tmp_path):
    image = tmp_path / "tea.jpg"
    image.write_bytes(b"not a real image")
    monkeypatch.setattr("agent.graph.retrieve_context", lambda *args, **kwargs: [])
    monkeypatch.setattr("document.ocr.ocr_image_file", lambda *args, **kwargs: "")
    monkeypatch.setattr("agent.graph.analyze_image_file", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("vision must not be called")))

    result = node_execute_vision_analysis({
        "uploaded_files": [str(image)],
        "user_query": "Analyze this image",
        "user_context": {"username": "engineer", "role": "engineer"},
    })

    assert "no related authorized source" in result["generated_response"].lower()