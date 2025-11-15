#!/bin/bash
# Start the dummy user database service

echo "Starting dummy user database service..."

cd dummy-service

# Check if docker-compose or docker compose is available
if command -v docker-compose &> /dev/null; then
    docker-compose -f docker-compose.dummy.yml up
else
    docker compose -f docker-compose.dummy.yml up
fi
