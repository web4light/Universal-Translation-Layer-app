# 🌑 Shadow Node na Windows

## Rychlý start

### 1. Spusť PRIMARY Node (v jednom terminálu)
```cmd
cd c:\Users\pan_jeskyne\Favorites\vakuova-mincovna
start.bat
```

Uvidíš:
```
=== VAKUOVÁ MINCOVNA - FAUCET BRIDGE ===
[BRIDGE] Prometheus server běží na portu 9302
[BRIDGE] Metriky: http://localhost:9302/metrics
```

### 2. Spusť SHADOW Node (v druhém terminálu)
```cmd
cd c:\Users\pan_jeskyne\Favorites\vakuova-mincovna
start_shadow.bat
```

Uvidíš:
```
🌑 SHADOW NODE - STÍNOVACÍ UZEL
[SHADOW] Prometheus endpoint: http://localhost:9303/metrics
[SHADOW] Monitoring Primary: http://localhost:9302/metrics
[SHADOW] Režim: MONITORING
```

---

## ✅ Kontrola že oba uzly běží

### Otevři prohlížeč a zkontroluj:

**Primary Node metriky:**
```
http://localhost:9302/metrics
```

Měl bys vidět:
```
# Vakuová Mincovna - Primary Node
mincovna_minted_coins_total 0.0
mincovna_total_silver_grams 0.0
mincovna_system_health 1.0
```

**Shadow Node metriky:**
```
http://localhost:9303/metrics
```

Měl bys vidět:
```
# Shadow Node metriky
shadow_is_primary 0.0
shadow_primary_health 1.0
shadow_synced_coins 0.0
shadow_synced_silver_grams 0.0
```

---

## 🧪 Testování FAILOVER

### Test 1: Automatický failover

1. **Spusť oba uzly** (Primary + Shadow)

2. **V terminálu s Primary Node stiskni `Ctrl+C`** (ukončí Primary)

3. **Sleduj Shadow Node terminál:**
```
[SHADOW] ⚠️  Primary Node timeout: 15.2s
============================================================
🚨 FAILOVER EVENT - SHADOW NODE PŘEBÍRÁ KONTROLU! 🚨
============================================================
[SHADOW→PRIMARY] Status změněn na PRIMARY
[SHADOW→PRIMARY] Systém pokračuje bez přerušení!
```

4. **Zkontroluj metriky Shadow Node:**
```
http://localhost:9303/metrics
```

Teď uvidíš:
```
shadow_is_primary 1.0    ← ZMĚNILO SE Z 0 NA 1!
shadow_primary_health 0.0
```

### Test 2: Primary se vrátil

1. **Znovu spusť Primary Node** (`start.bat`)

2. **Sleduj Shadow Node terminál:**
```
============================================================
🔄 PRIMARY NODE SE VRÁTIL - Vracím se do Shadow módu
============================================================
[PRIMARY→SHADOW] Kontrola předána zpět Primary Node
[PRIMARY→SHADOW] Obnovuji synchronizaci...
```

3. **Zkontroluj metriky Shadow Node:**
```
http://localhost:9303/metrics
```

Teď uvidíš:
```
shadow_is_primary 0.0    ← VRÁTILO SE NA 0!
shadow_primary_health 1.0
```

---

## 📊 Sledování obou uzlů v Prometheus

### Konfigurace Prometheus pro oba uzly

Edituj `prometheus\prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  external_labels:
    cluster: 'mincovna'

scrape_configs:
  # PRIMARY NODE
  - job_name: 'mincovna-primary'
    static_configs:
      - targets: ['localhost:9302']
        labels:
          node: 'primary'
  
  # SHADOW NODE
  - job_name: 'mincovna-shadow'
    static_configs:
      - targets: ['localhost:9303']
        labels:
          node: 'shadow'
```

### Spusť Prometheus

```cmd
cd c:\Users\pan_jeskyne\Favorites\vakuova-mincovna\prometheus
prometheus --config.file=prometheus.yml
```

Otevři Prometheus UI:
```
http://localhost:9090
```

### Užitečné Prometheus queries

**Který uzel je Primary?**
```promql
shadow_is_primary
```
- 0 = Shadow Node je v shadow módu
- 1 = Shadow Node převzal kontrolu (failover)

**Zdraví Primary Node z pohledu Shadow:**
```promql
shadow_primary_health
```
- 1 = Primary žije
- 0 = Primary je nedostupný

**Synchronizované mince:**
```promql
shadow_synced_coins
```

**Chyby synchronizace:**
```promql
rate(shadow_sync_errors_total[1m])
```

---

## 🚀 Nasazení na druhý počítač (Ubuntu 26.06)

### Příprava na Windows

1. **Vytvoř deployment balíček:**
```cmd
cd c:\Users\pan_jeskyne\Favorites\vakuova-mincovna
package.bat
```

To vytvoří `vakuova-mincovna-YYYYMMDD-HHMMSS.zip`

2. **Přenést na Ubuntu:**
- USB flash disk
- Sdílená složka
- SCP/SFTP
- Cloud (OneDrive, Google Drive)

### Instalace na Ubuntu

1. **Rozbalení:**
```bash
cd ~
unzip vakuova-mincovna-*.zip
cd vakuova-mincovna
```

2. **Instalace závislostí:**
```bash
# Python
sudo apt install python3 python3-pip

# Prometheus client
pip3 install prometheus_client requests
```

3. **Spuštění Shadow Node:**
```bash
chmod +x start_shadow.sh
./start_shadow.sh
```

4. **Nastavení IP adresy Primary Node:**

Pokud Primary běží na jiném počítači, změň v `shadow_node.py`:

```python
# Místo:
PRIMARY_URL = "http://localhost:9302/metrics"

# Použij IP Windows počítače:
PRIMARY_URL = "http://192.168.1.100:9302/metrics"
```

---

## 🔥 Pokročilé scénáře

### Scénář 1: Shadow běží na jiném počítači (síťové)

**Na Windows (Primary):**
1. Otevři firewall pro port 9302:
```cmd
netsh advfirewall firewall add rule name="Mincovna Primary" dir=in action=allow protocol=TCP localport=9302
```

**Na Ubuntu (Shadow):**
1. Zjisti IP Windows počítače (např. `192.168.1.100`)
2. Edituj `src/shadow_node.py`:
```python
PRIMARY_URL = "http://192.168.1.100:9302/metrics"
```
3. Spusť Shadow Node:
```bash
./start_shadow.sh
```

### Scénář 2: Dva uzly na Ubuntu 26.06

```bash
# Terminál 1: Primary
cd ~/vakuova-mincovna-primary
./start.sh

# Terminál 2: Shadow  
cd ~/vakuova-mincovna-shadow
./start_shadow.sh
```

### Scénář 3: Automatický start při boot (Ubuntu)

1. **Vytvoř systemd service:**

`/etc/systemd/system/mincovna-shadow.service`:
```ini
[Unit]
Description=Vakuová Mincovna - Shadow Node
After=network.target

[Service]
Type=simple
User=pan_jeskyne
WorkingDirectory=/home/pan_jeskyne/vakuova-mincovna
ExecStart=/usr/bin/python3 /home/pan_jeskyne/vakuova-mincovna/src/shadow_node.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

2. **Enable a start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable mincovna-shadow
sudo systemctl start mincovna-shadow
```

3. **Kontrola stavu:**
```bash
sudo systemctl status mincovna-shadow
```

---

## 📋 Checklist pro produkční nasazení

### Windows (Primary Node)
- [ ] Start.bat běží a Primary je na portu 9302
- [ ] Firewall povoluje port 9302 (pokud Shadow je na jiném PC)
- [ ] Prometheus sbírá metriky z Primary
- [ ] Metriky jsou dostupné na `http://localhost:9302/metrics`

### Ubuntu (Shadow Node)
- [ ] Shadow Node běží na portu 9303
- [ ] Může se připojit k Primary (zkontroluj `shadow_primary_health`)
- [ ] Synchronizace funguje (zkontroluj `shadow_last_sync_timestamp`)
- [ ] Metriky jsou dostupné na `http://localhost:9303/metrics`

### Testování
- [ ] Failover test: Vypni Primary → Shadow převezme kontrolu
- [ ] Recovery test: Zapni Primary → Shadow vrátí kontrolu
- [ ] Network test: Odpoj síť → Shadow detekuje timeout

---

## 🎯 Očekávané chování

### Normální provoz
```
[Primary]  9302 ─┐
                  ├──> metriky
[Shadow]   9303 ─┘
                  └──> shadow_is_primary = 0
```

### Po failover
```
[Primary]  OFFLINE
[Shadow]   9303 ──> shadow_is_primary = 1 (PŘEVZAL KONTROLU)
```

### Po recovery
```
[Primary]  9302 ─┐ (VRÁTIL SE)
                  ├──> metriky
[Shadow]   9303 ─┘ shadow_is_primary = 0 (VRÁTIL KONTROLU)
```

---

## 🛠️ Troubleshooting

### Problem: Shadow Node hlásí "Primary Node neodpovídá"
**Řešení:**
1. Zkontroluj že Primary běží: `http://localhost:9302/metrics`
2. Zkontroluj firewall (pokud síťové)
3. Zkontroluj IP adresu v `PRIMARY_URL`

### Problem: Shadow se nepřepne na Primary při failover
**Řešení:**
1. Zkontroluj timeout: `FAILOVER_TIMEOUT = 15` (15 sekund)
2. Zvyš timeout pokud síť je pomalá
3. Sleduj log Shadow Node

### Problem: Port 9303 je obsazený
**Řešení:**
```cmd
REM Windows - zjisti co běží na portu
netstat -ano | findstr :9303

REM Ukonči proces s PID (např. 1234)
taskkill /PID 1234 /F
```

```bash
# Ubuntu - zjisti co běží na portu
sudo lsof -i :9303

# Ukonči proces
kill -9 <PID>
```

---

## 🎉 Výsledek

Máš funkční **high availability** systém:

✅ **Primary Node** (Windows) - razí mince  
✅ **Shadow Node** (Ubuntu/Windows) - záloha  
✅ **Automatický failover** - bez přerušení  
✅ **Synchronizace** - v reálném čase  
✅ **Prometheus monitoring** - vidíš vše  

**První článek** je teď neprůstřelný! 🏗️🌑

---

**Příští kroky:**
1. Nasadit Shadow na Ubuntu 26.06
2. Otestovat failover v produkci
3. Přidat Grafana dashboard pro vizualizaci obou uzlů
4. Nastavit alerty pro failover events
