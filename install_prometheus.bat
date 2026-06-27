@echo off
REM ============================================================================
REM Prometheus Installation - Windows
REM Standard 700: 12g stříbra = 1 mince
REM ============================================================================

echo.
echo ============================================================
echo 📊 Installing Prometheus for Windows
echo ============================================================
echo.

cd /d "%~dp0"

REM Prometheus version
set PROM_VERSION=2.47.0

echo [INFO] Downloading Prometheus %PROM_VERSION%...
echo.

REM Download Prometheus
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/prometheus/prometheus/releases/download/v%PROM_VERSION%/prometheus-%PROM_VERSION%.windows-amd64.zip' -OutFile 'prometheus.zip'"

if not exist "prometheus.zip" (
    echo [ERROR] Download failed!
    echo [INFO] Please download manually from:
    echo https://prometheus.io/download/
    pause
    exit /b 1
)

echo [INFO] Extracting Prometheus...
powershell -Command "Expand-Archive -Path prometheus.zip -DestinationPath . -Force"

REM Rename folder
if exist "prometheus-%PROM_VERSION%.windows-amd64" (
    if exist "prometheus-bin" rmdir /s /q prometheus-bin
    move "prometheus-%PROM_VERSION%.windows-amd64" prometheus-bin
)

REM Cleanup
del prometheus.zip

echo.
echo ============================================================
echo ✅ Prometheus installed successfully!
echo ============================================================
echo.
echo Location: prometheus-bin\
echo Config: prometheus\prometheus.yml
echo.
echo Start with: start_prometheus.bat
echo.

pause
