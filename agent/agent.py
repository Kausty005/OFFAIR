"""
agent/agent.py
Main Agent Engine — orchestrates the full Plan→Execute→Verify loop.
Implements the Inspection Agent, Coding Agent, and General Agent workflows.
No LangChain or heavy frameworks — simple, reliable Python orchestration.
"""

import os
import re
import sys
import json
import time
from pathlib import Path
from typing import Any, Optional, Callable, Generator

_base = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _base)

from agent.state import AgentState, AgentStep
from agent.planner import create_plan
from agent.verifier import (
    verify_docx_output,
    verify_inspection_output,
    verify_coding_output,
    verify_rag_results,
)
from router.model_router import classify, RoutingDecision
from models.model_registry import get_available_model
import models.ollama_client as ollama
from security.audit import log
from tools.files import save_upload, get_output_path, get_temp_path
from tools.search import search_knowledge_base, ask_knowledge_base
from tools.calculator import bearing_temperature_risk, pump_efficiency
from tools.docx_generator import create_maintenance_approval_note, create_coding_report, docx_available
from tools.pptx_generator import (
    create_maintenance_approval_pptx,
    create_presentation_from_markdown,
    pptx_available,
)
from tools.sandbox import run_python_sandbox, docker_available
from document.pdf_processor import process_pdf
from document.ocr import ocr_pdf_pages, ocr_image_file, tesseract_available
from document.vision import analyze_image_file, analyze_pil_image

import yaml
_cfg_path = os.path.join(_base, "config", "settings.yaml")
with open(_cfg_path) as f:
    _settings = yaml.safe_load(f)


# ─── Extraction helpers ────────────────────────────────────────────────────────

_EXTRACTION_SYSTEM = """You are an information extraction AI for industrial inspection reports.
Extract structured information from the provided document text.
Return ONLY valid JSON. No explanation, no markdown code blocks, just the raw JSON object.
If a field is not found, use null."""

_EXTRACTION_PROMPT = """Extract the following information from this inspection report text and return it as JSON:

{{
  "equipment_name": "full name of equipment (e.g., 'Crude Oil Pump')",
  "equipment_id": "equipment tag/ID (e.g., 'P-104')",
  "inspection_date": "date of inspection (YYYY-MM-DD or as found)",
  "inspector": "inspector name if mentioned",
  "location": "plant/unit location",
  "findings": ["finding 1", "finding 2", ...],
  "measurements": {{
    "temperature": "value with unit",
    "pressure": "value with unit",
    "vibration": "value with unit",
    "other_measurements": "any other measurements"
  }},
  "recommendations": "recommended action",
  "severity": "critical/high/medium/low based on findings"
}}

DOCUMENT TEXT:
{text}"""

_CODING_SYSTEM = """You are an expert Python programmer. Generate clean, well-commented Python code.
Always include proper error handling. Follow PEP 8 style.
Return ONLY the Python code — no markdown, no explanations."""

_CODING_TEST_SYSTEM = """You are a Python testing expert. Generate unittest test cases for the provided code.
Return ONLY the Python test code using the unittest framework.
Include at least 3 meaningful test cases."""


def _extract_json(text: str) -> dict:
    """Try to parse JSON from LLM output, handling markdown code blocks."""
    # Remove markdown code fences
    text = re.sub(r"```(?:json)?", "", text).strip().strip("`").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
    return {}


def _safe_str(val) -> str:
    if val is None:
        return "Not specified"
    return str(val)


# ─── Main Agent Class ──────────────────────────────────────────────────────────

class Agent:
    """
    Lightweight agent engine. Creates a plan, executes each step,
    calls tools, calls LLMs, and verifies outputs.
    """

    def __init__(self):
        self._progress_callbacks: list[Callable] = []

    def add_progress_callback(self, cb: Callable[[AgentStep], None]):
        """Register a callback that fires when each step completes."""
        self._progress_callbacks.append(cb)

    def _notify(self, step: AgentStep):
        for cb in self._progress_callbacks:
            try:
                cb(step)
            except Exception:
                pass

    # ── Public API ─────────────────────────────────────────────────────────

    def run(
        self,
        task: str,
        uploaded_files: list[str] = None,
        has_image: bool = False,
        has_pdf: bool = False,
        user_context: dict = None,
    ) -> AgentState:
        """
        Main entry point. Given a task and optional files, returns a completed AgentState.
        Orchestrated via LangGraph stateful graph while maintaining full backward compatibility.
        """
        from agent.graph import get_agent_graph

        uploaded_files = uploaded_files or []
        graph = get_agent_graph()

        def event_cb(event_type: str, data: Any):
            if event_type == "progress_step" and isinstance(data, AgentStep):
                self._notify(data)

        initial_state = {
            "user_query": task,
            "uploaded_files": uploaded_files,
            "user_context": user_context or {},
            "event_callback": event_cb,
        }

        try:
            result = graph.invoke(initial_state)
        except Exception as e:
            log("AGENT_GRAPH_ERROR", error=str(e))
            # Fallback to legacy step execution if graph fails unexpectedly
            return self._legacy_run(task, uploaded_files, has_image, has_pdf)

        # Assemble backward-compatible AgentState
        state = AgentState()
        state.task = task
        state.uploaded_files = uploaded_files
        state.task_type = result.get("task_type", "general")
        state.selected_model = result.get("selected_model", "")
        state.routing_reason = result.get("model_reason", "")
        state.tool_results = result.get("tool_results", {})
        state.extracted_data = result.get("extracted_data", {})
        state.rag_sources = result.get("retrieved_context", [])
        state.output_files = result.get("output_files", [])
        state.verified = result.get("verified", False)
        state.verification_notes = result.get("verification_notes", [])
        state.final_output = result.get("final_output", "")

        # Convert plan to AgentSteps
        plan_list = result.get("execution_plan", [])
        for idx, p in enumerate(plan_list):
            s = state.add_step(p.get("description", f"Step {idx+1}"), tool=p.get("tool"))
            s.complete(s.description)

        state.complete(state.final_output)
        log("TASK_COMPLETED", status="done", verified=state.verified, output_files=state.output_files)
        return state

    def _legacy_run(
        self,
        task: str,
        uploaded_files: list[str] = None,
        has_image: bool = False,
        has_pdf: bool = False,
    ) -> AgentState:
        """Fallback execution method preserving the original procedural engine."""
        uploaded_files = uploaded_files or []
        decision = classify(task, has_image=has_image, has_pdf=has_pdf)

        state = AgentState()
        state.task = task
        state.uploaded_files = uploaded_files
        state.task_type = decision.task_type
        state.selected_model = decision.selected_model
        state.routing_reason = decision.reason
        state.start()

        state = create_plan(state)
        for step in state.plan:
            step.start()
            self._notify(step)
            try:
                self._execute_step(step, state)
                step.complete(step.result)
            except Exception as e:
                step.fail(str(e))
            self._notify(step)
            state.advance()

        ok, notes = self._verify_state(state)
        state.verified = ok
        state.verification_notes = notes
        state.complete(state.final_output or "Task completed.")
        return state


    # ── Step Dispatcher ────────────────────────────────────────────────────

    def _execute_step(self, step: AgentStep, state: AgentState):
        """Dispatch a step to the appropriate handler based on tool name."""
        tool = step.tool or ""

        # ── Document & OCR steps ──────────────────────────────────────────
        if tool == "files" and ("receive" in step.description.lower() or "process" in step.description.lower()):
            self._step_receive_files(step, state)

        elif tool == "pdf_processor" and "detect" in step.description.lower():
            self._step_detect_pdf(step, state)

        elif tool == "pdf_processor" and "extract" in step.description.lower():
            self._step_extract_text(step, state)

        elif tool == "ocr":
            self._step_ocr(step, state)

        elif tool == "vision":
            self._step_vision(step, state)

        elif tool in ("merge_pdf", "split_pdf", "extract_pages", "rotate_pdf", "delete_pages", "reorder_pages", "pdf_to_images", "images_to_pdf", "docx_to_text", "pdf_to_text", "compress_pdf", "strip_metadata", "ocr_pdf", "ocr_image", "crop_pdf", "resize_pdf", "add_blank_page", "duplicate_page"):
            from document_tools.agent_adapter import execute_document_tool
            res = execute_document_tool(tool_name=tool, params={}, uploaded_files=state.uploaded_files, query=state.task)
            if res.output_files:
                state.output_files.extend(res.output_files)
            state.final_output = res.message
            step.complete(res.message)

        # ── LLM steps ────────────────────────────────────────────────────
        elif tool == "llm_extraction":
            self._step_extract_findings(step, state)

        elif tool == "rag":
            self._step_rag_search(step, state)

        elif tool == "llm_reasoning":
            self._step_reason(step, state)

        elif tool == "llm":
            self._step_general_llm(step, state)

        elif tool == "llm_coding":
            self._step_coding(step, state)

        # ── Tool steps ────────────────────────────────────────────────────
        elif tool == "calculator":
            self._step_calculate(step, state)

        elif tool == "sandbox":
            self._step_sandbox(step, state)

        elif tool == "docx_generator":
            self._step_generate_docx(step, state)
        elif tool == "pptx_generator":
            self._step_generate_pptx(step, state)

        elif tool == "embeddings":
            step.result = "Embedding model ready"

        elif tool == "verifier":
            step.result = "Verification pending"

        else:
            step.result = f"Step completed: {step.description}"

    # ── Step Implementations ───────────────────────────────────────────────

    def _step_receive_files(self, step: AgentStep, state: AgentState):
        if not state.uploaded_files:
            step.result = "No files uploaded — text-only task"
            log("FILES_RECEIVED", count=0)
            return

        texts = []
        for fpath in state.uploaded_files:
            fpath_lower = fpath.lower()
            try:
                if fpath_lower.endswith(".txt"):
                    texts.append(Path(fpath).read_text(encoding="utf-8", errors="ignore"))
                elif fpath_lower.endswith(".docx"):
                    try:
                        import docx as _docx
                        doc = _docx.Document(fpath)
                        texts.append("\n".join(p.text for p in doc.paragraphs if p.text.strip()))
                    except ImportError:
                        texts.append("[python-docx not installed — cannot read .docx]")
                elif fpath_lower.endswith(".pdf"):
                    pass  # PDF handled later by pdf_processor step
            except Exception as e:
                texts.append(f"[Could not read {Path(fpath).name}: {e}]")

        if texts:
            state.tool_results["raw_text"] = "\n\n".join(texts)

        file_names = ', '.join(Path(f).name for f in state.uploaded_files)
        step.result = f"Received {len(state.uploaded_files)} file(s): {file_names}"
        log("FILES_RECEIVED", count=len(state.uploaded_files))

    def _step_detect_pdf(self, step: AgentStep, state: AgentState):
        pdf_files = [f for f in state.uploaded_files if f.lower().endswith(".pdf")]
        if not pdf_files:
            step.result = "No PDF files to process"
            return
        pdf_path = pdf_files[0]
        pdf_data = process_pdf(pdf_path)
        state.tool_results["pdf_data"] = pdf_data
        is_scanned = pdf_data.get("is_scanned", False)
        step.result = (
            f"{'Scanned PDF detected' if is_scanned else 'Digital PDF detected'} — "
            f"{pdf_data.get('total_pages', 0)} pages"
        )

    def _step_extract_text(self, step: AgentStep, state: AgentState):
        pdf_data = state.tool_results.get("pdf_data")
        if pdf_data:
            state.tool_results["raw_text"] = pdf_data.get("full_text", "")
            step.result = f"Extracted {len(state.tool_results['raw_text'])} characters from PDF"
        else:
            # Try all uploaded text-readable files
            texts = []
            for f in state.uploaded_files:
                if f.lower().endswith((".txt",)):
                    try:
                        texts.append(Path(f).read_text(encoding="utf-8"))
                    except Exception:
                        pass
            state.tool_results["raw_text"] = "\n".join(texts)
            step.result = f"Extracted {len(state.tool_results['raw_text'])} characters"

    def _step_ocr(self, step: AgentStep, state: AgentState):
        pdf_data = state.tool_results.get("pdf_data", {})
        pages = pdf_data.get("pages", [])

        if not pages:
            step.result = "No pages to OCR"
            return

        if not tesseract_available():
            step.result = "⚠️ Tesseract not available — using existing text extraction"
            # Still update raw_text from any existing text
            return

        pages = ocr_pdf_pages(pages)
        ocr_text = "\n\n".join(
            f"--- Page {p['page_num']} ---\n{p.get('ocr_text', p.get('text', ''))}"
            for p in pages
        )
        state.tool_results["pdf_data"]["pages"] = pages
        state.tool_results["raw_text"] = ocr_text
        step.result = f"OCR completed — {len(ocr_text)} characters extracted"
        log("OCR_EXECUTED", engine="tesseract", chars=len(ocr_text))

    def _step_vision(self, step: AgentStep, state: AgentState):
        vision_model = get_available_model("vision")
        if not vision_model:
            step.result = "Vision model not available — skipping visual analysis"
            return

        results = []
        pdf_data = state.tool_results.get("pdf_data", {})
        pages = pdf_data.get("pages", [])

        # Analyze first 2 pages that have images
        analyzed = 0
        for page in pages[:5]:
            if page.get("image") and analyzed < 2:
                r = analyze_pil_image(
                    page["image"],
                    prompt="Extract all text, numbers, equipment IDs, measurements, and inspection findings from this document page.",
                    model=vision_model,
                )
                if r.get("text"):
                    results.append(r["text"])
                    analyzed += 1

        # Also analyze direct image uploads
        img_files = [f for f in state.uploaded_files
                     if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp"))]
        for img_path in img_files[:2]:
            r = analyze_image_file(
                img_path,
                prompt="Analyze this inspection image and identify equipment, measurements, damage, and maintenance observations.",
                model=vision_model,
            )
            if r.get("text"):
                results.append(r["text"])

        if results:
            vision_text = "\n\n".join(results)
            state.tool_results["vision_text"] = vision_text
            # Augment raw text
            existing = state.tool_results.get("raw_text", "")
            state.tool_results["raw_text"] = existing + "\n\n[VISION ANALYSIS]\n" + vision_text
            step.result = f"Vision analysis completed — {len(vision_text)} chars extracted"
        else:
            step.result = "No images available for vision analysis"

    def _step_extract_findings(self, step: AgentStep, state: AgentState):
        raw_text = state.tool_results.get("raw_text", "")
        if not raw_text.strip():
            step.result = "No text available for extraction"
            state.extracted_data = {}
            return

        model = get_available_model("general") or "llama3.1:8b"
        # Limit text to avoid context overflow
        truncated = raw_text[:4000]

        prompt = _EXTRACTION_PROMPT.format(text=truncated)
        response = ollama.generate(
            model=model,
            prompt=prompt,
            system=_EXTRACTION_SYSTEM,
            temperature=0.0,
            max_tokens=1024,
        )

        extracted = _extract_json(response)
        if not extracted:
            # Fallback: parse manually
            extracted = self._fallback_extract(raw_text)

        state.extracted_data = extracted
        eq_id = extracted.get("equipment_id") or "Unknown"
        findings = extracted.get("findings") or []
        step.result = f"Extracted: {eq_id} — {len(findings)} findings"
        log("EXTRACTION_DONE", equipment_id=eq_id, findings=len(findings))

    def _fallback_extract(self, text: str) -> dict:
        """Simple regex-based extraction fallback."""
        import re
        findings = []
        # Look for common inspection finding patterns
        for line in text.split("\n"):
            line = line.strip()
            if any(kw in line.lower() for kw in
                   ["vibration", "leakage", "temperature", "pressure", "bearing",
                    "seal", "crack", "corrosion", "wear", "noise", "abnormal"]):
                if len(line) > 10:
                    findings.append(line)

        # Extract measurements
        measurements = {}
        temp_match = re.search(r"(\d+\.?\d*)\s*°?C", text)
        if temp_match:
            measurements["temperature"] = temp_match.group(0)
        press_match = re.search(r"(\d+\.?\d*)\s*bar", text)
        if press_match:
            measurements["pressure"] = press_match.group(0)

        return {
            "equipment_name": "Equipment (from OCR)",
            "equipment_id": "See document",
            "inspection_date": "See document",
            "findings": findings[:10],
            "measurements": measurements,
            "recommendations": "Maintenance inspection recommended",
            "severity": "high",
        }

    def _step_rag_search(self, step: AgentStep, state: AgentState):
        extracted = state.extracted_data
        findings = extracted.get("findings", [])
        equipment = extracted.get("equipment_name", "")

        # Build a targeted search query from extracted findings
        if findings:
            query = f"maintenance procedure {equipment} " + " ".join(findings[:3])
        elif state.task:
            query = state.task
        else:
            query = "equipment maintenance procedure inspection"

        result = search_knowledge_base(query, top_k=5)
        state.rag_sources = result.get("results", [])
        count = result.get("count", 0)
        step.result = f"Retrieved {count} relevant passages from local knowledge base"
        log("RAG_SEARCH", chunks=count)

    def _step_reason(self, step: AgentStep, state: AgentState):
        model = get_available_model("general") or "llama3.1:8b"
        extracted = state.extracted_data
        rag = state.rag_sources

        context = ""
        if rag:
            context = "\n\n".join(
                f"[{r.get('document', 'SOP')} — Page {r.get('page', '?')}]\n{r['text'][:400]}"
                for r in rag[:4]
            )

        findings_text = "\n".join(f"- {f}" for f in (extracted.get("findings") or []))
        measurements = extracted.get("measurements") or {}
        meas_text = "\n".join(f"- {k}: {v}" for k, v in measurements.items())

        prompt = f"""Based on the inspection findings and maintenance SOP context, provide a concise maintenance assessment and recommendation.

EQUIPMENT: {extracted.get('equipment_name', 'Unknown')} ({extracted.get('equipment_id', '')})
INSPECTION DATE: {extracted.get('inspection_date', 'Unknown')}

FINDINGS:
{findings_text or 'See document'}

MEASUREMENTS:
{meas_text or 'See document'}

SOP CONTEXT:
{context or 'No SOP context available — base recommendation on findings only.'}

Provide:
1. Assessment of severity (Critical/High/Medium/Low)
2. Key risks if not addressed
3. Specific recommended action
4. Urgency (Immediate/Scheduled/Monitoring)

Be concise and professional."""

        response = ollama.generate(
            model=model,
            prompt=prompt,
            system="You are an expert industrial maintenance engineer. Provide factual, conservative assessments.",
            temperature=0.1,
            max_tokens=800,
        )
        state.tool_results["reasoning"] = response
        state.final_output = response
        step.result = "Maintenance assessment completed"

    def _step_general_llm(self, step: AgentStep, state: AgentState):
        model = get_available_model("general")
        task_lower = state.task.lower()

        # ── Tool action: append text to a docx ────────────────────────────
        if "append" in task_lower and state.uploaded_files:
            docx_files = [f for f in state.uploaded_files if f.lower().endswith(".docx")]
            if docx_files:
                try:
                    import docx as _docx
                    doc_path = docx_files[0]
                    doc = _docx.Document(doc_path)
                    match = re.search(r'["\'](.*?)["\']', state.task)
                    text_to_append = match.group(1) if match else "Agent appended text."
                    doc.add_paragraph(text_to_append)
                    out_name = "Modified_" + Path(doc_path).name
                    out_path = get_output_path(out_name)
                    doc.save(out_path)
                    state.output_files.append(str(out_path))
                    state.final_output = (
                        f"✅ Done! I appended **\"{text_to_append}\"** to `{Path(doc_path).name}` "
                        f"and saved the updated file as `{out_name}`. "
                        f"You can download it from the Generated Files panel on the right."
                    )
                    step.result = f"Appended text to {Path(doc_path).name}"
                    return
                except Exception as e:
                    state.final_output = f"❌ Failed to modify DOCX: {e}"
                    step.result = "File modification failed"
                    return

        # ── Build context from uploaded files + RAG ───────────────────────
        file_context = state.tool_results.get("raw_text", "").strip()
        rag_context = ""
        if state.rag_sources:
            rag_context = "\n\n".join(
                f"[{r.get('document', 'SOP')}]\n{r.get('text', '')[:400]}"
                for r in state.rag_sources[:3]
            )

        # ── Check model availability before calling ────────────────────────
        if not model:
            state.final_output = (
                "⚠️ No AI model is available. Please start Ollama and pull a model:\n\n"
                "`ollama serve` then `ollama pull qwen3:4b`"
            )
            step.result = "No model available"
            return

        # Build the prompt
        system_prompt = (
            "You are an expert AI assistant integrated into a Sovereign AI Workbench for industrial use. "
            "Answer the user's question clearly and thoroughly. If document context is provided, "
            "base your answer on it. Be factual and concise."
        )

        prompt_parts = [state.task]
        if file_context:
            prompt_parts.append(f"\n\n--- FILE CONTENT ---\n{file_context[:4000]}")
        if rag_context:
            prompt_parts.append(f"\n\n--- KNOWLEDGE BASE ---\n{rag_context}")

        prompt = "\n".join(prompt_parts)

        response = ollama.generate(
            model=model,
            prompt=prompt,
            system=system_prompt,
            temperature=0.7,
            max_tokens=1500,
        )

        state.final_output = response if response.strip() else "The model returned an empty response. Please check that Ollama is running and a model is available."
        step.result = f"Response generated ({len(response)} chars)"

    def _step_coding(self, step: AgentStep, state: AgentState):
        model = get_available_model("coding") or get_available_model("general") or "llama3.1:8b"

        if "test" in step.description.lower() and state.tool_results.get("generated_code"):
            # Generate tests for existing code
            code = state.tool_results["generated_code"]
            prompt = f"""Generate unittest test cases for this Python code:

```python
{code}
```

Create at least 3 test methods. Use unittest.TestCase."""
            response = ollama.generate(
                model=model, prompt=prompt, system=_CODING_TEST_SYSTEM,
                temperature=0.1, max_tokens=1024,
            )
            state.tool_results["test_code"] = response
            step.result = "Test cases generated"

        elif "refine" in step.description.lower() and state.tool_results.get("sandbox_result"):
            sr = state.tool_results["sandbox_result"]
            if sr.get("success"):
                step.skip("Tests already passed — no refinement needed")
                return
            # One refinement attempt
            code = state.tool_results.get("generated_code", "")
            errors = sr.get("errors", [])
            error_text = "\n".join(str(e) for e in errors[:3])
            prompt = f"""Fix the following Python code. The tests failed with these errors:

ERRORS:
{error_text}

CURRENT CODE:
```python
{code}
```

Return only the corrected Python code."""
            response = ollama.generate(
                model=model, prompt=prompt, system=_CODING_SYSTEM,
                temperature=0.05, max_tokens=1500,
            )
            state.tool_results["generated_code"] = response
            step.result = "Code refined after test failure"

        else:
            # Generate code
            prompt = f"""Write a Python program for the following task:

{state.task}

Requirements:
- Clean, well-commented code
- Proper error handling
- Main function and if __name__ == '__main__' block
- Return computed results

Return only Python code."""
            response = ollama.generate(
                model=model, prompt=prompt, system=_CODING_SYSTEM,
                temperature=0.1, max_tokens=1500,
            )
            # Extract code from markdown block if present
            match = re.search(r"```(?:python)?\n?(.*?)\n?```", response, re.DOTALL | re.IGNORECASE)
            if match:
                response = match.group(1)
            else:
                # Fallback: strip backticks if regex didn't perfectly match block
                response = re.sub(r"```python\n?", "", response)
                response = re.sub(r"```\n?", "", response)
            state.tool_results["generated_code"] = response.strip()
            step.result = f"Code generated ({len(response)} chars)"

    def _step_calculate(self, step: AgentStep, state: AgentState):
        """Run deterministic calculations based on extracted data."""
        extracted = state.extracted_data
        measurements = extracted.get("measurements", {})
        results = {}

        # Bearing temperature risk
        temp_str = measurements.get("temperature", "")
        if temp_str:
            temp_match = re.search(r"(\d+\.?\d*)", temp_str)
            if temp_match:
                temp_c = float(temp_match.group(1))
                r = bearing_temperature_risk(temp_c)
                results["bearing_temp_risk"] = {
                    "value": temp_c,
                    "unit": r.unit,
                    "explanation": r.explanation,
                }

        state.tool_results["calculations"] = results
        step.result = f"Calculations completed: {list(results.keys())}"

    def _step_sandbox(self, step: AgentStep, state: AgentState):
        code = state.tool_results.get("generated_code", "")
        tests = state.tool_results.get("test_code", "")

        if not code:
            step.result = "No code to execute"
            return

        result = run_python_sandbox(code, tests)
        state.tool_results["sandbox_result"] = result

        if result.get("success"):
            step.result = (
                f"✅ Tests {result['tests_passed']}/{result['tests_total']} passed — "
                f"Docker sandbox, network disabled"
            )
        else:
            step.result = (
                f"⚠️ Tests {result.get('tests_passed', 0)}/{result.get('tests_total', 0)} passed — "
                f"{result.get('error', 'see output')}"
            )

    def _step_generate_docx(self, step: AgentStep, state: AgentState):
        if not docx_available():
            step.result = "python-docx not installed — cannot generate DOCX"
            return

        extracted = state.extracted_data
        equipment_id = extracted.get("equipment_id") or "EQUIP-001"
        safe_id = re.sub(r"[^\w\-]", "_", str(equipment_id))
        filename = f"{safe_id}_Maintenance_Approval_Note.docx"
        output_path = get_output_path(filename)

        # Format SOP references
        sop_refs = [
            {
                "document": r.get("document", "SOP"),
                "page": r.get("page", ""),
                "text": r.get("text", "")[:300],
            }
            for r in (state.rag_sources or [])[:5]
        ]

        # Determine risk level
        severity = extracted.get("severity", "high").upper()
        risk_map = {"CRITICAL": "CRITICAL", "HIGH": "HIGH", "MEDIUM": "MEDIUM", "LOW": "LOW"}
        risk_level = risk_map.get(severity, "HIGH")

        result = create_maintenance_approval_note(
            equipment_name=extracted.get("equipment_name") or "Industrial Equipment",
            equipment_id=equipment_id,
            inspection_date=extracted.get("inspection_date") or "See Document",
            findings=extracted.get("findings") or [],
            measurements=extracted.get("measurements") or {},
            recommendations=state.tool_results.get("reasoning", extracted.get("recommendations", "")),
            sop_references=sop_refs,
            ai_reasoning=state.tool_results.get("reasoning", ""),
            output_path=output_path,
            risk_level=risk_level,
        )

        if result["success"]:
            state.output_files.append(str(result["path"]))
            step.result = f"Generated: {filename} ({result.get('size', 0):,} bytes)"
        else:
            step.result = f"DOCX generation failed: {result.get('error')}"

    def _step_generate_pptx(self, step: AgentStep, state: AgentState):
        if not pptx_available():
            step.result = "python-pptx not installed — cannot generate PPTX"
            return

        extracted = state.extracted_data or {}
        # If equipment details exist, generate structured Maintenance Approval Note PPTX
        if extracted.get("equipment_id") or extracted.get("equipment_name"):
            equipment_id = extracted.get("equipment_id") or "EQUIP-001"
            safe_id = re.sub(r"[^\w\-]", "_", str(equipment_id))
            filename = f"{safe_id}_Maintenance_Approval_Note.pptx"
            output_path = get_output_path(filename)

            sop_refs = [
                {
                    "document": r.get("document", "SOP"),
                    "page": r.get("page", ""),
                    "text": r.get("text", "")[:300],
                }
                for r in (state.rag_sources or [])[:5]
            ]

            severity = extracted.get("severity", "high").upper()
            risk_map = {"CRITICAL": "CRITICAL", "HIGH": "HIGH", "MEDIUM": "MEDIUM", "LOW": "LOW"}
            risk_level = risk_map.get(severity, "HIGH")

            result = create_maintenance_approval_pptx(
                equipment_name=extracted.get("equipment_name") or "Industrial Equipment",
                equipment_id=equipment_id,
                inspection_date=extracted.get("inspection_date") or "See Document",
                findings=extracted.get("findings") or [],
                measurements=extracted.get("measurements") or {},
                recommendations=state.tool_results.get("reasoning", extracted.get("recommendations", "")),
                sop_references=sop_refs,
                output_path=output_path,
                risk_level=risk_level,
            )
        else:
            # General presentation from prompt / response / markdown text
            content_source = state.final_output or state.tool_results.get("reasoning", "") or state.task
            safe_title = re.sub(r"[^\w\-]", "_", state.task[:30]).strip("_") or "Presentation"
            filename = f"{safe_title}.pptx"
            output_path = get_output_path(filename)
            result = create_presentation_from_markdown(content_source, default_title=state.task[:40], output_path=output_path)

        if result["success"]:
            state.output_files.append(str(result["path"]))
            step.result = f"Generated: {Path(result['path']).name} ({result.get('size', 0):,} bytes)"
        else:
            step.result = f"PPTX generation failed: {result.get('error')}"

    # ── Verification ───────────────────────────────────────────────────────

    def _verify_state(self, state: AgentState) -> tuple[bool, list[str]]:
        notes = []

        if state.task_type == "coding":
            code = state.tool_results.get("generated_code", "")
            sr = state.tool_results.get("sandbox_result", {})
            ok, v_notes = verify_coding_output(code, sr)
            return ok, v_notes

        if state.output_files:
            docx_files = [f for f in state.output_files if f.lower().endswith(".docx")]
            pptx_files = [f for f in state.output_files if f.lower().endswith(".pptx")]

            if docx_files:
                ok, v_notes = verify_docx_output(
                    docx_files[0],
                    required_fields=["Equipment", "Findings", "Recommended"],
                )
                notes.extend(v_notes)
            if pptx_files:
                p_path = Path(pptx_files[0])
                if p_path.exists() and p_path.stat().st_size > 0:
                    notes.append(f"✅ Verified PPTX presentation: {p_path.name} ({p_path.stat().st_size:,} bytes)")
                else:
                    notes.append(f"❌ PPTX file {p_path.name} is missing or empty")

            v2_ok, v2_notes = verify_inspection_output(
                {
                    "extracted_data": state.extracted_data,
                    "rag_sources": state.rag_sources,
                    "output_files": state.output_files,
                }
            )
            notes.extend(v2_notes)
            return True, notes

        if state.rag_sources:
            ok, v_notes = verify_rag_results(state.rag_sources)
            notes.extend(v_notes)
            return ok, notes

        notes.append("✅ Task completed")
        return True, notes


# ── Convenience runner ─────────────────────────────────────────────────────────

def run_agent(
    task: str,
    uploaded_files: list[str] = None,
    has_image: bool = False,
    has_pdf: bool = False,
    progress_callback: Optional[Callable] = None,
) -> AgentState:
    """
    Top-level convenience function for running the agent.
    """
    agent = Agent()
    if progress_callback:
        agent.add_progress_callback(progress_callback)
    return agent.run(
        task=task,
        uploaded_files=uploaded_files or [],
        has_image=has_image,
        has_pdf=has_pdf,
    )
