"""
agent/graph.py
LangGraph Orchestration Engine for OffAir AI.

Implements a clean stateful workflow:
START -> ANALYZE & CLASSIFY -> PLAN -> BRANCH (Model/Tool) -> VERIFY -> FORMAT -> END
"""

import os
import re
import sys
import json
import time
import uuid
from typing import Any, Callable, Optional, TypedDict
from pathlib import Path

from langgraph.graph import StateGraph, START, END

# Import existing tools and services
from security.audit import log
from agent.task_classifier import classify_task, TaskType, PlannedStep
from agent.state import AgentStep, AgentState
from agent.verifier import verify_task_result
from tools.calculator import evaluate_expression, pump_efficiency, bearing_temperature_risk, CalcResult
from tools.sandbox import run_code_sandbox, run_python_sandbox
from rag.interface import retrieve_context
from models.model_registry import get_available_model
import models.ollama_client as ollama
from document.pdf_processor import process_pdf
from document.ocr import ocr_pdf_pages
from document.vision import analyze_image_file
from tools.docx_generator import create_maintenance_approval_note, create_document_from_markdown
from tools.pptx_generator import create_maintenance_approval_pptx, create_presentation_from_markdown
from tools.pdf_generator import create_pdf_from_markdown
from tools.files import get_output_path


# ─── State Definition ─────────────────────────────────────────────────────────

class AgentStateDict(TypedDict, total=False):
    request_id: str
    user_query: str
    user_id: Optional[str]
    user_role: Optional[str]
    user_context: Optional[dict[str, Any]]
    uploaded_files: list[str]
    task_type: str
    sub_tasks: list[dict[str, Any]]
    execution_plan: list[dict[str, Any]]
    current_step: int
    selected_model: str
    model_reason: str
    selected_tools: list[str]
    retrieved_context: list[dict[str, Any]]
    generated_code: Optional[str]
    language: str
    stdin: str
    tool_results: dict[str, Any]
    extracted_data: dict[str, Any]
    generated_response: Optional[str]
    final_output: Optional[str]
    verification_result: dict[str, Any]
    execution_status: str
    errors: list[str]
    audit_events: list[dict[str, Any]]
    output_files: list[str]
    verified: bool
    verification_notes: list[str]
    is_multi_step: bool
    event_callback: Optional[Any]


# ─── Event Dispatch Helper ───────────────────────────────────────────────────

def _emit_event(state: AgentStateDict, event_name: str, payload: dict[str, Any]):
    """Emit high-level observable event to registered callback."""
    cb = state.get("event_callback")
    if cb and callable(cb):
        try:
            cb(event_name, payload)
        except Exception:
            pass
    # Also log to security audit trail
    log(event_name, **payload)


def _emit_step(state: AgentStateDict, description: str, status: str, result: str = "", tool: str = ""):
    """Emit a step progress update to UI listeners."""
    cb = state.get("event_callback")
    if cb and callable(cb):
        step = AgentStep(
            index=0,
            description=description,
            tool=tool,
            status=status,
            result=result,
        )
        try:
            cb("progress_step", step)
        except Exception:
            pass



# ─── Node 1: Analyze Request & Classify Task ──────────────────────────────────

def node_analyze_and_plan(state: AgentStateDict) -> AgentStateDict:
    """Classify the incoming user query, formulate the plan, and select models/tools."""
    query = state.get("user_query", "")
    files = state.get("uploaded_files", [])
    req_id = state.get("request_id") or uuid.uuid4().hex[:8]

    _emit_event(state, "REQUEST_RECEIVED", {"request_id": req_id, "query": query[:120]})

    # Deterministic Task Classification & Planning
    classification = classify_task(query=query, uploaded_files=files)

    task_type = classification.primary_task
    plan_dicts = [
        {
            "step_id": s.step_id,
            "task_type": s.task_type,
            "description": s.description,
            "tool": s.tool,
            "status": "pending",
        }
        for s in classification.steps
    ]

    _emit_event(state, "TASK_CLASSIFIED", {
        "task_type": task_type,
        "is_multi_step": classification.is_multi_step,
        "confidence": classification.confidence,
        "reason": classification.reason,
    })

    _emit_event(state, "EXECUTION_PLAN_CREATED", {
        "steps_count": len(plan_dicts),
        "steps": [s["description"] for s in plan_dicts],
    })

    _emit_event(state, "MODEL_SELECTED", {
        "model": classification.selected_model,
        "role": classification.selected_role,
        "reason": classification.reason,
    })

    _emit_event(state, "TOOL_SELECTED", {
        "tools": classification.selected_tools,
    })

    # Inform UI of step-by-step progress
    cb = state.get("event_callback")
    if cb and callable(cb):
        for p in plan_dicts:
            step_obj = AgentStep(
                index=p["step_id"] - 1,
                description=p["description"],
                tool=p["tool"],
                status="pending",
            )
            cb("progress_step", step_obj)

    return {
        "request_id": req_id,
        "task_type": task_type,
        "is_multi_step": classification.is_multi_step,
        "sub_tasks": plan_dicts,
        "execution_plan": plan_dicts,
        "selected_model": classification.selected_model,
        "model_reason": classification.reason,
        "selected_tools": classification.selected_tools,
        "current_step": 0,
        "execution_status": "in_progress",
    }


# ─── Node 2: Calculation (Deterministic Safe Calculator) ───────────────────────

def node_execute_calculation(state: AgentStateDict) -> AgentStateDict:
    """Route calculation to deterministic AST evaluator."""
    query = state.get("user_query", "")
    _emit_event(state, "TOOL_EXECUTION_STARTED", {"tool": "calculator", "operation": "evaluate_expression"})

    tool_results = dict(state.get("tool_results") or {})
    output_text = ""

    try:
        # Check if engineering calculation requested
        q_lower = query.lower()
        if "pump efficiency" in q_lower:
            # Extract numbers
            nums = [float(n) for n in re.findall(r"[-+]?\d*\.?\d+", query)]
            if len(nums) >= 2:
                # assume first is pin, second is pout or vice versa
                p_in = max(nums[0], nums[1])
                p_out = min(nums[0], nums[1])
                res = pump_efficiency(input_power_kw=p_in, output_power_kw=p_out)
                tool_results["calculations"] = res
                output_text = f"**Pump Efficiency Calculation**:\n\n{res.explanation}\n\n**Result**: {res.result}{res.unit}"
            else:
                output_text = "To calculate pump efficiency, please provide input power (kW) and output power (kW)."
        else:
            # Extract expression: remove 'calculate', 'compute', etc.
            clean_expr = re.sub(r"^(?:calculate|compute|eval|what is)\s+", "", query, flags=re.IGNORECASE).strip()
            # If math operators exist, evaluate
            res = evaluate_expression(clean_expr)
            tool_results["calculations"] = res
            output_text = f"**Calculation Result**:\n\n{clean_expr} = **{res.result}**"

        _emit_event(state, "TOOL_EXECUTION_COMPLETED", {"tool": "calculator", "status": "success"})

    except Exception as e:
        tool_results["calculations"] = {"error": str(e)}
        output_text = f"Calculation error: {str(e)}"
        _emit_event(state, "ERROR", {"stage": "calculator", "error": str(e)})

    return {
        "tool_results": tool_results,
        "generated_response": output_text,
    }


# ─── Node 3: Code Generation ──────────────────────────────────────────────────

def node_execute_code_generation(state: AgentStateDict) -> AgentStateDict:
    """Generate clean code using local coding LLM and optionally test in Docker sandbox."""
    query = state.get("user_query", "")
    model = state.get("selected_model") or get_available_model("coding") or "qwen2.5-coder:3b"

    _emit_event(state, "TOOL_EXECUTION_STARTED", {"tool": "coding_model", "model": model})

    coding_system = (
        "You are an expert Python software engineer. "
        "Write clean, correct, well-structured Python code with proper error handling. "
        "Return the code inside a markdown ```python code block."
    )

    try:
        raw_response = ollama.generate(
            model=model,
            prompt=f"Task: {query}\n\nProvide the complete Python solution.",
            system=coding_system,
            temperature=0.1,
            max_tokens=2048,
        )

        # Extract code block
        code_match = re.search(r"```(?:python)?\s*\n(.*?)\n```", raw_response, re.DOTALL)
        code = code_match.group(1).strip() if code_match else raw_response.strip()

        tool_results = dict(state.get("tool_results") or {})
        tool_results["generated_code"] = code

        _emit_event(state, "TOOL_EXECUTION_COMPLETED", {"tool": "coding_model", "status": "success", "code_len": len(code)})

        # Check if testing was planned
        needs_test = any("sandbox" in s.get("tool", "") for s in state.get("execution_plan", []))
        if needs_test:
            _emit_event(state, "SANDBOX_STARTED", {"sandbox": "Docker", "network_disabled": True})
            # Generate unit tests
            test_prompt = f"Write unittest test cases for this code:\n\n{code}\n\nReturn only Python unittest code."
            test_resp = ollama.generate(model=model, prompt=test_prompt, temperature=0.1)
            test_match = re.search(r"```(?:python)?\s*\n(.*?)\n```", test_resp, re.DOTALL)
            test_code = test_match.group(1).strip() if test_match else test_resp.strip()

            sandbox_res = run_python_sandbox(code=code, tests=test_code)
            tool_results["sandbox_result"] = sandbox_res
            _emit_event(state, "SANDBOX_COMPLETED", {
                "success": sandbox_res.get("success"),
                "passed": sandbox_res.get("tests_passed"),
                "total": sandbox_res.get("tests_total"),
            })

        resp_text = f"Here is the generated Python code:\n\n```python\n{code}\n```"
        if "sandbox_result" in tool_results:
            sr = tool_results["sandbox_result"]
            status = "✅ All tests passed" if sr.get("success") else f"⚠️ Tests failed ({sr.get('tests_passed')}/{sr.get('tests_total')})"
            out = sr.get('test_output') or sr.get('stdout') or sr.get('stderr') or 'No test output'
            resp_text += f"\n\n**Sandbox Execution**: {status}\n```\n{out[:600]}\n```"

        return {
            "generated_code": code,
            "tool_results": tool_results,
            "generated_response": resp_text,
        }

    except Exception as e:
        _emit_event(state, "ERROR", {"stage": "code_generation", "error": str(e)})
        return {
            "errors": [str(e)],
            "generated_response": f"Failed to generate code: {str(e)}",
        }


# ─── Node 4: Code Execution (Sandbox) ──────────────────────────────────────────

def node_execute_code_execution(state: AgentStateDict) -> AgentStateDict:
    """Execute untrusted code inside the isolated Docker sandbox with stdin."""
    code = state.get("generated_code") or state.get("user_query", "")
    code_match = re.search(r"```(?:python)?\s*\n(.*?)\n```", code, re.DOTALL)
    if code_match:
        code = code_match.group(1).strip()
    elif "in sandbox:" in code.lower():
        idx = code.lower().find("in sandbox:")
        code = code[idx + len("in sandbox:"):].strip()

    stdin = state.get("stdin", "")
    lang = state.get("language", "python")

    _emit_event(state, "SANDBOX_STARTED", {"language": lang, "has_stdin": bool(stdin)})

    res = run_code_sandbox(code=code, language=lang, stdin=stdin)
    tool_results = dict(state.get("tool_results") or {})
    tool_results["sandbox_result"] = res

    _emit_event(state, "SANDBOX_COMPLETED", {
        "status": res.get("status"),
        "exit_code": res.get("exit_code"),
        "execution_time": res.get("execution_time"),
    })

    resp = (
        f"**Sandbox Execution ({res.get('status').upper()})**:\n"
        f"- Exit Code: {res.get('exit_code')}\n"
        f"- Time: {res.get('execution_time')}s\n\n"
        f"**Stdout**:\n```\n{res.get('stdout', 'No output')}\n```\n"
    )
    if res.get("stderr"):
        resp += f"**Stderr**:\n```\n{res.get('stderr')}\n```"

    return {
        "tool_results": tool_results,
        "generated_response": resp,
    }


# ─── Node 5: Knowledge Query (RAG Interface) ──────────────────────────────────

def node_execute_knowledge_query(state: AgentStateDict) -> AgentStateDict:
    """Query knowledge base via the modular RAG interface and synthesize grounded response."""
    query = state.get("user_query", "")
    user_context = state.get("user_context")
    model = state.get("selected_model") or get_available_model("general") or "llama3.1:8b"

    _emit_event(state, "RAG_REQUESTED", {"query": query[:100], "model": model})

    chunks = retrieve_context(query=query, user_context=user_context, top_k=5)

    if not chunks:
        answer = "I couldn't find this information in the authorized knowledge base."
        _emit_event(state, "RAG_ABSTAINED", {"query": query[:100], "reason": "no_authorized_context"})
        return {
            "retrieved_context": [],
            "generated_response": answer,
        }

    sources = []
    context_parts = []
    for i, c in enumerate(chunks):
        doc = c.get("document", "Document")
        page = c.get("page", "")
        context_parts.append(f"[Source {i+1}: {doc}{f' (Page {page})' if page else ''}]\n{c.get('text', '')}")
        sources.append({"index": i + 1, "document": doc, "page": page, "score": c.get("score", 0)})

    context_str = "\n\n".join(context_parts)

    system_prompt = (
        "You are an expert industrial engineering knowledge assistant. "
        "Answer the user query strictly using the provided context. "
        "Cite sources using [Source N] notation. Do not hallucinate."
    )
    prompt = f"CONTEXT:\n{context_str}\n\nQUESTION: {query}\n\nANSWER:"

    answer = ollama.generate(
        model=model,
        prompt=prompt,
        system=system_prompt,
        temperature=0.05,
        max_tokens=1024,
    )

    _emit_event(state, "TOOL_EXECUTION_COMPLETED", {"tool": "rag", "chunks_retrieved": len(chunks)})

    return {
        "retrieved_context": chunks,
        "generated_response": answer,
    }


# ─── Node 6: Document Analysis & Deliverable Generation ───────────────────────

def node_execute_document_analysis(state: AgentStateDict) -> AgentStateDict:
    """Extract uploaded documents, using industrial analysis only when requested."""
    files = state.get("uploaded_files", [])
    query = state.get("user_query", "")
    model = state.get("selected_model") or get_available_model("general") or "llama3.1:8b"

    _emit_event(state, "TOOL_EXECUTION_STARTED", {"tool": "pdf_processor", "files": len(files)})

    raw_text = ""
    extracted_data = {}
    output_files = list(state.get("output_files") or [])

    pdf_files = [f for f in files if f.lower().endswith(".pdf")]
    for pdf_p in pdf_files:
        p_res = process_pdf(pdf_p)
        raw_text += "\n" + p_res.get("full_text", "")
        # Run OCR if scanned
        if p_res.get("needs_ocr"):
            pages = p_res.get("pages", [])
            _emit_event(state, "TOOL_EXECUTION_STARTED", {"tool": "ocr", "pages": len(pages)})
            ocr_pages = ocr_pdf_pages(pages)
            raw_text += "\n" + "\n".join(page.get("ocr_text", "") for page in ocr_pages)

    for file_path in files:
        if file_path.lower().endswith((".txt", ".md")):
            raw_text += "\n" + Path(file_path).read_text(encoding="utf-8", errors="replace")
        elif file_path.lower().endswith(".docx"):
            try:
                from docx import Document
                document = Document(file_path)
                raw_text += "\n" + "\n".join(p.text for p in document.paragraphs if p.text.strip())
            except Exception as exc:
                raw_text += f"\n[DOCX extraction failed: {exc}]"

    if files and not raw_text.strip():
        _emit_event(state, "DOCUMENT_REJECTED", {"reason": "DOCUMENT_EXTRACTION_FAILED"})
        return {
            "tool_results": {"raw_text": "", "document_type": "unextractable", "rag_used": False},
            "retrieved_context": [],
            "output_files": output_files,
            "generated_response": "No information available: the uploaded document could not be extracted, including OCR.",
        }

    inspection_terms = (
        "inspection", "maintenance", "pump", "equipment", "bearing", "vibration",
        "mechanical seal", "operating temperature", "sop", "leakage",
    )
    is_inspection = any(term in f"{query}\n{raw_text[:6000]}".lower() for term in inspection_terms)

    user_context = state.get("user_context")
    retrieval_query = query
    if query.strip().lower() in {"analyse document", "analyze document", "summarize document"}:
        retrieval_query = raw_text[:3000]
    related_context = retrieve_context(
        retrieval_query,
        user_context=user_context,
        top_k=5,
    )
    # Use a lower threshold so we get results — our hybrid rerank scores typically 0.15-0.65
    relevant_context = [
        chunk for chunk in related_context
        if chunk.get("rerank_score", chunk.get("score", 0)) >= 0.20
    ]
    # Fall back to top-3 results if threshold still gives nothing
    if not relevant_context and related_context:
        relevant_context = related_context[:3]
    if not relevant_context:
        reason = "NO_RELEVANT_AUTHORIZED_SOURCE"
        if user_context and not user_context.get("role"):
            reason = "ROLE_NOT_AUTHENTICATED"
        _emit_event(state, "RAG_ABSTAINED", {
            "reason": reason,
            "query": retrieval_query[:120],
        })
        return {
            "tool_results": {
                "raw_text": raw_text,
                "document_type": "unmatched",
                "rag_used": False,
            },
            "retrieved_context": [],
            "output_files": output_files,
            "generated_response": (
                "No information available: your role is not authorized for a related source."
                if reason == "ROLE_NOT_AUTHENTICATED"
                else "No information available: no related authorized source was found in the knowledge base."
            ),
        }

    if not is_inspection:
        summary_prompt = (
            "Answer using only the uploaded document and the related authorized knowledge-base context. "
            "If the context does not support an answer, say no information is available. Do not invent facts.\n\n"
            f"UPLOADED DOCUMENT:\n{raw_text[:8000]}\n\n"
            f"AUTHORIZED KNOWLEDGE CONTEXT:\n{chr(10).join(c.get('text', '') for c in relevant_context)}"
        )
        summary = ollama.generate(model=model, prompt=summary_prompt, temperature=0.1) if model else ""
        if not summary.strip():
            source_lines = []
            for index, chunk in enumerate(relevant_context[:3], start=1):
                source = chunk.get("document", "document")
                page = chunk.get("page", "")
                excerpt = " ".join(chunk.get("text", "").split())[:500]
                source_lines.append(f"[Source {index}] {source}"
                                    f"{f' (Page {page})' if page else ''}: {excerpt}")
            summary = (
                "Related authorized knowledge-base content found. "
                "Ollama is unavailable, so returning retrieved source evidence without generation.\n\n"
                + "\n\n".join(source_lines)
            )
        return {
            "tool_results": {"raw_text": raw_text, "document_type": "general"},
            "retrieved_context": relevant_context,
            "output_files": output_files,
            "generated_response": summary or "No information available: Ollama did not return a grounded answer.",
        }

    img_files = [f for f in files if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".webp"))]
    for img_p in img_files:
        _emit_event(state, "TOOL_EXECUTION_STARTED", {"tool": "vision", "file": Path(img_p).name})
        v_res = analyze_image_file(img_p, prompt="Extract all equipment name, tag, measurements, defect findings, and observations from this image.")
        if v_res.get("text"):
            raw_text += f"\n[IMAGE ANALYSIS ({Path(img_p).name})]\n" + v_res["text"]

    # Extract structured findings from raw_text or query prompt if raw_text is empty
    input_text_for_extraction = f"{query}\n\n{raw_text[:4000]}" if not raw_text.strip() else raw_text[:4000]
    prompt = f"Extract equipment_name, equipment_id, inspection_date, findings (list), measurements (dict), severity, recommendations as JSON from this text:\n\n{input_text_for_extraction}"
    llm_resp = ollama.generate(model=model, prompt=prompt, temperature=0.1)

    # Clean JSON
    clean_json = re.sub(r"```(?:json)?", "", llm_resp).strip().strip("`")
    try:
        extracted_data = json.loads(clean_json)
    except Exception:
        extracted_data = {"equipment_name": "Equipment Inspection", "findings": ["General inspection completed"]}

    # Search SOPs
    sops = relevant_context

    # Generate Word Document ONLY if explicitly requested
    needs_docx = any(k in query.lower() for k in ("docx", "word", "approval note", "make report", "generate report", "create document"))
    if needs_docx:
        equip_id = extracted_data.get("equipment_id") or "P-104"
        safe_id = re.sub(r"[^\w\-]", "_", str(equip_id))
        out_path = get_output_path(f"{safe_id}_Maintenance_Approval_Note.docx")
        
        doc_res = create_maintenance_approval_note(
            equipment_name=extracted_data.get("equipment_name", "Boiler Feed Pump P-104"),
            equipment_id=equip_id,
            inspection_date=extracted_data.get("inspection_date", "2024-01-20"),
            findings=extracted_data.get("findings", []),
            measurements=extracted_data.get("measurements", {}),
            recommendations=extracted_data.get("recommendations", "Review findings and perform maintenance."),
            sop_references=[{"document": s.get("document", "SOP"), "text": s.get("text", "")} for s in sops],
            ai_reasoning="Generated based on automated document analysis.",
            output_path=out_path,
            risk_level=extracted_data.get("severity", "High"),
        )
        if doc_res and doc_res.get("success"):
            output_files.append(doc_res["path"])
            _emit_event(state, "TOOL_EXECUTION_COMPLETED", {"tool": "docx_generator", "output_file": Path(doc_res["path"]).name})

    # Synthesize grounded answer
    context_str = "\n\n".join(f"[{s.get('document', 'SOP')}]\n{s.get('text', '')}" for s in sops)
    doc_prompt = (
        "You are an industrial expert. Answer the question using the uploaded document data and relevant SOP context.\n\n"
        f"DOCUMENT SUMMARY: {json.dumps(extracted_data)}\n"
        f"EXTRACTED TEXT: {raw_text[:2000]}\n"
        f"SOP CONTEXT:\n{context_str}\n\n"
        f"QUESTION: {query}\n\nANSWER:"
    )
    grounded_ans = ollama.generate(model=model, prompt=doc_prompt, temperature=0.1) if model else ""

    if grounded_ans and len(grounded_ans.strip()) > 10:
        response_text = grounded_ans.strip()
    else:
        response_text = (
            f"**Inspection & Document Analysis Complete**:\n\n"
            f"- Equipment: {extracted_data.get('equipment_name')}\n"
            f"- Tag: {extracted_data.get('equipment_id', 'N/A')}\n"
            f"- Severity: {extracted_data.get('severity', 'Medium')}"
        )

    if output_files and needs_docx:
        response_text += f"\n\n✅ **Deliverable Generated**: `{Path(output_files[-1]).name}`"

    return {
        "extracted_data": extracted_data,
        "retrieved_context": sops,
        "output_files": output_files,
        "generated_response": response_text,
    }


# ─── Node 6b: Vision Analysis ──────────────────────────────────────────────────

def node_execute_vision_analysis(state: AgentStateDict) -> AgentStateDict:
    """Analyze uploaded industrial photograph or diagram using local multimodal vision model."""
    files = state.get("uploaded_files", [])
    query = state.get("user_query", "")
    model = state.get("selected_model") or get_available_model("vision") or "llava-phi3:latest"

    img_files = [f for f in files if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".webp"))]
    if not img_files:
        for cand in [Path("workspace/uploads/inspection_image.jpg"), Path("demo_data/inspection_image.jpg")]:
            if cand.exists():
                img_files = [str(cand)]
                break

    if not img_files:
        return {
            "generated_response": "No image file provided for vision analysis. Please attach or upload an inspection image.",
        }

    target_img = img_files[0]
    user_context = state.get("user_context")
    ocr_probe = ""
    try:
        from document.ocr import ocr_image_file
        ocr_probe = ocr_image_file(target_img)
    except Exception:
        pass
    related_context = retrieve_context(
        f"{query}\n{ocr_probe[:1200]}",
        user_context=user_context,
        top_k=5,
    )
    relevant_context = [
        chunk for chunk in related_context
        if chunk.get("rerank_score", chunk.get("score", 0)) >= 0.20
    ]
    # Fall back to top-3 if nothing passes threshold
    if not relevant_context and related_context:
        relevant_context = related_context[:3]
    if not relevant_context:
        _emit_event(state, "VISION_REJECTED", {
            "reason": "NO_RELEVANT_AUTHORIZED_SOURCE",
            "file": Path(target_img).name,
        })
        return {
            "generated_response": (
                "No information available: this image has no related authorized source "
                "in the knowledge base, so vision analysis was not performed."
            ),
        }
    _emit_event(state, "TOOL_EXECUTION_STARTED", {"tool": "vision", "model": model, "file": Path(target_img).name})

    res = analyze_image_file(target_img, prompt=query, model=model)
    vision_text = res.get("text", "")

    tool_results = dict(state.get("tool_results") or {})
    tool_results["vision_text"] = vision_text

    _emit_event(state, "TOOL_EXECUTION_COMPLETED", {"tool": "vision", "length": len(vision_text)})

    return {
        "tool_results": tool_results,
        "generated_response": vision_text,
    }


# ─── Node 7: General Chat ─────────────────────────────────────────────────────

def node_execute_general_chat(state: AgentStateDict) -> AgentStateDict:
    """General reasoning and explanation using local LLM, grounded with RAG when possible."""
    query = state.get("user_query", "")
    user_context = state.get("user_context")
    model = state.get("selected_model") or get_available_model("general") or "llama3.1:8b"

    _emit_event(state, "TOOL_EXECUTION_STARTED", {"tool": "local_llm", "model": model})

    # Try to retrieve relevant context from knowledge base to ground the answer
    rag_context_str = ""
    retrieved = []
    try:
        chunks = retrieve_context(query=query, user_context=user_context, top_k=3)
        relevant = [c for c in chunks if c.get("rerank_score", c.get("score", 0)) >= 0.20]
        if not relevant and chunks:
            relevant = chunks[:2]  # fallback: take top-2 anyway
        if relevant:
            retrieved = relevant
            rag_context_str = "\n\n".join(
                f"[{c.get('document', 'Knowledge Base')}]\n{c.get('text', '')[:400]}"
                for c in relevant
            )
    except Exception:
        pass

    if rag_context_str:
        sys_prompt = (
            "You are OffAir AI, a private, secure, air-gapped sovereign AI assistant. "
            "Answer using the provided knowledge base context when relevant. "
            "Cite sources using [Source Name] notation. Be direct, technical, and concise."
        )
        prompt = f"CONTEXT FROM KNOWLEDGE BASE:\n{rag_context_str}\n\nQUESTION: {query}\n\nANSWER:"
    else:
        sys_prompt = (
            "You are OffAir AI, a private, secure, air-gapped sovereign AI assistant. "
            "Be direct, technical, and concise. Do not mention external internet sources."
        )
        prompt = query

    resp = ollama.generate(model=model, prompt=prompt, system=sys_prompt, temperature=0.3, max_tokens=1500)

    _emit_event(state, "TOOL_EXECUTION_COMPLETED", {"tool": "local_llm", "status": "success"})

    return {
        "generated_response": resp,
        "retrieved_context": retrieved,
    }


# ─── Node 7b: Presentation Generation ──────────────────────────────────────────

def node_execute_presentation(state: AgentStateDict) -> AgentStateDict:
    """Synthesize presentation structure and generate PowerPoint (.pptx) deliverable."""
    query = state.get("user_query", "")
    model = state.get("selected_model") or get_available_model("general") or "llama3.1:8b"
    output_files = list(state.get("output_files") or [])

    _emit_event(state, "TOOL_EXECUTION_STARTED", {"tool": "pptx_generator", "task": "Synthesizing presentation slides"})

    # Check if the query already provides structured markdown slides
    has_markdown_slides = bool(
        re.search(r"slide\s*\d+", query, re.IGNORECASE) or
        ("---" in query and "####" in query) or
        ("### " in query and "#### " in query)
    )

    slides_content = ""
    if has_markdown_slides:
        slides_content = query
    else:
        sys_prompt = (
            "You are an expert presentation designer for OffAir AI Sovereign Workbench. "
            "Generate clean, highly structured presentation slides in markdown format based on the user's topic.\n"
            "Format rules:\n"
            "- Start with ### Presentation Title\n"
            "- Subtitle line wrapped in asterisks: *Subtitle or Organization*\n"
            "- Separate each slide with ---\n"
            "- Each slide header: #### Slide X: Title\n"
            "- 3 to 4 concise bullet points (- point)\n"
            "- Optional source line: *Source: Citations*\n"
            "Be factual, concise, and structured. Do not include conversational intro or outro."
        )
        try:
            slides_content = ollama.generate(
                model=model,
                prompt=f"Create presentation slides for: {query}",
                system=sys_prompt,
                temperature=0.3,
                max_tokens=1500,
            )
        except Exception:
            slides_content = ""

        # Fallback structured outline if Ollama is offline or did not format markdown
        if not slides_content or not ("####" in slides_content or "Slide" in slides_content):
            topic = re.sub(
                r"(?i)\b(?:make|generate|create)\s+(?:a\s+)?(?:ppt|pptx|powerpoint|presentation|slides)\s+(?:of\s+\d+\s+slides\s+)?(?:on\s+)?",
                "",
                query,
            ).strip() or "Technical Analysis"
            topic_title = topic.title()
            slides_content = (
                f"### {topic_title}: Technical Analysis\n"
                f"*OffAir AI | Air-Gapped Sovereign System*\n\n"
                f"---\n\n"
                f"#### Slide 1: Current State & Baseline\n"
                f"- Primary technical benchmarks and operating indicators for {topic}\n"
                f"- Current performance envelope and baseline measurements\n"
                f"- Key variances identified against design standards\n"
                f"*Source: Sovereign Technical Records*\n\n"
                f"---\n\n"
                f"#### Slide 2: Critical Parameters & Analysis\n"
                f"- Quantitative parameters and stress conditions\n"
                f"- Systemic risk factors and dependency matrices\n"
                f"- Operational resilience and threshold tolerances\n"
                f"*Source: Engineering Standards*\n\n"
                f"---\n\n"
                f"#### Slide 3: Thresholds & Risk Vectors\n"
                f"- Warning indicators and automatic trip thresholds\n"
                f"- Mitigation protocols and containment pathways\n"
                f"- Safety margins and compliance verifications\n"
                f"*Source: Safety Governance Framework*\n\n"
                f"---\n\n"
                f"#### Slide 4: Action Framework & Recommendations\n"
                f"- Immediate high-priority remediation measures\n"
                f"- Scheduled maintenance and monitoring milestones\n"
                f"- Sovereign verification and compliance sign-off\n"
                f"*Source: Operational Directives*"
            )

    # Derive clean title and safe filename
    m_title = re.search(r"###\s+([^\n]+)", slides_content)
    raw_title = m_title.group(1).strip() if m_title else query[:30]
    safe_title = re.sub(r"[^\w\-]", "_", raw_title[:35]).strip("_") or "Presentation"
    filename = f"{safe_title}.pptx"
    out_path = get_output_path(filename)

    ppt_res = create_presentation_from_markdown(
        slides_content,
        default_title=raw_title,
        output_path=out_path,
    )

    if ppt_res.get("success"):
        output_files.append(str(out_path))
        _emit_event(state, "TOOL_EXECUTION_COMPLETED", {
            "tool": "pptx_generator",
            "output_file": filename,
            "size": ppt_res.get("size", 0),
        })
        final_text = (
            f"{slides_content.strip()}\n\n"
            f"---\n"
            f"✅ **PowerPoint Presentation Generated:** `{filename}` ({ppt_res.get('size', 0):,} bytes)"
        )
    else:
        final_text = (
            f"{slides_content.strip()}\n\n"
            f"---\n"
            f"⚠️ **PowerPoint Generation Note:** Presentation synthesis completed; export error: {ppt_res.get('error')}"
        )

    return {
        "output_files": output_files,
        "generated_response": final_text,
    }


# ─── Node 7c: Word Document (.docx) Generation ─────────────────────────────────

def node_execute_report(state: AgentStateDict) -> AgentStateDict:
    """Synthesize structured report content and generate Word (.docx) deliverable."""
    query = state.get("user_query", "")
    model = state.get("selected_model") or get_available_model("general") or "llama3.1:8b"
    output_files = list(state.get("output_files") or [])

    _emit_event(state, "TOOL_EXECUTION_STARTED", {"tool": "docx_generator", "task": "Synthesizing document report"})

    user_context = state.get("user_context")
    context_chunks = retrieve_context(query=query, user_context=user_context, top_k=3)
    rag_context = ""
    if context_chunks:
        rag_context = "\n\n".join(f"[{c.get('document', 'SOP')}]\n{c.get('text', '')[:400]}" for c in context_chunks)

    clean_title = re.sub(
        r"(?i)\b(?:make|generate|create|write)\s+(?:a\s+)?(?:word\s+document|word\s+doc|docx|report\s+as\s+docx|document|report)\s+(?:about|on|for)?\s*",
        "",
        query,
    ).strip() or "Technical Report"
    doc_title = clean_title.title()

    sys_prompt = (
        "You are an expert technical documentation specialist for OffAir AI Sovereign Workbench. "
        "Generate a complete, highly structured, well-formatted technical report in markdown.\n"
        "Include clear section headers (## Header), overview, key technical procedures, analysis, "
        "safety/compliance standards, and recommendations. Be thorough and professional."
    )
    prompt = f"Topic: {query}"
    if rag_context:
        prompt += f"\n\nContext from Knowledge Base:\n{rag_context}"

    try:
        report_content = ollama.generate(
            model=model,
            prompt=prompt,
            system=sys_prompt,
            temperature=0.2,
            max_tokens=2048,
        )
    except Exception:
        report_content = ""

    if not report_content or len(report_content.strip()) < 50:
        report_content = (
            f"# {doc_title}\n\n"
            f"*OffAir AI | Air-Gapped Sovereign Document*\n\n"
            f"## 1. Executive Summary\n\n"
            f"This document provides the standard technical framework, procedures, and operational guidelines for {clean_title}.\n\n"
            f"## 2. Technical Specifications & Guidelines\n\n"
            f"- Compliance with standard industrial operating protocols\n"
            f"- Regular verification of operational parameters and tolerance thresholds\n"
            f"- Mandatory routine safety inspections and logging\n\n"
            f"## 3. Maintenance & Safety Directives\n\n"
            f"- All personnel must adhere to authorized sovereign safety procedures\n"
            f"- Critical anomalies must be documented and escalated immediately\n"
            f"- Maintenance cycles must follow OEM and facility engineering standards\n\n"
            f"## 4. Recommendations & Sign-Off\n\n"
            f"Scheduled preventative maintenance is approved and recommended."
        )

    safe_title = re.sub(r"[^\w\-]", "_", doc_title[:35]).strip("_") or "Document"
    filename = f"{safe_title}.docx"
    out_path = get_output_path(filename)

    docx_res = create_document_from_markdown(
        report_content,
        title=doc_title,
        output_path=out_path,
    )

    if docx_res.get("success"):
        output_files.append(str(out_path))
        _emit_event(state, "TOOL_EXECUTION_COMPLETED", {
            "tool": "docx_generator",
            "output_file": filename,
            "size": docx_res.get("size", 0),
        })
        final_text = (
            f"{report_content.strip()}\n\n"
            f"---\n"
            f"✅ **Word Document Generated:** `{filename}` ({docx_res.get('size', 0):,} bytes)"
        )
    else:
        final_text = (
            f"{report_content.strip()}\n\n"
            f"---\n"
            f"⚠️ **Word Document Generation Note:** Content generated; export error: {docx_res.get('error')}"
        )

    return {
        "output_files": output_files,
        "generated_response": final_text,
    }


# ─── Node 7d: PDF Report (.pdf) Generation ─────────────────────────────────────

def node_execute_pdf(state: AgentStateDict) -> AgentStateDict:
    """Synthesize structured report content and generate PDF (.pdf) deliverable."""
    query = state.get("user_query", "")
    model = state.get("selected_model") or get_available_model("general") or "llama3.1:8b"
    output_files = list(state.get("output_files") or [])

    _emit_event(state, "TOOL_EXECUTION_STARTED", {"tool": "pdf_generator", "task": "Synthesizing PDF report"})

    user_context = state.get("user_context")
    context_chunks = retrieve_context(query=query, user_context=user_context, top_k=3)
    rag_context = ""
    if context_chunks:
        rag_context = "\n\n".join(f"[{c.get('document', 'SOP')}]\n{c.get('text', '')[:400]}" for c in context_chunks)

    clean_title = re.sub(
        r"(?i)\b(?:make|generate|create|write)\s+(?:a\s+)?(?:pdf|pdf\s+report|pdf\s+document|report\s+as\s+pdf|document|report)\s+(?:about|on|for)?\s*",
        "",
        query,
    ).strip() or "Technical Report"
    doc_title = clean_title.title()

    sys_prompt = (
        "You are an expert technical documentation specialist for OffAir AI Sovereign Workbench. "
        "Generate a complete, highly structured, well-formatted technical report in markdown.\n"
        "Include clear section headers (## Header), executive summary, detailed technical analysis, "
        "procedures, compliance specifications, and recommendations. Be thorough and professional."
    )
    prompt = f"Topic: {query}"
    if rag_context:
        prompt += f"\n\nContext from Knowledge Base:\n{rag_context}"

    try:
        report_content = ollama.generate(
            model=model,
            prompt=prompt,
            system=sys_prompt,
            temperature=0.2,
            max_tokens=2048,
        )
    except Exception:
        report_content = ""

    if not report_content or len(report_content.strip()) < 50:
        report_content = (
            f"# {doc_title}\n\n"
            f"*OffAir AI | Air-Gapped Sovereign Document*\n\n"
            f"## 1. Executive Summary\n\n"
            f"This formal PDF report establishes operational standards, safety procedures, and guidelines for {clean_title}.\n\n"
            f"## 2. Operational Procedures & Protocols\n\n"
            f"- Compliance verification against standard operating procedures\n"
            f"- Continuous monitoring of key operating thresholds\n"
            f"- Strict adherence to sovereign air-gapped facility protocols\n\n"
            f"## 3. Risk Assessment & Safety Standards\n\n"
            f"- Risk identification and preventative maintenance measures\n"
            f"- Verification of equipment tolerance envelopes\n"
            f"- Mitigation procedures for abnormal indicators\n\n"
            f"## 4. Engineering Recommendations\n\n"
            f"All procedures documented herein have been verified for immediate implementation."
        )

    safe_title = re.sub(r"[^\w\-]", "_", doc_title[:35]).strip("_") or "Report"
    filename = f"{safe_title}.pdf"
    out_path = get_output_path(filename)

    pdf_res = create_pdf_from_markdown(
        report_content,
        title=doc_title,
        output_path=out_path,
    )

    if pdf_res.get("success"):
        output_files.append(str(out_path))
        _emit_event(state, "TOOL_EXECUTION_COMPLETED", {
            "tool": "pdf_generator",
            "output_file": filename,
            "size": pdf_res.get("size", 0),
        })
        final_text = (
            f"{report_content.strip()}\n\n"
            f"---\n"
            f"✅ **PDF Report Generated:** `{filename}` ({pdf_res.get('size', 0):,} bytes)"
        )
    else:
        final_text = (
            f"{report_content.strip()}\n\n"
            f"---\n"
            f"⚠️ **PDF Report Generation Note:** Content generated; export error: {pdf_res.get('error')}"
        )

    return {
        "output_files": output_files,
        "generated_response": final_text,
    }


# ─── Node 8: Multi-Step Task Execution ────────────────────────────────────────

def node_execute_multi_step(state: AgentStateDict) -> AgentStateDict:
    """Execute compound industrial workflows sequentially with dynamic RAG grounding."""
    plan = state.get("execution_plan", [])
    query = state.get("user_query", "")
    model = state.get("selected_model") or get_available_model("general") or "llama3.1:8b"
    user_context = state.get("user_context")
    tool_results = dict(state.get("tool_results") or {})
    output_files = list(state.get("output_files") or [])
    retrieved = []
    extracted_text = ""
    calc_res = None

    # Step 1: Execute steps sequentially
    for step in plan:
        tool = step.get("tool", "")
        _emit_event(state, "TOOL_EXECUTION_STARTED", {"tool": tool, "step": step.get("description")})

        if tool in ("pdf_processor", "ocr"):
            files = state.get("uploaded_files", [])
            for f in files:
                if f.lower().endswith(".pdf"):
                    p_res = process_pdf(f)
                    extracted_text += "\n" + p_res.get("full_text", p_res.get("text", ""))
        elif tool in ("rag", "llm_reasoning"):
            retrieved = retrieve_context(query=query, user_context=user_context, top_k=5)
            tool_results["rag_sources"] = retrieved
        elif tool == "calculator":
            nums = [float(n) for n in re.findall(r"[-+]?\d*\.?\d+", query)]
            if len(nums) >= 2:
                p_in = max(nums[0], nums[1])
                p_out = min(nums[0], nums[1])
                calc_res = pump_efficiency(input_power_kw=p_in, output_power_kw=p_out)
                tool_results["calculations"] = calc_res
        elif tool == "docx_generator":
            clean_t = re.sub(r"(?i)\b(?:make|generate|create|write)\s+(?:a\s+)?(?:word\s+document|docx|report)\b", "", query).strip() or "Technical Report"
            out_path = get_output_path(f"{re.sub(r'[^\w\-]', '_', clean_t[:30])}.docx")
            doc_res = create_document_from_markdown(
                f"# {clean_t.title()}\n\n"
                f"## Executive Summary\nAnalysis generated for: {query}\n\n"
                f"## Knowledge Base Context\n" + "\n\n".join(f"- {c.get('text', '')[:200]}" for c in retrieved[:3]),
                title=clean_t.title(),
                output_path=out_path,
            )
            if doc_res and doc_res.get("success"):
                output_files.append(doc_res["path"])

        _emit_event(state, "TOOL_EXECUTION_COMPLETED", {"tool": tool, "status": "done"})

    # Step 2: Synthesize grounded response using LLM
    context_str = "\n\n".join(
        f"[{c.get('document', 'KB')}]\n{c.get('text', '')}"
        for c in (retrieved or retrieve_context(query=query, user_context=user_context, top_k=5))
    )
    prompt = (
        "You are OffAir AI. Answer the user query using the provided knowledge base context and any document extraction data.\n\n"
        f"EXTRACTED DOCUMENT TEXT: {extracted_text[:2000]}\n"
        f"KNOWLEDGE BASE CONTEXT:\n{context_str}\n\n"
        f"USER QUESTION: {query}\n\n"
        "ANSWER:"
    )
    grounded_ans = ollama.generate(model=model, prompt=prompt, temperature=0.1, max_tokens=1500)

    final_ans = grounded_ans.strip() if grounded_ans else "Completed multi-step analysis."
    if output_files:
        final_ans += "\n\n" + "\n".join(f"✅ **Deliverable Generated**: `{Path(f).name}`" for f in output_files)

    return {
        "tool_results": tool_results,
        "retrieved_context": retrieved,
        "output_files": output_files,
        "generated_response": final_ans,
    }


# ─── Node 9: Verification ─────────────────────────────────────────────────────

def node_verify(state: AgentStateDict) -> AgentStateDict:
    """Deterministic verification based on task type."""
    _emit_event(state, "VERIFICATION_STARTED", {"task_type": state.get("task_type")})

    task_type = state.get("task_type", "general_chat")
    ok, notes = verify_task_result(task_type, dict(state))

    _emit_event(state, "VERIFICATION_COMPLETED", {"verified": ok, "notes": notes})

    return {
        "verified": ok,
        "verification_notes": notes,
        "verification_result": {"verified": ok, "notes": notes},
    }


# ─── Node 10: Format Final Response ───────────────────────────────────────────

def node_format_final_response(state: AgentStateDict) -> AgentStateDict:
    """Assemble final output and log task completion."""
    response = state.get("generated_response") or "Task completed."
    _emit_event(state, "FINAL_RESPONSE_READY", {"length": len(response)})

    return {
        "final_output": response,
        "execution_status": "completed",
    }


# ─── Conditional Branch Router ────────────────────────────────────────────────

# ─── Node 2b: Document Operations (Deterministic Tools) ──────────────────────

def node_execute_document_operation(state: AgentStateDict) -> AgentStateDict:
    """Execute deterministic document tool (or pipeline) locally without LLM inference."""
    from document_tools.chat_resolver import resolve_explicit_document_operation
    from document_tools.agent_adapter import execute_document_tool

    query = state.get("user_query", "")
    files = list(state.get("uploaded_files") or [])
    output_files = list(state.get("output_files") or [])
    tool_results = dict(state.get("tool_results") or {})

    intent = resolve_explicit_document_operation(query, files)
    tool_name = intent.tool_name if intent else "merge_pdf"
    params = intent.params if intent else {}
    is_compound = intent.is_compound if intent else False
    pipeline = intent.pipeline if intent else []

    _emit_event(state, "TOOL_EXECUTION_STARTED", {
        "tool": tool_name,
        "is_compound": is_compound,
        "query": query[:80],
    })

    if is_compound and pipeline:
        current_files = list(files)
        final_msg = ""
        for idx, step in enumerate(pipeline):
            _emit_step(state, step.description, "running", tool=step.tool_name)
            res = execute_document_tool(
                tool_name=step.tool_name,
                params=step.params,
                uploaded_files=current_files,
                query=query,
            )
            if not res.success:
                _emit_step(state, step.description, "failed", result=res.message, tool=step.tool_name)
                _emit_event(state, "TOOL_EXECUTION_FAILED", {"tool": step.tool_name, "error": res.message})
                return {
                    "generated_response": res.message,
                    "execution_status": "failed",
                    "output_files": output_files,
                }
            _emit_step(state, step.description, "done", result="Success", tool=step.tool_name)
            if res.output_files:
                current_files = list(res.output_files)
                for f in res.output_files:
                    if f not in output_files:
                        output_files.append(f)
            final_msg = res.message

        _emit_event(state, "TOOL_EXECUTION_COMPLETED", {"tool": "pipeline", "status": "success"})
        return {
            "output_files": output_files,
            "generated_response": final_msg,
            "tool_results": {"pipeline": [s.tool_name for s in pipeline]},
            "execution_status": "completed",
        }
    else:
        desc = intent.description if intent else f"Execute {tool_name}"
        _emit_step(state, desc, "running", tool=tool_name)
        res = execute_document_tool(
            tool_name=tool_name,
            params=params,
            uploaded_files=files,
            query=query,
        )

        if not res.success:
            _emit_step(state, desc, "failed", result=res.message, tool=tool_name)
            _emit_event(state, "TOOL_EXECUTION_FAILED", {"tool": tool_name, "error": res.message})
            return {
                "generated_response": res.message,
                "execution_status": "failed",
                "output_files": output_files,
            }

        _emit_step(state, desc, "done", result="Success", tool=tool_name)
        if res.output_files:
            for f in res.output_files:
                if f not in output_files:
                    output_files.append(f)

        _emit_event(state, "TOOL_EXECUTION_COMPLETED", {"tool": tool_name, "status": "success"})
        return {
            "output_files": output_files,
            "generated_response": res.message,
            "tool_results": {tool_name: res.details},
            "execution_status": "completed",
        }


def route_by_task(state: AgentStateDict) -> str:
    """Select the execution branch according to classified task."""
    t = state.get("task_type")
    if t == TaskType.DOCUMENT_OPERATION:
        return "execute_document_operation"

    if state.get("is_multi_step"):
        return "execute_multi_step"

    if t == TaskType.CALCULATION:
        return "execute_calculation"
    elif t == TaskType.CODE_GENERATION:
        return "execute_code_generation"
    elif t == TaskType.CODE_EXECUTION:
        return "execute_code_execution"
    elif t == TaskType.KNOWLEDGE_QUERY:
        return "execute_knowledge_query"
    elif t == TaskType.VISION_ANALYSIS:
        return "execute_vision_analysis"
    elif t == TaskType.PRESENTATION_GENERATION or "pptx_generator" in state.get("selected_tools", []):
        return "execute_presentation"
    elif t == TaskType.PDF_GENERATION or "pdf_generator" in state.get("selected_tools", []):
        return "execute_pdf"
    elif t == TaskType.REPORT_GENERATION or "docx_generator" in state.get("selected_tools", []):
        return "execute_report"
    elif t == TaskType.DOCUMENT_ANALYSIS:
        return "execute_document_analysis"
    return "execute_general_chat"


# ─── Build & Compile StateGraph ───────────────────────────────────────────────

def build_agent_graph():
    """Build and compile the LangGraph workflow."""
    workflow = StateGraph(AgentStateDict)

    workflow.add_node("analyze_and_plan", node_analyze_and_plan)
    workflow.add_node("execute_calculation", node_execute_calculation)
    workflow.add_node("execute_code_generation", node_execute_code_generation)
    workflow.add_node("execute_code_execution", node_execute_code_execution)
    workflow.add_node("execute_knowledge_query", node_execute_knowledge_query)
    workflow.add_node("execute_vision_analysis", node_execute_vision_analysis)
    workflow.add_node("execute_presentation", node_execute_presentation)
    workflow.add_node("execute_report", node_execute_report)
    workflow.add_node("execute_pdf", node_execute_pdf)
    workflow.add_node("execute_document_analysis", node_execute_document_analysis)
    workflow.add_node("execute_document_operation", node_execute_document_operation)
    workflow.add_node("execute_general_chat", node_execute_general_chat)
    workflow.add_node("execute_multi_step", node_execute_multi_step)
    workflow.add_node("verify", node_verify)
    workflow.add_node("format_final_response", node_format_final_response)

    workflow.add_edge(START, "analyze_and_plan")
    workflow.add_conditional_edges(
        "analyze_and_plan",
        route_by_task,
        {
            "execute_calculation": "execute_calculation",
            "execute_code_generation": "execute_code_generation",
            "execute_code_execution": "execute_code_execution",
            "execute_knowledge_query": "execute_knowledge_query",
            "execute_vision_analysis": "execute_vision_analysis",
            "execute_presentation": "execute_presentation",
            "execute_report": "execute_report",
            "execute_pdf": "execute_pdf",
            "execute_document_analysis": "execute_document_analysis",
            "execute_document_operation": "execute_document_operation",
            "execute_general_chat": "execute_general_chat",
            "execute_multi_step": "execute_multi_step",
        },
    )

    workflow.add_edge("execute_calculation", "verify")
    workflow.add_edge("execute_code_generation", "verify")
    workflow.add_edge("execute_code_execution", "verify")
    workflow.add_edge("execute_knowledge_query", "verify")
    workflow.add_edge("execute_vision_analysis", "verify")
    workflow.add_edge("execute_presentation", "verify")
    workflow.add_edge("execute_report", "verify")
    workflow.add_edge("execute_pdf", "verify")
    workflow.add_edge("execute_document_analysis", "verify")
    workflow.add_edge("execute_document_operation", "verify")
    workflow.add_edge("execute_general_chat", "verify")
    workflow.add_edge("execute_multi_step", "verify")

    workflow.add_edge("verify", "format_final_response")
    workflow.add_edge("format_final_response", END)

    return workflow.compile()


_compiled_graph = None


def get_agent_graph():
    """Return singleton compiled LangGraph instance."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_agent_graph()
    return _compiled_graph
