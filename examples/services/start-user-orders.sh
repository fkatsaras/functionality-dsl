#!/bin/bash
# Start user and order services for demo_user_orders.fdsl

echo "Starting User & Order Services..."
docker compose -f docker-compose.user-orders.yml up -d

echo ""
echo "Waiting for services to be ready..."
sleep 3

echo ""
echo "Testing User Service..."
curl -s http://localhost:8001/users/user-001 | head -n 5

echo ""
echo ""
echo "Testing Order Service..."
curl -s "http://localhost:8002/orders?user_id=user-001&status=pending" | head -n 10

echo ""
echo ""
echo "✅ Services are running!"
echo "  - User Service:  http://localhost:8001"
echo "  - Order Service: http://localhost:8002"
echo ""
echo "To view logs: docker compose -f docker-compose.user-orders.yml logs -f"
echo "To stop: docker compose -f docker-compose.user-orders.yml down"
