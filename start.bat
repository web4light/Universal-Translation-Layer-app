@echo off
REM Spousteci skript pro Vakuovou Mincovnu - Windows verze
REM Prvni autonomni clanek projektu

echo === VAKUOVA MINCOVNA - INICIALIZACE ===
echo.

REM Kontrola GNAT/SPARK
echo [1/4] Kontrola GNAT/SPARK...
where gprbuild >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   [OK] GNAT/SPARK nalezen
) else (
    echo   [CHYBA] GNAT/SPARK nenalezen!
    echo   Nainstaluj: https://www.adacore.com/community
    echo   Nebo pouzij AdaDev2024.zip
    pause
    exit /b 1
)

REM Build Ada/SPARK Core
echo [2/4] Build Ada/SPARK Core...
gprbuild -P mincovna.gpr
if %ERRORLEVEL% EQU 0 (
    echo   [OK] Build uspesny
) else (
    echo   [CHYBA] Build selhal!
    pause
    exit /b 1
)

REM Kontrola Python
echo [3/4] Kontrola Python dependencies...
where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   [OK] Python nalezen
    
    REM Install prometheus_client pokud chybi
    python -c "import prometheus_client" 2>nul
    if %ERRORLEVEL% NEQ 0 (
        echo   [INFO] Installing prometheus_client...
        pip install prometheus_client
    )
    echo   [OK] Dependencies OK
) else (
    echo   [CHYBA] Python nenalezen!
    pause
    exit /b 1
)

REM Spusteni Faucet Bridge
echo [4/4] Spousteni Faucet Bridge...
echo.
python src\faucet_bridge.py
