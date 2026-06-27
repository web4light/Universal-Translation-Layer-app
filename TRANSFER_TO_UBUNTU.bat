@echo off
REM ============================================================================
REM Transfer Vakuová Mincovna na Ubuntu
REM 
REM Tento script vytvoří archiv pro přenos na Ubuntu
REM Standard 700: 12g stříbra = 1 mince
REM ============================================================================

echo.
echo ============================================================
echo 📦 TRANSFER TO UBUNTU - Creating Archive
echo ============================================================
echo.

cd /d "%~dp0"

REM Vytvoř archiv (vyžaduje 7-Zip nebo WinRAR)
echo [INFO] Creating archive vakuova-mincovna.zip...
echo.

REM Pokus 1: PowerShell (vestavěný Windows)
powershell -Command "Compress-Archive -Path . -DestinationPath ..\vakuova-mincovna-ubuntu.zip -Force"

if exist "..\vakuova-mincovna-ubuntu.zip" (
    echo.
    echo ============================================================
    echo ✅ Archive created successfully!
    echo ============================================================
    echo.
    echo Location: C:\Users\pan_jeskyne\Favorites\vakuova-mincovna-ubuntu.zip
    echo Size: 
    dir /s "..\vakuova-mincovna-ubuntu.zip" | find "vakuova-mincovna-ubuntu.zip"
    echo.
    echo ============================================================
    echo 📋 NEXT STEPS - Na Ubuntu:
    echo ============================================================
    echo.
    echo 1. Přenes archiv na Ubuntu pomocí:
    echo    • USB flash disk
    echo    • SCP: scp vakuova-mincovna-ubuntu.zip pan@stars:~/
    echo    • Shared network folder
    echo.
    echo 2. Na Ubuntu rozbal:
    echo    cd ~
    echo    unzip vakuova-mincovna-ubuntu.zip -d vakuova-mincovna
    echo.
    echo 3. Spusť instalaci:
    echo    cd ~/vakuova-mincovna
    echo    chmod +x install_ubuntu_complete.sh
    echo    ./install_ubuntu_complete.sh
    echo.
    echo ============================================================
    echo Standard 700: 12g stříbra = 1 mince
    echo ============================================================
) else (
    echo.
    echo [ERROR] Archive creation failed!
    echo [INFO] Trying alternative method...
    echo.
    echo Install 7-Zip or use manual copy:
    echo   xcopy /E /I /Y . \\ubuntu-pc\share\vakuova-mincovna
)

echo.
pause
