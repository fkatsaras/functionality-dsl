#!/bin/bash
# Start dummy storage service using Docker

echo "Starting Dummy Storage Service..."
echo "  - Storage Service (port 9900)"
echo ""

cd dummy-service

# Check if docker-compose or docker compose is available
if command -v docker-compose &> /dev/null; then
    docker-compose up
else
    docker compose up
fi
