@echo off
REM Vytvoření deployment balíčku pro Ubuntu

echo === VYTVARENI DEPLOYMENT BALICKU ===
echo.

set PACKAGE_NAME=vakuova-mincovna-v1.0.zip

echo [1/2] Kontrola 7-Zip...
where 7z >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   [INFO] 7-Zip nenalezen, pouzivam PowerShell Compress-Archive
    echo.
    echo [2/2] Vytvareni archivu...
    powershell -Command "Compress-Archive -Path src,prometheus,mincovna.gpr,start.sh,*.md -DestinationPath %PACKAGE_NAME% -Force"
) else (
    echo   [OK] 7-Zip nalezen
    echo.
    echo [2/2] Vytvareni archivu...
    7z a %PACKAGE_NAME% src prometheus mincovna.gpr start.sh *.md
)

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [OK] HOTOVO!
    echo.
    echo Soubor: %PACKAGE_NAME%
    echo.
    echo Pro deployment na Ubuntu:
    echo   1. Zkopiruj %PACKAGE_NAME% na Ubuntu system
    echo   2. Rozbal: unzip %PACKAGE_NAME%
    echo   3. Nasleduj instrukce v DEPLOY_UBUNTU.md
) else (
    echo.
    echo [CHYBA] Vytvoreni archivu selhalo
    exit /b 1
)
