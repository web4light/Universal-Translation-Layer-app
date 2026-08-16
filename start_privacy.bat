@echo off
REM Privacy Protocol 4:23 starter (Windows)

echo ========================================
echo Privacy Protocol 4:23
echo ========================================
echo.

echo [PRIVACY] Installing dependencies...
pip install schedule prometheus_client

echo.
echo [PRIVACY] Starting privacy daemon...
echo [PRIVACY] Daily purge: 04:23 AM
echo [PRIVACY] Zero cookies: ENABLED
echo [PRIVACY] Port: 9305
echo.

python src\privacy_purge_423.py

pause
