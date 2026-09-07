import os
import json
import uuid
import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Any

router = APIRouter(prefix="/api/history", tags=["history"])

HISTORY_DIR = Path("workspace/history")
HISTORY_DIR.mkdir(parents=True, exist_ok=True)

class SessionUpdate(BaseModel):
    title: Optional[str] = None
    messages: List[Any]

def get_session_file(session_id: str) -> Path:
    if not session_id.isalnum() and "-" not in session_id:
        raise HTTPException(status_code=400, detail="Invalid session ID")
    return HISTORY_DIR / f"{session_id}.json"

@router.get("/")
def list_sessions():
    sessions = []
    for f in HISTORY_DIR.glob("*.json"):
        try:
            with open(f, "r", encoding="utf-8") as file:
                data = json.load(file)
                sessions.append({
                    "id": data.get("id", f.stem),
                    "title": data.get("title", "New Chat"),
                    "updatedAt": data.get("updatedAt", "")
                })
        except Exception:
            pass
    # Sort by updatedAt descending
    sessions.sort(key=lambda x: x.get("updatedAt", ""), reverse=True)
    return sessions

@router.get("/{session_id}")
def get_session(session_id: str):
    file_path = get_session_file(session_id)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}")
def save_session(session_id: str, payload: SessionUpdate):
    file_path = get_session_file(session_id)
    
    # Load existing to preserve title if not provided
    data = {"id": session_id, "title": "New Chat", "messages": [], "updatedAt": ""}
    is_new = not file_path.exists()
    
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass

    if payload.title and (is_new or data["title"] == "New Chat" or data["title"] == payload.title):
        title = payload.title
        # Attempt LLM auto-title on the first save
        if len(payload.messages) <= 2:
            try:
                import ollama
                from models.model_registry import get_available_model
                model = get_available_model("coding") or "qwen2.5-coder:3b"
                prompt = f"Generate a very short 2-4 word title for this conversation based on the first message. Do not include quotes.\n\nMessage: {payload.title}\n\nTitle:"
                resp = ollama.generate(model=model, prompt=prompt, temperature=0.1)
                llm_title = resp.get("response", "").strip().replace('"', '').replace("'", "")
                if llm_title and len(llm_title) < 40:
                    title = llm_title
            except Exception as e:
                pass
        data["title"] = title
        
    data["messages"] = payload.messages
    data["updatedAt"] = datetime.datetime.utcnow().isoformat() + "Z"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        
    return {"status": "success", "session": data}

@router.delete("/{session_id}")
def delete_session(session_id: str):
    file_path = get_session_file(session_id)
    if file_path.exists():
        file_path.unlink()
        return {"status": "success"}
    raise HTTPException(status_code=404, detail="Session not found")
