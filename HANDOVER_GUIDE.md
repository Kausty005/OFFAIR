# 🛡️ SIH26117 — Sovereign AI Workbench: Teammate Handover & Developer Guide

> **Project Tagline**: *"Private Data. Local Intelligence. Real Work."*  
> **Target**: Air-gapped, sovereign AI agent workbench using multiple open-weight LLMs running locally on hardware (optimized for RTX 4050 6GB VRAM laptops).

---

## 📌 1. Project Overview & What Has Been Done

We have built the **first working prototype** for an on-premise, air-gapped Sovereign AI Workbench. The system takes raw user tasks or industrial files (PDFs, images, data), dynamically selects the best local LLM for the task, extracts structured data, queries a local RAG knowledge base, executes calculations/code in a sandbox, and outputs verified reports (`.docx`).

### Core Architecture & Tech Stack

```
                        ┌────────────────────────────────────────┐
                        │      Next.js Frontend (:5000)          │
                        │ React 18 / Tailwind / SSE Streaming    │
                        └───────────────────┬────────────────────┘
                                            │ HTTP / SSE
                                            ▼
                        ┌────────────────────────────────────────┐
                        │       FastAPI Backend (:8000)          │
                        │       (main.py & Agent Engine)         │
                        └───────┬───────────┬────────────┬───────┘
                                │           │            │
             ┌──────────────────┘           │            └──────────────────┐
             ▼                              ▼                               ▼
 ┌───────────────────────┐    ┌───────────────────────────┐    ┌───────────────────────┐
 │   Ollama LLM Engine   │    │     Local ChromaDB RAG    │    │  Docker Code Sandbox  │
 │   (:11434 - REST)     │    │ (nomic-embed-text model)  │    │  (python:3.11-slim)   │
 └───────────────────────┘    └───────────────────────────┘    └───────────────────────┘
```

- **Frontend**: Next.js App Router UI (`frontend/`) connecting via **Server-Sent Events (SSE)** to stream agent steps real-time.
- **Backend API**: FastAPI (`main.py`) exposing endpoints for file upload, task streaming, security logs, knowledge base ingestion, and status checks. (Legacy Streamlit interface is also present in `app.py`).
- **Agent Orchestrator**: Lightweight custom Python engine (`agent/agent.py`) using **Plan → Execute → Verify** logic without heavy framework overhead.
- **Model Router**: Heuristic & rule-based classifier (`router/model_router.py`) that routes general, coding, vision, and calculation tasks to specific local Ollama models.
- **Document & OCR Pipeline**:
  - `document/pdf_processor.py`: Parses digital PDFs and detects scanned documents.
  - `document/ocr.py`: Applies Tesseract OCR (`pytesseract`) on scanned PDF pages or images.
  - `document/vision.py`: Sends image frames to local vision LLMs (`llava-phi3:latest`).
- **Local RAG System**: Uses ChromaDB (`rag/vector_store.py` & `tools/search.py`) with `nomic-embed-text` embeddings.
- **Secure Code Execution**: Docker container sandbox (`tools/sandbox.py`) running Python code with `--network none` (network disabled) and running auto-generated unit tests.
- **Report Generation**: `tools/docx_generator.py` produces formatted, professional `.docx` deliverables (e.g. Maintenance Approval Notes).
- **Air-Gap Guard**: `security/network_guard.py` & `security/audit.py` log zero external API calls and block remote connections in air-gapped mode.

---

## ⚠️ 2. What Is Not Done Properly / Known Limitations & TODOs

Here are the current gaps, edge cases, and areas that need polishing or further work:

1. **Ollama Pre-Pull Requirement**:
   - The workbench relies on Ollama models already being downloaded (`ollama pull ...`). If a model is missing when a user submits a task, the agent gracefully returns a warning message instructing them to pull the model, but it does not auto-download models (to preserve strict air-gap rules).
2. **Tesseract Binary OS Dependency**:
   - `pytesseract` requires the Tesseract OCR executable (`tesseract.exe` on Windows) installed on the system and added to `PATH`. If missing, scanned PDF OCR will fall back to standard text extraction (which yields empty text for pure images).
3. **Docker Desktop Dependency**:
   - The Coding Agent sandbox relies on Docker Desktop being running. If Docker daemon is offline, sandbox execution skips Docker and returns a warning result without crashing.
4. **Single-Attempt Code Refinement Loop**:
   - If unit tests fail in the Docker sandbox, `agent.py` only performs **1 iteration** of code repair. Implementing a multi-turn retry loop (up to 3 attempts) would improve code completion rates.
5. **PDF Context Length Truncation**:
   - For long document extractions, text is truncated to ~4000 characters to prevent VRAM context window overflow on 8B/3B models. Chunking + map-reduce summarization can be added for massive 50+ page PDFs.
6. **SSE Connection Re-attach**:
   - In `main.py`, SSE streams (`/api/stream/{task_id}`) stream progress to the frontend. If the user refreshes the browser while an agent task is running, the frontend loses state subscription (the backend finish task silently). Adding persistent task state in DB/Redis would make streaming resilient.

---

## 🧪 3. Tests Needed to Check Working

### A. Automated Unit Tests (Pytest)
Run the unit test suite via Python:
```powershell
pytest tests/
```
**Current Status**: ✅ All 11 unit tests pass (`test_calculator.py`, `test_model_router.py`, `test_network_guard.py`).

### B. Verification & Health Endpoint
Check if all system services are active by visiting:
- **`http://localhost:8000/api/status`**
- Verify JSON returns: `{"ollama": true, "docker": true, "ocr": true, "external_api_calls": 0}`

### C. Manual Demo Test Matrix (Feature Checklist)

| # | Test Scenario | Steps to Execute | Expected Result |
|---|---|---|---|
| 1 | **System Health** | Open UI (`http://localhost:5000`), check system tab | Ollama, Docker, OCR, RAG show ✅ READY |
| 2 | **RAG Knowledge Base** | 1. Go to **Knowledge Base** tab<br>2. Upload `demo_data/maintenance_sop.pdf`<br>3. Click **Ingest** | Document chunks embedded into ChromaDB |
| 3 | **Inspection Agent Workflow** | 1. Go to **Inspection Agent** tab<br>2. Upload `demo_data/inspection_report.pdf`<br>3. Click **Run Agent** | OCR extracts text → RAG context lookup → `.docx` approval report generated in `workspace/outputs/` |
| 4 | **Coding Agent Sandbox** | 1. Go to **Coding Agent** tab<br>2. Submit: *"Write a python function to compute fibonacci sequence and unit tests"* | Model generates Python + unittest code → Runs in Docker container with network disabled (`--network none`) → All tests pass |
| 5 | **Multimodal Vision** | 1. Go to **AI Workbench** tab<br>2. Upload `demo_data/inspection_image.jpg`<br>3. Prompt: *"Analyze this photograph"* | Router detects image → Sends to `llava-phi3` → Vision summary generated |
| 6 | **Air-Gap & Security Check** | Go to **Audit & Security** tab | Confirms `External API Calls = 0` and Air-Gap mode active |

---

## 💻 4. How to Download, Install & Run the Project

### System Prerequisites to Download

1. **Python 3.11+**: Download from [python.org](https://www.python.org/downloads/) (Ensure "Add Python to PATH" is checked).
2. **Node.js 18+ & npm**: Download from [nodejs.org](https://nodejs.org/).
3. **Ollama**: Download from [ollama.com](https://ollama.com/).
4. **Docker Desktop**: Download from [docker.com](https://www.docker.com/products/docker-desktop/).
5. **Tesseract OCR (Windows)**:
   - Download installer from [UB-Mannheim Tesseract Wiki](https://github.com/UB-Mannheim/tesseract/wiki).
   - Add `C:\Program Files\Tesseract-OCR` to System Environment Variable `PATH`.

---

### Step-by-Step Installation

#### Step 1: Install Python Dependencies & Node Modules
Open PowerShell inside the `sih26117/` directory:
```powershell
# Install Python packages
pip install -r requirements.txt

# Install Frontend packages
cd frontend
npm install
cd ..
```

#### Step 2: Start Ollama & Pull Open-Weight Models
In a separate terminal, ensure Ollama service is active:
```powershell
ollama serve
```
Then pull the required models:
```powershell
ollama pull nomic-embed-text:latest
ollama pull qwen2.5-coder:3b
ollama pull llava-phi3:latest
ollama pull llama3.1:8b
```

#### Step 3: Start Docker Desktop & Pull Sandbox Image
Ensure Docker Desktop is open and running, then pull the lightweight sandbox base image:
```powershell
docker pull python:3.11-slim
```

#### Step 4: Run Automated Setup Script (Optional Convenience)
You can run our automated script which performs checks and pulls dependencies:
```powershell
.\setup.ps1
```

---

### Running the Project

Run the master start script from the root `sih26117/` directory:
```powershell
.\run.ps1
```

This will automatically launch:
1. **FastAPI Backend** on `http://localhost:8000` (API docs at `http://localhost:8000/docs`)
2. **Next.js Frontend UI** on `http://localhost:5000`

*Alternative (Manual Launch):*
- Terminal 1 (Backend): `python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload`
- Terminal 2 (Frontend): `cd frontend; npm run dev`
- Terminal 3 (Legacy Streamlit option): `streamlit run app.py`

---

## 📁 Key Directories Quick Reference

- **`main.py`**: FastAPI server & endpoints (`/api/run`, `/api/stream`, `/api/status`, `/api/upload`).
- **`agent/`**: Agent planner, step executor, state manager, and verifier.
- **`router/`**: Rule-based task classifier & model selector.
- **`document/`**: PDF parsing, OCR, and vision model handlers.
- **`rag/`**: Vector DB (ChromaDB) and document ingestion tools.
- **`tools/`**: Docker sandbox runner, DOCX generator, calculators.
- **`security/`**: Air-gap network guard and audit logger.
- **`frontend/`**: Next.js 14/15 React frontend.
- **`demo_data/`**: Sample PDFs and images for testing.
- **`workspace/`**: Temporary storage for uploaded and generated output files.
