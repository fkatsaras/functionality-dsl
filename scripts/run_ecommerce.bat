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
(
echo MY_ECOMM_DB_URL=postgresql://shop_admin:shop_secret@ecommerce-byodb-db:5432/ecommerce_shop
echo SHIPPING_API_KEY=test_shipping_key_123
) > .env

echo Starting application...
docker compose -p thesis down -v 2>nul
docker compose -p thesis up --build -d

echo Starting external database...
cd /d "%BYODB_DIR%"
docker compose -f docker-compose.byodb-db.yml up -d

echo Starting dummy service...
cd /d "%EXAMPLE_DIR%"
docker compose up -d

echo.
echo Services running:
echo   Frontend: http://localhost:5173
echo   Backend:  http://localhost:8080/docs
echo   Dummy:    http://localhost:9001
echo.
echo View logs:
echo   docker logs thesis-backend-1 -f
echo   docker logs thesis-frontend-1 -f
