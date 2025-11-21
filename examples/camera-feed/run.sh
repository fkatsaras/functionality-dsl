#!/bin/bash
# Start the dummy camera feed service

echo "Starting dummy camera feed service..."
echo "This will start:"
echo "  - 1 WebSocket server (port 9700) streaming image frames at 10 fps"
echo "  - Loops through 200 PNG frames from vidf1_33_000.y directory"
echo ""

cd dummy-service

# Check if docker-compose or docker compose is available
if command -v docker-compose &> /dev/null; then
    docker-compose -f docker-compose.dummycamera.yaml -p thesis up
else
    docker compose -f docker-compose.dummycamera.yaml -p thesis up
fi
