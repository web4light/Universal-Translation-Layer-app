@echo off
REM ============================================================================
REM Faucet Fix - Oprava Git repository problému
REM ============================================================================

echo.
echo ============================================================
echo 🔧 FAUCET FIX - Git Repository Setup
echo ============================================================
echo.

cd /d "%~dp0\faucet"

REM Kontrola Git
git --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git not found! Installing...
    winget install Git.Git
    echo [INFO] Git installed. Restartuj terminál a spusť znovu.
    pause
    exit /b 1
)

echo [FIX] Git version:
git --version
echo.

REM Inicializace Git repo (pokud ještě není)
if not exist ".git" (
    echo [FIX] Initializing Git repository...
    git init
    git config user.name "Pan Jeskyne"
    git config user.email "pan.jeskyne@vakuova-mincovna.cz"
    
    echo [FIX] Adding files...
    git add .
    
    echo [FIX] Creating initial commit...
    git commit -m "Initial commit - Faucet SDN for Vakuova Mincovna"
    
    echo [FIX] ✓ Git repository created
) else (
    echo [FIX] Git repository already exists
)

echo.
echo ============================================================
echo [FIX] Creating PBR version file...
echo ============================================================
echo.

REM Vytvoř version tag
git tag -a v1.0.0 -m "Vakuova Mincovna - Faucet v1.0.0" 2>nul
echo [FIX] ✓ Version tag created: v1.0.0

echo.
echo ============================================================
echo [FIX] Installing Faucet with dependencies...
echo ============================================================
echo.

REM Aktivuj venv
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [FIX] Creating new venv...
    python -m venv venv
    call venv\Scripts\activate.bat
)

REM Upgrade pip
python -m pip install --upgrade pip

REM Instaluj závislosti přímo z requirements.txt (bez -e)
echo [FIX] Installing dependencies from requirements.txt...
pip install -r requirements.txt

REM Instaluj eventlet (chybí)
echo [FIX] Installing eventlet...
pip install eventlet

REM Instaluj další potřebné
pip install prometheus_client pyyaml

echo.
echo ============================================================
echo [FIX] ✓ Faucet fix completed!
echo ============================================================
echo.
echo [NEXT] Run: python -m faucet.faucet --verbose
echo.

pause
