#!/bin/bash
# ============================================================
#  Vakuová Mincovna — MASTER START SCRIPT (V2 - Robustní)
# ============================================================

PROJECT_ROOT="/home/asgard/Universal-Translation-Layer"
cd "$PROJECT_ROOT"

# PYTHONPATH pro knihovny z .venv
export PYTHONPATH="$PROJECT_ROOT/.venv/lib/python3.14/site-packages:$PYTHONPATH"

echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║              🏗️  VAKUOVÁ MINCOVNA - START ALL                      ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"

# Zabití případných visících procesů
pkill -f faucet_bridge.py
pkill -f shadow_node.py
sleep 1

# 1. NAS (Volitelně, neblokující)
echo "[*] Kontrola NAS (192.168.123.121)..."
./mount_nas.sh
# mount_nas.sh nyní používá sudo -n, takže nezůstane viset na hesle

# 2. Ada Core
echo "[1/3] Kontrola Ada binárky..."
if [ ! -f bin/mincovna_main ]; then
    gprbuild -P mincovna.gpr mincovna_main.adb
fi
echo "  ✓ Ada Core připraven"

# 3. Primary Node
echo "[2/3] Spouštění Primary Node (9302)..."
python3 src/faucet_bridge.py > logs/bridge.out 2>&1 &
BRIDGE_PID=$!
sleep 2

if ps -p $BRIDGE_PID > /dev/null; then
    echo "  ✓ Primary Node běží (PID: $BRIDGE_PID)"
else
    echo "  ✗ CHYBA: Primary Node nenastartoval! Koukněte do logs/bridge.out"
    exit 1
fi

# 4. Shadow Node
echo "[3/3] Spouštění Shadow Node (9303)..."
python3 src/shadow_node.py > logs/shadow.out 2>&1 &
SHADOW_PID=$!
sleep 1
echo "  ✓ Shadow Node běží (PID: $SHADOW_PID)"

echo ""
echo "=== SYSTÉM BĚŽÍ ==="
echo "Metriky: http://localhost:9302/metrics"
echo "==================="
echo "Ctrl+C pro vypnutí."

trap "kill $BRIDGE_PID $SHADOW_PID; echo -e '\nUkončeno.'; exit" INT TERM
wait
