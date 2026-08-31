#!/bin/bash
# ============================================================
#  Vakuová Mincovna — MASTER START SCRIPT (Robustní verze)
# ============================================================

# Cesta k projektu
PROJECT_ROOT="/home/asgard/Universal-Translation-Layer"
cd "$PROJECT_ROOT"

# Nastavení PYTHONPATH pro venv knihovny
export PYTHONPATH="$PROJECT_ROOT/.venv/lib/python3.14/site-packages:$PYTHONPATH"

echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║              🏗️  VAKUOVÁ MINCOVNA - START ALL                      ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"

# 1. NAS Integration
echo "[*] Kontrola NAS (192.168.123.121)..."
./mount_nas.sh
if [ $? -ne 0 ]; then
    echo "  [!] VAROVÁNÍ: NAS se nepodařilo připojit."
    echo "  [!] Logy budou ukládány lokálně do $PROJECT_ROOT/logs/"
fi

# 2. Build Ada Core
echo "[1/3] Kontrola Ada/SPARK binárky..."
gprbuild -P mincovna.gpr mincovna_main.adb &> /dev/null
if [ $? -eq 0 ]; then
    echo "  ✓ Ada Core (mincovna_main) připraven"
else
    echo "  ✗ CHYBA: Build Ada Core selhal!"
    exit 1
fi

# 3. Start Primary Node (Bridge)
echo "[2/3] Spouštění Primary Node (port 9302)..."
python3 src/faucet_bridge.py &
BRIDGE_PID=$!
sleep 2 # Počkat na inicializaci serveru

if ps -p $BRIDGE_PID > /dev/null; then
    echo "  ✓ Primary Node běží (PID: $BRIDGE_PID)"
else
    echo "  ✗ CHYBA: Primary Node se nepodařilo spustit!"
    kill $(jobs -p) 2>/dev/null
    exit 1
fi

# 4. Start Shadow Node (Monitoring)
echo "[3/3] Spouštění Shadow Node (port 9303)..."
python3 src/shadow_node.py &
SHADOW_PID=$!
sleep 1

if ps -p $SHADOW_PID > /dev/null; then
    echo "  ✓ Shadow Node běží (PID: $SHADOW_PID)"
else
    echo "  [!] VAROVÁNÍ: Shadow Node neběží."
fi

echo ""
echo "=== SYSTÉM BĚŽÍ ==="
echo "Primary Metriky: http://localhost:9302/metrics"
echo "Shadow Metriky:  http://localhost:9303/metrics"
echo "==================="
echo "Pro ukončení stiskněte Ctrl+C."

# Úklid při ukončení
trap "echo -e '\nUkončuji služby...'; kill $BRIDGE_PID $SHADOW_PID 2>/dev/null; exit" INT TERM
wait
