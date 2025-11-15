#!/bin/bash
# Start the dummy WebSocket echo service

echo "Starting dummy WebSocket echo service on port 8765..."

cd dummy-service

# Check if Python 3 is available
if command -v python3 &> /dev/null; then
    # Install websockets if not already installed
    pip3 install websockets 2>/dev/null || true

    echo "WebSocket echo server running on ws://localhost:8765"
    echo "It will echo back any message you send (with auth support)."
    python3 ws_auth_echo.py
else
    echo "Error: Python 3 is required but not found."
    exit 1
fi
