#!/bin/bash
# Start e-commerce dummy services using Docker

echo "Starting DB Services with Docker..."
echo ""

cd dummy-service

# Check if docker-compose or docker compose is available
if command -v docker-compose &> /dev/null; then
    docker-compose -f docker-compose.yml up
else
    docker compose -f docker-compose.yml up
fi
