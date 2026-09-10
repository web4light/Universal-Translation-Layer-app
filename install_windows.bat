@echo off
REM ============================================================
REM  Asterisk (*) — Univerzalni instalator pro Windows
REM  Podporuje: Next.js 3D Avatar, Chrome Extension, SPARK Core
REM ============================================================

chcp 65001 >nul
echo.
echo ============================================================
echo   ASTERISK (*) SOVEREIGN PLATFORM — INSTALACE PRO WINDOWS
echo ============================================================
echo.

REM 1. Kontrola Node.js a npm
echo [1/4] Kontrola Node.js a npm...
where node >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [VAROVANI] Node.js nenalezen!
    echo Pro instalaci muzete pouzit prikaz:
    echo   winget install OpenJS.NodeJS.LTS
    echo Nebo stahnete instalator z: https://nodejs.org/
    echo.
    set NODE_MISSING=1
) else (
    for /f "tokens=*" %%i in ('node -v') do set NODE_VER=%%i
    for /f "tokens=*" %%i in ('npm -v') do set NPM_VER=%%i
    echo   [OK] Node.js nalezen: %NODE_VER% (npm: %NPM_VER%)
    set NODE_MISSING=0
)

REM 2. Kontrola Pythonu
echo [2/4] Kontrola Pythonu...
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [VAROVANI] Python nenalezen!
    echo Pro instalaci muzete pouzit: winget install Python.Python.3.11
    echo Nebo stahnete z: https://www.python.org/
    set PY_MISSING=1
) else (
    for /f "tokens=*" %%i in ('python --version') do set PY_VER=%%i
    echo   [OK] Python nalezen: %PY_VER%
    set PY_MISSING=0
)

REM 3. Kontrola GNAT/Ada (volitelne)
echo [3/4] Kontrola Ada/SPARK nastroju (GNAT)...
where gprbuild >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   [OK] GNAT/SPARK nalezene (gprbuild)
) else (
    echo   [INFO] GNAT nastroje nebyly v PATH nalezeny.
    echo   Pro SPARK jadro muzete pouzit install_ada.bat nebo Alire (alr).
)

REM 4. Instalace balicku pro 3D avatar (dlp3d)
echo [4/4] Instalace npm balicku pro 3D Avatar (dlp3d)...
if %NODE_MISSING% EQU 0 (
    echo   Instaluji zavislosti v dlp3d...
    cd dlp3d
    call npm install
    cd ..
    if %ERRORLEVEL% EQU 0 (
        echo   [OK] Zavislosti dlp3d uspesne nainstalovany!
    ) else (
        echo   [VAROVANI] npm install v dlp3d skoncil s chybou.
    )
) else (
    echo   [PRESKOCENO] Node.js neni nainstalovan, preskakuji npm install.
)

echo.
echo ============================================================
echo   INSTALACE PRO WINDOWS DOKONCENA!
echo ============================================================
echo.
echo Pro spusteni aplikaci muzete pouzit:
echo   - start_windows.bat  (Graficke menu pro spusteni vseho)
echo   - npm run dev        (Spusteni 3D avatara na http://localhost:3000)
echo   - npm run dev:studio (Spusteni AI Studia na http://localhost:8088)
echo.
pause
