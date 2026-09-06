"""
agent/planner.py
Generates step-by-step plans for different task types.
Returns a list of AgentStep objects that the agent will execute.
"""

import os
import sys
from typing import Optional

_base = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _base)

from agent.state import AgentState, AgentStep


def plan_inspection_task(state: AgentState) -> AgentState:
    """Plan for: Upload PDF → OCR → Extract → RAG → Reason → Generate DOCX."""
    has_image = any(
        f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp"))
        for f in state.uploaded_files
    )
    has_pdf = any(f.lower().endswith(".pdf") for f in state.uploaded_files)

    state.add_step("Receive and validate uploaded document", tool="files")
    state.add_step("Detect document type (digital PDF or scanned)", tool="pdf_processor")
    state.add_step("Extract text from document", tool="pdf_processor")
    if has_pdf:
        state.add_step("Run local OCR on scanned pages", tool="ocr")
        if has_image or True:   # Always try vision for inspection
            state.add_step("Analyze pages with local vision model", tool="vision")
    state.add_step("Extract structured findings (equipment, measurements, defects)", tool="llm_extraction")
    state.add_step("Search local knowledge base for relevant SOPs", tool="rag")
    state.add_step("Reason over findings and SOP context", tool="llm_reasoning")
    state.add_step("Generate Maintenance Approval Note (DOCX)", tool="docx_generator")
    state.add_step("Verify output file and content", tool="verifier")
    return state


def plan_coding_task(state: AgentState) -> AgentState:
    """Plan for: Generate code → Test → Docker sandbox → Verify."""
    state.add_step("Analyze coding request and identify requirements", tool="llm")
    state.add_step("Generate Python code using local coding model", tool="llm_coding")
    state.add_step("Generate unit test cases", tool="llm_coding")
    state.add_step("Execute code and tests in Docker sandbox", tool="sandbox")
    state.add_step("Evaluate test results", tool="verifier")
    state.add_step("Refine code if tests failed (max 1 retry)", tool="llm_coding")
    state.add_step("Save verified code to workspace", tool="files")
    return state


def plan_vision_task(state: AgentState) -> AgentState:
    """Plan for: Upload image → Vision model → Structure observations."""
    state.add_step("Receive uploaded image", tool="files")
    state.add_step("Send image to local vision model", tool="vision")
    state.add_step("Structure and format observations", tool="llm")
    state.add_step("Apply AI-generated observation disclaimer", tool="verifier")
    return state


def plan_rag_task(state: AgentState) -> AgentState:
    """Plan for: Query → Embed → Retrieve → Generate grounded answer."""
    state.add_step("Embed search query with local embedding model", tool="embeddings")
    state.add_step("Search local knowledge base (ChromaDB)", tool="rag")
    state.add_step("Retrieve and rank relevant passages", tool="rag")
    state.add_step("Generate answer grounded in retrieved context", tool="llm")
    state.add_step("Format answer with source citations", tool="llm")
    return state


def plan_general_task(state: AgentState) -> AgentState:
    """Generic plan for general reasoning / calculation / chat tasks."""
    has_files = bool(state.uploaded_files)
    if has_files:
        # Always receive files first so content is extracted into raw_text
        state.add_step("Process uploaded files", tool="files")
    if state.task_type == "calculation":
        state.add_step("Parse numerical parameters from request", tool="llm")
        state.add_step("Execute deterministic calculation", tool="calculator")
        state.add_step("Format calculation result with formula", tool="calculator")
    else:
        state.add_step("Check knowledge base for relevant context", tool="rag")
        state.add_step("Generate response using local model", tool="llm")
    return state


def create_plan(state: AgentState) -> AgentState:
    """
    Select and build the appropriate plan based on task type.
    """
    task_type = state.task_type
    task_lower = state.task.lower()

    # Inspection-specific keywords
    inspection_keywords = [
        "inspection", "approve", "approval", "maintenance note", "approval note",
        "equipment", "pump", "finding", "defect", "anomaly", "bearing", "seal"
    ]
    is_inspection = any(kw in task_lower for kw in inspection_keywords)
    has_pdf = any(f.lower().endswith(".pdf") for f in state.uploaded_files)

    is_doc_gen = "word document" in task_lower or "docx" in task_lower

    if (is_inspection and has_pdf) or "inspection agent" in task_lower or is_doc_gen:
        return plan_inspection_task(state)
    elif task_type == "coding":
        return plan_coding_task(state)
    elif task_type == "vision":
        return plan_vision_task(state)
    elif task_type == "document" and has_pdf:
        return plan_inspection_task(state)
    else:
        return plan_general_task(state)
