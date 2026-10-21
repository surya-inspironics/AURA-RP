@echo off
setlocal

:: Always run from the directory this bat file lives in
cd /d "%~dp0"

echo.
echo  AURA Gold Loan Platform - Dev Startup
echo  ======================================
echo.

:: Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 3.11+ is required. Install from https://python.org
    pause
    exit /b 1
)

:: Check pnpm
where pnpm >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] pnpm not found. Installing via npm...
    npm install -g pnpm
)

:: Create venv if it doesn't exist
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Creating Python virtual environment...
    python -m venv .venv
)

:: Install backend deps using the project venv's pip directly
echo [INFO] Checking Python dependencies...
.venv\Scripts\pip.exe install -q -r backend\requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install Python dependencies.
    pause
    exit /b 1
)

:: Install frontend deps if needed
if not exist "node_modules" (
    echo [INFO] Installing frontend dependencies...
    pnpm install
)

:: Start backend in a new window using the project venv's python directly
echo.
echo [INFO] Starting FastAPI backend on http://localhost:8000 ...
start "AURA Backend" cmd /k ".venv\Scripts\python.exe backend\run.py"

:: Wait for backend to be ready
timeout /t 4 /nobreak >nul

:: Start frontend in the current window
echo [INFO] Starting Next.js frontend on http://localhost:3000 ...
echo.
echo  --------------------------------------------------
echo  Frontend : http://localhost:3000
echo  API Docs : http://localhost:8000/api/v1/docs
echo  Gold Rates: http://localhost:8000/api/v1/gold-loan/rates/live
echo  --------------------------------------------------
echo.
pnpm dev
