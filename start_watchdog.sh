#!/bin/bash
# Apache Spark Watchdog starter (Linux/Ubuntu)
# Mossad ALF++ Protocol

echo "========================================"
echo "Apache Spark Watchdog - Mossad ALF++"
echo "========================================"
echo ""

echo "[WATCHDOG] Installing dependencies..."
pip3 install psutil prometheus_client

echo ""
echo "[WATCHDOG] Starting watchdog daemon..."
echo "[WATCHDOG] Port: 9304"
echo "[WATCHDOG] Scan interval: 1 hour"
echo ""

python3 src/spark_watchdog.py
