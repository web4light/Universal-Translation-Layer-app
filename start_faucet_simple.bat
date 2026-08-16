@echo off
REM ============================================================================
REM Faucet SDN Controller - Jednoduchý Start (pip install)
REM 
REM Standard 700: 12g stříbra = 1 mince
REM ============================================================================

echo.
echo ============================================================
echo 🌊 FAUCET SDN CONTROLLER - SIMPLE START
echo ============================================================
echo.

cd /d "%~dp0"

REM Vytvoř venv v root projektu
if not exist "venv-faucet" (
    echo [FAUCET] Creating virtual environment...
    python -m venv venv-faucet
)

echo [FAUCET] Activating virtual environment...
call venv-faucet\Scripts\activate.bat

echo [FAUCET] Upgrading pip...
python -m pip install --upgrade pip --quiet

echo [FAUCET] Installing Faucet from PyPI...
pip install faucet --quiet

if errorlevel 1 (
    echo [ERROR] Faucet installation failed!
    echo [INFO] Trying manual dependencies...
    pip install eventlet prometheus_client pyyaml
    pause
    exit /b 1
)

echo [FAUCET] ✓ Faucet installed successfully
echo.

REM Vytvoř config složku
if not exist "etc\faucet" (
    echo [FAUCET] Creating config directory...
    mkdir etc\faucet
)

REM Vytvoř default config
if not exist "etc\faucet\faucet.yaml" (
    echo [FAUCET] Creating default configuration...
    
    (
        echo # Vakuová Mincovna - Faucet Config
        echo # Standard 700: 12g stříbra = 1 mince
        echo.
        echo vlans:
        echo     vlan100:
        echo         vid: 100
        echo         description: "P2P Network - Vakuova Mincovna"
        echo.
        echo dps:
        echo     switch-1:
        echo         dp_id: 0x1
        echo         hardware: "Open vSwitch"
        echo         interfaces:
        echo             1:
        echo                 native_vlan: vlan100
        echo             2:
        echo                 native_vlan: vlan100
    ) > etc\faucet\faucet.yaml
    
    echo [FAUCET] ✓ Config created: etc\faucet\faucet.yaml
)

echo.
echo ============================================================
echo [FAUCET] Configuration
echo ============================================================
echo [FAUCET] Config: etc\faucet\faucet.yaml
echo [FAUCET] OpenFlow port: 6653
echo [FAUCET] Prometheus port: 9302
echo ============================================================
echo.

echo [FAUCET] Starting Faucet Controller...
echo [FAUCET] Press Ctrl+C to stop
echo.

REM Spusť Faucet s config
faucet --verbose --ryu-config-file=etc\faucet\faucet.yaml

echo.
echo [FAUCET] Controller stopped
pause
