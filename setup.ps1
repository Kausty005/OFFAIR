# setup.ps1
# SIH26117 Setup Script

Write-Host "====================================="
Write-Host "SIH26117 Sovereign AI Workbench Setup"
Write-Host "====================================="

Write-Host "1. Installing Python dependencies..."
pip install -r requirements.txt

Write-Host "2. Checking Ollama..."
$ollama_running = Test-Connection -ComputerName localhost -Port 11434 -Count 1 -ErrorAction SilentlyContinue
if ($ollama_running) {
    Write-Host "   ✅ Ollama is running."
} else {
    Write-Host "   ⚠️ Ollama is not running on port 11434. Please start it using 'ollama serve'."
}

Write-Host "3. Pulling required models (this may take time depending on internet speed)..."
Write-Host "   Pulling nomic-embed-text..."
ollama pull nomic-embed-text:latest
Write-Host "   Pulling qwen2.5-coder:3b..."
ollama pull qwen2.5-coder:3b
Write-Host "   Pulling llava-phi3:latest..."
ollama pull llava-phi3:latest
Write-Host "   (Assuming llama3.1:8b is already installed per plan)"

Write-Host "4. Generating Demo Data..."
python demo_data/generate_demo.py

Write-Host "5. Checking Docker..."
docker info > $null 2>&1
if ($?) {
    Write-Host "   ✅ Docker is running."
    Write-Host "   Pulling python:3.11-slim image for sandbox..."
    docker pull python:3.11-slim
} else {
    Write-Host "   ⚠️ Docker is not running. Coding Agent Sandbox will not work until Docker Desktop is started."
}

Write-Host "====================================="
Write-Host "Setup Complete!"
Write-Host "Run '.\run.ps1' to start the application."
Write-Host "====================================="
