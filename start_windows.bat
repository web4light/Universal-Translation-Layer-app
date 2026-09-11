@echo off
REM ============================================================
REM  Asterisk (*) — Hlavni spoustec pro Windows
REM ============================================================

chcp 65001 >nul
title Asterisk (*) Sovereign Platform — Windows Launcher

:MENU
cls
echo.
echo ============================================================
echo   ✦ ASTERISK (*) SOVEREIGN PLATFORM — WINDOWS MENU
echo   Dohled: SPARKdog Guardian • 100%% In-Memory RAM
echo ============================================================
echo.
echo   [1] Spustit 3D Znakovy Avatar (Next.js na http://localhost:3000)
echo   [2] Spustit Hackathon AI Studio (Web na http://localhost:8088)
echo   [3] Prelozit a spustit Ada/SPARK jadro (SPARKdog)
echo   [4] Otevrit slozku Chrome rozsireni (Sidepanel Asistent)
echo   [5] Spustit Flutter aplikaci (Desktop / Web)
echo   [6] Spustit VSE (3D Avatar + Studio)
echo   [7] Re-instalovat zavislosti (npm install)
echo   [8] Otestovat Soulbound ETH Wallet (Ada/SPARK Web4)
echo   [0] Ukoncit
echo.
echo ============================================================
set /p VOLBA="Zadejte volbu [0-8]: "

if "%VOLBA%"=="1" goto START_AVATAR
if "%VOLBA%"=="2" goto START_STUDIO
if "%VOLBA%"=="3" goto START_SPARK
if "%VOLBA%"=="4" goto OPEN_EXT
if "%VOLBA%"=="5" goto START_FLUTTER
if "%VOLBA%"=="6" goto START_ALL
if "%VOLBA%"=="7" goto REINSTALL
if "%VOLBA%"=="8" goto START_WALLET
if "%VOLBA%"=="0" goto EXIT
goto MENU

:START_AVATAR
echo.
echo Spoustim 3D Avatar (Next.js dev server)...
cd dlp3d
start "Asterisk 3D Avatar" npm run dev
cd ..
echo Server spusten v novem okne. Oteviram prohlizec...
timeout /t 3 >nul
start http://localhost:3000
goto MENU

:START_STUDIO
echo.
echo Spoustim Hackathon AI Studio na portu 8088...
start "Hackathon Studio" python -m http.server 8088 --directory web
timeout /t 2 >nul
start http://localhost:8088/hackathon_studio.html
goto MENU

:START_SPARK
echo.
echo Prekladam Ada/SPARK jadro...
where gprbuild >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [CHYBA] gprbuild nenalezen v PATH.
    echo Spustte install_ada.bat pro instalaci AdaCore nastroju.
    pause
    goto MENU
)
gprbuild -P spark_agent.gpr
if %ERRORLEVEL% EQU 0 (
    echo [OK] Preklad uspesny, spoustim test jadra...
    if exist obj\spark_agent_main.exe (
        obj\spark_agent_main.exe
    ) else if exist obj\spark_agent_main (
        obj\spark_agent_main
    )
) else (
    echo [CHYBA] Preklad Ada/SPARK selhal!
)
pause
goto MENU

:OPEN_EXT
echo.
echo Oteviram slozku rozsireni...
echo.
echo POSTUP V CHROME:
echo   1. Otevrete v Chrome: chrome://extensions
echo   2. Zapnete vpravo nahore 'Rezim pro vyvojare' (Developer mode)
echo   3. Kliknete na 'Nacist rozbalene' (Load unpacked)
echo   4. Vyberte slozku: %CD%\extension
echo.
explorer "%CD%\extension"
start chrome://extensions
pause
goto MENU

:START_FLUTTER
echo.
echo Spoustim Flutter aplikaci...
cd app
call flutter pub get
call flutter run -d chrome
cd ..
pause
goto MENU

:START_ALL
echo.
echo Spoustim 3D Avatar i AI Studio soucasne...
cd dlp3d
start "Asterisk 3D Avatar" npm run dev
cd ..
start "Hackathon Studio" python -m http.server 8088 --directory web
timeout /t 3 >nul
start http://localhost:3000
start http://localhost:8088/hackathon_studio.html
goto MENU

:REINSTALL
echo.
echo Re-instaluji zavislosti pro dlp3d...
cd dlp3d
call npm install
cd ..
pause
goto MENU

:START_WALLET
echo.
echo Prekladam a spoustim Soulbound ETH Wallet (Web4)...
gprbuild -P eth_wallet.gpr
if %ERRORLEVEL% EQU 0 (
    echo [OK] Preklad uspesny, spoustim test penezenky...
    if exist obj\eth_wallet\eth_wallet_main.exe (
        obj\eth_wallet\eth_wallet_main.exe
    ) else if exist obj\eth_wallet\eth_wallet_main (
        obj\eth_wallet\eth_wallet_main
    )
) else (
    echo [CHYBA] Preklad eth_wallet selhal!
)
pause
goto MENU

:EXIT
echo Nashledanou!
exit /b 0
