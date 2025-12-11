#!/bin/bash

echo "=========================================="
echo "Starting Delivery Tracking Dummy Service"
echo "=========================================="
echo ""
echo "This service simulates a delivery database on port 9700"
echo ""

cd dummy-service

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running"
    echo "Please start Docker and try again"
    exit 1
fi

# Build and start the dummy service
echo "Building and starting dummy delivery database..."
docker compose up --build

echo ""
echo "Dummy service stopped"
