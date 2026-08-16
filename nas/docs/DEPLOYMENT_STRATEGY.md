# 🎯 Vakuová Mincovna - Deployment Strategie

## Hardware Inventura

### i7 "asterisk" (Windows) - Herní PC
```
Název:      asterisk
CPU:        Intel i7-12700F (12 jader @ 2.10 GHz)
RAM:        32 GB DDR4
GPU:        NVIDIA RTX 3070 (8 GB VRAM)
Storage:    932 GB (168 GB použito)
OS:         Windows 11 64-bit
Role:       GAMING + HEAVY COMPUTATION
```

### i5 FUJITSU ESPRIMO G5010 (Ubuntu)
```
Model:      FUJITSU ESPRIMO G5010
CPU:        Intel i5-10500T (6C/12T @ 2.3 GHz)
RAM:        8 GB DDR4
GPU:        Intel UHD 630 (integrovaná)
Storage:    256 GB SSD
OS:         Ubuntu 26.04 LTS (čistý systém)
Kernel:     Linux 7.0.0-22-generic
Desktop:    GNOME 50 (Wayland)
Role:       DEDICATED SERVER
```

### WD MyCloud EX2 Ultra (NAS)
```
Model:      Western Digital MyCloud EX2 Ultra
Storage:    3 TB RAID (redundance)
Network:    192.168.123.121
Protocol:   SMB/NFS/WebDAV
Role:       STORAGE + BACKUP + LOGS
Power:      ~10W (ultra low)
```

---

## 🏗️ Doporučená Architektura

### Varianta A: i5 Primary + i7 Shadow (DOPORUČENO)

```
┌─────────────────────────────────────────────────────────────┐
│                    NETWORK TOPOLOGY                          │
└─────────────────────────────────────────────────────────────┘

┌──────────────────────┐                  ┌──────────────────────┐
│  i5 ESPRIMO          │                  │  i7 "asterisk"       │
│  Ubuntu 26.04        │                  │  Windows 11          │
│  (Čistý systém)      │                  │  (Herní PC)          │
├──────────────────────┤                  ├──────────────────────┤
│                      │                  │                      │
│  PRIMARY NODE        │◄────────────────►│  SHADOW NODE         │
│  Port: 9302          │   sync každých   │  Port: 9303          │
│  • Ada/SPARK Core    │      5 sekund    │  • Failover backup   │
│  • Faucet Bridge     │                  │  • Monitoring only   │
│  • Prometheus        │                  │                      │
│  • Watchdog (light)  │                  │  + HEAVY TASKS:      │
│  • Privacy Protocol  │                  │  • Apache Spark      │
│                      │                  │  • Vertex AI         │
└──────────────────────┘                  │  • Real-time dubbing │
                                          │  • Gaming když neběží│
                                          │  • Grafana dashboard │
                                          └──────────────────────┘

    ↓ Advantage                               ↓ Advantage
• Běží 24/7 bez přerušení              • RTX 3070 pro AI/ML
• Nízká spotřeba (i5-T = 35W)          • 32 GB RAM pro Spark
• Čistý Ubuntu = stabilita             • Můžeš vypnout když hraješ
• Dedicated server = spolehlivost      • Heavy computation offload
```

**Proč tohle?**
1. **i5 je energeticky úsporný** (i5-10500T = 35W TDP) → může běžet 24/7
2. **i5 má čistý Ubuntu** → žádné konflikty, stabilní
3. **i7 s RTX 3070** → může dělat těžké úkoly (Apache Spark, AI) když nehraješ
4. **Shadow může být vypnutý** → když hraješ, Shadow prostě nereaguje, Primary běží dál
5. **Watchdog na Primary** → lehký scan každých 60s (i5 to zvládne)
6. **Heavy Watchdog na Shadow** → když běží, využije RTX pro rychlejší scanning

---

### Varianta B: i7 Primary + i5 Shadow (MOŽNÉ, ale NEdoporučeno)

```
┌──────────────────────┐                  ┌──────────────────────┐
│  i7 "asterisk"       │                  │  i5 ESPRIMO          │
│  Windows 11          │                  │  Ubuntu 26.04        │
├──────────────────────┤                  ├──────────────────────┤
│  PRIMARY NODE        │◄────────────────►│  SHADOW NODE         │
│  Port: 9302          │                  │  Port: 9303          │
└──────────────────────┘                  └──────────────────────┘
```

**Problém:**
- ❌ i7 musí běžet 24/7 (vysoká spotřeba)
- ❌ i7 nemůžeš vypnout když hraješ → Primary spadne → Shadow failover
- ❌ i5 jako Shadow má málo RAM (8 GB) pro heavy tasks
- ✅ Výhoda: Windows Primary = snazší debug

---

## 🎯 FINÁLNÍ ROZHODNUTÍ: Varianta A

### Deployment plán

#### Phase 1: Local Test (i7 Windows) - **TEĎKA**
```cmd
cd c:\Users\pan_jeskyne\Favorites\vakuova-mincovna

REM Terminal 1: Primary (simulace)
start.bat

REM Terminal 2: Shadow (test)
start_shadow.bat

REM Terminal 3: Watchdog
start_watchdog.bat

REM Terminal 4: Privacy Protocol
start_privacy.bat
```

**Cíl:** Otestovat vše lokálně na Windows před transferem

---

#### Phase 2: Transfer na i5 Ubuntu - **PŘÍŠTĚ**

**Na i7 Windows:**
```cmd
cd c:\Users\pan_jeskyne\Favorites\vakuova-mincovna
package.bat
REM → vytvoří vakuova-mincovna-package.zip
```

**Přenos:**
- USB flash disk NEBO
- Síťový share NEBO
- SCP přes network

**Na i5 Ubuntu:**
```bash
# Rozbalit
cd ~
unzip vakuova-mincovna-package.zip
cd vakuova-mincovna

# Install dependencies
sudo apt update
sudo apt install -y python3 python3-pip
pip3 install prometheus_client requests

# Install GNAT/SPARK (volitelné, můžeš použít pre-compiled binary)
# wget https://community.download.adacore.com/...

# Build Ada/SPARK Core
gprbuild -P mincovna.gpr

# Spustit Primary Node
chmod +x start.sh
./start.sh
```

---

#### Phase 3: Network Configuration

**Zjistit IP adresy:**

Na i5 Ubuntu:
```bash
ip addr show
# Například: 192.168.1.100
```

Na i7 Windows:
```cmd
ipconfig
# Například: 192.168.1.50
```

**Upravit Shadow Node na i7:**

`src/shadow_node.py`:
```python
# Změnit z localhost na IP adresu i5
PRIMARY_URL = "http://192.168.1.100:9302/metrics"
```

**Firewall na i5 Ubuntu:**
```bash
sudo ufw allow 9302/tcp
sudo ufw allow 9303/tcp
sudo ufw enable
```

**Firewall na i7 Windows:**
```cmd
netsh advfirewall firewall add rule name="Mincovna Shadow" dir=in action=allow protocol=TCP localport=9303
```

---

#### Phase 4: Production Run

**i5 Ubuntu (Primary Node):**
```bash
cd ~/vakuova-mincovna

# Spustit jako systemd service (běží 24/7)
sudo nano /etc/systemd/system/mincovna-primary.service
```

```ini
[Unit]
Description=Vakuova Mincovna Primary Node
After=network.target

[Service]
Type=simple
User=pan_jeskyne
WorkingDirectory=/home/pan_jeskyne/vakuova-mincovna
ExecStart=/usr/bin/python3 /home/pan_jeskyne/vakuova-mincovna/src/faucet_bridge.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable mincovna-primary
sudo systemctl start mincovna-primary
sudo systemctl status mincovna-primary
```

**i7 Windows (Shadow Node):**
```cmd
REM Spustit když počítač není používán na hraní
cd c:\Users\pan_jeskyne\Favorites\vakuova-mincovna
start_shadow.bat
```

NEBO vytvořit Windows Service (automatický start):
```cmd
REM TODO: Vytvoř pomocí NSSM (Non-Sucking Service Manager)
```

---

## 📊 Resource Allocation

### i5 ESPRIMO (Primary Node)

**CPU Usage:**
- Ada/SPARK Core: ~5% (lehká matematika)
- Faucet Bridge: ~2% (Python HTTP server)
- Prometheus scraping: ~1%
- Watchdog (light mode): ~10%
- Privacy Protocol: ~2%
- **Celkem: ~20% CPU (4-5 vláken ze 12)**

**RAM Usage:**
- Ada/SPARK: ~50 MB
- Python Bridge: ~100 MB
- Prometheus: ~200 MB
- Watchdog: ~150 MB
- Privacy: ~100 MB
- **Celkem: ~600 MB ze 8 GB = OK!**

**Storage:**
- Projekt: ~500 MB
- Logs: ~1 GB/měsíc
- **Celkem: 256 GB SSD = dost místa**

---

### i7 "asterisk" (Shadow Node + Heavy Tasks)

**CPU Usage:**
- Shadow Node: ~2% (monitoring only)
- Apache Spark (když běží): ~50-80% (6-10 jader)
- Vertex AI inference: ~30-50%
- **Gaming má prioritu → můžeš Shadow vypnout**

**RAM Usage:**
- Shadow Node: ~100 MB
- Apache Spark: ~10-15 GB
- Vertex AI: ~5-8 GB
- **Gaming: zbytek (15-20 GB free)**

**GPU Usage:**
- RTX 3070 pro AI/ML inference
- Real-time dubbing processing
- Gaming má prioritu

---

## 🔐 Security Considerations

### i5 Ubuntu (Primary)
```bash
# Pouze potřebné porty
sudo ufw allow 9302/tcp  # Primary Node
sudo ufw allow ssh       # Remote access
sudo ufw enable

# Žádný X11, jen CLI server
# Minimální attack surface
```

### i7 Windows (Shadow)
```cmd
REM Gaming PC = více software = více rizik
REM → Proto je Shadow, ne Primary!
REM Watchdog může běžet na i7 s RTX (rychlejší scan)
```

---

## 🌐 Network Topology

```
Internet
    │
    ├──► Router (192.168.1.1)
    │
    ├──► i5 ESPRIMO (192.168.1.100)
    │    ├─ :9302 (Primary Node)
    │    ├─ :9090 (Prometheus)
    │    └─ :22   (SSH)
    │
    └──► i7 asterisk (192.168.1.50)
         ├─ :9303 (Shadow Node)
         ├─ :3000 (Grafana)
         └─ :9304 (Watchdog - volitelné)
```

**Latence:**
- Lokální síť: ~1-5 ms
- Sync každých 5s → latence není problém
- Failover timeout 15s → dostatečně rychlé

---

## ⚡ Power Management

### i5 ESPRIMO (Always On)
```
Spotřeba:
- Idle:       ~15W (i5-10500T = 35W TDP)
- Load:       ~35W
- 24h:        ~0.36 kWh/den
- Měsíčně:    ~10.8 kWh
- Ročně:      ~130 kWh

Náklady (6 Kč/kWh):
- Měsíčně:    ~65 Kč
- Ročně:      ~780 Kč
```

### i7 asterisk (On Demand)
```
Spotřeba:
- Idle:       ~50W
- Shadow:     ~80W
- Heavy:      ~250W
- Gaming:     ~400W (PC + monitor + RTX)

→ Zapínej jen když potřebuješ heavy computation
→ Při gamingu vypni Shadow
```

---

## 🧪 Test Scenarios

### Scenario 1: Normal Operation
```
i5 Primary:  ✅ RUNNING (24/7)
i7 Shadow:   ✅ RUNNING (monitoring)

Result: shadow_is_primary = 0
```

### Scenario 2: Gaming Time
```
i5 Primary:  ✅ RUNNING
i7 Shadow:   ⏸️  STOPPED (vypnutý pro gaming)

Result: Primary běží normálně, Shadow nedostupný
```

### Scenario 3: i5 Outage (elektřina/network)
```
i5 Primary:  ❌ DOWN
i7 Shadow:   🚨 FAILOVER → becomes Primary!

Result: shadow_is_primary = 1
```

### Scenario 4: i5 Recovery
```
i5 Primary:  ✅ BACK ONLINE
i7 Shadow:   🔄 DEMOTE → back to Shadow

Result: shadow_is_primary = 0
```

---

## 📋 Deployment Checklist

### i7 Windows (TEĎKA)
- [x] Opravit mcp.json
- [x] Vytvořit faucet_bridge.py
- [x] Vytvořit start_shadow.bat
- [x] Dokumentace
- [ ] **Otestovat lokálně (Primary + Shadow)**
- [ ] **Test failover**
- [ ] **Package pro Ubuntu**

### i5 Ubuntu (PŘÍŠTĚ)
- [ ] Přenést package
- [ ] Install GNAT/SPARK (volitelné)
- [ ] Install Python + dependencies
- [ ] Build Ada/SPARK Core
- [ ] Test Primary Node
- [ ] Konfigurace firewall
- [ ] Zjistit IP adresu
- [ ] Vytvořit systemd service

### Network (PŘÍŠTĚ)
- [ ] Upravit Shadow na i7 (použít IP adresu i5)
- [ ] Test cross-machine sync
- [ ] Test failover přes síť
- [ ] Test recovery

---

## 🎯 Příští Kroky (Priority)

### 1️⃣ URGENT: Test na i7 Windows (TEĎ!)
```cmd
cd c:\Users\pan_jeskyne\Favorites\vakuova-mincovna

REM Terminal 1:
start.bat

REM Terminal 2:
start_shadow.bat
```

### 2️⃣ HIGH: Package pro transfer
```cmd
package.bat
```

### 3️⃣ MEDIUM: Setup i5 Ubuntu
```bash
# Podle DEPLOY_UBUNTU.md
```

### 4️⃣ LOW: Optimization
- Prometheus federation
- Grafana dashboards
- Alert management

---

## 💡 Pro Tip: Hybrid Mode

**Když hraješ na i7:**
```
1. Ukončit Shadow Node (Ctrl+C)
2. Hrát
3. Po hraní spustit Shadow znovu
4. Shadow se automaticky resyncuje s Primary
```

**Primary na i5 běží pořád** → žádné downtime!

---

## 🔮 Budoucí Rozšíření

### Phase 5: Apache Spark Cluster
```
i5 Primary:   Spark Worker 1 (light)
i7 Shadow:    Spark Master + Worker 2 (heavy)
```

### Phase 6: Vertex AI Integration
```
i7 RTX 3070:  Real-time dubbing inference
              Tartanskomunikátor processing
```

### Phase 7: Třetí Node? (volitelné)
```
Raspberry Pi 5:  Third Shadow (ultra low power)
                 Běží 24/7 (~5W)
```

---

## 📞 Support

**Autor:** Pan Jeskyně  
**Asistent:** Kiro (Claude Sonnet 4.5)  
**Projekt:** Vakuová Mincovna (Web4 Article #1)  
**Standard:** 700 (12g stříbra)

---

## ✅ ZÁVĚR

**DOPORUČENÁ KONFIGURACE:**

```
✅ i5 FUJITSU ESPRIMO (Ubuntu 26.04)
   → PRIMARY NODE (běží 24/7)
   → Nízká spotřeba (~65 Kč/měsíc)
   → Stabilní, čistý systém

✅ i7 "asterisk" (Windows 11)
   → SHADOW NODE (on-demand)
   → RTX 3070 pro heavy tasks
   → Gaming má prioritu
   → Můžeš vypnout kdykoliv
```

**První krok:** Otestuj na i7 Windows lokálně → `start.bat` + `start_shadow.bat`

🏗️✨
