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
    $resp = Invoke-WebRequest -Uri "http://127.0.0.1:11434/" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    if ($resp.StatusCode -eq 200) {
        Write-Host "      [OK] Ollama is running" -ForegroundColor Green
        $ollamaUp = $true
    }
} catch {
    Write-Host "      [ERR] Ollama not running. Please start: ollama serve" -ForegroundColor Red
    Write-Host "      Models needed: ollama pull qwen2.5-coder:3b && ollama pull nomic-embed-text" -ForegroundColor Yellow
}

# Free ports 8000 and 5000 if currently occupied by stale processes
Get-NetTCPConnection -LocalPort 8000, 5000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "      [INFO] Freeing port $($_.LocalPort) from existing PID $($_.OwningProcess)..." -ForegroundColor Yellow
    Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Milliseconds 500

# Start FastAPI backend
Write-Host ""
Write-Host "[2/3] Starting FastAPI backend on :8000..." -ForegroundColor Yellow
$backend = Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload" `
    -WorkingDirectory $PSScriptRoot -PassThru -WindowStyle Normal
Write-Host "      [OK] Backend starting (PID $($backend.Id))" -ForegroundColor Green
Start-Sleep -Seconds 2

# Start Next.js frontend
Write-Host ""
Write-Host "[3/3] Starting Next.js frontend on :5000..." -ForegroundColor Yellow
$npmCmd = if ($env:OS -eq "Windows_NT") { "npm.cmd" } else { "npm" }
$frontend = Start-Process -FilePath $npmCmd -ArgumentList "run", "dev" `
    -WorkingDirectory (Join-Path $PSScriptRoot "frontend") -PassThru -WindowStyle Normal
if ($frontend) {
    Write-Host "      [OK] Frontend starting (PID $($frontend.Id))" -ForegroundColor Green
} else {
    Write-Host "      [ERR] Frontend failed to start" -ForegroundColor Red
}

# Detect local LAN IPv4 address (ignore WSL / virtual adapters)
$localIp = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { 
    $_.InterfaceAlias -notlike "*vEthernet*" -and 
    $_.InterfaceAlias -notlike "*Virtual*" -and 
    $_.InterfaceAlias -notlike "*WSL*" -and
    $_.IPAddress -notlike "127.*" -and 
    $_.IPAddress -notlike "169.254.*" 
} | Sort-Object { if ($_.InterfaceAlias -like "*Wi-Fi*") { 0 } else { 1 } } | Select-Object -First 1).IPAddress
if (!$localIp) { $localIp = "127.0.0.1" }

Write-Host ""
Write-Host "-----------------------------------------------------" -ForegroundColor Gray
Write-Host ""
Write-Host "  Local UI:        http://localhost:5000" -ForegroundColor Cyan
Write-Host "  Network UI:      http://$($localIp):5000" -ForegroundColor Cyan
Write-Host "  Network API:     http://$($localIp):8000" -ForegroundColor Blue
Write-Host "  API Docs:        http://$($localIp):8000/docs" -ForegroundColor Blue
Write-Host ""
Write-Host "  All inference:   LOCAL (Ollama @ localhost:11434)" -ForegroundColor Green
Write-Host "  External API calls: 0" -ForegroundColor Green
Write-Host ""
Write-Host "  Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ""

# Keep alive and monitor processes
try {
    while ((!$backend.HasExited) -or (!$frontend.HasExited)) {
        Start-Sleep -Seconds 1
    }
} finally {
    Write-Host "Shutting down..." -ForegroundColor Yellow
    if ($backend -and !$backend.HasExited) { Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue }
    if ($frontend -and !$frontend.HasExited) { Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue }
}
