#!/bin/bash
# Start the dummy WebSocket echo service using Docker

set -e

echo "==================================================================="
echo "  WebSocket Chat Example - Starting Services"
echo "==================================================================="

# Start dummy echo service
echo ""
echo "[1/2] Starting dummy WebSocket echo service..."
cd dummy-service
docker compose up
cd ..

echo ""
echo "✓ Dummy echo service started on ws://localhost:8765"
echo ""
echo "[2/2] Starting generated application..."
echo ""
echo "Run the following command in the generated directory:"
echo "  cd ../../../generated && docker compose -p thesis up"
echo ""
echo "==================================================================="
echo "  Services Ready"
echo "==================================================================="
echo ""
echo "Dummy Echo Service:  ws://localhost:8765"
echo "Generated Backend:   http://localhost:8080"
echo "Generated Frontend:  http://localhost:3000"
echo ""
echo "To stop the dummy service:"
echo "  cd dummy-service && docker compose down"
echo ""
