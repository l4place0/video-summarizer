#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# --- Prerequisites ---
check_cmd() {
    if ! command -v "$1" &>/dev/null; then
        echo "Error: $1 is required but not found"
        exit 1
    fi
}

check_cmd python3
check_cmd ffmpeg

# --- uv ---
if ! command -v uv &>/dev/null; then
    echo "Installing uv..."
    pip install uv 2>/dev/null || pip3 install uv 2>/dev/null
fi

# --- .env ---
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "No .env found, copying from .env.example"
        cp .env.example .env
        echo ">>> Edit .env with your API keys before first use <<<"
    fi
fi

# --- Dependencies ---
echo "Syncing dependencies..."
uv sync --quiet

# --- Start ---
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

# Kill existing process on port if present
PID=$(lsof -ti :"$PORT" 2>/dev/null || true)
if [ -n "$PID" ]; then
    echo "Port $PORT in use (PID $PID), stopping..."
    kill "$PID" 2>/dev/null || true
    sleep 1
fi

echo ""
echo "=== Video Summarizer Dev Server ==="
echo "http://${HOST}:${PORT}"
echo "http://localhost:${PORT}/health"
echo ""

exec uv run uvicorn core.main:app --host "$HOST" --port "$PORT" --reload
