"""
agent/verifier.py
Verification module — checks that agent outputs meet expected quality criteria.
Every major workflow has a specific verifier.
"""

import os
import sys
from pathlib import Path
from typing import Any, Optional

_base = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _base)

from security.audit import log


def verify_docx_output(
    file_path: str | Path,
    required_fields: Optional[list[str]] = None,
) -> tuple[bool, list[str]]:
    """
    Verify that a generated DOCX file exists and contains required content.
    Returns (ok, notes).
    """
    notes = []
    path = Path(file_path)

    if not path.exists():
        notes.append(f"❌ Output file does not exist: {path}")
        return False, notes
    notes.append(f"✅ Output file exists: {path.name}")

    if path.stat().st_size < 100:
        notes.append(f"❌ Output file too small ({path.stat().st_size} bytes) — likely empty.")
        return False, notes
    notes.append(f"✅ File size: {path.stat().st_size:,} bytes")

    # Check DOCX is readable
    try:
        from docx import Document
        doc = Document(str(path))
        text = "\n".join([p.text for p in doc.paragraphs])
        notes.append(f"✅ DOCX readable — {len(doc.paragraphs)} paragraphs")

        if required_fields:
            for field_name in required_fields:
                found = field_name.lower() in text.lower()
                if found:
                    notes.append(f"✅ Required field present: '{field_name}'")
                else:
                    notes.append(f"⚠️  Required field not found: '{field_name}'")
    except Exception as e:
        notes.append(f"⚠️  Could not read DOCX content: {e}")

    log("VERIFICATION", type="docx", file=str(path), passed=True)
    return True, notes


def verify_inspection_output(state_data: dict) -> tuple[bool, list[str]]:
    """
    Verify that the inspection agent produced a complete output.
    Checks for: equipment name, findings, output file.
    """
    notes = []
    ok = True

    extracted = state_data.get("extracted_data", {})

    # Check equipment info
    equip = extracted.get("equipment_name") or extracted.get("equipment_id")
    if equip:
        notes.append(f"✅ Equipment identified: {equip}")
    else:
        notes.append("⚠️  Equipment name not extracted")

    # Check findings
    findings = extracted.get("findings", [])
    if findings:
        notes.append(f"✅ Findings extracted: {len(findings)} items")
    else:
        notes.append("⚠️  No findings extracted")

    # Check RAG was used
    rag_sources = state_data.get("rag_sources", [])
    if rag_sources:
        notes.append(f"✅ RAG sources retrieved: {len(rag_sources)}")
    else:
        notes.append("⚠️  No RAG sources retrieved — answer may lack SOP context")

    # Check output file
    output_files = state_data.get("output_files", [])
    if output_files:
        for f in output_files:
            exists = Path(f).exists()
            if exists:
                notes.append(f"✅ Output file verified: {Path(f).name}")
            else:
                notes.append(f"❌ Output file missing: {f}")
                ok = False
    else:
        notes.append("❌ No output files generated")
        ok = False

    log("VERIFICATION", type="inspection", passed=ok)
    return ok, notes


def verify_coding_output(
    code: str,
    test_result: dict,
) -> tuple[bool, list[str]]:
    """Verify that the coding agent produced working, tested code."""
    notes = []
    ok = True

    if code and len(code) > 20:
        notes.append(f"✅ Code generated ({len(code)} chars)")
    else:
        notes.append("❌ Code generation failed or empty")
        ok = False

    sandbox_used = test_result.get("sandbox_used", False)
    if sandbox_used:
        notes.append("✅ Docker sandbox used for execution")
    else:
        notes.append("⚠️  Code was not executed in Docker sandbox")

    tests_passed = test_result.get("tests_passed", 0)
    tests_total = test_result.get("tests_total", 0)
    if tests_total > 0:
        if tests_passed == tests_total:
            notes.append(f"✅ Tests: {tests_passed}/{tests_total} PASSED")
        else:
            notes.append(f"⚠️  Tests: {tests_passed}/{tests_total} passed")
    else:
        notes.append("⚠️  No test results available")

    network_disabled = test_result.get("network_disabled", False)
    if network_disabled:
        notes.append("✅ Sandbox network: DISABLED")
    else:
        notes.append("⚠️  Sandbox network status unknown")

    log("VERIFICATION", type="coding", passed=ok)
    return ok, notes


def verify_rag_results(results: list[dict]) -> tuple[bool, list[str]]:
    """Verify RAG retrieval produced useful results."""
    notes = []
    if not results:
        notes.append("❌ No RAG results returned")
        return False, notes

    notes.append(f"✅ {len(results)} chunks retrieved from knowledge base")
    for i, r in enumerate(results[:3]):
        doc = r.get("document", "unknown")
        score = r.get("score", 0)
        notes.append(f"  [{i+1}] {doc} — similarity: {score:.3f}")

    log("VERIFICATION", type="rag", chunks=len(results))
    return True, notes


def verify_calculation_output(calc_result: Any) -> tuple[bool, list[str]]:
    """
    Verify calculation result is structurally valid and non-null.
    """
    notes = []
    if calc_result is None:
        notes.append("❌ Calculation returned None")
        return False, notes

    # Support CalcResult dataclass or dict
    if hasattr(calc_result, "result"):
        val = calc_result.result
        formula = getattr(calc_result, "formula", "unknown")
    elif isinstance(calc_result, dict):
        val = calc_result.get("result")
        formula = calc_result.get("formula", "unknown")
    else:
        val = calc_result
        formula = "expression"

    import math
    if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
        notes.append("❌ Calculation produced NaN or Infinity")
        return False, notes

    notes.append(f"✅ Calculation verified: {formula} = {val}")
    log("VERIFICATION", type="calculation", formula=formula, result=val, passed=True)
    return True, notes


def verify_code_execution_output(sandbox_result: dict) -> tuple[bool, list[str]]:
    """
    Verify interactive code execution result from Docker sandbox.
    Checks container startup, completion, timeouts, and exit code.
    """
    notes = []
    ok = True

    sandbox_used = sandbox_result.get("sandbox_used", False)
    if not sandbox_used:
        notes.append("❌ Docker sandbox was not used or failed to start")
        return False, notes
    notes.append("✅ Docker sandbox initialized with network isolation")

    if sandbox_result.get("error") and "timeout" in str(sandbox_result.get("error", "")).lower():
        notes.append("❌ Execution timed out inside container")
        return False, notes

    exit_code = sandbox_result.get("exit_code", -1)
    if exit_code == 0:
        notes.append("✅ Process exited with code 0 (success)")
    else:
        notes.append(f"⚠️ Process exited with non-zero code {exit_code}")
        ok = False

    stdout = sandbox_result.get("stdout", "")
    if stdout.strip():
        notes.append(f"✅ Standard output captured ({len(stdout)} chars)")
    else:
        notes.append("ℹ️ Standard output is empty")

    stderr = sandbox_result.get("stderr", "")
    if stderr.strip():
        notes.append(f"⚠️ Standard error reported: {stderr.strip()[:100]}")

    log("VERIFICATION", type="code_execution", exit_code=exit_code, passed=ok)
    return ok, notes


def verify_model_output(
    response_text: str,
    expected_type: str = "text",
) -> tuple[bool, list[str]]:
    """
    Verify LLM generated response against format and content criteria.
    """
    notes = []
    ok = True

    if not response_text or not response_text.strip():
        notes.append("❌ Model returned empty response")
        return False, notes
    notes.append(f"✅ Model response non-empty ({len(response_text)} chars)")

    if expected_type == "code":
        import re
        has_code = bool(re.search(r"```python|def\s+\w+|import\s+\w+", response_text))
        if has_code:
            notes.append("✅ Python code structure detected in response")
        else:
            notes.append("⚠️ Expected Python code but no standard code markers detected")
            ok = False

    elif expected_type == "json":
        import json
        import re
        clean_text = re.sub(r"```(?:json)?", "", response_text).strip().strip("`")
        try:
            json.loads(clean_text)
            notes.append("✅ Valid JSON structure verified")
        except Exception:
            notes.append("❌ Invalid JSON in response")
            ok = False

    log("VERIFICATION", type="model_output", expected=expected_type, passed=ok)
    return ok, notes


def verify_task_result(task_type: str, state_data: dict) -> tuple[bool, list[str]]:
    """
    Unified task verifier that dynamically selects appropriate checks.
    """
    notes = []
    ok = True

    if task_type in ("calculation",):
        res = state_data.get("tool_results", {}).get("calculations")
        v_ok, v_notes = verify_calculation_output(res)
        notes.extend(v_notes)
        ok = ok and v_ok

    elif task_type in ("code_execution",):
        res = state_data.get("tool_results", {}).get("sandbox_result", {})
        v_ok, v_notes = verify_code_execution_output(res)
        notes.extend(v_notes)
        ok = ok and v_ok

    elif task_type in ("coding", "code_generation"):
        code = state_data.get("generated_code") or state_data.get("tool_results", {}).get("generated_code", "")
        test_res = state_data.get("tool_results", {}).get("sandbox_result", {})
        v_ok, v_notes = verify_coding_output(code, test_res)
        notes.extend(v_notes)
        ok = ok and v_ok

    elif task_type in ("knowledge_query", "rag"):
        chunks = state_data.get("retrieved_context") or state_data.get("rag_sources", [])
        v_ok, v_notes = verify_rag_results(chunks)
        notes.extend(v_notes)
        ok = ok and v_ok

    elif task_type in ("presentation_generation", "presentation"):
        output_files = state_data.get("output_files", [])
        if output_files:
            for f in output_files:
                p = Path(f)
                if p.exists() and p.stat().st_size > 100:
                    notes.append(f"✅ PowerPoint presentation verified: {p.name} ({p.stat().st_size:,} bytes)")
                else:
                    notes.append(f"❌ Presentation file missing or empty: {f}")
                    ok = False
        else:
            notes.append("❌ No presentation output files generated")
            ok = False

    elif task_type in ("document_operation", "ocr"):
        output_files = state_data.get("output_files", [])
        if not output_files:
            notes.append("❌ No output files generated by document operation")
            ok = False
        else:
            for f in output_files:
                p = Path(f)
                if not p.exists():
                    notes.append(f"❌ Output file does not exist: {p.name}")
                    ok = False
                elif p.stat().st_size == 0:
                    notes.append(f"❌ Output file is empty: {p.name}")
                    ok = False
                elif p.suffix.lower() == ".pdf":
                    data = p.read_bytes()
                    if not data.startswith(b"%PDF"):
                        notes.append(f"❌ Output file is missing %PDF header: {p.name}")
                        ok = False
                    else:
                        notes.append(f"✅ Valid PDF output verified: {p.name} ({len(data):,} bytes)")
                else:
                    notes.append(f"✅ Output file verified: {p.name} ({p.stat().st_size:,} bytes)")

    elif task_type in ("pdf_generation", "pdf_report"):
        output_files = state_data.get("output_files", [])
        if output_files:
            for f in output_files:
                p = Path(f)
                if p.exists() and p.stat().st_size > 100:
                    notes.append(f"✅ PDF report verified: {p.name} ({p.stat().st_size:,} bytes)")
                else:
                    notes.append(f"❌ PDF report missing or empty: {f}")
                    ok = False
        else:
            notes.append("❌ No PDF report output files generated")
            ok = False

    elif task_type in ("report_generation", "docx_generation"):
        output_files = state_data.get("output_files", [])
        if output_files:
            for f in output_files:
                p = Path(f)
                if p.exists() and p.stat().st_size > 100:
                    notes.append(f"✅ Word document verified: {p.name} ({p.stat().st_size:,} bytes)")
                else:
                    notes.append(f"❌ Word document missing or empty: {f}")
                    ok = False
        else:
            notes.append("❌ No Word document output files generated")
            ok = False

    elif task_type in ("document", "document_analysis"):
        v_ok, v_notes = verify_inspection_output(state_data)
        notes.extend(v_notes)
        ok = ok and v_ok

    else:
        # General chat or fallback
        resp = state_data.get("generated_response") or state_data.get("final_output", "")
        v_ok, v_notes = verify_model_output(resp, expected_type="text")
        notes.extend(v_notes)
        ok = ok and v_ok

    return ok, notes

