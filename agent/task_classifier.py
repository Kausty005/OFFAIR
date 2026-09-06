"""
agent/task_classifier.py
Deterministic task classifier and execution planner.

Classifies user requests using deterministic heuristics to avoid unnecessary LLM calls
for obvious requests, supports multi-step compound plans, and integrates with the
local model registry.
"""

import re
from dataclasses import dataclass, field
from typing import Optional, List
from models.model_registry import get_available_model


class TaskType:
    GENERAL_CHAT = "general_chat"
    KNOWLEDGE_QUERY = "knowledge_query"
    DOCUMENT_ANALYSIS = "document_analysis"
    CODE_GENERATION = "code_generation"
    CODE_EXECUTION = "code_execution"
    CALCULATION = "calculation"
    VISION_ANALYSIS = "vision_analysis"
    REPORT_GENERATION = "report_generation"
    PRESENTATION_GENERATION = "presentation_generation"


@dataclass
class PlannedStep:
    step_id: int
    task_type: str
    description: str
    tool: str
    status: str = "pending"
    result: Optional[str] = None
    error: Optional[str] = None


@dataclass
class ClassificationResult:
    primary_task: str
    is_multi_step: bool
    steps: List[PlannedStep]
    selected_model: str
    selected_role: str
    reason: str
    confidence: float
    selected_tools: List[str] = field(default_factory=list)


# --- Heuristic Regex Rules ---

_CODE_EXECUTION_PATTERNS = [
    r"\brun\s+(?:this\s+)?(?:python\s+)?code\b",
    r"\bexecute\s+(?:this\s+)?(?:python\s+)?code\b",
    r"\brun\s+(?:the\s+)?script\b",
    r"\bexecute\s+(?:the\s+)?script\b",
    r"\brun\s+in\s+sandbox\b",
    r"\bexecute\s+in\s+sandbox\b",
    r"\brun\s+program\b",
]

_CALCULATION_PATTERNS = [
    r"^\s*calculate\s+[\d\(\)\.\+\-\*\/\^ ]+",
    r"^\s*compute\s+[\d\(\)\.\+\-\*\/\^ ]+",
    r"^\s*[\d\(\)\.\+\-\*\/\^ ]{4,}\s*$",  # Pure math expression like (25 * 4) / 10
    r"\bcalculate\b",
    r"\bcompute\b",
    r"\bpump\s+efficiency\b",
    r"\bpressure\s+drop\b",
    r"\bbearing\s+temperature\b",
    r"\btemperature\s+conversion\b",
    r"\bpower\s+from\s+efficiency\b",
]

_CODE_GENERATION_PATTERNS = [
    r"\bwrite\s+(?:a\s+)?(?:python\s+)?(?:code|program|function|script|algorithm|class)\b",
    r"\bgenerate\s+(?:python\s+)?(?:code|program|function|script)\b",
    r"\bcode\s+(?:for|to)\b",
    r"\bimplement\s+(?:a\s+)?(?:binary\s+search|algorithm|function|class)\b",
    r"\bdef\s+\w+\(",
    r"\bpython\s+code\b",
]

_KNOWLEDGE_PATTERNS = [
    r"\baccording\s+to\s+(?:the|our)?\s*(?:uploaded)?\s*(?:\w+\s+)?(?:sop|manual|document|procedure|guidelines)\b",
    r"\bwhat\s+(?:is|are)\s+(?:the\s+)?procedure\b",
    r"\bwhat\s+does\s+(?:the|our)?\s*(?:\w+\s+)?(?:sop|manual|policy|safety\s+manual)\s+say\b",
    r"\bsearch\s+(?:the\s+)?(?:knowledge\s+base|kb|docs)\b",
    r"\bstandard\s+operating\s+procedure\b",
    r"\bsafety\s+protocol\b",
    r"\bsop\b",
    r"\bsafety\s+manual\b",
    r"\bknowledge\s+base\b",
    r"\bprocedure\s+for\b",
]

_VISION_PATTERNS = [
    r"\blook\s+at\s+(?:this\s+)?(?:image|photo|photograph|picture|diagram|drawing)\b",
    r"\banalyze\s+(?:this\s+)?(?:image|photo|photograph|picture|diagram|drawing|inspection\s+(?:photo|photograph|image))\b",
    r"\binspect\s+(?:this\s+)?(?:image|photo|photograph|drawing)\b",
    r"\b(?:inspection\s+)?(?:photo|photograph|image|diagram)\b",
    r"\bp&id\b",
    r"\bpiping\s+and\s+instrumentation\b",
]

_REPORT_PATTERNS = [
    r"\bgenerate\s+(?:a\s+)?(?:maintenance\s+approval\s+note|report|document|docx)\b",
    r"\bcreate\s+(?:a\s+)?(?:word\s+document|docx|approval\s+note|report)\b",
    r"\bmaintenance\s+approval\s+note\b",
]

_PRESENTATION_PATTERNS = [
    r"\b(?:make|generate|create)\s+(?:a\s+)?(?:ppt|pptx|powerpoint|slides|presentation)\b",
    r"\bppt\b",
    r"\bpptx\b",
    r"\bpowerpoint\b",
    r"\bslides\s+on\b",
    r"\bpresentation\s+on\b",
]

_DOCUMENT_ANALYSIS_PATTERNS = [
    r"\banalyze\s+(?:this\s+)?(?:document|pdf|inspection\s+report|file)\b",
    r"\bextract\s+findings\b",
    r"\binspection\s+report\b",
    r"\bextract\s+(?:data|measurements|defects)\b",
]


def classify_task(
    query: str,
    uploaded_files: Optional[List[str]] = None,
    has_image: bool = False,
    has_pdf: bool = False,
    has_docx: bool = False,
) -> ClassificationResult:
    """
    Classify task using deterministic rules and determine execution plan.
    """
    files = uploaded_files or []
    q = query.strip()
    q_lower = q.lower()

    # Detect file indicators
    if not has_image:
        has_image = any(f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".webp")) for f in files)
    if not has_pdf:
        has_pdf = any(f.lower().endswith(".pdf") for f in files)
    if not has_docx:
        has_docx = any(f.lower().endswith((".docx", ".doc")) for f in files)

    # 1. Vision Analysis check
    if has_image or any(re.search(p, q_lower) for p in _VISION_PATTERNS):
        model = get_available_model("vision") or "llava-phi3:latest"
        steps = [
            PlannedStep(1, TaskType.VISION_ANALYSIS, "Load and preprocess image", "files"),
            PlannedStep(2, TaskType.VISION_ANALYSIS, "Analyze image with local vision model", "vision"),
            PlannedStep(3, TaskType.VISION_ANALYSIS, "Verify visual observations", "verifier"),
        ]
        return ClassificationResult(
            primary_task=TaskType.VISION_ANALYSIS,
            is_multi_step=False,
            steps=steps,
            selected_model=model,
            selected_role="vision",
            reason="Multimodal vision task detected from query or uploaded image.",
            confidence=0.95,
            selected_tools=["vision", "files", "verifier"],
        )

    # 2. Check for Multi-Step Compound Request
    # Example: "Analyze this document, find relevant SOP information, calculate the efficiency, identify risks and generate a report."
    is_multi = False
    has_doc_intent = (has_pdf or has_docx or any(re.search(p, q_lower) for p in _DOCUMENT_ANALYSIS_PATTERNS))
    has_rag_intent = any(re.search(p, q_lower) for p in _KNOWLEDGE_PATTERNS) or "sop" in q_lower
    has_calc_intent = any(re.search(p, q_lower) for p in _CALCULATION_PATTERNS)
    has_report_intent = any(re.search(p, q_lower) for p in _REPORT_PATTERNS)

    matched_intents = sum([has_doc_intent, has_rag_intent, has_calc_intent, has_report_intent])
    if matched_intents >= 3 or ("and" in q_lower and matched_intents >= 2 and (has_report_intent or has_doc_intent)):
        is_multi = True
        steps = []
        step_id = 1
        tools = []
        if has_doc_intent:
            steps.append(PlannedStep(step_id, TaskType.DOCUMENT_ANALYSIS, "Extract and process uploaded document text & OCR", "pdf_processor"))
            tools.append("pdf_processor")
            step_id += 1
        if has_rag_intent:
            steps.append(PlannedStep(step_id, TaskType.KNOWLEDGE_QUERY, "Query local knowledge base for relevant SOP guidelines", "rag"))
            tools.append("rag")
            step_id += 1
        if has_calc_intent:
            steps.append(PlannedStep(step_id, TaskType.CALCULATION, "Perform deterministic calculation using safe calculator", "calculator"))
            tools.append("calculator")
            step_id += 1
        steps.append(PlannedStep(step_id, "reasoning", "Synthesize findings, SOP standards, and calculations", "llm_reasoning"))
        tools.append("llm_reasoning")
        step_id += 1
        if has_report_intent:
            steps.append(PlannedStep(step_id, TaskType.REPORT_GENERATION, "Generate structured Word deliverable (.docx)", "docx_generator"))
            tools.append("docx_generator")
            step_id += 1
        steps.append(PlannedStep(step_id, "verification", "Verify output deliverables and assertions", "verifier"))
        tools.append("verifier")

        model = get_available_model("general") or "llama3.1:8b"
        return ClassificationResult(
            primary_task=TaskType.DOCUMENT_ANALYSIS,
            is_multi_step=True,
            steps=steps,
            selected_model=model,
            selected_role="general",
            reason="Multi-step industrial workflow detected combining document parsing, SOP search, calculations, and reporting.",
            confidence=0.92,
            selected_tools=tools,
        )

    # 3. Direct Code Execution
    if any(re.search(p, q_lower) for p in _CODE_EXECUTION_PATTERNS):
        steps = [
            PlannedStep(1, TaskType.CODE_EXECUTION, "Execute untrusted code in Docker sandbox with stdin", "sandbox"),
            PlannedStep(2, TaskType.CODE_EXECUTION, "Verify sandbox exit status and output", "verifier"),
        ]
        return ClassificationResult(
            primary_task=TaskType.CODE_EXECUTION,
            is_multi_step=False,
            steps=steps,
            selected_model="none (direct sandbox)",
            selected_role="sandbox",
            reason="Code execution request routed directly to isolated Docker sandbox.",
            confidence=0.98,
            selected_tools=["sandbox", "verifier"],
        )

    # 4. Calculation
    if any(re.search(p, q_lower) for p in _CALCULATION_PATTERNS) and not any(re.search(p, q_lower) for p in _CODE_GENERATION_PATTERNS):
        steps = [
            PlannedStep(1, TaskType.CALCULATION, "Evaluate math expression using safe AST calculator", "calculator"),
            PlannedStep(2, TaskType.CALCULATION, "Verify calculation precision and bounds", "verifier"),
        ]
        return ClassificationResult(
            primary_task=TaskType.CALCULATION,
            is_multi_step=False,
            steps=steps,
            selected_model="deterministic tool",
            selected_role="calculator",
            reason="Deterministic numerical calculation routed to safe AST evaluator.",
            confidence=0.95,
            selected_tools=["calculator", "verifier"],
        )

    # 5. Code Generation
    if any(re.search(p, q_lower) for p in _CODE_GENERATION_PATTERNS):
        model = get_available_model("coding") or "qwen2.5-coder:3b"
        # Check if testing was explicitly requested
        needs_tests = ("test" in q_lower or "unit" in q_lower or "run" in q_lower)
        steps = [
            PlannedStep(1, TaskType.CODE_GENERATION, "Generate Python code with local coding model", "llm_coding"),
        ]
        tools = ["llm_coding", "verifier"]
        if needs_tests:
            steps.append(PlannedStep(2, TaskType.CODE_GENERATION, "Run generated tests in isolated Docker sandbox", "sandbox"))
            tools.append("sandbox")
        steps.append(PlannedStep(len(steps) + 1, TaskType.CODE_GENERATION, "Verify code syntax and structure", "verifier"))

        return ClassificationResult(
            primary_task=TaskType.CODE_GENERATION,
            is_multi_step=False,
            steps=steps,
            selected_model=model,
            selected_role="coding",
            reason="Software engineering task routed to local Qwen2.5-Coder model.",
            confidence=0.92,
            selected_tools=tools,
        )

    # 6. Knowledge Query (RAG)
    if any(re.search(p, q_lower) for p in _KNOWLEDGE_PATTERNS):
        model = get_available_model("general") or "llama3.1:8b"
        steps = [
            PlannedStep(1, TaskType.KNOWLEDGE_QUERY, "Retrieve relevant passages from local knowledge base", "rag"),
            PlannedStep(2, TaskType.KNOWLEDGE_QUERY, "Generate grounded answer citing source documents", "llm"),
            PlannedStep(3, TaskType.KNOWLEDGE_QUERY, "Verify grounding and source citations", "verifier"),
        ]
        return ClassificationResult(
            primary_task=TaskType.KNOWLEDGE_QUERY,
            is_multi_step=False,
            steps=steps,
            selected_model=model,
            selected_role="general",
            reason="Document knowledge inquiry routed to local RAG retrieval and citation engine.",
            confidence=0.88,
            selected_tools=["rag", "llm", "verifier"],
        )

    # 7. Document Analysis (if PDF/DOCX uploaded or keywords)
    if has_pdf or has_docx or any(re.search(p, q_lower) for p in _DOCUMENT_ANALYSIS_PATTERNS):
        model = get_available_model("general") or "llama3.1:8b"
        steps = [
            PlannedStep(1, TaskType.DOCUMENT_ANALYSIS, "Process document and perform local OCR if scanned", "pdf_processor"),
            PlannedStep(2, TaskType.DOCUMENT_ANALYSIS, "Extract structured findings and measurements", "llm_extraction"),
            PlannedStep(3, TaskType.DOCUMENT_ANALYSIS, "Search SOP knowledge base for compliance criteria", "rag"),
            PlannedStep(4, TaskType.DOCUMENT_ANALYSIS, "Generate deliverable document", "docx_generator"),
            PlannedStep(5, TaskType.DOCUMENT_ANALYSIS, "Verify document integrity", "verifier"),
        ]
        return ClassificationResult(
            primary_task=TaskType.DOCUMENT_ANALYSIS,
            is_multi_step=True,
            steps=steps,
            selected_model=model,
            selected_role="general",
            reason="Document analysis task routed to document extraction and OCR pipeline.",
            confidence=0.90,
            selected_tools=["pdf_processor", "llm_extraction", "rag", "docx_generator", "verifier"],
        )

    # 7.5. Presentation Generation
    if any(re.search(p, q_lower) for p in _PRESENTATION_PATTERNS):
        model = get_available_model("general") or "llama3.1:8b"
        steps = [
            PlannedStep(1, TaskType.PRESENTATION_GENERATION, "Synthesize presentation slides using local model", "llm"),
            PlannedStep(2, TaskType.PRESENTATION_GENERATION, "Generate formatted PowerPoint presentation (.pptx)", "pptx_generator"),
            PlannedStep(3, TaskType.PRESENTATION_GENERATION, "Verify generated presentation file", "verifier"),
        ]
        return ClassificationResult(
            primary_task=TaskType.PRESENTATION_GENERATION,
            is_multi_step=False,
            steps=steps,
            selected_model=model,
            selected_role="general",
            reason="Presentation generation request routed to PPTX generator.",
            confidence=0.92,
            selected_tools=["llm", "pptx_generator", "verifier"],
        )

    # 8. Report Generation
    if any(re.search(p, q_lower) for p in _REPORT_PATTERNS):
        model = get_available_model("general") or "llama3.1:8b"
        steps = [
            PlannedStep(1, TaskType.REPORT_GENERATION, "Synthesize report sections using local model", "llm"),
            PlannedStep(2, TaskType.REPORT_GENERATION, "Generate formatted Word document (.docx)", "docx_generator"),
            PlannedStep(3, TaskType.REPORT_GENERATION, "Verify generated document on filesystem", "verifier"),
        ]
        return ClassificationResult(
            primary_task=TaskType.REPORT_GENERATION,
            is_multi_step=False,
            steps=steps,
            selected_model=model,
            selected_role="general",
            reason="Formal document generation request routed to DOCX generator.",
            confidence=0.89,
            selected_tools=["llm", "docx_generator", "verifier"],
        )

    # 9. Fallback: General Chat / Reasoning
    model = get_available_model("general") or "llama3.1:8b"
    steps = [
        PlannedStep(1, TaskType.GENERAL_CHAT, "Generate response using local general reasoning model", "llm"),
        PlannedStep(2, TaskType.GENERAL_CHAT, "Verify response completeness", "verifier"),
    ]
    return ClassificationResult(
        primary_task=TaskType.GENERAL_CHAT,
        is_multi_step=False,
        steps=steps,
        selected_model=model,
        selected_role="general",
        reason="General inquiry routed to local reasoning LLM.",
        confidence=0.75,
        selected_tools=["llm", "verifier"],
    )
