# 📚 RAG Service Verification & Operational Guide — SIH26117

> **Project**: Sovereign AI Workbench  
> **Tagline**: *"Private Data. Local Intelligence. Real Work."*  
> **Hardware Target**: Air-gapped edge / local workstation (e.g. NVIDIA RTX 4050 6GB VRAM)  
> **Security Guarantee**: **Zero Cloud API calls, 100% On-Premise Execution**

---

## 📑 Table of Contents

1. [Executive Summary & RAG Architecture](#1-executive-summary--rag-architecture)
2. [Prerequisites & Environment Setup](#2-prerequisites--environment-setup)
3. [How to Run the Entire System Properly](#3-how-to-run-the-entire-system-properly)
4. [How to Verify & Check the RAG Service](#4-how-to-verify--check-the-rag-service)
   - [Method 1: Automated Standalone Test Script](#method-1-automated-standalone-test-script)
   - [Method 2: Pytest Unit Test Suite](#method-2-pytest-unit-test-suite)
   - [Method 3: Interactive Next.js Web UI](#method-3-interactive-nextjs-web-ui)
   - [Method 4: REST API Endpoints (cURL / Postman)](#method-4-rest-api-endpoints-curl--postman)
   - [Method 5: Legacy Streamlit UI](#method-5-legacy-streamlit-ui)
5. [Benchmark Query Matrix & Expected Grounded Outputs](#5-benchmark-query-matrix--expected-grounded-outputs)
6. [Air-Gap & Security Verification (Proof of Zero Cloud Calls)](#6-air-gap--security-verification)
7. [Troubleshooting & FAQ](#7-troubleshooting--faq)

---

## 1. Executive Summary & RAG Architecture

The **Sovereign RAG (Retrieval-Augmented Generation)** service allows industrial technicians and engineers to ingest proprietary Standard Operating Procedures (SOPs), manuals, inspection certificates, and technical reports into a high-speed local vector database, perform semantic search queries, and receive factually grounded answers with source citations.

### Complete Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Document Ingestion                            │
│  PDF / DOCX / TXT ──► OCR / Parser ──► Text Chunker (512 tokens / 50 ov)│
│                                              │                          │
│                                              ▼                          │
│                                      Local Embeddings                   │
│                                    (nomic-embed-text)                   │
│                                              │                          │
│                                              ▼                          │
│                                   Local Pure-Python Store               │
│                                 (workspace/chroma/rag.json)             │
└──────────────────────────────────────────────┬──────────────────────────┘
                                               │
┌──────────────────────────────────────────────▼──────────────────────────┐
│                            Retrieval & Q&A                              │
│  User Query ──► Local Embedding ──► Cosine Search (Threshold >= 0.25)   │
│                                              │                          │
│                                              ▼                          │
│                                  Top-K Context Chunks                   │
│                                              │                          │
│                                              ▼                          │
│                                 Local LLM (llama3.1:8b)                 │
│                                              │                          │
│                                              ▼                          │
│                          Grounded Answer + [Source N] Citations         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Core Components

| Component | Technology | Role |
|---|---|---|
| **Document Parser** | `pypdf2` + `python-docx` + `pytesseract` | Extracts text and metadata; OCRs scanned pages. |
| **Embeddings** | `nomic-embed-text` (via Ollama @ `:11434`) | Generates dense vector representations locally. |
| **Vector Store** | Pure Python Vector Engine (`rag/vector_store.py`) | Local JSON-backed vector storage with cosine similarity. |
| **Retriever** | `rag/retriever.py` | Performs top-K search and contextual grounding. |
| **LLM Inference** | `llama3.1:8b` / `qwen2.5-coder:3b` (Ollama) | Generates grounded responses with source citations. |
| **API Layer** | FastAPI (`main.py` @ `:8000`) | Exposes upload, ingestion, search, and Q&A endpoints. |
| **Web UI** | Next.js 16 (`frontend/` @ `:5000`) | Interactive dashboard with real-time SSE streaming. |

---

## 2. Prerequisites & Environment Setup

### Required Tools
1. **Python 3.11+** installed and added to `PATH`.
2. **Node.js 18+** & `npm` installed.
3. **Ollama** installed (from [ollama.com](https://ollama.com/)).
4. **Docker Desktop** (optional, required for isolated code sandbox execution).
5. **Tesseract OCR** (optional, required for scanned PDF OCR).

### Pull Required Open-Weight Models
Ensure Ollama is running (`ollama serve`), then pull the models:
```powershell
ollama pull nomic-embed-text
ollama pull llama3.1:8b
ollama pull qwen2.5-coder:3b
ollama pull llava-phi3:latest
```

---

## 3. How to Run the Entire System Properly

### Option 1: Master Automated Launch (Recommended)
From the root directory (`sih26117/`):
```powershell
.\run.ps1
```
This automatically starts:
- **FastAPI Backend**: `http://localhost:8000` (API Docs: `http://localhost:8000/docs`)
- **Next.js Frontend**: `http://localhost:5000`

---

### Option 2: Manual Two-Terminal Launch

**Terminal 1 — Backend (FastAPI)**
```powershell
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 — Frontend (Next.js)**
```powershell
cd frontend
npm run dev
```

---

### Option 3: Streamlit Interface (Legacy Option)
```powershell
streamlit run app.py
```

---

## 4. How to Verify & Check the RAG Service

### Method 1: Automated Standalone Test Script (Fastest)

We provide a dedicated verification script that tests the entire RAG lifecycle:
```powershell
python test_rag_service.py
```

#### What It Tests:
1. **Vector Store Operations**: Adds vector chunks, verifies cosine similarity, checks metadata storage and collection reset.
2. **Document Ingestion**: Parses `demo_data/maintenance_sop.pdf`, generates chunks and embeddings.
3. **Semantic Search Queries**: Executes industrial queries (e.g., vibration limits, bearing temperatures, seal replacement) and checks score rankings.
4. **Grounded Q&A**: Tests LLM completion with source attribution (`[Source N]`).
5. **Air-Gap & Security**: Verifies zero external API calls and active air-gap guard.
6. **Backend Connectivity**: Checks live status of FastAPI endpoints.

---

### Method 2: Pytest Unit Test Suite

Run the full automated test suite:
```powershell
pytest tests/
```
Or run only the RAG tests:
```powershell
pytest tests/test_rag.py -v
```

Expected output:
```text
tests/test_rag.py::test_cosine_similarity PASSED
tests/test_rag.py::test_chunk_text PASSED
tests/test_rag.py::test_doc_id_deterministic PASSED
tests/test_rag.py::test_vector_store_lifecycle PASSED
tests/test_rag.py::test_ingest_text_and_search_tool PASSED
==================== 16 passed in 1.47s ====================
```

---

### Method 3: Interactive Next.js Web UI

1. Open your browser and navigate to **`http://localhost:5000`**.
2. Click on the **Knowledge Base** tab on the left sidebar.
3. **Check Metrics Banner**: Verify `Total Documents`, `Indexed Vector Chunks`, `Embedding Model (nomic-embed-text)`, and `Air-Gap Status (🔒 100% Local)`.
4. **Upload a Document**: Click **Add Document** and select `demo_data/maintenance_sop.pdf`.
5. **Index Vectors**: Click **Index All Chunks** to embed all documents into the local vector store.
6. **Test Semantic Search**:
   - Select **Semantic Search** toggle.
   - Enter: `"What is the acceptable vibration limit?"`
   - Click **Search**.
   - Observe the matched chunk with **Relevance Score (e.g. 73.3%)**, **Source (maintenance_sop.pdf)**, and **Page Number (Page 1)**.
7. **Test Grounded Q&A (LLM)**:
   - Select **Grounded Q&A (LLM)** toggle.
   - Enter: `"What are the steps for mechanical seal replacement?"`
   - Click **Ask RAG**.
   - Observe the grounded answer citing `[Source 1: maintenance_sop.pdf - Page 2]`.

---

### Method 4: REST API Endpoints (cURL / Postman)

You can interact directly with the FastAPI backend using standard HTTP requests:

#### 1. Ingest All Documents in Knowledge Base
```bash
curl -X POST http://localhost:8000/api/knowledge/ingest
```
**Response:**
```json
{
  "status": "Ingestion started in background"
}
```

#### 2. Get Knowledge Base & Vector Store Stats
```bash
curl -X GET http://localhost:8000/api/knowledge
```
**Response:**
```json
{
  "documents": [
    {
      "name": "maintenance_sop.pdf",
      "size": 4195,
      "path": "knowledge_base\\maintenance_sop.pdf",
      "ext": "pdf"
    }
  ],
  "total_documents": 1,
  "vector_store": {
    "available": true,
    "collection": "sovereign_rag",
    "count": 2,
    "path": "workspace\\chroma\\sovereign_rag.json",
    "cloud": false
  }
}
```

#### 3. Semantic Search
```bash
curl -X POST http://localhost:8000/api/knowledge/search \
  -H "Content-Type: application/json" \
  -d '{"query": "acceptable vibration limit", "top_k": 3}'
```
**Response:**
```json
{
  "query": "acceptable vibration limit",
  "results": [
    {
      "id": "7b58c7041a87d0486c06a14761066d03",
      "text": "Section 3.2 - Vibration Limits\n- Acceptable: Below 4.5 mm/s RMS\n- Warning: 4.5 - 7.0 mm/s RMS (schedule maintenance)\n- Action required: Above 7.0 mm/s RMS (maintenance within 48 hours)",
      "metadata": {
        "source": "maintenance_sop.pdf",
        "page": "1",
        "chunk_idx": 0,
        "type": "pdf"
      },
      "score": 0.7333,
      "document": "maintenance_sop.pdf",
      "page": "1",
      "section": ""
    }
  ],
  "count": 1,
  "local": true
}
```

#### 4. Grounded Question Answering (RAG Q&A)
```bash
curl -X POST http://localhost:8000/api/knowledge/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the action threshold for bearing temperature?", "top_k": 3}'
```
**Response:**
```json
{
  "answer": "According to the procedure [Source 1], the action threshold for bearing temperature is above 85 degrees Celsius, which requires immediate inspection.",
  "sources": [
    {
      "index": 1,
      "document": "maintenance_sop.pdf",
      "page": "1",
      "score": 0.81,
      "text": "Section 3.1 - Temperature Limits\n- Normal: 55-75 C\n- Action threshold: Above 85 C"
    }
  ],
  "model": "llama3.1:8b",
  "rag_used": true
}
```

#### 5. Reset / Clear Vector Collection
```bash
curl -X POST http://localhost:8000/api/knowledge/reset
```

---

### Method 5: Legacy Streamlit UI

1. Run `streamlit run app.py`.
2. Go to the **Knowledge Base** tab.
3. Ingest documents via the file uploader.
4. Use the test search box on the right pane to execute queries.

---

## 5. Benchmark Query Matrix & Expected Grounded Outputs

Using `demo_data/maintenance_sop.pdf`:

| # | Test Query | Expected Chunk Extracted | Grounded LLM Response Highlights |
|---|---|---|---|
| **1** | *"What is the acceptable vibration limit?"* | `maintenance_sop.pdf` (Page 1): Section 3.2 | Acceptable is **below 4.5 mm/s RMS**; warning threshold is 4.5–7.0 mm/s RMS. Cites `[Source 1]`. |
| **2** | *"What are the temperature thresholds for bearing inspection?"* | `maintenance_sop.pdf` (Page 1): Section 3.1 | Normal: 55–75°C, Warning: 75–85°C, Action: >85°C, Critical shutdown: >95°C. Cites `[Source 1]`. |
| **3** | *"What are the steps for mechanical seal replacement?"* | `maintenance_sop.pdf` (Page 2): Section 4.2 | 12 steps including LOTO, casing drain, impeller removal (left-hand thread), gland plate extraction, flush seal for 5 minutes. Cites `[Source 1]`. |
| **4** | *"Who must approve unplanned emergency shutdowns?"* | `maintenance_sop.pdf` (Page 2): Section 5.1 | **Plant Manager** approval is required for unplanned emergency shutdowns. Cites `[Source 1]`. |

---

## 6. Air-Gap & Security Verification

The Sovereign AI Workbench includes an active **Network Guard** (`security/network_guard.py`) and **JSONL Audit Logger** (`security/audit.py`).

### Verification Commands

1. **Check Security Endpoint**:
   ```bash
   curl http://localhost:8000/api/security
   ```
   Verify that `external_llm_api: 0` and `all_local: true`.

2. **Inspect Audit Log**:
   Check `logs/audit.jsonl` to verify all logged actions:
   ```powershell
   Get-Content logs/audit.jsonl -Tail 15
   ```
   Every event (`EMBEDDING`, `RAG_SEARCH`, `LLM_CALL`, `INGEST_DONE`) is strictly logged locally with zero outbound network calls.

---

## 7. Troubleshooting & FAQ

### Q1: "Ollama request timed out or connection refused"
- **Solution**: Ensure the Ollama service is active. Run `ollama serve` in a dedicated PowerShell terminal.

### Q2: "No relevant chunks found during search"
- **Solution**: Click **Index All Chunks** (or call `/api/knowledge/ingest`) to ensure the documents in `knowledge_base/` are chunked and embedded into the local store.

### Q3: "Scanned PDF has empty text"
- **Solution**: Ensure Tesseract OCR (`tesseract.exe`) is installed and in your system `PATH`. The system automatically invokes `pytesseract` on scanned pages when OCR is active.

### Q4: "How does the system operate without an internet connection?"
- **Solution**: All embeddings (`nomic-embed-text`) and inference models (`llama3.1:8b`, `qwen2.5-coder:3b`, `llava-phi3:latest`) run locally via Ollama's REST API (`localhost:11434`). The vector store is pure Python stored on disk in `workspace/chroma/sovereign_rag.json`.

---

*Generated for SIH26117 Sovereign AI Workbench Team & Evaluators.*
