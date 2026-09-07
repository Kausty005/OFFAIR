@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo   OFFAIR AI ENTERPRISE CLIENT LAUNCHER
echo ========================================================
echo.

if not exist ".env.server" (
    echo [ERROR] .env.server not found! Please run start_server.bat first.
    pause
    exit /b 1
)

:: Read SERVER_IP from .env.server
for /f "tokens=1,2 delims==" %%A in (.env.server) do (
    if "%%A"=="SERVER_IP" set SERVER_IP=%%B
)

echo [INFO] Detected Server IP from config: !SERVER_IP!
echo [INFO] API URL will be: http://!SERVER_IP!:8000
echo.

:: We need to pass the API URL to Next.js via .env.local in the frontend directory
echo NEXT_PUBLIC_API_URL=http://!SERVER_IP!:8000> frontend\.env.local

echo [STARTING] Next.js Frontend...
echo Connect your browser to: http://localhost:5000 (Local) or http://!SERVER_IP!:5000 (LAN)
echo.

cd frontend
call npm run dev
