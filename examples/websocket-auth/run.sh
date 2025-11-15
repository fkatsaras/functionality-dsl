#!/bin/bash
# Start the dummy authenticated WebSocket echo service

echo "Starting authenticated WebSocket echo service on port 8765..."
echo "This service requires bearer token authentication."
echo ""

# Since websocket-auth shares the same dummy service structure as websocket-chat
# we just need to point to the ws_auth_echo.py file

# Check if Python 3 is available
if command -v python3 &> /dev/null; then
    # Check if we have the service locally, otherwise copy from websocket-chat
    if [ ! -f "dummy-service/ws_auth_echo.py" ]; then
        echo "Copying dummy service from websocket-chat..."
        mkdir -p dummy-service
        cp ../websocket-chat/dummy-service/ws_auth_echo.py dummy-service/
    fi

    # Install websockets if not already installed
    pip3 install websockets 2>/dev/null || true

    cd dummy-service
    echo "WebSocket echo server running on ws://localhost:8765"
    echo "Authentication: Bearer token 'secret123'"
    python3 ws_auth_echo.py
else
    echo "Error: Python 3 is required but not found."
    exit 1
fi
