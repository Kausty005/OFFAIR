# SIH26117 — Sovereign AI Workbench

**“Private Data. Local Intelligence. Real Work.”**

First working prototype for Smart India Hackathon 2026. This project demonstrates an air-gapped, sovereign AI agent workbench using multiple open-weight models running entirely on local hardware.

## Key Features Implemented

1. **Local/Self-Hosted LLM Inference**: Powered by Ollama. No cloud APIs used.
2. **Multi-Model Routing**: Automatically routes tasks (General, Coding, Vision) to the appropriate local model.
3. **Agentic Execution**: Autonomous multi-step execution (Plan → Extract → Reason → Generate → Verify).
4. **Local Document Processing & OCR**: Parses digital PDFs and runs Tesseract OCR on scanned documents entirely locally.
5. **Multimodal Vision**: Uses local vision-language models (e.g., LLaVA) for image understanding.
6. **Local Knowledge Base (RAG)**: Ingests documents into a local ChromaDB instance with local embeddings.
7. **Secure Docker Sandbox**: Generated Python code is executed in an isolated, network-disabled Docker container.
8. **Real Word Generation**: Generates professional, structured `.docx` deliverables.
9. **Deterministic Calculations**: Complex math bypasses the LLM and uses accurate local Python tools.
10. **Audit Logs & Security Dashboard**: Verifiable proof of zero external calls and air-gapped operation.

## Architecture

- **UI**: Streamlit
- **Agent Orchestration**: Custom Python engine (No heavy frameworks for V1)
- **Inference Provider**: Ollama REST API
- **Vector DB**: ChromaDB
- **Embeddings**: Nomic-Embed-Text (via Ollama)
- **OCR**: Pytesseract (Tesseract)

## Hardware Constraints Addressed

Designed to run on an **NVIDIA RTX 4050 Laptop (6GB VRAM)**.
- Models are configured in `config/models.yaml`.
- Uses sequential loading: Ollama manages VRAM by only keeping the currently needed model in memory.
- Default models: `llama3.1:8b` (General), `qwen2.5-coder:3b` (Coding), `llava-phi3` (Vision).

---

## 🚀 Setup & Installation

### Prerequisites

1. **Python 3.11+**
2. **Ollama**: Must be installed and running (`ollama serve`). [Download Ollama](https://ollama.com/)
3. **Docker Desktop**: Must be running for the Coding Sandbox to work. [Download Docker](https://www.docker.com/)
4. **Tesseract OCR**: Required for scanned PDF support.
   - Windows: [Download Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) and ensure it's in your system `PATH`.

### Installation Steps

Run the setup script:

```powershell
.\setup.ps1
```

**What setup.ps1 does:**
- Installs Python dependencies from `requirements.txt`
- Pulls required models via Ollama
- Generates demo data in `demo_data/`
- Pulls the Docker image for the sandbox

### Running the Application

```powershell
.\run.ps1
```
(Or run manually: `streamlit run app.py`)

---

## 🎯 How to Run the Demos

### 1. System Health Check
- Go to the **System** tab. Ensure Ollama, Docker, OCR, and ChromaDB show as ✅ READY.

### 2. Knowledge Base (RAG) Demo
- Go to the **Knowledge Base** tab.
- Click **Ingest Document** and upload `demo_data/maintenance_sop.pdf`.
- Try searching for: *"What is the acceptable vibration limit?"*

### 3. Inspection Agent Demo (Primary Workflow)
- Go to the **Inspection Agent** tab.
- Upload `demo_data/inspection_report.pdf`.
- Click **RUN AGENT**.
- **What happens:** The system detects a scanned PDF → runs local OCR → extracts findings → searches the knowledge base for SOP context → generates a professional DOCX approval note.
- Download the generated `.docx` file.

### 4. Coding Agent Demo
- Go to the **Coding Agent** tab.
- Click **Generate & Run** with the default prompt.
- **What happens:** The coding model writes a Python script with unit tests → executes it in an isolated Docker container with network disabled → verifies the tests pass.

### 5. Multimodal Vision Demo
- Go to the **AI Workbench** tab.
- Upload `demo_data/inspection_image.jpg`.
- Prompt: *"Analyze this inspection photograph."*
- **What happens:** The Model Router detects image input and routes the task to the local Vision model.

### 6. Security Verification
- Go to the **Audit & Security** tab.
- Verify that **External API Calls = 0**.

---

## 🔒 Air-Gapped Mode Configuration

By default, the application is in air-gapped mode. You can configure this in `config/settings.yaml`:

```yaml
security:
  air_gapped_mode: true
  allowed_hosts:
    - "localhost"
    - "127.0.0.1"
```
When `air_gapped_mode` is true, the `security/network_guard.py` module will explicitly block any network requests to non-local IP addresses or known cloud API domains, raising an exception if one is attempted.

---

## Testing

Run unit tests with pytest:
```bash
pytest tests/
```
