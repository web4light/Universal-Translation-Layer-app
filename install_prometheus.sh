#!/bin/bash
################################################################################
# Prometheus Installation - Ubuntu
# Standard 700: 12g stříbra = 1 mince
################################################################################

echo ""
echo "============================================================"
echo "📊 Installing Prometheus for Ubuntu"
echo "============================================================"
echo ""

cd "$(dirname "$0")"

# Prometheus version
PROM_VERSION="2.47.0"

echo "[INFO] Installing via apt (recommended)..."
echo ""

# Update and install
sudo apt update
sudo apt install -y prometheus

if command -v prometheus &> /dev/null; then
    echo ""
    echo "============================================================"
    echo "✅ Prometheus installed via apt!"
    echo "============================================================"
    echo ""
    echo "Config: /etc/prometheus/prometheus.yml"
    echo ""
    echo "Copy our config:"
    echo "sudo cp prometheus/prometheus.yml /etc/prometheus/"
    echo ""
    echo "Start: sudo systemctl start prometheus"
    echo "Enable: sudo systemctl enable prometheus"
    echo "Status: sudo systemctl status prometheus"
    echo ""
else
    echo ""
    echo "[INFO] Installing from binary..."
    echo ""
    
    # Download
    wget "https://github.com/prometheus/prometheus/releases/download/v${PROM_VERSION}/prometheus-${PROM_VERSION}.linux-amd64.tar.gz"
    
    # Extract
    tar xvf "prometheus-${PROM_VERSION}.linux-amd64.tar.gz"
    
    # Move
    if [ -d "prometheus-bin" ]; then
        rm -rf prometheus-bin
    fi
    mv "prometheus-${PROM_VERSION}.linux-amd64" prometheus-bin
    
    # Cleanup
    rm "prometheus-${PROM_VERSION}.linux-amd64.tar.gz"
    
    echo ""
    echo "============================================================"
    echo "✅ Prometheus installed from binary!"
    echo "============================================================"
    echo ""
    echo "Location: prometheus-bin/"
    echo "Config: prometheus/prometheus.yml"
    echo ""
    echo "Start with: ./start_prometheus.sh"
    echo ""
fi
