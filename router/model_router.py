"""
router/model_router.py
Rule-based task classifier and model selector.
Returns a structured routing decision that is displayed in the UI.

Architecture note: The classify() function is the only entry point.
Replace the internals with an ML classifier later without changing the interface.
"""

import re
import os
import sys
from dataclasses import dataclass
from typing import Optional

_base = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _base)

from models.model_registry import get_model_for_task, get_available_model, _registry


@dataclass
class RoutingDecision:
    task_type: str
    selected_role: str
    selected_model: str
    reason: str
    confidence: float
    inference: str = "LOCAL"
    external_api: str = "NONE"


# ─────────────────────────────────────────────────────────
# Keyword rule sets  (order matters — most specific first)
# ─────────────────────────────────────────────────────────

_CODING_KEYWORDS = [
    r"\bpython\b", r"\bcode\b", r"\bprogram\b", r"\bfunction\b",
    r"\bdebug\b", r"\balgorithm\b", r"\bclass\b", r"\bscript\b",
    r"\bapi\b", r"\bmodule\b", r"\bimport\b", r"\bdef\b",
    r"\bcompile\b", r"\bsyntax\b", r"\bloop\b", r"\btest\b.*\bunit\b",
    r"\bwrite.*code\b", r"\bgenerate.*code\b", r"\bcoding\b",
    r"\bjavascript\b", r"\bsql\b", r"\bjava\b", r"\bc\+\+\b",
]

_VISION_KEYWORDS = [
    r"\bimage\b", r"\bphoto\b", r"\bpicture\b", r"\bphotograph\b",
    r"\bdrawing\b", r"\bdiagram\b", r"\bhandwritten\b", r"\bscan\b",
    r"\bvisual\b", r"\blook at\b", r"\bsee\b.*\bimage\b",
    r"\banalyze.*image\b", r"\binspect.*photo\b",
    r"\bp&id\b", r"\bpiping.*diagram\b",
]

_CALCULATION_KEYWORDS = [
    r"\bcalculate\b", r"\bcompute\b", r"\bformula\b", r"\bequation\b",
    r"\bpressure\b", r"\btemperature\b", r"\bflow\b.*\brate\b",
    r"\befficiency\b", r"\bpower\b", r"\bwatt\b", r"\bkw\b",
    r"\bbar\b", r"\bpsi\b", r"\bdelta\b", r"\bconvert\b",
    r"\bpercentage\b", r"\b%\b", r"\bkg/\b", r"\bm3/\b",
    r"\brpm\b", r"\btorque\b", r"\bvoltage\b", r"\bcurrent\b",
    r"\bforce\b", r"\bmoment\b", r"\bstress\b", r"\bstrain\b",
]

_DOCUMENT_KEYWORDS = [
    r"\bdocument\b", r"\bpdf\b", r"\breport\b", r"\bfile\b",
    r"\bsummarize\b", r"\bextract\b", r"\bsop\b", r"\bmanual\b",
    r"\bprocedure\b", r"\binspection\b", r"\bmaintenance\b",
    r"\bapproval\b", r"\bnote\b", r"\bmemo\b", r"\bletter\b",
    r"\bcertificate\b", r"\bspecification\b",
    r"\bppt\b", r"\bpptx\b", r"\bpowerpoint\b", r"\bslides\b", r"\bpresentation\b",
]


def _score_keywords(text: str, patterns: list[str]) -> int:
    """Count how many keyword patterns match in the text."""
    text_lower = text.lower()
    return sum(1 for p in patterns if re.search(p, text_lower))


def classify(
    text: str,
    has_image: bool = False,
    has_pdf: bool = False,
    has_docx: bool = False,
) -> RoutingDecision:
    """
    Classify a user request and return a routing decision.

    Args:
        text: The user's prompt text.
        has_image: Whether an image was uploaded.
        has_pdf: Whether a PDF was uploaded.
        has_docx: Whether a DOCX was uploaded.

    Returns:
        RoutingDecision with task_type, model, and reasoning.
    """
    from document_tools.chat_resolver import resolve_explicit_document_operation, is_explicit_vision_request

    mock_files = []
    if has_image:
        mock_files.append("image.png")
    if has_pdf:
        mock_files.append("document.pdf")
    if has_docx:
        mock_files.append("document.docx")

    # 1. Deterministic document operations (Highest Priority)
    doc_op = resolve_explicit_document_operation(text, uploaded_files=mock_files)
    if doc_op:
        return RoutingDecision(
            task_type="document_operation",
            selected_role="document_tools",
            selected_model="NONE",
            reason=f"Deterministic document operation routed to {doc_op.tool_name} tool.",
            confidence=1.0,
            inference="LOCAL",
            external_api="NONE",
        )

    # 2. Explicit Vision Analysis
    if is_explicit_vision_request(text):
        model_name = get_available_model("vision") or "llava-phi3:latest"
        return RoutingDecision(
            task_type="vision",
            selected_role="vision",
            selected_model=model_name,
            reason="Visual analysis task requested — routed to vision model.",
            confidence=0.95,
        )

    # --- Score each category ---
    coding_score = _score_keywords(text, _CODING_KEYWORDS)
    vision_score = _score_keywords(text, _VISION_KEYWORDS)
    calc_score = _score_keywords(text, _CALCULATION_KEYWORDS)
    doc_score = _score_keywords(text, _DOCUMENT_KEYWORDS)

    # Boost vision only if image attached AND vision keywords present
    if has_image and vision_score > 0:
        vision_score += 5

    # PDF upload boosts document score
    if has_pdf or has_docx:
        doc_score += 5

    scores = {
        "coding": coding_score,
        "vision": vision_score,
        "calculation": calc_score,
        "document": doc_score,
    }

    # Find best match
    best_type = max(scores, key=lambda k: scores[k])
    best_score = scores[best_type]

    # If no strong signal, fall back to general
    if best_score == 0:
        return RoutingDecision(
            task_type="general",
            selected_role="general",
            selected_model=get_available_model("general") or "llama3.1:8b",
            reason="No specific task signals detected — using general reasoning model.",
            confidence=0.5,
        )

    # Map task type to model role
    role_map = {
        "coding": "coding",
        "vision": "vision",
        "calculation": "general",  # Use reasoning model for calculations
        "document": "general",
    }
    total = sum(scores.values()) or 1
    confidence = round(min(best_score / total, 0.95), 2)

    role = role_map[best_type]
    model_name = get_available_model(role) or get_available_model("general") or "llama3.1:8b"

    reason_map = {
        "coding": f"Code-related keywords detected (score={best_score}). Code generation requires specialized coding model.",
        "vision": f"Image/visual keywords detected (score={best_score}). Visual content requires multimodal vision model.",
        "calculation": f"Engineering calculation keywords detected (score={best_score}). Deterministic calculation tool + reasoning model.",
        "document": f"Document analysis keywords detected (score={best_score}). Document understanding via general reasoning model.",
    }

    return RoutingDecision(
        task_type=best_type,
        selected_role=role,
        selected_model=model_name,
        reason=reason_map[best_type],
        confidence=confidence,
    )


def get_routing_display(decision: RoutingDecision) -> dict:
    """Format routing decision for UI display."""
    task_icons = {
        "coding": "💻",
        "vision": "🖼️",
        "calculation": "🔢",
        "document": "📄",
        "document_operation": "📄",
        "general": "🧠",
    }
    return {
        "icon": task_icons.get(decision.task_type, "🤖"),
        "task_type": decision.task_type.upper(),
        "selected_model": decision.selected_model,
        "reason": decision.reason,
        "confidence": f"{int(decision.confidence * 100)}%",
        "inference": decision.inference,
        "external_api": decision.external_api,
    }
