#!/bin/bash
################################################################################
# Vakuová Mincovna - Complete Ubuntu Installation
# 
# Automatická instalace VŠECH komponent na Ubuntu 26.06
# Standard 700: 12g stříbra = 1 mince
# 
# Autor: Pan Jeskyně
# Asistent: Kiro (Claude Sonnet 4.5)
################################################################################

set -e  # Exit on error

echo ""
echo "============================================================"
echo "🏗️  VAKUOVÁ MINCOVNA - UBUNTU COMPLETE INSTALL"
echo "============================================================"
echo "Standard 700: 12g stříbra = 1 mince"
echo "Node: Shadow (Ubuntu 26.06)"
echo "============================================================"
echo ""

# Zjisti IP adresu
IP_ADDR=$(hostname -I | awk '{print $1}')
echo "[INFO] Ubuntu IP: $IP_ADDR"
echo ""

# Požádej o Primary IP
read -p "Zadej IP adresu Windows Primary PC [např. 192.168.1.100]: " PRIMARY_IP
if [ -z "$PRIMARY_IP" ]; then
    PRIMARY_IP="192.168.1.100"
fi
echo "[INFO] Primary IP: $PRIMARY_IP"
echo ""

################################################################################
# PHASE 1: System Dependencies
################################################################################

echo "============================================================"
echo "PHASE 1: Installing system dependencies..."
echo "============================================================"
echo ""

sudo apt update
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-full \
    git \
    build-essential \
    curl \
    wget \
    net-tools \
    openjdk-17-jdk \
    scala \
    prometheus \
    grafana

echo "[✓] System dependencies installed"
echo ""

################################################################################
# PHASE 2: GNAT/SPARK (optional)
################################################################################

echo "============================================================"
echo "PHASE 2: GNAT/SPARK (optional - pro Ada/SPARK build)"
echo "============================================================"
echo ""

read -p "Instalovat GNAT/SPARK? (y/n) [n]: " INSTALL_GNAT
if [ "$INSTALL_GNAT" = "y" ]; then
    echo "[INFO] Instalace GNAT/SPARK..."
    sudo apt install -y gnat gprbuild gnatprove
    echo "[✓] GNAT/SPARK installed"
else
    echo "[SKIP] GNAT/SPARK přeskočeno"
fi
echo ""

################################################################################
# PHASE 3: Apache Spark (pro Watchdog)
################################################################################

echo "============================================================"
echo "PHASE 3: Installing Apache Spark..."
echo "============================================================"
echo ""

if [ ! -d "/opt/spark" ]; then
    echo "[INFO] Downloading Apache Spark 3.5.0..."
    cd /tmp
    wget -q https://dlcdn.apache.org/spark/spark-3.5.0/spark-3.5.0-bin-hadoop3.tgz
    tar xzf spark-3.5.0-bin-hadoop3.tgz
    sudo mv spark-3.5.0-bin-hadoop3 /opt/spark
    
    # Add to PATH
    echo 'export SPARK_HOME=/opt/spark' >> ~/.bashrc
    echo 'export PATH=$PATH:$SPARK_HOME/bin' >> ~/.bashrc
    
    echo "[✓] Apache Spark installed: /opt/spark"
else
    echo "[✓] Apache Spark already installed"
fi

pip3 install pyspark
echo ""

################################################################################
# PHASE 4: Faucet SDN Controller
################################################################################

echo "============================================================"
echo "PHASE 4: Installing Faucet SDN Controller..."
echo "============================================================"
echo ""

cd ~/vakuova-mincovna/faucet

# Virtual environment
if [ ! -d "venv" ]; then
    echo "[INFO] Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Git init (pro pbr versioning)
if [ ! -d ".git" ]; then
    echo "[INFO] Initializing Git repository..."
    git init
    git config user.name "Pan Jeskyne"
    git config user.email "pan@vakuova-mincovna.cz"
    git add .
    git commit -m "Faucet for Vakuova Mincovna - Shadow Node"
    git tag v1.0.0
fi

# Install dependencies
echo "[INFO] Installing Faucet dependencies..."
pip install -r requirements.txt
pip install eventlet
pip install -e .

# Config
mkdir -p etc/faucet
if [ ! -f "etc/faucet/faucet.yaml" ]; then
    cat > etc/faucet/faucet.yaml << 'EOF'
# Vakuová Mincovna - Faucet Config (Shadow Node)
# Standard 700: 12g stříbra = 1 mince

vlans:
    vlan100:
        vid: 100
        description: "P2P Network - Shadow"

dps:
    switch-shadow:
        dp_id: 0x2
        hardware: "Open vSwitch"
        interfaces:
            1:
                native_vlan: vlan100
            2:
                native_vlan: vlan100
EOF
fi

deactivate
echo "[✓] Faucet SDN installed"
echo ""

################################################################################
# PHASE 5: Python Components
################################################################################

echo "============================================================"
echo "PHASE 5: Installing Python components..."
echo "============================================================"
echo ""

cd ~/vakuova-mincovna

# Install Python dependencies
pip3 install prometheus_client requests pyspark

echo "[✓] Python dependencies installed"
echo ""

################################################################################
# PHASE 6: Update Primary IP in configs
################################################################################

echo "============================================================"
echo "PHASE 6: Updating Primary IP in configurations..."
echo "============================================================"
echo ""

# Update shadow_node.py
if [ -f "src/shadow_node.py" ]; then
    sed -i "s|PRIMARY_URL = \"http://localhost:9302/metrics\"|PRIMARY_URL = \"http://$PRIMARY_IP:9302/metrics\"|g" src/shadow_node.py
    echo "[✓] shadow_node.py updated with Primary IP: $PRIMARY_IP"
fi

# Update spark_watchdog.py
if [ -f "src/spark_watchdog.py" ]; then
    sed -i "s|localhost|$PRIMARY_IP|g" src/spark_watchdog.py
    echo "[✓] spark_watchdog.py updated"
fi

echo ""

################################################################################
# PHASE 7: Firewall Configuration
################################################################################

echo "============================================================"
echo "PHASE 7: Configuring firewall..."
echo "============================================================"
echo ""

sudo ufw allow 9303/tcp  # Shadow Node
sudo ufw allow 9304/tcp  # Watchdog
sudo ufw allow 9305/tcp  # Privacy
sudo ufw allow 6653/tcp  # Faucet OpenFlow
sudo ufw allow from $PRIMARY_IP  # Allow Primary PC

echo "[✓] Firewall rules added"
echo ""

################################################################################
# PHASE 8: Cron Job for Privacy 4:23
################################################################################

echo "============================================================"
echo "PHASE 8: Setting up cron job for Privacy Protocol 4:23..."
echo "============================================================"
echo ""

# Add cron job if not exists
(crontab -l 2>/dev/null | grep -v "privacy_purge_423") ; echo "23 4 * * * cd ~/vakuova-mincovna && ./start_privacy.sh" | crontab -

echo "[✓] Cron job added: Every day at 4:23 AM"
echo ""

################################################################################
# PHASE 9: Make scripts executable
################################################################################

echo "============================================================"
echo "PHASE 9: Making scripts executable..."
echo "============================================================"
echo ""

cd ~/vakuova-mincovna
chmod +x *.sh

echo "[✓] All scripts are executable"
echo ""

################################################################################
# PHASE 10: Summary & Next Steps
################################################################################

echo ""
echo "============================================================"
echo "✅  INSTALLATION COMPLETE!"
echo "============================================================"
echo ""
echo "📍 Shadow Node Configuration:"
echo "   • IP Address: $IP_ADDR"
echo "   • Primary Node: $PRIMARY_IP:9302"
echo "   • Shadow Port: 9303"
echo "   • Watchdog Port: 9304"
echo "   • Privacy Port: 9305"
echo ""
echo "🚀 Start Services:"
echo ""
echo "   # Terminal 1: Faucet"
echo "   cd ~/vakuova-mincovna"
echo "   ./start_faucet.sh"
echo ""
echo "   # Terminal 2: Shadow Node"
echo "   ./start_shadow.sh"
echo ""
echo "   # Terminal 3: Watchdog"
echo "   ./start_watchdog.sh"
echo ""
echo "   # Terminal 4: Privacy (background)"
echo "   ./start_privacy.sh &"
echo ""
echo "📊 Check Status:"
echo "   curl http://localhost:9303/metrics"
echo "   curl http://$PRIMARY_IP:9302/metrics"
echo ""
echo "============================================================"
echo "Standard 700: 12g stříbra = 1 mince"
echo "============================================================"
echo ""
