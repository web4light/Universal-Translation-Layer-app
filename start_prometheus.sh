#!/bin/bash
################################################################################
# Start Prometheus - Ubuntu
# Standard 700: 12g stříbra = 1 mince
################################################################################

echo ""
echo "============================================================"
echo "📊 Starting Prometheus"
echo "============================================================"
echo ""

cd "$(dirname "$0")"

# Check if installed via apt
if command -v prometheus &> /dev/null && [ -f "/etc/prometheus/prometheus.yml" ]; then
    echo "[PROMETHEUS] Starting system service..."
    echo ""
    sudo systemctl start prometheus
    sudo systemctl status prometheus --no-pager
    echo ""
    echo "Web UI: http://localhost:9090"
    
# Check if installed from binary
elif [ -f "prometheus-bin/prometheus" ]; then
    echo "[PROMETHEUS] Config: prometheus/prometheus.yml"
    echo "[PROMETHEUS] Web UI: http://localhost:9090"
    echo "[PROMETHEUS] Scraping:"
    echo "  - Primary Node: localhost:9302"
    echo "  - Shadow Node: localhost:9303"
    echo ""
    
    prometheus-bin/prometheus --config.file=prometheus/prometheus.yml
    
else
    echo "[ERROR] Prometheus not installed!"
    echo "[INFO] Run: ./install_prometheus.sh"
    exit 1
fi
