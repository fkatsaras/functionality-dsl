#!/bin/bash
# Start e-commerce dummy services using Docker

echo "Starting E-Commerce Services with Docker..."
echo "  - Product Service (port 9001)"
echo "  - Cart Service REST (port 9002)"
echo "  - Cart Service WebSocket (port 9003)"
echo ""

cd dummy-services

# Check if docker-compose or docker compose is available
if command -v docker-compose &> /dev/null; then
    docker-compose -f docker-compose.dummy.yml up
else
    docker compose -f docker-compose.dummy.yml up
fi
