#!/bin/bash
# Start the dummy IoT sensor service

echo "Starting dummy IoT sensor service..."
echo "This will start:"
echo "  - 4 WebSocket servers (ports 9601-9604) for sensor feeds"
echo "  - 1 REST API (port 9500) for device metadata and control"
echo ""

cd dummy-service

# Check if docker-compose or docker compose is available
if command -v docker-compose &> /dev/null; then
    docker-compose -f docker-compose.multisource.yaml up
else
    docker compose -f docker-compose.multisource.yaml up
fi
