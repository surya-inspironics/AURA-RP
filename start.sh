#!/usr/bin/env bash
set -e

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║          AURA Gold Loan Platform - Dev Startup           ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] Python 3.11+ is required."
    exit 1
fi

# Check / install pnpm
if ! command -v pnpm &>/dev/null; then
    echo "[INFO] pnpm not found. Installing..."
    npm install -g pnpm
fi

# Create venv if needed
if [ ! -d ".venv" ]; then
    echo "[INFO] Creating Python virtual environment..."
    python3 -m venv .venv
fi
source .venv/bin/activate

echo "[INFO] Installing Python dependencies..."
pip install -q -r backend/requirements.txt

# Install frontend deps if needed
if [ ! -d "node_modules" ]; then
    echo "[INFO] Installing frontend dependencies..."
    pnpm install
fi

# Start backend in background
echo ""
echo "[INFO] Starting FastAPI backend on http://localhost:8000 ..."
python backend/run.py &
BACKEND_PID=$!
echo "[INFO] Backend PID: $BACKEND_PID"

# Wait for backend
sleep 3

# Start frontend
echo "[INFO] Starting Next.js frontend on http://localhost:3000 ..."
echo ""
echo "  Open your browser at: http://localhost:3000"
echo "  API Docs (Swagger):   http://localhost:8000/api/v1/docs"
echo "  Live Gold Rates:      http://localhost:8000/api/v1/gold-loan/rates/live"
echo ""

trap "kill $BACKEND_PID 2>/dev/null" EXIT
pnpm dev
