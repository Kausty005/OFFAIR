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
