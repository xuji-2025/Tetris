#!/usr/bin/env bash
set -e

echo "🎮 Starting TetrisCore development environment..."

# Start Python backend
echo "Starting Python WebSocket server..."
cd engine/python
uv run uvicorn api.server:app --reload --port 8000 &
BACKEND_PID=$!

# Start web frontend
echo "Starting web frontend..."
cd ../../apps/web
pnpm dev &
FRONTEND_PID=$!

# Cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT

echo "✅ Backend running on http://localhost:8000"
echo "✅ Frontend running on http://localhost:3000"
echo "Press Ctrl+C to stop all services"

wait
