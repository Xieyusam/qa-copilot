#!/usr/bin/env bash

# Dev startup script for Mac/Linux
# Usage:
#   ./dev.sh         - start both backend and frontend
#   ./dev.sh --reload - start both and enable backend auto-reload

RELOAD=0
if [ "$1" = "--reload" ]; then
    RELOAD=1
fi

ROOT_DIR=$(pwd)
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_PORT=8008
FRONTEND_PORT=5173

# 1. Kill existing ports
echo "==> Clearing occupied service ports..."
if lsof -Pi :$BACKEND_PORT -sTCP:LISTEN -t >/dev/null ; then
    echo "  Killing process on port $BACKEND_PORT"
    lsof -Pi :$BACKEND_PORT -sTCP:LISTEN -t | xargs kill -9
fi
if lsof -Pi :$FRONTEND_PORT -sTCP:LISTEN -t >/dev/null ; then
    echo "  Killing process on port $FRONTEND_PORT"
    lsof -Pi :$FRONTEND_PORT -sTCP:LISTEN -t | xargs kill -9
fi

sleep 1

# 2. Start Backend
echo "==> Starting backend (http://localhost:$BACKEND_PORT)"
cd "$BACKEND_DIR" || exit 1
VENV_PYTHON=".venv/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "  [ERROR] venv not found: $VENV_PYTHON"
    echo "  Run in backend/: python -m venv .venv; .venv/bin/pip install -r requirements.txt"
    exit 1
fi

BACKEND_CMD="$VENV_PYTHON -m uvicorn app.main:app --host 127.0.0.1 --port $BACKEND_PORT"
if [ $RELOAD -eq 1 ]; then
    BACKEND_CMD="$BACKEND_CMD --reload"
fi

# Run backend in background
eval "$BACKEND_CMD" &
BACKEND_PID=$!
echo "  backend started (PID: $BACKEND_PID)"

# 3. Start Frontend
echo "==> Starting frontend (http://localhost:$FRONTEND_PORT)"
cd "$FRONTEND_DIR" || exit 1

if [ ! -d "node_modules" ]; then
    echo "  [ERROR] node_modules not found"
    echo "  Run in frontend/: npm install"
    kill $BACKEND_PID
    exit 1
fi

npm run dev &
FRONTEND_PID=$!
echo "  frontend started (PID: $FRONTEND_PID)"

# 4. Handle exit
cleanup() {
    echo ""
    echo "==> Stopping services..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "  Services stopped."
    exit 0
}

trap cleanup SIGINT SIGTERM

echo ""
echo -e "\033[1;33mServices running:\033[0m"
echo "  Backend   -> http://localhost:$BACKEND_PORT"
echo "  API Docs  -> http://localhost:$BACKEND_PORT/docs"
echo "  Frontend  -> http://localhost:$FRONTEND_PORT"
echo -e "\033[1;36mPress Ctrl+C to stop all services.\033[0m"
echo ""

# Wait for background processes to keep script running
wait $BACKEND_PID $FRONTEND_PID
