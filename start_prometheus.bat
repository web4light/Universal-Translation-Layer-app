@echo off
REM ============================================================================
REM Start Prometheus - Windows
REM Standard 700: 12g stříbra = 1 mince
REM ============================================================================

echo.
echo ============================================================
echo 📊 Starting Prometheus
echo ============================================================
echo.

cd /d "%~dp0"

if not exist "prometheus-bin\prometheus.exe" (
    echo [ERROR] Prometheus not installed!
    echo [INFO] Run: install_prometheus.bat
    pause
    exit /b 1
)

echo [PROMETHEUS] Config: prometheus\prometheus.yml
echo [PROMETHEUS] Web UI: http://localhost:9090
echo [PROMETHEUS] Scraping:
echo   - Primary Node: localhost:9302
echo   - Shadow Node: localhost:9303
echo.

prometheus-bin\prometheus.exe --config.file=prometheus\prometheus.yml

pause
