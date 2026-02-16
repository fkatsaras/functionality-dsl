#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
EXAMPLE_DIR="$PROJECT_ROOT/examples/ecommerce"
BYODB_DIR="$EXAMPLE_DIR/byodb_setup"
GENERATED_DIR="$PROJECT_ROOT/generated"

echo "Generating code..."
cd "$PROJECT_ROOT"
if [ -d "venv_WSL" ]; then
    source venv_WSL/bin/activate
elif [ -d "venv_WIN/Scripts" ]; then
    source venv_WIN/Scripts/activate
else
    source venv/bin/activate
fi
fdsl generate "$EXAMPLE_DIR/main.fdsl" --out generated

echo "Configuring environment..."
cd "$GENERATED_DIR"
cat > .env << 'EOF'
MY_ECOMM_DB_URL=postgresql://shop_admin:shop_secret@ecommerce-byodb-db:5432/ecommerce_shop
SHIPPING_API_KEY=test_shipping_key_123
EOF

echo "Starting application..."
docker compose -p thesis down -v 2>/dev/null || true
docker compose -p thesis up --build -d

echo "Starting external database..."
cd "$BYODB_DIR"
docker compose -f docker-compose.byodb-db.yml up -d

echo "Starting dummy service..."
cd "$EXAMPLE_DIR"
docker compose up -d

echo ""
echo "Services running:"
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8080/docs"
echo "  Dummy:    http://localhost:9001"
echo ""
echo "View logs:"
echo "  docker logs thesis-backend-1 -f"
echo "  docker logs thesis-frontend-1 -f"
