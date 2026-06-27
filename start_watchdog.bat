@echo off
REM Apache Spark Watchdog starter (Windows)
REM Mossad ALF++ Protocol

echo ========================================
echo Apache Spark Watchdog - Mossad ALF++
echo ========================================
echo.

echo [WATCHDOG] Installing dependencies...
pip install psutil prometheus_client

echo.
echo [WATCHDOG] Starting watchdog daemon...
echo [WATCHDOG] Port: 9304
echo [WATCHDOG] Scan interval: 1 hour
echo.

python src\spark_watchdog.py

pause
