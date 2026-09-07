"""
main.py
FastAPI backend for the Sovereign AI Workbench.
Replaces the old Streamlit app.py entry point.
"""

import asyncio
import json
import logging
import os
import shutil
import sys
import time
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Any

from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sse_starlette.sse import EventSourceResponse

# Add backend root to path
sys.path.insert(0, os.path.dirname(__file__))

from agent.agent import Agent
from agent.state import AgentStep
from models.model_registry import get_all_models, get_available_model
import models.ollama_client as ollama_client
from security.audit import log, get_recent_logs
from tools.files import get_output_path
from tools.pptx_generator import (
    create_maintenance_approval_pptx,
    create_presentation_from_markdown,
    pptx_available,
)
from document_tools import document_tools_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Sovereign AI Workbench API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Air-gapped LAN — all local-network clients allowed
    allow_credentials=False,  # Must be False when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ── Document Tools (no AI/Ollama/Docker dependency) ─────────────────────────
app.include_router(document_tools_router)

from router.history import router as history_router
app.include_router(history_router)

# Task queue registry: task_id -> asyncio.Queue
task_queues: dict[str, asyncio.Queue] = {}
# Task state registry: task_id -> AgentState
task_states: dict[str, Any] = {}
last_completed_state: Optional[Any] = None

UPLOAD_DIR = Path("workspace/uploads")
OUTPUT_DIR = Path("workspace/outputs")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@app.on_event("startup")
async def auto_ingest_knowledge_base():
    """Auto-ingest knowledge base on startup if it's empty or sparse."""
    try:
        from rag.vector_store import get_collection_stats
        from rag.ingest import ingest_directory

        stats = get_collection_stats()
        count = stats.get("count", 0)
        kb_path = Path("knowledge_base")

        if count < 5 and kb_path.exists() and any(kb_path.iterdir()):
            logger.info(f"Knowledge base sparse ({count} chunks). Auto-ingesting...")
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: ingest_directory(str(kb_path)))
            new_stats = get_collection_stats()
            logger.info(f"Auto-ingest complete. KB now has {new_stats.get('count', 0)} chunks.")
        else:
            logger.info(f"Knowledge base ready ({count} chunks).")
    except Exception as e:
        logger.warning(f"Auto-ingest skipped: {e}")


# ─────────────────────────────────────────────────────────────
# File Upload
# ─────────────────────────────────────────────────────────────

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file to workspace. Returns filename and server path."""
    safe_name = Path(file.filename).name  # Prevent path traversal
    file_path = UPLOAD_DIR / safe_name
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {
        "filename": safe_name,
        "path": str(file_path),
        "size": file_path.stat().st_size,
    }


@app.post("/api/ingest")
async def ingest_to_knowledge_base(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    classification: str = Form("internal"),
    department: str = Form(""),
):
    """Upload and ingest a document into the local knowledge base."""
    from rag.ingest import ingest_file
    KB_DIR = Path("knowledge_base")
    KB_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename).name
    dest = KB_DIR / safe_name
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    security_metadata = {
        "classification": classification,
        "department": department,
        "allowed_roles": ["admin", "engineer", "employee"],
    }
    result = ingest_file(dest, security_metadata=security_metadata)
    log("KB_INGEST", file=safe_name, chunks=result.get("chunks", 0))
    return {
        "filename": safe_name,
        "chunks": result.get("chunks", 0),
        "stored": result.get("stored", False),
        "error": result.get("error"),
    }


@app.get("/api/kb/stats")
async def kb_stats():
    """Return knowledge base statistics."""
    from rag.vector_store import get_collection_stats
    stats = get_collection_stats()
    kb_path = Path("knowledge_base")
    docs = [f.name for f in kb_path.iterdir() if f.is_file()] if kb_path.exists() else []
    return {**stats, "documents": docs, "document_count": len(docs)}


@app.post("/api/kb/reingest")
async def reingest_knowledge_base(background_tasks: BackgroundTasks):
    """Re-ingest all documents in the knowledge_base directory."""
    from rag.ingest import ingest_directory
    from rag.vector_store import delete_collection

    def _do_reingest():
        delete_collection()
        result = ingest_directory("knowledge_base")
        log("KB_REINGEST", total_chunks=result.get("total_chunks", 0))

    background_tasks.add_task(asyncio.to_thread, _do_reingest)
    return {"status": "reingest_started", "message": "Re-ingestion is running in the background."}


# ─────────────────────────────────────────────────────────────
# Agent Run + SSE Stream
# ─────────────────────────────────────────────────────────────
# Interactive Code Execution (Direct Sandbox - No LLM overhead)
# ─────────────────────────────────────────────────────────────

from pydantic import BaseModel, Field

class CodeExecuteRequest(BaseModel):
    code: str = Field(..., description="Code to execute in Docker sandbox")
    language: Optional[str] = Field("python", description="Language of code")
    stdin: Optional[str] = Field("", description="Standard input (supports multiline)")
    timeout: Optional[int] = Field(30, description="Timeout in seconds")


@app.post("/api/execute")
@app.post("/api/code/execute")
@app.post("/execute")
async def execute_code_endpoint(req: CodeExecuteRequest):
    """
    Interactive code execution in Docker sandbox.
    Direct path from Code Editor + Stdin -> Docker Sandbox -> Response.
    Bypasses LLM and LangGraph to reduce GPU usage, latency, and token cost.
    """
    from tools.sandbox import run_code_sandbox
    result = run_code_sandbox(
        code=req.code,
        language=req.language or "python",
        stdin=req.stdin or "",
        timeout=req.timeout or 30,
    )
    return result


# ─────────────────────────────────────────────────────────────
# Agent Run + SSE Stream
# ─────────────────────────────────────────────────────────────

@app.post("/api/run")
async def run_agent_endpoint(
    background_tasks: BackgroundTasks,
    task: str = Form(...),
    files: str = Form("[]"),
    user_context: str = Form("{}"),
    chat_history: str = Form("[]"),
):
    """
    Start an agent run via LangGraph stateful orchestration.
    Returns a task_id immediately. Connect to /api/stream/{task_id} for SSE events.
    """
    try:
        file_paths = json.loads(files)
    except Exception:
        file_paths = []

    try:
        u_context = json.loads(user_context)
    except Exception:
        u_context = {}

    try:
        c_history = json.loads(chat_history)
    except Exception:
        c_history = []

    if u_context.get("session_token"):
        from security.auth import user_from_token
        try:
            authenticated = user_from_token(u_context["session_token"])
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"MongoDB unavailable: {exc}") from exc
        if not authenticated:
            raise HTTPException(status_code=401, detail="Valid login session required")
        u_context = authenticated

    task_id = os.urandom(8).hex()
    queue: asyncio.Queue = asyncio.Queue()
    task_queues[task_id] = queue

    loop = asyncio.get_running_loop()

    has_image = any(
        f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".webp"))
        for f in file_paths
    )
    has_pdf = any(f.lower().endswith(".pdf") for f in file_paths)
    logger.info(f"[API/RUN] task={task!r:.80} files={file_paths} history_len={len(c_history)}")

    def _push(event_type: str, data: dict):
        """Thread-safe push to queue."""
        try:
            loop.call_soon_threadsafe(queue.put_nowait, {"type": event_type, "data": data})
        except Exception as e:
            logger.error(f"Queue push error: {e}")

    def sync_run():
        agent = Agent()

        def on_step(step: AgentStep):
            _push("progress", {
                "description": step.description,
                "status": step.status,
                "result": step.result or "",
                "tool": step.tool or "",
            })

        agent.add_progress_callback(on_step)

        try:
            state = agent.run(
                task=task,
                uploaded_files=file_paths,
                has_image=has_image,
                has_pdf=has_pdf,
                user_context=u_context,
                chat_history=c_history,
            )
            task_states[task_id] = state
            global last_completed_state
            last_completed_state = state
            _push("complete", {
                "final_output": state.final_output or "",
                "verified": state.verified,
                "verification_notes": state.verification_notes or [],
                "output_files": state.output_files or [],
                "rag_sources": state.rag_sources or [],
                "extracted_data": state.extracted_data or {},
                "selected_model": state.selected_model or "",
                "task_type": state.task_type or "",
                "routing_reason": state.routing_reason or "",
                "tool_results": {
                    k: v for k, v in (state.tool_results or {}).items()
                    if k in ["calculations", "sandbox_result", "generated_code"]
                },
            })
        except Exception as e:
            logger.exception("Agent run failed")
            _push("error", {"error": str(e)})

    background_tasks.add_task(asyncio.to_thread, sync_run)
    return {"task_id": task_id}


@app.get("/api/stream/{task_id}")
async def stream_task(task_id: str):
    """SSE stream for real-time agent activity."""
    queue = task_queues.get(task_id)
    if queue is None:
        raise HTTPException(status_code=404, detail="Task not found")

    async def generator():
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=5)
                except asyncio.TimeoutError:
                    yield {"data": json.dumps({"type": "heartbeat"})}
                    continue
                yield {"data": json.dumps(msg)}
                if msg["type"] in ("complete", "error"):
                    break
        finally:
            task_queues.pop(task_id, None)

    return EventSourceResponse(
        generator(),
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


# ─────────────────────────────────────────────────────────────
# Model & System Info
# ─────────────────────────────────────────────────────────────

@app.get("/api/models")
async def get_models():
    """Get all configured models and their availability."""
    configured = get_all_models()
    available_names = []
    try:
        available_names = [m.get("name", "") for m in ollama_client.list_models()]
    except Exception:
        pass

    result = {}
    for role, info in configured.items():
        model_name = info.get("name", "")
        result[role] = {
            **info,
            "available": any(
                model_name in n or model_name.split(":")[0] in n
                for n in available_names
            ),
        }
    return result


@app.get("/api/status")
async def get_status():
    """System health check."""
    ollama_up = ollama_client.ping()
    ollama_models = []
    try:
        ollama_models = [m.get("name", "") for m in ollama_client.list_models()]
    except Exception:
        pass

    # Check docker
    import subprocess
    docker_up = False
    try:
        r = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
        docker_up = r.returncode == 0
    except Exception:
        pass

    # Check tesseract
    try:
        from document.ocr import tesseract_available
        ocr_up = tesseract_available()
    except Exception:
        ocr_up = False

    # Check knowledge base
    kb_path = Path("knowledge_base")
    kb_docs = list(kb_path.glob("*.pdf")) if kb_path.exists() else []

    return {
        "ollama": ollama_up,
        "ollama_models": ollama_models,
        "docker": docker_up,
        "ocr": ocr_up,
        "knowledge_base": len(kb_docs),
        "external_api_calls": 0,
        "internet_dependency": False,
        "timestamp": time.time(),
    }


@app.get("/api/security")
async def get_security():
    """Security dashboard data."""
    return {
        "local_model_inference": True,
        "local_ocr": True,
        "local_rag": True,
        "local_file_storage": True,
        "external_llm_api": 0,
        "remote_endpoints": 0,
        "internet_dependency": "NONE AFTER SETUP",
        "ollama_endpoint": "http://localhost:11434",
        "all_local": True,
    }


@app.get("/api/logs")
async def get_logs(limit: int = 30):
    """Get recent audit log entries."""
    try:
        return get_recent_logs(limit=limit)
    except Exception as e:
        return []


# ─────────────────────────────────────────────────────────────
# File Download
# ─────────────────────────────────────────────────────────────

@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """Download a generated output file by filename."""
    safe_name = Path(filename).name
    file_path = OUTPUT_DIR / safe_name
    if not file_path.exists():
        file_path = Path("workspace") / safe_name
    if not file_path.exists():
        file_path = Path("workspace/outputs") / safe_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    media_types = {
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pdf": "application/pdf",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".txt": "text/plain; charset=utf-8",
    }
    media_type = media_types.get(file_path.suffix.lower(), "application/octet-stream")
    return FileResponse(path=str(file_path), filename=safe_name, media_type=media_type)


@app.get("/api/download")
async def download_file_by_path(path: str):
    """Download a generated output file by full absolute path or relative path."""
    safe_name = Path(path).name

    # Try candidates in order of preference
    candidates = [
        Path(path),                      # exact path as provided
        OUTPUT_DIR / safe_name,          # just the filename in outputs dir
        Path("workspace") / safe_name,   # workspace root fallback
    ]

    resolved = None
    for candidate in candidates:
        try:
            resolved_candidate = candidate.resolve()
            if resolved_candidate.exists() and resolved_candidate.is_file():
                resolved = resolved_candidate
                break
        except Exception:
            continue

    if not resolved:
        raise HTTPException(status_code=404, detail=f"File not found: {safe_name}")

    media_types = {
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pdf": "application/pdf",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".txt": "text/plain; charset=utf-8",
    }
    media_type = media_types.get(resolved.suffix.lower(), "application/octet-stream")
    return FileResponse(
        path=str(resolved),
        filename=safe_name,
        media_type=media_type,
    )


# ─────────────────────────────────────────────────────────────
# PPTX Presentation Generation Endpoint
# ─────────────────────────────────────────────────────────────

from pydantic import BaseModel

class GeneratePPTXRequest(BaseModel):
    task_id: Optional[str] = None
    equipment_name: Optional[str] = None
    equipment_id: Optional[str] = None
    inspection_date: Optional[str] = None
    findings: Optional[list[str]] = None
    measurements: Optional[dict] = None
    recommendations: Optional[str] = None
    sop_references: Optional[list[dict]] = None
    risk_level: Optional[str] = "HIGH"
    title: Optional[str] = None
    content: Optional[str] = None
    format: Optional[str] = "file"  # "file" or "json"


def _build_pptx_for_state_or_data(
    task_id: Optional[str] = None,
    req_data: Optional[GeneratePPTXRequest] = None,
) -> dict:
    if not pptx_available():
        raise HTTPException(status_code=503, detail="python-pptx is not installed")

    # 1. Retrieve state from task_id or last_completed_state
    state = None
    if task_id and task_id in task_states:
        state = task_states[task_id]
    elif last_completed_state is not None:
        state = last_completed_state

    # 2. Extract fields
    extracted = (state.extracted_data or {}) if state else {}
    req = req_data or GeneratePPTXRequest()

    eq_name = req.equipment_name or extracted.get("equipment_name") or "Industrial Equipment"
    eq_id = req.equipment_id or extracted.get("equipment_id") or "EQUIP-001"
    insp_date = req.inspection_date or extracted.get("inspection_date") or datetime.now().strftime("%Y-%m-%d")
    findings = req.findings or extracted.get("findings") or ["No critical anomalies noted during inspection."]
    measurements = req.measurements or extracted.get("measurements") or {}
    recommendations = req.recommendations or (state.tool_results.get("reasoning") if state else "") or extracted.get("recommendations") or "Verify equipment parameters and schedule routine maintenance."
    risk_level = req.risk_level or extracted.get("severity", "HIGH").upper()

    # SOP references
    sop_refs = req.sop_references
    if not sop_refs and state and state.rag_sources:
        sop_refs = [
            {
                "document": r.get("document", "SOP"),
                "page": r.get("page", ""),
                "text": r.get("text", "")[:300],
            }
            for r in state.rag_sources[:5]
        ]
    if not sop_refs:
        sop_refs = [{"document": "SOP-GENERAL", "page": "1", "text": "Standard operational guidelines applied."}]

    # If arbitrary content/markdown was sent, use markdown presentation builder
    if req.content:
        safe_title = re.sub(r"[^\w\-]", "_", (req.title or "Presentation")[:30]).strip("_") or "Presentation"
        filename = f"{safe_title}.pptx"
        out_path = OUTPUT_DIR / filename
        res = create_presentation_from_markdown(
            req.content,
            default_title=req.title or "Presentation",
            output_path=out_path
        )
    else:
        safe_id = re.sub(r"[^\w\-]", "_", str(eq_id))
        filename = f"{safe_id}_Maintenance_Approval_Note.pptx"
        out_path = OUTPUT_DIR / filename
        res = create_maintenance_approval_pptx(
            equipment_name=eq_name,
            equipment_id=eq_id,
            inspection_date=insp_date,
            findings=findings,
            measurements=measurements,
            recommendations=recommendations,
            sop_references=sop_refs,
            output_path=out_path,
            risk_level=risk_level,
        )

    if not res.get("success"):
        raise HTTPException(status_code=500, detail=res.get("error", "Failed to generate PPTX"))

    return {
        "success": True,
        "path": str(out_path),
        "filename": filename,
        "size": res.get("size", 0),
        "verification_question": "Is the generated PPTX correctly formatted and includes all inspection details?"
    }


@app.get("/api/generate-pptx")
async def generate_pptx_get(task_id: Optional[str] = None, format: Optional[str] = "file"):
    """Generate or download PPTX presentation via GET request."""
    result = _build_pptx_for_state_or_data(task_id=task_id)
    if format == "json":
        return result
    return FileResponse(
        path=result["path"],
        filename=result["filename"],
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )


@app.post("/api/generate-pptx")
async def generate_pptx_post(req: Optional[GeneratePPTXRequest] = None):
    """Generate PPTX presentation via POST request with optional payload."""
    req_data = req or GeneratePPTXRequest()
    result = _build_pptx_for_state_or_data(task_id=req_data.task_id, req_data=req_data)
    if req_data.format == "file":
        return FileResponse(
            path=result["path"],
            filename=result["filename"],
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        )
    return result


# ─────────────────────────────────────────────────────────────
# Knowledge Base & RAG Endpoints
# ─────────────────────────────────────────────────────────────

class RAGSearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    user_id: Optional[str] = None
    role: Optional[str] = None
    session_token: Optional[str] = None

class RAGAskRequest(BaseModel):
    query: str
    model: Optional[str] = None
    top_k: Optional[int] = 5
    user_id: Optional[str] = None
    role: Optional[str] = None
    session_token: Optional[str] = None


class AuthRequest(BaseModel):
    username: str
    password: str
    role: str
    details: Optional[dict[str, Any]] = None


def _authenticated_user(token: Optional[str]) -> dict[str, str]:
    from security.auth import user_from_token
    try:
        user = user_from_token(token or "")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"MongoDB unavailable: {exc}") from exc
    if not user:
        raise HTTPException(status_code=401, detail="Valid login session required")
    return user


@app.post("/api/auth/register")
async def register(req: AuthRequest):
    from security.auth import register_user
    try:
        return register_user(req.username, req.password, req.role, req.details or {})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"MongoDB unavailable: {exc}") from exc


@app.post("/api/auth/login")
async def login(req: AuthRequest):
    from security.auth import login_user
    try:
        return login_user(req.username, req.password, req.role)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"MongoDB unavailable: {exc}") from exc


@app.post("/api/auth/logout")
async def logout(authorization: Optional[str] = Header(None)):
    from security.auth import logout_user
    token = (authorization or "").removeprefix("Bearer ")
    logout_user(token)
    return {"logged_out": True}


@app.get("/api/auth/status")
async def auth_status():
    """Report local MongoDB availability for login diagnostics."""
    from security.auth import MONGODB_DATABASE, MONGODB_URI, _database
    try:
        _database().command("ping")
        return {"connected": True, "database": MONGODB_DATABASE, "uri": MONGODB_URI}
    except Exception as exc:
        return {"connected": False, "database": MONGODB_DATABASE, "uri": MONGODB_URI, "error": str(exc)}


@app.get("/api/knowledge/diagnostics")
async def knowledge_diagnostics(session_token: str):
    """Show whether authorized local retrieval is returning real indexed chunks."""
    from rag.vector_store import get_collection_stats
    from rag.retriever import retrieve
    from security.permissions import User
    authenticated = _authenticated_user(session_token)
    user = User(authenticated["username"], authenticated["role"])
    results = retrieve("maintenance vibration safety", top_k=3, user=user, authorized_only=True)
    return {
        "rag_local": True,
        "vector_store": get_collection_stats(),
        "user": authenticated,
        "authorized_results": len(results),
        "sources": [{"document": r.get("document"), "page": r.get("page"), "score": r.get("rerank_score", r.get("score"))} for r in results],
    }


@app.get("/api/knowledge")
async def list_knowledge():
    """List documents in the knowledge base along with vector store statistics and provenance metadata."""
    from rag.vector_store import get_collection_stats, _load_store
    kb_path = Path("knowledge_base")
    store = _load_store()
    doc_meta_map = {}
    for meta in store.get("metadatas", []):
        src = meta.get("source")
        if src and src not in doc_meta_map:
            doc_meta_map[src] = {
                "uploaded_by": meta.get("uploaded_by", "system"),
                "uploaded_at": meta.get("uploaded_at", ""),
                "allowed_roles": meta.get("allowed_roles", ["admin", "engineer", "employee"]),
                "min_role_level": meta.get("min_role_level", 10),
                "classification": meta.get("classification", "internal"),
                "department": meta.get("department", ""),
            }

    docs = []
    if kb_path.exists():
        for p in kb_path.iterdir():
            if p.suffix.lower() in (".pdf", ".txt", ".docx", ".md", ".csv", ".json"):
                m = doc_meta_map.get(p.name, {})
                docs.append({
                    "name": p.name,
                    "size": p.stat().st_size,
                    "path": str(p),
                    "ext": p.suffix.lower().replace(".", ""),
                    "uploaded_by": m.get("uploaded_by", "admin"),
                    "uploaded_at": m.get("uploaded_at", ""),
                    "allowed_roles": m.get("allowed_roles", ["admin", "engineer", "employee"]),
                    "min_role_level": m.get("min_role_level", 10),
                    "classification": m.get("classification", "internal"),
                    "department": m.get("department", ""),
                })
    stats = get_collection_stats()
    return {
        "documents": docs,
        "total_documents": len(docs),
        "vector_store": stats,
    }


@app.get("/api/knowledge/status")
async def knowledge_status():
    """Get RAG knowledge base operational status."""
    from rag.retriever import get_kb_status
    return get_kb_status()


@app.post("/api/knowledge/upload")
async def upload_knowledge(
    file: UploadFile = File(...),
    auto_ingest: bool = Form(False),
    department: str = Form(""),
    classification: str = Form("internal"),
    allowed_roles: str = Form(""),
    session_token: Optional[str] = Form(None),
):
    """Upload a document to the knowledge base, optionally auto-ingesting with provenance tracking."""
    kb_path = Path("knowledge_base")
    kb_path.mkdir(exist_ok=True)
    safe_name = Path(file.filename).name
    dest = kb_path / safe_name
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    ingest_result = None
    if auto_ingest:
        from rag.ingest import ingest_file
        from security.permissions import access_metadata, normalize_role

        authenticated = None
        if session_token:
            try:
                authenticated = _authenticated_user(session_token)
            except Exception:
                pass

        uploader_name = authenticated["username"] if authenticated else "admin"
        uploader_role = authenticated["role"] if authenticated else "admin"

        dept_str = str(department.default if hasattr(department, "default") else department or "").strip()
        class_str = str(classification.default if hasattr(classification, "default") else classification or "internal").strip()
        roles_str = str(allowed_roles.default if hasattr(allowed_roles, "default") else allowed_roles or "").strip()

        # Determine roles based on input or hierarchy
        raw_roles = [normalize_role(role.strip()) for role in roles_str.split(",") if role.strip()]
        if not raw_roles:
            if uploader_role == "admin":
                raw_roles = ["admin", "engineer", "employee"]
            elif uploader_role in ("engineer", "eng"):
                raw_roles = ["admin", "engineer"]
            else:
                raw_roles = ["admin", "employee"]

        sec_meta = access_metadata(
            department=dept_str,
            classification=class_str,
            allowed_roles=raw_roles,
            uploaded_by=uploader_name,
        )

        ingest_result = ingest_file(
            dest,
            security_metadata=sec_meta,
        )

    return {
        "filename": safe_name,
        "path": str(dest),
        "size": dest.stat().st_size,
        "auto_ingested": auto_ingest,
        "ingest_result": ingest_result,
    }


@app.post("/api/knowledge/ingest")
async def ingest_knowledge(
    background_tasks: BackgroundTasks,
    department: str = Form(""),
    classification: str = Form("internal"),
    allowed_roles: str = Form(""),
    session_token: Optional[str] = Form(None),
):
    """Ingest all documents in knowledge_base/ into ChromaDB / pure-Python store."""
    def do_ingest():
        try:
            from rag.ingest import ingest_directory
            kb_path = Path("knowledge_base")
            kb_path.mkdir(exist_ok=True)
            authenticated = _authenticated_user(session_token)
            if authenticated["role"] != "admin":
                raise HTTPException(status_code=403, detail="Only admins may bulk-index the knowledge base")
            roles = [role.strip() for role in allowed_roles.split(",") if role.strip()]
            if not roles:
                roles = [authenticated["role"]]
            result = ingest_directory(
                str(kb_path),
                security_metadata={
                    "department": department.strip(),
                    "classification": classification.strip(),
                    "allowed_roles": roles,
                    "uploaded_by": authenticated["username"],
                },
            )
            log("KB_INGEST", result=result)
            return result
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            return {"error": str(e)}
    background_tasks.add_task(asyncio.to_thread, do_ingest)
    return {"status": "Ingestion started in background"}


@app.post("/api/knowledge/search")
async def search_knowledge(req: RAGSearchRequest):
    """Semantic search against the local knowledge base."""
    from rag.retriever import retrieve
    from security.permissions import User
    if not req.query.strip():
        return {"query": "", "results": [], "count": 0}
    authenticated = _authenticated_user(req.session_token)
    user = User(authenticated["username"], authenticated["role"])
    results = retrieve(
        req.query,
        top_k=req.top_k or 5,
        user=user,
        authorized_only=True,
    )
    return {
        "query": req.query,
        "results": results,
        "count": len(results),
        "local": True,
    }


@app.post("/api/knowledge/ask")
async def ask_knowledge(req: RAGAskRequest):
    """Ask a question and receive a grounded answer with source citations."""
    from rag.retriever import answer_with_rag
    from security.permissions import User
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    authenticated = _authenticated_user(req.session_token)
    user = User(authenticated["username"], authenticated["role"])
    return answer_with_rag(
        req.query,
        top_k=req.top_k or 5,
        model=req.model,
        user=user,
        authorized_only=True,
    )


@app.post("/api/knowledge/reset")
async def reset_knowledge():
    """Reset the vector store collection."""
    from rag.vector_store import delete_collection
    ok = delete_collection()
    return {"reset": ok}



# ─────────────────────────────────────────────────────────────
# Ollama Chat (for direct chat in workbench)
# ─────────────────────────────────────────────────────────────

@app.post("/api/chat")
async def chat_endpoint(
    message: str = Form(...),
    model_role: str = Form("general"),
    history: str = Form("[]"),
):
    """Direct streaming chat endpoint for the workbench."""
    try:
        history_msgs = json.loads(history)
    except Exception:
        history_msgs = []

    model = get_available_model(model_role) or get_available_model("general")
    if not model:
        raise HTTPException(status_code=503, detail="No model available")

    task_id = os.urandom(8).hex()
    queue: asyncio.Queue = asyncio.Queue()
    task_queues[task_id] = queue

    loop = asyncio.get_running_loop()

    def do_chat():
        try:
            messages = history_msgs + [{"role": "user", "content": message}]
            resp = ollama_client.chat(model=model, messages=messages)
            loop.call_soon_threadsafe(
                queue.put_nowait,
                {"type": "complete", "data": {"response": resp, "model": model}}
            )
        except Exception as e:
            loop.call_soon_threadsafe(
                queue.put_nowait,
                {"type": "error", "data": {"error": str(e)}}
            )

    asyncio.get_event_loop().run_in_executor(None, do_chat)
    return {"task_id": task_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
