#!/bin/bash
echo "Starting dummy pdf database service..."

cd dummy-service

# Check if docker-compose or docker compose is available
if command -v docker-compose &> /dev/null; then
    docker-compose -f docker-compose.yml up
else
    docker compose -f docker-compose.yml up
fi

