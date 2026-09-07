"""
tools/docx_generator.py
Professional Word document generator using python-docx.
Creates structured industrial documents with headers, tables, and footers.
"""

import os
import sys
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

_base = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _base)

from security.audit import log

try:
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    _DOCX_AVAILABLE = True
except ImportError:
    _DOCX_AVAILABLE = False


def _add_heading(doc, text: str, level: int = 1):
    heading = doc.add_heading(text, level=level)
    return heading


def _add_table(doc, headers: list[str], rows: list[list[str]]):
    """Add a styled table to the document."""
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Light Shading Accent 1"

    # Header row
    hdr = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = h
        for para in hdr[i].paragraphs:
            for run in para.runs:
                run.bold = True

    # Data rows
    for row_idx, row in enumerate(rows):
        cells = table.rows[row_idx + 1].cells
        for col_idx, val in enumerate(row):
            cells[col_idx].text = str(val)

    return table


def _add_footer(doc, text: str):
    """Add footer to all sections."""
    for section in doc.sections:
        footer = section.footer
        p = footer.paragraphs[0]
        p.text = text
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER


def create_maintenance_approval_note(
    equipment_name: str,
    equipment_id: str,
    inspection_date: str,
    findings: list[str],
    measurements: dict,
    recommendations: str,
    sop_references: list[dict],
    ai_reasoning: str,
    output_path: str | Path,
    risk_level: str = "HIGH",
) -> dict:
    """
    Generate a professional Maintenance Approval Note DOCX.

    Returns:
        {"success": bool, "path": str, "error": str|None}
    """
    if not _DOCX_AVAILABLE:
        return {"success": False, "path": "", "error": "python-docx not installed. Run: pip install python-docx"}

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        doc = Document()

        # ── Document Metadata ──────────────────────────────────────────────
        doc.core_properties.author = "Sovereign AI Workbench — SIH26117"
        doc.core_properties.title = "Maintenance Approval Note"
        doc.core_properties.subject = f"Equipment: {equipment_id}"

        # ── Title ──────────────────────────────────────────────────────────
        title = doc.add_heading("MAINTENANCE APPROVAL NOTE", 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        subtitle = doc.add_paragraph()
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = subtitle.add_run("⚠️  AI-GENERATED DRAFT — REQUIRES AUTHORIZED HUMAN REVIEW")
        run.bold = True

        doc.add_paragraph()  # Spacer

        # ── 1. Subject ─────────────────────────────────────────────────────
        _add_heading(doc, "1. Subject", 2)
        doc.add_paragraph(
            f"Request for maintenance approval for equipment {equipment_id} — {equipment_name} "
            f"based on inspection findings dated {inspection_date}."
        )

        # ── 2. Equipment Details ───────────────────────────────────────────
        _add_heading(doc, "2. Equipment Details", 2)
        _add_table(
            doc,
            headers=["Parameter", "Value"],
            rows=[
                ["Equipment Name", equipment_name],
                ["Equipment ID", equipment_id],
                ["Inspection Date", inspection_date],
                ["Risk Level", risk_level],
                ["Document Generated", datetime.now().strftime("%Y-%m-%d %H:%M")],
            ],
        )

        # ── 3. Inspection Summary ──────────────────────────────────────────
        _add_heading(doc, "3. Inspection Summary", 2)
        doc.add_paragraph(
            f"A detailed inspection of {equipment_name} ({equipment_id}) was conducted on {inspection_date}. "
            "The following observations were recorded and processed through the Sovereign AI Workbench (SIH26117) "
            "for automated analysis and approval note generation."
        )

        # ── 4. Key Findings ────────────────────────────────────────────────
        _add_heading(doc, "4. Key Findings", 2)
        if findings:
            for finding in findings:
                p = doc.add_paragraph(style="List Bullet")
                p.add_run(finding)
        else:
            doc.add_paragraph("No specific findings extracted.")

        # ── 5. Measurements ───────────────────────────────────────────────
        _add_heading(doc, "5. Measurements & Observations", 2)
        if measurements:
            meas_rows = [[k, str(v)] for k, v in measurements.items()]
            _add_table(doc, headers=["Parameter", "Measured Value"], rows=meas_rows)
        else:
            doc.add_paragraph("No specific measurements recorded.")

        # ── 6. SOP/Guideline References ────────────────────────────────────
        _add_heading(doc, "6. Relevant SOP / Guideline References", 2)
        if sop_references:
            for ref in sop_references:
                doc_name = ref.get("document", "")
                page = ref.get("page", "")
                snippet = ref.get("text", "")[:200]
                p = doc.add_paragraph(style="List Bullet")
                label = f"{doc_name}" + (f" — Page {page}" if page else "")
                p.add_run(label).bold = True
                if snippet:
                    doc.add_paragraph(f'   "{snippet}..."')
        else:
            doc.add_paragraph("No SOP references retrieved. Manual SOP lookup recommended.")

        # ── 7. Risk / Operational Considerations ──────────────────────────
        _add_heading(doc, "7. Risk / Operational Considerations", 2)
        risk_text = {
            "CRITICAL": "Immediate shutdown and maintenance required. Risk of equipment failure and safety incident.",
            "HIGH": "Maintenance should be scheduled at earliest opportunity. Monitor equipment closely in the interim.",
            "MEDIUM": "Schedule maintenance in next planned shutdown window. Continue monitoring.",
            "LOW": "Minor maintenance recommended during next scheduled service.",
        }.get(risk_level.upper(), "Consult maintenance engineer for risk assessment.")
        doc.add_paragraph(risk_text)

        # ── 8. Recommended Action ─────────────────────────────────────────
        _add_heading(doc, "8. Recommended Action", 2)
        doc.add_paragraph(recommendations or "Detailed inspection and maintenance by qualified engineer.")

        # ── 9. Approval Requested ─────────────────────────────────────────
        _add_heading(doc, "9. Approval Requested", 2)
        doc.add_paragraph(
            "Authorization is requested to proceed with the recommended maintenance action on "
            f"{equipment_name} ({equipment_id})."
        )
        doc.add_paragraph()
        _add_table(
            doc,
            headers=["Role", "Name", "Signature", "Date"],
            rows=[
                ["Maintenance Engineer", "", "_______________", ""],
                ["Section Head", "", "_______________", ""],
                ["Plant Manager", "", "_______________", ""],
            ],
        )

        # ── 10. AI Processing Audit Information ───────────────────────────
        _add_heading(doc, "10. AI Processing Audit Information", 2)
        _add_table(
            doc,
            headers=["Parameter", "Value"],
            rows=[
                ["AI System", "Sovereign AI Workbench (SIH26117)"],
                ["Inference", "LOCAL — No cloud API"],
                ["OCR", "LOCAL — Tesseract / Vision Model"],
                ["RAG", f"LOCAL — {len(sop_references)} sources retrieved"],
                ["External API Calls", "0"],
                ["Generated At", datetime.now().isoformat()],
                ["Human Review Required", "YES — This is a draft"],
            ],
        )

        doc.add_paragraph()
        disclaimer = doc.add_paragraph()
        run = disclaimer.add_run(
            "DISCLAIMER: This document was generated by an AI system as a draft for human review. "
            "All findings and recommendations must be verified by qualified personnel before any maintenance action is taken. "
            "The AI system does not have authority to approve maintenance operations."
        )
        run.italic = True

        # ── Footer ────────────────────────────────────────────────────────
        _add_footer(
            doc,
            f"SIH26117 Sovereign AI Workbench | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | LOCAL | DRAFT — HUMAN REVIEW REQUIRED"
        )

        # Save
        doc.save(str(output_path))
        log("DOCX_GENERATED", path=str(output_path), size=output_path.stat().st_size)

        return {
            "success": True,
            "path": str(output_path),
            "size": output_path.stat().st_size,
            "error": None,
        }

    except Exception as e:
        log("DOCX_ERROR", error=str(e))
        return {"success": False, "path": "", "error": str(e)}


def create_coding_report(
    prompt: str,
    code: str,
    test_code: str,
    sandbox_result: dict,
    output_path: str | Path,
) -> dict:
    """Generate a coding agent report DOCX."""
    if not _DOCX_AVAILABLE:
        return {"success": False, "path": "", "error": "python-docx not installed"}

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        doc = Document()
        doc.add_heading("CODING AGENT REPORT", 0)
        doc.add_paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        doc.add_heading("1. Task", 2)
        doc.add_paragraph(prompt)
        doc.add_heading("2. Generated Code", 2)
        doc.add_paragraph(code, style="No Spacing")
        doc.add_heading("3. Test Cases", 2)
        doc.add_paragraph(test_code or "No test cases.", style="No Spacing")
        doc.add_heading("4. Sandbox Execution Results", 2)
        _add_table(
            doc,
            headers=["Parameter", "Value"],
            rows=[
                ["Sandbox", "Docker"],
                ["Network", "DISABLED"],
                ["Tests Passed", str(sandbox_result.get("tests_passed", 0))],
                ["Tests Total", str(sandbox_result.get("tests_total", 0))],
                ["Success", str(sandbox_result.get("success", False))],
                ["Elapsed", f"{sandbox_result.get('elapsed_s', 0)}s"],
            ],
        )
        _add_footer(doc, f"SIH26117 Coding Agent | {datetime.now().strftime('%Y-%m-%d %H:%M')} | LOCAL EXECUTION")
        doc.save(str(output_path))
        log("DOCX_GENERATED", path=str(output_path), type="coding")
        return {"success": True, "path": str(output_path), "error": None}
    except Exception as e:
        return {"success": False, "path": "", "error": str(e)}


def create_document_from_markdown(
    content: str,
    title: Optional[str] = None,
    output_path: Optional[str | Path] = None,
) -> dict:
    """
    Generate a professional Word (.docx) document from markdown or plain text.

    Args:
        content: Markdown or plain text.
        title: Optional document title.
        output_path: Target filesystem path. If None, auto-generated in workspace/outputs/.

    Returns:
        dict: {"success": bool, "path": str, "size": int, "error": str | None}
    """
    if not _DOCX_AVAILABLE:
        return {"success": False, "path": "", "size": 0, "error": "python-docx not installed."}

    from tools.files import get_output_path
    import re

    # Determine output file path
    if output_path is None:
        safe_title = re.sub(r"[^\w\-]", "_", (title or "Document")[:30]).strip("_") or "Document"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_title}_{timestamp}.docx"
        out_file = get_output_path(filename)
    else:
        out_file = Path(output_path)

    out_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        doc = Document()

        # Metadata
        doc.core_properties.author = "Sovereign AI Workbench — OffAir AI"
        doc.core_properties.title = title or "Report"

        lines = content.strip().split("\n")
        if not title:
            for l in lines:
                if l.startswith("#"):
                    title = l.lstrip("#").strip()
                    break
            if not title:
                title = "Technical Report"

        # Document Title
        main_h = doc.add_heading(title, 0)
        main_h.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Subtitle / Generation info
        meta_p = doc.add_paragraph()
        meta_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        meta_run = meta_p.add_run(f"Generated on {datetime.now().strftime('%B %d, %Y at %H:%M')} | Sovereign AI Workbench")
        meta_run.font.size = Pt(9)
        meta_run.font.color.rgb = RGBColor(120, 120, 120)

        in_code_block = False
        table_lines = []

        for line in lines:
            stripped = line.strip()

            # Handle Markdown Table rows
            if "|" in stripped and stripped.startswith("|"):
                table_lines.append(stripped)
                continue
            elif table_lines:
                # Flush accumulated table
                _render_markdown_table(doc, table_lines)
                table_lines = []

            # Handle Code Blocks
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue

            if not stripped:
                continue

            if in_code_block:
                p = doc.add_paragraph(style="No Spacing")
                p.paragraph_format.left_indent = Inches(0.4)
                r = p.add_run(line)
                r.font.name = "Consolas"
                r.font.size = Pt(9.5)
                r.font.color.rgb = RGBColor(50, 50, 50)
            elif stripped.startswith("# "):
                doc.add_heading(stripped[2:].strip(), level=1)
            elif stripped.startswith("## "):
                doc.add_heading(stripped[3:].strip(), level=2)
            elif stripped.startswith("### "):
                doc.add_heading(stripped[4:].strip(), level=3)
            elif stripped.startswith("- ") or stripped.startswith("* "):
                bullet_txt = stripped[2:].strip()
                p = doc.add_paragraph(style="List Bullet")
                _add_formatted_text(p, bullet_txt)
            elif re.match(r"^\d+\.\s+", stripped):
                num_txt = re.sub(r"^\d+\.\s+", "", stripped)
                p = doc.add_paragraph(style="List Number")
                _add_formatted_text(p, num_txt)
            else:
                p = doc.add_paragraph()
                _add_formatted_text(p, stripped)

        if table_lines:
            _render_markdown_table(doc, table_lines)

        # Add sovereign footer
        _add_footer(
            doc,
            f"OffAir AI · Sovereign AI Workbench | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | 100% Local"
        )

        doc.save(str(out_file))
        size = out_file.stat().st_size
        log("DOCX_GENERATED", path=str(out_file), size=size)
        return {"success": True, "path": str(out_file), "size": size, "error": None}

    except Exception as e:
        log("DOCX_ERROR", error=str(e))
        return {"success": False, "path": "", "size": 0, "error": str(e)}


def _add_formatted_text(paragraph, text: str):
    """Parse basic markdown bold (**text**) and italic (*text*) into docx runs."""
    import re
    # Simple tokenization by **bold**
    parts = re.split(r"(\*\*.*?\*\*)", text)
    for part in parts:
        if part.startswith("**") and part.endswith("**"):
            run = paragraph.add_run(part[2:-2])
            run.bold = True
        else:
            paragraph.add_run(part)


def _render_markdown_table(doc, lines: list[str]):
    """Render markdown table lines into docx table."""
    rows = []
    for l in lines:
        cleaned = l.strip().strip("|")
        cells = [c.strip() for c in cleaned.split("|")]
        # Skip divider row (e.g. |---|---|)
        if all(re.match(r"^:?-+:?$", c) for c in cells if c):
            continue
        rows.append(cells)

    if not rows:
        return

    headers = rows[0]
    data_rows = rows[1:] if len(rows) > 1 else []
    _add_table(doc, headers=headers, rows=data_rows)


def docx_available() -> bool:
    return _DOCX_AVAILABLE
