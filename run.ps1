# run.ps1 - Start the full Sovereign AI Workbench
# Run from the sih26117/ directory

Write-Host ""
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "        SOVEREIGN AI WORKBENCH - SIH 26117           " -ForegroundColor Cyan
Write-Host "     On-Premise - Air-Gap Ready - Open-Weight LLMs   " -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host ""

# Check Ollama
Write-Host "[1/3] Checking Ollama..." -ForegroundColor Yellow
$ollamaUp = $false
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:11434/" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    if ($resp.StatusCode -eq 200) {
        Write-Host "      [OK] Ollama is running" -ForegroundColor Green
        $ollamaUp = $true
    }
} catch {
    Write-Host "      [ERR] Ollama not running. Please start: ollama serve" -ForegroundColor Red
    Write-Host "      Models needed: ollama pull qwen2.5-coder:3b && ollama pull nomic-embed-text" -ForegroundColor Yellow
}

# Start FastAPI backend
Write-Host ""
Write-Host "[2/3] Starting FastAPI backend on :8000..." -ForegroundColor Yellow
$backend = Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000" `
    -WorkingDirectory $PSScriptRoot -PassThru -NoNewWindow
Write-Host "      [OK] Backend starting (PID $($backend.Id))" -ForegroundColor Green
Start-Sleep -Seconds 2

# Start Next.js frontend
Write-Host ""
Write-Host "[3/3] Starting Next.js frontend on :5000..." -ForegroundColor Yellow
$npmCmd = if ($env:OS -eq "Windows_NT") { "npm.cmd" } else { "npm" }
$frontend = Start-Process -FilePath $npmCmd -ArgumentList "run", "dev" `
    -WorkingDirectory (Join-Path $PSScriptRoot "frontend") -PassThru -NoNewWindow
if ($frontend) {
    Write-Host "      [OK] Frontend starting (PID $($frontend.Id))" -ForegroundColor Green
} else {
    Write-Host "      [ERR] Frontend failed to start" -ForegroundColor Red
}

Write-Host ""
Write-Host "-----------------------------------------------------" -ForegroundColor Gray
Write-Host ""
Write-Host "  UI:      http://localhost:5000" -ForegroundColor Cyan
Write-Host "  API:     http://localhost:8000" -ForegroundColor Blue
Write-Host "  Docs:    http://localhost:8000/docs" -ForegroundColor Blue
Write-Host ""
Write-Host "  All inference: LOCAL (Ollama @ localhost:11434)" -ForegroundColor Green
Write-Host "  External API calls: 0" -ForegroundColor Green
Write-Host ""
Write-Host "  Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ""

# Wait
try {
    Wait-Process -Id $backend.Id
} catch {
    Write-Host "Shutting down..." -ForegroundColor Yellow
    if (!$backend.HasExited) { 
        Start-Process "taskkill" -ArgumentList "/F /PID $($backend.Id) /T" -NoNewWindow -Wait
    }
    if (!$frontend.HasExited) { 
        Start-Process "taskkill" -ArgumentList "/F /PID $($frontend.Id) /T" -NoNewWindow -Wait
    }
}
