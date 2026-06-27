                                                                                                                                                                                                                                                             
# Spouštěcí skript pro Shadow Node
# Stínovací uzel pro Vakuovou Mincovnu

echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║              🌑 SHADOW NODE - STÍNOVACÍ UZEL                      ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo ""

# Kontrola Python
echo "[1/2] Kontrola Python dependencies..."
if command -v python3 &> /dev/null; then
    echo "  ✓ Python3 nalezen"
    
    # Install dependencies pokud chybí
    python3 -c "import prometheus_client" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "  Installing prometheus_client..."
        pip3 install prometheus_client
    fi
    
    python3 -c "import requests" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "  Installing requests..."
        pip3 install requests
    fi
    
    echo "  ✓ Dependencies OK"
else
    echo "  ✗ Python3 nenalezen!"
    exit 1
fi

# Spuštění Shadow Node
echo "[2/2] Spouštění Shadow Node..."
echo ""

# Volitelně: custom Primary URL jako argument
if [ -n "$1" ]; then
    echo "  Primary URL: $1"
    python3 src/shadow_node.py "$1"
else
    echo "  Primary URL: http://localhost:9302/metrics (default)"
    python3 src/shadow_node.py
fi
