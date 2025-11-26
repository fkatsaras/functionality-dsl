#!/bin/bash
# Start dummy text service using Docker

echo "Starting Dummy Text Service..."
echo "  - Text Service (port 9800)"
echo ""

cd dummy-service

# Check if docker-compose or docker compose is available
if command -v docker-compose &> /dev/null; then
    docker-compose up
else
    docker compose up
fi
