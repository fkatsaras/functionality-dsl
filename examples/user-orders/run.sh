#!/bin/bash
# Start both dummy microservices for user-orders demo

echo "Starting dummy microservices..."
echo "  - User Service (port 8001)"
echo "  - Order Service (port 8002)"
echo ""

cd dummy-services

# Start user service in background
echo "Starting User Service..."
cd user-service
npm install > /dev/null 2>&1
node server.js &
USER_PID=$!
cd ..

# Start order service in background
echo "Starting Order Service..."
cd order-service
npm install > /dev/null 2>&1
node server.js &
ORDER_PID=$!
cd ..

echo ""
echo "Both services started!"
echo "  User Service PID: $USER_PID"
echo "  Order Service PID: $ORDER_PID"
echo ""
echo "Press Ctrl+C to stop both services"

# Trap Ctrl+C to cleanup
trap "echo 'Stopping services...'; kill $USER_PID $ORDER_PID 2>/dev/null; exit" INT

# Wait for both processes
wait
