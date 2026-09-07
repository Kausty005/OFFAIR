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

from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
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
    allow_origins=["http://localhost:5000", "http://127.0.0.1:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ── Document Tools (no AI/Ollama/Docker dependency) ─────────────────────────
app.include_router(document_tools_router)

# Task queue registry: task_id -> asyncio.Queue
task_queues: dict[str, asyncio.Queue] = {}
# Task state registry: task_id -> AgentState
task_states: dict[str, Any] = {}
last_completed_state: Optional[Any] = None

UPLOAD_DIR = Path("workspace/uploads")
OUTPUT_DIR = Path("workspace/outputs")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


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

    task_id = os.urandom(8).hex()
    queue: asyncio.Queue = asyncio.Queue()
    task_queues[task_id] = queue

    loop = asyncio.get_running_loop()

    has_image = any(
        f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".webp"))
        for f in file_paths
    )
    has_pdf = any(f.lower().endswith(".pdf") for f in file_paths)

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
                    msg = await asyncio.wait_for(queue.get(), timeout=120)
                except asyncio.TimeoutError:
                    yield {"data": json.dumps({"type": "heartbeat"})}
                    continue
                yield {"data": json.dumps(msg)}
                if msg["type"] in ("complete", "error"):
                    break
        finally:
            task_queues.pop(task_id, None)

    return EventSourceResponse(generator())


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
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=str(file_path), filename=safe_name)


@app.get("/api/download")
async def download_file_by_path(path: str):
    """Download a generated output file by full absolute path."""
    file_path = Path(path)
    # Security: only allow files in workspace/ dir
    workspace_root = Path("workspace").resolve()
    try:
        file_path.resolve().relative_to(workspace_root)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream",
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

class RAGAskRequest(BaseModel):
    query: str
    model: Optional[str] = None
    top_k: Optional[int] = 5


@app.get("/api/knowledge")
async def list_knowledge():
    """List documents in the knowledge base along with vector store statistics."""
    from rag.vector_store import get_collection_stats
    kb_path = Path("knowledge_base")
    docs = []
    if kb_path.exists():
        for p in kb_path.iterdir():
            if p.suffix.lower() in (".pdf", ".txt", ".docx", ".md", ".csv", ".json"):
                docs.append({
                    "name": p.name,
                    "size": p.stat().st_size,
                    "path": str(p),
                    "ext": p.suffix.lower().replace(".", ""),
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
async def upload_knowledge(file: UploadFile = File(...), auto_ingest: bool = Form(False)):
    """Upload a document to the knowledge base, optionally auto-ingesting."""
    kb_path = Path("knowledge_base")
    kb_path.mkdir(exist_ok=True)
    safe_name = Path(file.filename).name
    dest = kb_path / safe_name
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    ingest_result = None
    if auto_ingest:
        from rag.ingest import ingest_file
        ingest_result = ingest_file(dest)

    return {
        "filename": safe_name,
        "path": str(dest),
        "size": dest.stat().st_size,
        "auto_ingested": auto_ingest,
        "ingest_result": ingest_result,
    }


@app.post("/api/knowledge/ingest")
async def ingest_knowledge(background_tasks: BackgroundTasks):
    """Ingest all documents in knowledge_base/ into ChromaDB / pure-Python store."""
    def do_ingest():
        try:
            from rag.ingest import ingest_directory
            kb_path = Path("knowledge_base")
            kb_path.mkdir(exist_ok=True)
            result = ingest_directory(str(kb_path))
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
    if not req.query.strip():
        return {"query": "", "results": [], "count": 0}
    results = retrieve(req.query, top_k=req.top_k or 5)
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
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    return answer_with_rag(req.query, top_k=req.top_k or 5, model=req.model)


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
