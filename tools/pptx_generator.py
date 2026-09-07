"""
tools/pptx_generator.py
Professional PowerPoint presentation generator using python-pptx.
Creates structured industrial presentations with title slides, content slides,
data tables, and a disclaimer footer — mirroring the docx_generator interface.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

_base = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _base)

from security.audit import log

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt, Emu
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    _PPTX_AVAILABLE = True
except ImportError:
    _PPTX_AVAILABLE = False
    RGBColor = None
    class _PP_ALIGN_FALLBACK:
        LEFT = 1
        CENTER = 2
        RIGHT = 3
    PP_ALIGN = _PP_ALIGN_FALLBACK


# ── Design constants ──────────────────────────────────────────────────────────
if _PPTX_AVAILABLE:
    _DARK_BG    = RGBColor(0x0D, 0x11, 0x17)   # near-black background
    _ACCENT     = RGBColor(0x00, 0xD6, 0x8F)   # green accent
    _HEADER_BG  = RGBColor(0x16, 0x1C, 0x26)   # slide header band
    _WHITE      = RGBColor(0xFF, 0xFF, 0xFF)
    _LIGHT_GREY = RGBColor(0xC8, 0xD0, 0xDA)
    _RED_ALERT  = RGBColor(0xFF, 0x45, 0x45)
    _AMBER      = RGBColor(0xFF, 0xA5, 0x00)

    _SLIDE_W = Inches(13.33)
    _SLIDE_H = Inches(7.5)
else:
    _DARK_BG = _ACCENT = _HEADER_BG = _WHITE = _LIGHT_GREY = _RED_ALERT = _AMBER = None
    _SLIDE_W = _SLIDE_H = None


def _hex(color) -> str:
    return f"{color[0]:02X}{color[1]:02X}{color[2]:02X}"


def _set_bg(slide, color):
    """Fill slide background with a solid colour."""
    from pptx.oxml.ns import qn
    from lxml import etree

    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def _add_textbox(slide, left, top, width, height, text, font_size=14,
                 bold=False, color=_WHITE, align=PP_ALIGN.LEFT, wrap=True):
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.color.rgb = color
    return txBox


def _add_rect(slide, left, top, width, height, fill_color: RGBColor, line_color=None):
    shape = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        left, top, width, height
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    if line_color:
        shape.line.color.rgb = line_color
    else:
        shape.line.fill.background()  # no line
    return shape


# ── Slide builders ────────────────────────────────────────────────────────────

def _slide_title(prs: "Presentation", title: str, subtitle: str, generated_at: str):
    """Slide 1 — Dark branded title card."""
    slide_layout = prs.slide_layouts[6]  # blank
    slide = prs.slides.add_slide(slide_layout)
    _set_bg(slide, _DARK_BG)

    # Accent bar — left vertical strip
    _add_rect(slide, Inches(0), Inches(0), Inches(0.15), _SLIDE_H, _ACCENT)

    # Logo / system tag top-right
    _add_textbox(slide, Inches(9.5), Inches(0.25), Inches(3.5), Inches(0.5),
                 "⬡  SOVEREIGN AI WORKBENCH · SIH26117",
                 font_size=9, color=_ACCENT, align=PP_ALIGN.RIGHT)

    # Main title
    _add_textbox(slide, Inches(0.6), Inches(1.8), Inches(11.5), Inches(1.8),
                 title, font_size=36, bold=True, color=_WHITE, align=PP_ALIGN.LEFT)

    # Subtitle
    _add_textbox(slide, Inches(0.6), Inches(3.7), Inches(11), Inches(1),
                 subtitle, font_size=18, color=_LIGHT_GREY, align=PP_ALIGN.LEFT)

    # Divider line (thin rect)
    _add_rect(slide, Inches(0.6), Inches(3.6), Inches(10), Inches(0.03), _ACCENT)

    # Bottom meta
    _add_textbox(slide, Inches(0.6), Inches(6.5), Inches(12), Inches(0.6),
                 f"Generated: {generated_at}  |  LOCAL · AIR-GAPPED · NO CLOUD",
                 font_size=9, color=_LIGHT_GREY, align=PP_ALIGN.LEFT)

    # AI-draft badge
    _add_rect(slide, Inches(9.5), Inches(6.3), Inches(3.5), Inches(0.7), _RED_ALERT)
    _add_textbox(slide, Inches(9.5), Inches(6.3), Inches(3.5), Inches(0.7),
                 "⚠  DRAFT — HUMAN REVIEW REQUIRED",
                 font_size=9, bold=True, color=_WHITE, align=PP_ALIGN.CENTER)


def _slide_equipment_summary(prs, equipment_name, equipment_id, inspection_date, risk_level):
    """Slide 2 — Equipment identity card."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide, _DARK_BG)
    _add_rect(slide, Inches(0), Inches(0), Inches(0.15), _SLIDE_H, _ACCENT)

    # Header band
    _add_rect(slide, Inches(0.15), Inches(0), Inches(13.18), Inches(1.1), _HEADER_BG)
    _add_textbox(slide, Inches(0.4), Inches(0.2), Inches(10), Inches(0.7),
                 "01  |  Equipment Summary",
                 font_size=22, bold=True, color=_ACCENT)

    risk_color = {"CRITICAL": _RED_ALERT, "HIGH": _RED_ALERT,
                  "MEDIUM": _AMBER, "LOW": _ACCENT}.get(risk_level.upper(), _AMBER)

    rows = [
        ("Equipment Name", equipment_name),
        ("Equipment / Tag ID", equipment_id),
        ("Inspection Date", inspection_date),
        ("Risk Level", risk_level.upper()),
    ]

    y = Inches(1.4)
    for label, value in rows:
        _add_rect(slide, Inches(0.4), y, Inches(4.5), Inches(0.55), _HEADER_BG)
        _add_textbox(slide, Inches(0.5), y, Inches(4.3), Inches(0.55),
                     label, font_size=12, color=_LIGHT_GREY)

        val_color = risk_color if label == "Risk Level" else _WHITE
        _add_rect(slide, Inches(5.1), y, Inches(7.5), Inches(0.55), RGBColor(0x1A, 0x22, 0x30))
        _add_textbox(slide, Inches(5.2), y, Inches(7.3), Inches(0.55),
                     value, font_size=13, bold=(label == "Risk Level"), color=val_color)
        y += Inches(0.7)

    _add_textbox(slide, Inches(0.4), Inches(6.8), Inches(12), Inches(0.4),
                 "SIH26117 Sovereign AI Workbench  |  LOCAL INFERENCE  |  DRAFT",
                 font_size=8, color=_LIGHT_GREY, align=PP_ALIGN.CENTER)


def _slide_findings(prs, findings: list[str]):
    """Slide 3 — Key inspection findings (bulleted)."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide, _DARK_BG)
    _add_rect(slide, Inches(0), Inches(0), Inches(0.15), _SLIDE_H, _ACCENT)
    _add_rect(slide, Inches(0.15), Inches(0), Inches(13.18), Inches(1.1), _HEADER_BG)
    _add_textbox(slide, Inches(0.4), Inches(0.2), Inches(10), Inches(0.7),
                 "02  |  Key Inspection Findings",
                 font_size=22, bold=True, color=_ACCENT)

    tf_box = slide.shapes.add_textbox(Inches(0.4), Inches(1.3), Inches(12.5), Inches(5.5))
    tf = tf_box.text_frame
    tf.word_wrap = True

    for i, finding in enumerate(findings[:10]):  # max 10 bullets
        p = tf.add_paragraph() if i > 0 else tf.paragraphs[0]
        p.text = f"•  {finding}"
        p.font.size = Pt(14)
        p.font.color.rgb = _WHITE
        p.space_after = Pt(6)

    _add_textbox(slide, Inches(0.4), Inches(6.8), Inches(12), Inches(0.4),
                 "SIH26117 Sovereign AI Workbench  |  LOCAL INFERENCE  |  DRAFT",
                 font_size=8, color=_LIGHT_GREY, align=PP_ALIGN.CENTER)


def _slide_measurements(prs, measurements: dict):
    """Slide 4 — Measurements table."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide, _DARK_BG)
    _add_rect(slide, Inches(0), Inches(0), Inches(0.15), _SLIDE_H, _ACCENT)
    _add_rect(slide, Inches(0.15), Inches(0), Inches(13.18), Inches(1.1), _HEADER_BG)
    _add_textbox(slide, Inches(0.4), Inches(0.2), Inches(10), Inches(0.7),
                 "03  |  Measurements & Observations",
                 font_size=22, bold=True, color=_ACCENT)

    if not measurements:
        _add_textbox(slide, Inches(0.4), Inches(2), Inches(12), Inches(1),
                     "No specific measurements recorded.", font_size=14, color=_LIGHT_GREY)
        return

    items = list(measurements.items())
    y = Inches(1.35)
    row_h = Inches(0.55)
    # Header row
    _add_rect(slide, Inches(0.4), y, Inches(6), row_h, _ACCENT)
    _add_textbox(slide, Inches(0.5), y, Inches(5.8), row_h, "Parameter", font_size=13, bold=True, color=_DARK_BG)
    _add_rect(slide, Inches(6.5), y, Inches(6.4), row_h, _ACCENT)
    _add_textbox(slide, Inches(6.6), y, Inches(6.2), row_h, "Value", font_size=13, bold=True, color=_DARK_BG)
    y += row_h

    for idx, (k, v) in enumerate(items[:8]):
        row_bg = RGBColor(0x16, 0x1C, 0x26) if idx % 2 == 0 else RGBColor(0x1A, 0x22, 0x30)
        _add_rect(slide, Inches(0.4), y, Inches(6), row_h, row_bg)
        _add_textbox(slide, Inches(0.5), y, Inches(5.8), row_h, str(k), font_size=12, color=_LIGHT_GREY)
        _add_rect(slide, Inches(6.5), y, Inches(6.4), row_h, row_bg)
        _add_textbox(slide, Inches(6.6), y, Inches(6.2), row_h, str(v), font_size=12, color=_WHITE)
        y += row_h

    _add_textbox(slide, Inches(0.4), Inches(6.8), Inches(12), Inches(0.4),
                 "SIH26117 Sovereign AI Workbench  |  LOCAL INFERENCE  |  DRAFT",
                 font_size=8, color=_LIGHT_GREY, align=PP_ALIGN.CENTER)


def _slide_recommendations(prs, recommendations: str, risk_level: str):
    """Slide 5 — Recommendations and risk."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide, _DARK_BG)
    _add_rect(slide, Inches(0), Inches(0), Inches(0.15), _SLIDE_H, _ACCENT)
    _add_rect(slide, Inches(0.15), Inches(0), Inches(13.18), Inches(1.1), _HEADER_BG)
    _add_textbox(slide, Inches(0.4), Inches(0.2), Inches(10), Inches(0.7),
                 "04  |  Recommendations & Risk Assessment",
                 font_size=22, bold=True, color=_ACCENT)

    risk_text = {
        "CRITICAL": "🔴  CRITICAL — Immediate shutdown required. Risk of failure and safety incident.",
        "HIGH": "🟠  HIGH — Schedule maintenance at earliest opportunity. Monitor closely.",
        "MEDIUM": "🟡  MEDIUM — Schedule maintenance in next planned shutdown window.",
        "LOW": "🟢  LOW — Minor maintenance recommended during next scheduled service.",
    }.get(risk_level.upper(), "⚪  UNKNOWN — Consult maintenance engineer.")

    risk_color = {"CRITICAL": _RED_ALERT, "HIGH": _RED_ALERT,
                  "MEDIUM": _AMBER, "LOW": _ACCENT}.get(risk_level.upper(), _LIGHT_GREY)

    _add_rect(slide, Inches(0.4), Inches(1.3), Inches(12.5), Inches(0.7),
              RGBColor(0x1A, 0x22, 0x30))
    _add_textbox(slide, Inches(0.5), Inches(1.3), Inches(12.3), Inches(0.7),
                 risk_text, font_size=14, bold=True, color=risk_color)

    _add_textbox(slide, Inches(0.4), Inches(2.3), Inches(2.5), Inches(0.4),
                 "RECOMMENDED ACTION:", font_size=13, bold=True, color=_ACCENT)

    _add_textbox(slide, Inches(0.4), Inches(2.8), Inches(12.5), Inches(3.5),
                 recommendations or "Detailed inspection and maintenance by qualified engineer.",
                 font_size=14, color=_WHITE, wrap=True)

    _add_textbox(slide, Inches(0.4), Inches(6.8), Inches(12), Inches(0.4),
                 "SIH26117 Sovereign AI Workbench  |  LOCAL INFERENCE  |  DRAFT",
                 font_size=8, color=_LIGHT_GREY, align=PP_ALIGN.CENTER)


def _slide_sop_references(prs, sop_references: list[dict]):
    """Slide 6 — SOP / document references."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide, _DARK_BG)
    _add_rect(slide, Inches(0), Inches(0), Inches(0.15), _SLIDE_H, _ACCENT)
    _add_rect(slide, Inches(0.15), Inches(0), Inches(13.18), Inches(1.1), _HEADER_BG)
    _add_textbox(slide, Inches(0.4), Inches(0.2), Inches(10), Inches(0.7),
                 "05  |  SOP & Guideline References",
                 font_size=22, bold=True, color=_ACCENT)

    if not sop_references:
        _add_textbox(slide, Inches(0.4), Inches(2), Inches(12), Inches(1),
                     "No SOP references retrieved. Manual SOP lookup recommended.",
                     font_size=14, color=_LIGHT_GREY)
        return

    y = Inches(1.35)
    for ref in sop_references[:5]:
        doc_name = ref.get("document", "Unknown")
        snippet = str(ref.get("text", ""))[:160]
        _add_rect(slide, Inches(0.4), y, Inches(12.5), Inches(0.45), _HEADER_BG)
        _add_textbox(slide, Inches(0.5), y, Inches(12.3), Inches(0.45),
                     f"📄  {doc_name}", font_size=13, bold=True, color=_ACCENT)
        y += Inches(0.5)
        if snippet:
            _add_textbox(slide, Inches(0.6), y, Inches(12.2), Inches(0.5),
                         f'"{snippet}…"', font_size=11, color=_LIGHT_GREY)
            y += Inches(0.6)
        else:
            y += Inches(0.15)

    _add_textbox(slide, Inches(0.4), Inches(6.8), Inches(12), Inches(0.4),
                 "SIH26117 Sovereign AI Workbench  |  LOCAL INFERENCE  |  DRAFT",
                 font_size=8, color=_LIGHT_GREY, align=PP_ALIGN.CENTER)


def _slide_disclaimer(prs, generated_at: str, n_sources: int):
    """Slide 7 — Audit trail + disclaimer."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide, _DARK_BG)
    _add_rect(slide, Inches(0), Inches(0), Inches(0.15), _SLIDE_H, _RED_ALERT)
    _add_rect(slide, Inches(0.15), Inches(0), Inches(13.18), Inches(1.1), _HEADER_BG)
    _add_textbox(slide, Inches(0.4), Inches(0.2), Inches(10), Inches(0.7),
                 "06  |  AI Audit Information & Disclaimer",
                 font_size=22, bold=True, color=_RED_ALERT)

    audit_rows = [
        ("AI System", "Sovereign AI Workbench (SIH26117)"),
        ("Inference Mode", "LOCAL — No cloud API"),
        ("RAG Sources Retrieved", str(n_sources)),
        ("External API Calls", "0"),
        ("Generated At", generated_at),
        ("Human Review Required", "YES — THIS IS A DRAFT"),
    ]

    y = Inches(1.35)
    row_h = Inches(0.52)
    for idx, (label, val) in enumerate(audit_rows):
        row_bg = RGBColor(0x16, 0x1C, 0x26) if idx % 2 == 0 else RGBColor(0x1A, 0x22, 0x30)
        _add_rect(slide, Inches(0.4), y, Inches(5.5), row_h, row_bg)
        _add_textbox(slide, Inches(0.5), y, Inches(5.3), row_h, label, font_size=12, color=_LIGHT_GREY)
        val_color = _RED_ALERT if "DRAFT" in val else _WHITE
        _add_rect(slide, Inches(6.0), y, Inches(6.9), row_h, row_bg)
        _add_textbox(slide, Inches(6.1), y, Inches(6.7), row_h, val,
                     font_size=12, bold=("DRAFT" in val), color=val_color)
        y += row_h

    disclaimer = (
        "DISCLAIMER: This presentation was generated by an AI system as a draft for human review. "
        "All findings and recommendations must be verified by qualified personnel before any "
        "maintenance action is taken. The AI system does not have authority to approve operations."
    )
    _add_textbox(slide, Inches(0.4), Inches(6.0), Inches(12.5), Inches(0.7),
                 disclaimer, font_size=9, color=_LIGHT_GREY, wrap=True)


def _slide_custom_content(prs, slide_num: int, title: str, points: list[str], source: str = "", badge: str = ""):
    """A clean, sleek dark-themed content slide with bullet points and optional source."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _set_bg(slide, _DARK_BG)
    _add_rect(slide, Inches(0), Inches(0), Inches(0.15), _SLIDE_H, _ACCENT)
    _add_rect(slide, Inches(0.15), Inches(0), Inches(13.18), Inches(1.1), _HEADER_BG)

    header_text = f"{slide_num:02d}  |  {title}" if slide_num > 0 else title
    _add_textbox(slide, Inches(0.4), Inches(0.2), Inches(10), Inches(0.7),
                 header_text, font_size=22, bold=True, color=_ACCENT)

    if badge:
        _add_rect(slide, Inches(10.2), Inches(0.25), Inches(2.6), Inches(0.5), RGBColor(0x1A, 0x22, 0x30))
        _add_textbox(slide, Inches(10.2), Inches(0.25), Inches(2.6), Inches(0.5),
                     badge, font_size=10, bold=True, color=_ACCENT, align=PP_ALIGN.CENTER)

    tf_box = slide.shapes.add_textbox(Inches(0.6), Inches(1.5), Inches(12.0), Inches(4.5))
    tf = tf_box.text_frame
    tf.word_wrap = True

    for i, pt in enumerate(points):
        p = tf.add_paragraph() if i > 0 else tf.paragraphs[0]
        cleaned_pt = pt.strip().lstrip("-*• ").strip()
        p.text = f"•  {cleaned_pt}"
        p.font.size = Pt(15)
        p.font.color.rgb = _WHITE
        p.space_after = Pt(12)

    if source:
        _add_rect(slide, Inches(0.6), Inches(6.2), Inches(12.0), Inches(0.45), RGBColor(0x16, 0x1C, 0x26))
        _add_textbox(slide, Inches(0.8), Inches(6.2), Inches(11.6), Inches(0.45),
                     f"Source / Reference: {source.strip().lstrip('*_').rstrip('*_')}",
                     font_size=10, color=_LIGHT_GREY)

    _add_textbox(slide, Inches(0.4), Inches(6.9), Inches(12), Inches(0.4),
                 "SIH26117 Sovereign AI Workbench  |  LOCAL INFERENCE  |  DRAFT",
                 font_size=8, color=_LIGHT_GREY, align=PP_ALIGN.CENTER)


# ── Public API ────────────────────────────────────────────────────────────────

def create_maintenance_approval_pptx(
    equipment_name: str,
    equipment_id: str,
    inspection_date: str,
    findings: list[str],
    measurements: dict,
    recommendations: str,
    sop_references: list[dict],
    output_path: "str | Path",
    risk_level: str = "HIGH",
) -> dict:
    """
    Generate a professional 7-slide Maintenance Approval Note PPTX.

    Returns:
        {"success": bool, "path": str, "size": int, "error": str|None}
    """
    if not _PPTX_AVAILABLE:
        return {
            "success": False,
            "path": "",
            "error": "python-pptx not installed. Run: pip install python-pptx",
        }

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        prs = Presentation()
        prs.slide_width  = _SLIDE_W
        prs.slide_height = _SLIDE_H

        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        subtitle = f"Equipment: {equipment_id}  |  Inspection: {inspection_date}  |  Risk: {risk_level.upper()}"

        _slide_title(prs, "MAINTENANCE APPROVAL NOTE", subtitle, now)
        _slide_equipment_summary(prs, equipment_name, equipment_id, inspection_date, risk_level)
        _slide_findings(prs, findings)
        _slide_measurements(prs, measurements)
        _slide_recommendations(prs, recommendations, risk_level)
        _slide_sop_references(prs, sop_references)
        _slide_disclaimer(prs, now, len(sop_references))

        prs.save(str(output_path))
        size = output_path.stat().st_size
        log("PPTX_GENERATED", path=str(output_path), size=size)

        return {"success": True, "path": str(output_path), "size": size, "error": None}

    except Exception as e:
        log("PPTX_ERROR", error=str(e))
        return {"success": False, "path": "", "error": str(e)}


def create_custom_presentation(
    title: str,
    subtitle: str,
    slides: list[dict],
    output_path: "str | Path",
    badge: str = "SOVEREIGN AI",
) -> dict:
    """
    Generate a presentation from a list of slide dictionaries.
    Each slide dict: {"title": str, "points": list[str], "source": Optional[str]}
    """
    if not _PPTX_AVAILABLE:
        return {"success": False, "path": "", "error": "python-pptx not installed"}

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        prs = Presentation()
        prs.slide_width = _SLIDE_W
        prs.slide_height = _SLIDE_H

        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        _slide_title(prs, title, subtitle, now)

        for idx, s in enumerate(slides, start=1):
            s_title = s.get("title", f"Slide {idx}")
            s_points = s.get("points", [])
            s_source = s.get("source", "")
            _slide_custom_content(prs, idx, s_title, s_points, source=s_source, badge=badge)

        prs.save(str(output_path))
        size = output_path.stat().st_size
        log("PPTX_GENERATED", path=str(output_path), size=size)
        return {"success": True, "path": str(output_path), "size": size, "error": None}
    except Exception as e:
        log("PPTX_ERROR", error=str(e))
        return {"success": False, "path": "", "error": str(e)}


def create_presentation_from_markdown(
    markdown_text: str,
    default_title: str = "Presentation",
    output_path: "str | Path | None" = None,
) -> dict:
    """
    Parse markdown slide outline and generate a PPTX.
    Supports headers (#, ##, ###, #### Slide X: Title), bullet points (- or *), and *Source: ...*.
    """
    import re

    lines = [line.rstrip() for line in markdown_text.splitlines()]
    title = default_title
    subtitle = "OffAir AI | Air-Gapped Sovereign System"
    slides = []
    current_slide = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Presentation Title (### Title or # Title)
        if (stripped.startswith("# ") or stripped.startswith("### ")) and not slides and current_slide is None:
            raw = re.sub(r"^#+\s*", "", stripped).strip()
            # Clean up (4-Slide PPT) or similar annotations if present
            cleaned_title = re.sub(r"\s*\(\s*\d+[\s\-]*(?:slide|slides)?\s*(?:ppt|pptx|presentation)?\s*\)", "", raw, flags=re.IGNORECASE).strip()
            title = cleaned_title or raw
            continue

        # Subtitle (*Subtitle*) — only before any content slides have been encountered
        if stripped.startswith("*") and stripped.endswith("*") and not stripped.lower().startswith("*source") and current_slide is None and not slides:
            subtitle = stripped.strip("*_ ").strip()
            continue

        # Slide header or delimiter
        slide_match = re.match(r"^(?:#{1,4}\s+)?(?:Slide\s+\d+[:\s]+)?(.+)$", stripped, re.IGNORECASE)
        if (stripped.startswith("#### ") or stripped.startswith("## ") or stripped.startswith("---") or
            re.match(r"^Slide\s+\d+[:\s]+", stripped, re.IGNORECASE)):

            if stripped == "---":
                if current_slide and (current_slide["points"] or current_slide["title"]):
                    slides.append(current_slide)
                    current_slide = None
                continue

            header_text = re.sub(r"^#+\s*", "", stripped).strip()
            header_text = re.sub(r"^Slide\s+\d+[:\s]+", "", header_text, flags=re.IGNORECASE).strip()

            if current_slide and (current_slide["points"] or current_slide["title"]):
                slides.append(current_slide)

            current_slide = {"title": header_text, "points": [], "source": ""}
            continue

        # Bullet point
        if stripped.startswith("- ") or stripped.startswith("* ") or stripped.startswith("• "):
            pt = re.sub(r"^[-*•]\s*", "", stripped).strip()
            if current_slide is None:
                current_slide = {"title": "Key Points", "points": [], "source": ""}
            current_slide["points"].append(pt)
            continue

        # Source reference
        if "source:" in stripped.lower():
            src = re.sub(r"^\*?Source:\s*", "", stripped, flags=re.IGNORECASE).rstrip("*_ ")
            if current_slide:
                current_slide["source"] = src
            continue

        # Regular text inside a slide
        if current_slide is not None:
            current_slide["points"].append(stripped)

    if current_slide and (current_slide["points"] or current_slide["title"]):
        slides.append(current_slide)

    if not output_path:
        from tools.files import get_output_path
        safe_name = re.sub(r"[^\w\-]", "_", title)[:40]
        output_path = get_output_path(f"{safe_name}.pptx")

    return create_custom_presentation(title, subtitle, slides, output_path)


def pptx_available() -> bool:
    return _PPTX_AVAILABLE

