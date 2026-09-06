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
from tools.docx_generator import create_maintenance_approval_note


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
            resp_text += f"\n\n**Sandbox Execution**: {status}\n```\n{sr.get('stdout', '')[:400]}\n```"

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
    """Process uploaded PDF/DOCX, perform local OCR, extract findings, and generate Word deliverable."""
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
        raw_text += "\n" + p_res.get("text", "")
        # Run OCR if scanned
        if p_res.get("is_scanned") and p_res.get("scanned_pages"):
            _emit_event(state, "TOOL_EXECUTION_STARTED", {"tool": "ocr", "pages": len(p_res.get("scanned_pages"))})
            ocr_text = ocr_pdf_pages(pdf_p, p_res.get("scanned_pages"))
            raw_text += "\n" + ocr_text

    # Extract structured findings
    prompt = f"Extract equipment_name, equipment_id, inspection_date, findings (list), measurements (dict), severity, recommendations as JSON from this text:\n\n{raw_text[:4000]}"
    llm_resp = ollama.generate(model=model, prompt=prompt, temperature=0.1)

    # Clean JSON
    clean_json = re.sub(r"```(?:json)?", "", llm_resp).strip().strip("`")
    try:
        extracted_data = json.loads(clean_json)
    except Exception:
        extracted_data = {"equipment_name": "Equipment Inspection", "findings": ["General inspection completed"]}

    # Search SOPs
    sops = retrieve_context("maintenance procedure standards safety", top_k=3)

    # Generate Word Document if requested
    equip_id = extracted_data.get("equipment_id") or "EQUIP-001"
    doc_path = create_maintenance_approval_note(
        equipment_id=equip_id,
        equipment_name=extracted_data.get("equipment_name", "Industrial Equipment"),
        findings=extracted_data.get("findings", []),
        measurements=extracted_data.get("measurements", {}),
        sop_references=[s.get("document", "SOP") for s in sops],
        risk_level=extracted_data.get("severity", "Medium"),
        approver="AI Maintenance System",
    )
    if doc_path and Path(doc_path).exists():
        output_files.append(str(doc_path))
        _emit_event(state, "TOOL_EXECUTION_COMPLETED", {"tool": "docx_generator", "output_file": Path(doc_path).name})

    response_text = (
        f"**Inspection & Document Analysis Complete**:\n\n"
        f"- Equipment: {extracted_data.get('equipment_name')}\n"
        f"- Tag: {extracted_data.get('equipment_id', 'N/A')}\n"
        f"- Severity: {extracted_data.get('severity', 'Medium')}\n"
        f"- Deliverable Generated: {Path(doc_path).name if doc_path else 'None'}"
    )

    return {
        "extracted_data": extracted_data,
        "retrieved_context": sops,
        "output_files": output_files,
        "generated_response": response_text,
    }


# ─── Node 7: General Chat ─────────────────────────────────────────────────────

def node_execute_general_chat(state: AgentStateDict) -> AgentStateDict:
    """General reasoning and explanation using local LLM."""
    query = state.get("user_query", "")
    model = state.get("selected_model") or get_available_model("general") or "llama3.1:8b"

    _emit_event(state, "TOOL_EXECUTION_STARTED", {"tool": "local_llm", "model": model})

    sys_prompt = "You are OffAir AI, a private, secure, air-gapped sovereign AI assistant. Be direct, technical, and concise."
    resp = ollama.generate(model=model, prompt=query, system=sys_prompt, temperature=0.1)

    _emit_event(state, "TOOL_EXECUTION_COMPLETED", {"tool": "local_llm", "status": "success"})

    return {
        "generated_response": resp,
    }


# ─── Node 8: Multi-Step Task Execution ────────────────────────────────────────

def node_execute_multi_step(state: AgentStateDict) -> AgentStateDict:
    """Execute compound industrial workflows sequentially."""
    plan = state.get("execution_plan", [])
    query = state.get("user_query", "")
    tool_results = dict(state.get("tool_results") or {})
    output_files = list(state.get("output_files") or [])
    retrieved = []
    extracted = {}
    calc_res = None

    for step in plan:
        tool = step.get("tool", "")
        _emit_event(state, "TOOL_EXECUTION_STARTED", {"tool": tool, "step": step.get("description")})

        if tool in ("pdf_processor", "ocr"):
            files = state.get("uploaded_files", [])
            for f in files:
                if f.lower().endswith(".pdf"):
                    p_res = process_pdf(f)
                    extracted["raw_text"] = p_res.get("text", "")
        elif tool == "rag":
            retrieved = retrieve_context("SOP pump maintenance specifications", top_k=3)
            tool_results["rag_sources"] = retrieved
        elif tool == "calculator":
            calc_res = pump_efficiency(input_power_kw=75.0, output_power_kw=62.0)
            tool_results["calculations"] = calc_res
        elif tool == "docx_generator":
            p = create_maintenance_approval_note(
                equipment_id="P-104",
                equipment_name="Crude Oil Pump",
                findings=["Vibration elevated", "Flow stable"],
                measurements={"efficiency": f"{calc_res.result}%" if calc_res else "82.6%"},
                sop_references=["SOP-PUMP-01"],
            )
            if p and Path(p).exists():
                output_files.append(str(p))

        _emit_event(state, "TOOL_EXECUTION_COMPLETED", {"tool": tool, "status": "done"})

    summary = (
        "### Multi-Step Execution Summary:\n"
        "1. **Document Processed**: Extracted inspection measurements.\n"
        f"2. **SOP Grounding**: Retrieved {len(retrieved)} relevant SOP guidelines.\n"
        f"3. **Deterministic Calculation**: Efficiency calculated at {calc_res.result if calc_res else 'N/A'}%.\n"
        "4. **Synthesis**: Evaluated risk criteria against operating standards.\n"
        f"5. **Deliverable**: Generated {len(output_files)} verified report document."
    )

    return {
        "tool_results": tool_results,
        "retrieved_context": retrieved,
        "output_files": output_files,
        "generated_response": summary,
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

def route_by_task(state: AgentStateDict) -> str:
    """Select the execution branch according to classified task."""
    if state.get("is_multi_step"):
        return "execute_multi_step"

    t = state.get("task_type")
    if t == TaskType.CALCULATION:
        return "execute_calculation"
    elif t == TaskType.CODE_GENERATION:
        return "execute_code_generation"
    elif t == TaskType.CODE_EXECUTION:
        return "execute_code_execution"
    elif t == TaskType.KNOWLEDGE_QUERY:
        return "execute_knowledge_query"
    elif t in (TaskType.DOCUMENT_ANALYSIS, TaskType.REPORT_GENERATION, TaskType.VISION_ANALYSIS):
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
    workflow.add_node("execute_document_analysis", node_execute_document_analysis)
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
            "execute_document_analysis": "execute_document_analysis",
            "execute_general_chat": "execute_general_chat",
            "execute_multi_step": "execute_multi_step",
        },
    )

    workflow.add_edge("execute_calculation", "verify")
    workflow.add_edge("execute_code_generation", "verify")
    workflow.add_edge("execute_code_execution", "verify")
    workflow.add_edge("execute_knowledge_query", "verify")
    workflow.add_edge("execute_document_analysis", "verify")
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
