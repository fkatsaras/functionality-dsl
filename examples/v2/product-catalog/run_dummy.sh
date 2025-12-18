#!/bin/bash
# Start the dummy service
cd dummy-service

# Check if docker-compose or docker compose is available
if command -v docker-compose &> /dev/null; then
    docker-compose -f docker-compose.yml -p thesis up
else
    docker compose -f docker-compose.yml -p thesis up
fi
