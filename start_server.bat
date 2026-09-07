@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo   OFFAIR AI ENTERPRISE SERVER LAUNCHER
echo ========================================================
echo.

:: Get local IP address (IPv4)
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address"') do (
    set SERVER_IP=%%a
    set SERVER_IP=!SERVER_IP: =!
    goto :found_ip
)
:found_ip
if "%SERVER_IP%"=="" (
    set SERVER_IP=127.0.0.1
    echo [WARNING] Could not detect LAN IP, falling back to 127.0.0.1
) else (
    echo [INFO] Detected Server IP: !SERVER_IP!
)

:: Write IP to .env.server
echo SERVER_IP=!SERVER_IP!> .env.server
echo FASTAPI_PORT=8000>> .env.server
echo OLLAMA_HOST=http://localhost:11434>> .env.server
echo QDRANT_HOST=localhost>> .env.server
echo QDRANT_PORT=6333>> .env.server
echo NEXT_PUBLIC_API_URL=http://!SERVER_IP!:8000>> .env.server

echo [INFO] Updated .env.server configuration.
echo.
echo [STARTING] FastAPI Server on port 8000...
echo.

:: Start FastAPI using uvicorn via python
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
