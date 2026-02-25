@echo off
setlocal

set PROJECT_ROOT=c:\ffile\functionality-dsl
set EXAMPLE_DIR=%PROJECT_ROOT%\examples\ecommerce
set BYODB_DIR=%EXAMPLE_DIR%\byodb_setup
set GENERATED_DIR=%PROJECT_ROOT%\generated

echo Generating code...
cd /d "%PROJECT_ROOT%"
call venv_WIN\Scripts\activate
fdsl generate "%EXAMPLE_DIR%\main.fdsl" --out generated

echo Configuring environment...
cd /d "%GENERATED_DIR%"
REM Update specific env vars while preserving the rest
powershell -Command "(Get-Content .env) -replace '^MY_ECOMM_DB_URL=.*', 'MY_ECOMM_DB_URL=postgresql://shop_admin:shop_secret@ecommerce-byodb-db:5432/ecommerce_shop' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace '^SHIPPING_API_KEY=.*', 'SHIPPING_API_KEY=test_shipping_key_123' | Set-Content .env"

echo Cleaning up old containers...
cd /d "%GENERATED_DIR%"
docker compose -p thesis down -v 2>nul

cd /d "%BYODB_DIR%"
docker compose -f docker-compose.byodb-db.yml down -v 2>nul

cd /d "%EXAMPLE_DIR%"
docker compose down -v 2>nul

REM Remove dangling networks
docker network rm thesis_fdsl_net 2>nul

echo Starting application (creates network)...
cd /d "%GENERATED_DIR%"
docker compose -p thesis up --build -d

echo Waiting for network to be ready...
timeout /t 2 /nobreak >nul

echo Starting external database...
cd /d "%BYODB_DIR%"
docker compose -f docker-compose.byodb-db.yml up -d --force-recreate

echo Waiting for database to be ready...
:wait_db
docker exec ecommerce-byodb-db pg_isready -U shop_admin -d ecommerce_shop >nul 2>&1
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto wait_db
)
echo Database is ready!

echo Restarting backend to connect to database...
cd /d "%GENERATED_DIR%"
docker compose -p thesis restart backend

echo Starting dummy service...
cd /d "%EXAMPLE_DIR%"
docker compose up -d --force-recreate

echo.
echo Services running:
echo   Frontend: http://localhost:5173
echo   Backend:  http://localhost:8080/docs
echo   Dummy:    http://localhost:9001
echo.
echo View logs:
echo   docker logs thesis-backend-1 -f
echo   docker logs thesis-frontend-1 -f
