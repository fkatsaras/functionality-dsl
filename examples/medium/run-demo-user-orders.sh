#!/bin/bash
# Complete setup and run script for demo_user_orders.fdsl

set -e

echo "╔═══════════════════════════════════════════════════╗"
echo "║   User Orders API Demo - Complete Setup          ║"
echo "╚═══════════════════════════════════════════════════╝"
echo ""

# Step 1: Start services
echo "* Step 1: Starting microservices..."
cd ../services
if ! docker compose -f docker-compose.user-orders.yml up -d; then
    echo "! Failed to start services"
    exit 1
fi
cd ../medium

echo "   Waiting for services to be ready..."
sleep 3
echo "[OK] Services started"
echo ""

# Step 2: Validate FDSL
echo "* Step 2: Validating FDSL specification..."
if ! fdsl validate demo_user_orders.fdsl; then
    echo "! Validation failed"
    docker compose -f ../services/docker-compose.user-orders.yml down
    exit 1
fi
echo "[OK] Validation passed"
echo ""

# Step 3: Generate code
echo "*  Step 3: Generating API code..."
OUTPUT_DIR="../../generated/user-orders-demo"
if ! fdsl generate demo_user_orders.fdsl --out "$OUTPUT_DIR"; then
    echo "! Code generation failed"
    docker compose -f ../services/docker-compose.user-orders.yml down
    exit 1
fi
echo "[OK] Code generated to: $OUTPUT_DIR"
echo ""

# Step 4: Start generated API
echo "* Step 4: Starting generated API..."
cd "$OUTPUT_DIR"

echo "   Installing dependencies..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt

echo "   Starting FastAPI server on port 8000..."
echo ""
echo "╔═══════════════════════════════════════════════════╗"
echo "║   API is starting...                              ║"
echo "║   Press Ctrl+C to stop                            ║"
echo "╚═══════════════════════════════════════════════════╝"
echo ""
echo "* Endpoints:"
echo "   - API:            http://localhost:8000"
echo "   - API Docs:       http://localhost:8000/docs"
echo "   - User Service:   http://localhost:8001"
echo "   - Order Service:  http://localhost:8002"
echo ""
echo "* Test with:"
echo '   curl "http://localhost:8000/api/users/user-001/orders?status=pending"'
echo ""
echo "─────────────────────────────────────────────────────"
echo ""

uvicorn main:app --reload --port 8000
