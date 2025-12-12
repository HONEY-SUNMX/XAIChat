#!/bin/bash
# Qwen Chat Web Application Startup Script
# Author: Generated with love by Harei-chan

echo "=========================================="
echo "  🤖 Qwen Chat Web Application"
echo "=========================================="
echo ""

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Create necessary directories
mkdir -p uploads outputs

# Function to start backend
start_backend() {
    echo "Starting FastAPI backend on port 8000..."
    uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload &
    BACKEND_PID=$!
    echo "Backend PID: $BACKEND_PID"
}

# Function to start frontend
start_frontend() {
    echo "Starting React frontend on port 5173..."
    cd web
    npm run dev &
    FRONTEND_PID=$!
    cd ..
    echo "Frontend PID: $FRONTEND_PID"
}

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down..."
    [ ! -z "$BACKEND_PID" ] && kill $BACKEND_PID 2>/dev/null
    [ ! -z "$FRONTEND_PID" ] && kill $FRONTEND_PID 2>/dev/null
    exit 0
}

# Trap SIGINT (Ctrl+C)
trap cleanup SIGINT

# Parse arguments
case "$1" in
    "backend")
        echo "Starting backend only..."
        uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
        ;;
    "frontend")
        echo "Starting frontend only..."
        cd web && npm run dev
        ;;
    "install")
        echo "Installing dependencies..."
        pip install -r requirements.txt
        cd web && npm install && cd ..
        echo "Done!"
        ;;
    *)
        # Start both
        start_backend
        sleep 2
        start_frontend

        echo ""
        echo "=========================================="
        echo "  Services started!"
        echo "  Backend:  http://localhost:8000"
        echo "  Frontend: http://localhost:5173"
        echo "  API Docs: http://localhost:8000/docs"
        echo "=========================================="
        echo ""
        echo "Press Ctrl+C to stop all services..."

        # Wait for both processes
        wait
        ;;
esac
