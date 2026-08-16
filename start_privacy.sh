#!/bin/bash
# Privacy Protocol 4:23 starter (Linux/Ubuntu)

echo "========================================"
echo "Privacy Protocol 4:23"
echo "========================================"
echo ""

echo "[PRIVACY] Installing dependencies..."
pip3 install schedule prometheus_client

echo ""
echo "[PRIVACY] Starting privacy daemon..."
echo "[PRIVACY] Daily purge: 04:23 AM"
echo "[PRIVACY] Zero cookies: ENABLED"
echo "[PRIVACY] Port: 9305"
echo ""

python3 src/privacy_purge_423.py
