# 🏗️ Vakuová Mincovna - Kompletní Setup pro Oba Počítače

**Standard 700:** 12g stříbra = 1 mince  
**Architektura:** Primary (Windows) + Shadow (Ubuntu)  
**Autor:** Pan Jeskyně + Kiro AI

---

## 📋 Přehled

```
┌─────────────────────────────────────────────────────────┐
│                  VAKUOVÁ MINCOVNA                       │
│              (Distributed Architecture)                 │
└─────────────────────────────────────────────────────────┘
                          │
         ┌────────────────┴────────────────┐
         │                                 │
┌────────▼──────────┐          ┌──────────▼────────┐
│  PRIMARY NODE     │          │   SHADOW NODE     │
│  (Windows PC)     │◄────────►│   (Ubuntu 26.06)  │
│                   │   sync   │   "stars"         │
│  • Faucet (9302)  │          │   • Shadow (9303) │
│  • Ada/SPARK      │          │   • Watchdog      │
│  • Gemini AI      │          │   • Faucet        │
└───────────────────┘          └───────────────────┘
```

---

## 🖥️ PART 1: Windows PC (Primary Node)

### A. Ada/SPARK Core

```cmd
cd c:\Users\pan_jeskyne\Favorites\vakuova-mincovna

# Build všechny komponenty
gprbuild -P mincovna.gpr

# Formální verifikace
gnatprove -P mincovna.gpr --level=4

# Spusť
bin\mincovna.exe
bin\faucet_controller.exe
bin\gemini_bridge.exe
```

### B. Faucet SDN (Windows)

#### Možnost 1: Git fix + install
```cmd
cd c:\Users\pan_jeskyne\Favorites\vakuova-mincovna
FAUCET_FIX.bat
```

#### Možnost 2: Simple PyPI install
```cmd
cd c:\Users\pan_jeskyne\Favorites\vakuova-mincovna
start_faucet_simple.bat
```

### C. Python Bridge (Primary 9302)

```cmd
cd c:\Users\pan_jeskyne\Favorites\vakuova-mincovna
pip install prometheus_client requests
python src\faucet_bridge.py
```

### D. Prometheus

```cmd
# Download Prometheus pro Windows
# https://prometheus.io/download/

# Spusť
prometheus.exe --config.file=prometheus\prometheus.yml
```

---

## 🐧 PART 2: Ubuntu 26.06 (Shadow Node "stars")

### A. System Dependencies

```bash
sudo apt update
sudo apt install -y \
    python3 python3-pip python3-venv python3-full \
    git build-essential \
    gnat gprbuild gnatprove \
    prometheus grafana
```

### B. Faucet SDN (Ubuntu)

```bash
cd ~/vakuova-mincovna/faucet

# Instalace
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip

# Git init (pro pbr)
git init
git config user.name "Pan Jeskyne"
git config user.email "pan@vakuova-mincovna.cz"
git add .
git commit -m "Faucet for Vakuova Mincovna"
git tag v1.0.0

# Dependencies
pip install -r requirements.txt
pip install eventlet
pip install -e .

# Config
mkdir -p etc/faucet
cat > etc/faucet/faucet.yaml << 'EOF'
vlans:
    vlan100:
        vid: 100
        description: "P2P Network"
dps:
    switch-1:
        dp_id: 0x1
        hardware: "Open vSwitch"
        interfaces:
            1:
                native_vlan: vlan100
            2:
                native_vlan: vlan100
EOF

# Spusť
python3 -m faucet.faucet --verbose
```

### C. Shadow Node (Port 9303)

```bash
cd ~/vakuova-mincovna

# Instalace dependencies
pip3 install prometheus_client requests

# Spusť Shadow
chmod +x start_shadow.sh
./start_shadow.sh
```

### D. Watchdog (Port 9304)

```bash
cd ~/vakuova-mincovna

# Instalace Spark
sudo apt install -y openjdk-17-jdk scala
# Download Apache Spark
wget https://dlcdn.apache.org/spark/spark-3.5.0/spark-3.5.0-bin-hadoop3.tgz
tar xvf spark-3.5.0-bin-hadoop3.tgz
sudo mv spark-3.5.0-bin-hadoop3 /opt/spark

# PySpark
pip3 install pyspark

# Spusť Watchdog
chmod +x start_watchdog.sh
./start_watchdog.sh
```

### E. Privacy 4:23 (Port 9305)

```bash
cd ~/vakuova-mincovna

# Spusť Privacy Purge
chmod +x start_privacy.sh
./start_privacy.sh

# Schedule 4:23 AM purge
crontab -e
# Přidej:
23 4 * * * /home/pan/vakuova-mincovna/start_privacy.sh
```

---

## 🔗 PART 3: Network Connection (oba počítače)

### Zjistit IP adresy

**Windows:**
```cmd
ipconfig
# Hledej IPv4 Address: 192.168.x.x
```

**Ubuntu:**
```bash
ip addr show
# Nebo
hostname -I
```

### Update konfigurace

**Windows (Primary) - aktualizuj Shadow URL:**

Upravit `src\shadow_node.py`:
```python
PRIMARY_URL = "http://192.168.1.100:9302/metrics"  # IP Windows PC
```

**Ubuntu (Shadow) - aktualizuj Primary URL:**

Upravit `src/shadow_node.py`:
```python
PRIMARY_URL = "http://192.168.1.100:9302/metrics"  # IP Windows PC
```

### Test connectivity

**Z Ubuntu na Windows:**
```bash
ping 192.168.1.100
curl http://192.168.1.100:9302/metrics
```

**Z Windows na Ubuntu:**
```cmd
ping 192.168.1.101
curl http://192.168.1.101:9303/metrics
```

---

## 🚀 PART 4: Startup Sequence

### 1. Spusť Windows Primary (v tomto pořadí):

```cmd
# Terminal 1: Ada/SPARK
cd c:\Users\pan_jeskyne\Favorites\vakuova-mincovna
bin\mincovna.exe

# Terminal 2: Faucet
start_faucet_simple.bat

# Terminal 3: Python Bridge (Primary)
python src\faucet_bridge.py

# Terminal 4: Prometheus
prometheus.exe --config.file=prometheus\prometheus.yml
```

### 2. Spusť Ubuntu Shadow (v tomto pořadí):

```bash
# Terminal 1: Faucet
cd ~/vakuova-mincovna/faucet
source venv/bin/activate
python3 -m faucet.faucet --verbose

# Terminal 2: Shadow Node
cd ~/vakuova-mincovna
./start_shadow.sh

# Terminal 3: Watchdog
./start_watchdog.sh

# Terminal 4: Privacy (background)
./start_privacy.sh &
```

---

## 📊 PART 5: Monitoring & Testing

### Kontrola všech portů

| Port | Služba | PC | URL |
|------|--------|----|----|
| 9302 | Primary Node | Windows | http://192.168.1.100:9302/metrics |
| 9303 | Shadow Node | Ubuntu | http://192.168.1.101:9303/metrics |
| 9304 | Watchdog | Ubuntu | http://192.168.1.101:9304/metrics |
| 9305 | Privacy | Ubuntu | http://192.168.1.101:9305/metrics |
| 6653 | Faucet OpenFlow | Both | N/A (internal) |
| 9090 | Prometheus | Windows | http://192.168.1.100:9090 |

### Test Failover

```bash
# Na Ubuntu:
curl http://192.168.1.101:9303/metrics | grep shadow_is_primary
# Mělo by být: shadow_is_primary 0

# Vypni Windows Primary
# Počkej 20 sekund

curl http://192.168.1.101:9303/metrics | grep shadow_is_primary
# Mělo by být: shadow_is_primary 1  (FAILOVER!)
```

---

## 🔧 PART 6: Troubleshooting

### Windows - Faucet nefunguje

```cmd
# Zkus FAUCET_FIX.bat
FAUCET_FIX.bat

# Nebo nainstaluj Git
winget install Git.Git

# A znovu
cd faucet
git init
git add .
git commit -m "init"
git tag v1.0.0
venv\Scripts\activate.bat
pip install -e .
```

### Ubuntu - Permission denied

```bash
chmod +x start_*.sh
sudo ufw allow 9303/tcp
sudo ufw allow 9304/tcp
sudo ufw allow 9305/tcp
```

### Network - Počítače se nevidí

```bash
# Ubuntu firewall
sudo ufw status
sudo ufw allow from 192.168.1.0/24

# Windows firewall
netsh advfirewall firewall add rule name="Vakuova Mincovna" dir=in action=allow protocol=TCP localport=9302
```

---

## 📚 Reference

- **BUILD.md** - Build instrukce
- **FAUCET_QUICKSTART.md** - Faucet detaily
- **SHADOW_NODE.md** - Shadow Node dokumentace
- **SECURITY_WATCHDOG.md** - Watchdog konfigurace
- **PRIVACY_PROTOCOL_423.md** - Privacy detaily
- **DEPLOY_UBUNTU.md** - Ubuntu deployment
- **SYSTEM_OVERVIEW.md** - Kompletní architektura

---

## ✅ Checklist

### Windows (Primary):
- [ ] GNAT/SPARK nainstalován
- [ ] Ada komponenty zkompilované
- [ ] Faucet běží (port 6653, 9302)
- [ ] Python Bridge běží (port 9302)
- [ ] Prometheus běží (port 9090)

### Ubuntu (Shadow):
- [ ] System dependencies nainstalovány
- [ ] Faucet běží (port 6653)
- [ ] Shadow Node běží (port 9303)
- [ ] Watchdog běží (port 9304)
- [ ] Privacy běží (port 9305)
- [ ] Cron job 4:23 nastaven

### Network:
- [ ] IP adresy známé
- [ ] Ping funguje (obousměrně)
- [ ] Firewall rules nastavené
- [ ] Shadow synchronizuje Primary
- [ ] Failover test úspěšný

---

**Standard 700:** 12g stříbra = 1 mince  
**Příští krok:** Začít s Windows Primary, pak přidat Ubuntu Shadow
