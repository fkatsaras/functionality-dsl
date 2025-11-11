@echo off
REM Start user and order services for demo_user_orders.fdsl

echo Starting User ^& Order Services...
docker compose -f docker-compose.user-orders.yml up -d

echo.
echo Waiting for services to be ready...
timeout /t 3 /nobreak > nul

echo.
echo Testing User Service...
curl -s http://localhost:8001/users/user-001

echo.
echo.
echo Testing Order Service...
curl -s "http://localhost:8002/orders?user_id=user-001&status=pending"

echo.
echo.
echo ✅ Services are running!
echo   - User Service:  http://localhost:8001
echo   - Order Service: http://localhost:8002
echo.
echo To view logs: docker compose -f docker-compose.user-orders.yml logs -f
echo To stop: docker compose -f docker-compose.user-orders.yml down
