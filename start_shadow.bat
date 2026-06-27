@echo off
REM Spousteci skript pro Shadow Node - Windows verze
REM Stinovaci uzel pro high availability

echo ========================================
echo SHADOW NODE - STINOVACI UZEL
echo ========================================
echo.

REM Kontrola Python
echo [1/2] Kontrola Python dependencies...
where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   [OK] Python nalezen
    
    REM Install dependencies pokud chybi
    python -c "import prometheus_client" 2>nul
    if %ERRORLEVEL% NEQ 0 (
        echo   [INFO] Installing prometheus_client...
        pip install prometheus_client
    )
    
    python -c "import requests" 2>nul
    if %ERRORLEVEL% NEQ 0 (
        echo   [INFO] Installing requests...
        pip install requests
    )
    
    echo   [OK] Dependencies OK
) else (
    echo   [CHYBA] Python nenalezen!
    pause
    exit /b 1
)

REM Spusteni Shadow Node
echo [2/2] Spousteni Shadow Node...
echo.
echo Konfigurace:
echo   - Port: 9303
echo   - Primary URL: http://localhost:9302/metrics
echo   - Heartbeat: 5s
echo   - Failover timeout: 15s
echo.
echo Prometheus metrics: http://localhost:9303/metrics
echo.
echo ========================================
echo.

python src\shadow_node.py

echo.
echo Shadow Node ukoncen.
pause
