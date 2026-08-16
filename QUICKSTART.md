# 🚀 Vakuová Mincovna - Quickstart Guide

## Rychlý start (Windows)

### 1. Instaluj dependencies

```cmd
pip install prometheus_client requests psutil schedule
```

### 2. Spusť všechny komponenty

```cmd
REM Terminal 1: Shadow Node
start_shadow.bat

REM Terminal 2: Watchdog (Security)
start_watchdog.bat

REM Terminal 3: Privacy Protocol
start_privacy.bat
```

### 3. Kontroluj metriky

- Shadow Node: http://localhost:9303/metrics
- Watchdog: http://localhost:9304/metrics
- Privacy: http://localhost:9305/metrics

---

## Rychlý start (Linux/Ubuntu)

### 1. Instaluj dependencies

```bash
pip3 install prometheus_client requests psutil schedule
```

### 2. Spusť všechny komponenty

```bash
# Terminal 1: Shadow Node
./start_shadow.sh

# Terminal 2: Watchdog (Security)
./start_watchdog.sh

# Terminal 3: Privacy Protocol
./start_privacy.sh
```

### 3. Kontroluj metriky

```bash
curl http://localhost:9303/metrics  # Shadow
curl http://localhost:9304/metrics  # Watchdog
curl http://localhost:9305/metrics  # Privacy
```

---

## 🧪 Testing

### Test Shadow Node failover

```bash
# Spusť Shadow Node
python src/shadow_node.py

# Pozoruj:
# [SHADOW] Primary Node neodpovídá
# [SHADOW] ⚠️ Primary Node timeout: 17.1s
# 🚨 FAILOVER EVENT
# [SHADOW→PRIMARY] Status změněn na PRIMARY
```

### Test Watchdog scan

```bash
# Jednorázový scan
python src/spark_watchdog.py --once

# Výstup:
# 🔍 LEVEL 1: FILESYSTEM INTEGRITY SCAN
# 🔍 LEVEL 2: BINARY ANALYSIS
# 🔍 LEVEL 3: MEMORY FORENSICS
# 🔍 LEVEL 4: BEHAVIORAL ANALYSIS
# 🔍 LEVEL 5: STEGANOGRAPHY DETECTION
# 📊 SCAN SUMMARY
```

### Test Privacy purge

```bash
# Okamžitý purge
python src/privacy_purge_423.py --now

# Výstup:
# 🔐 PRIVACY PROTOCOL 4:23 - METADATA PURGE
# [PRIVACY] Purging temp files...
# [PRIVACY] Purging logs...
# [PRIVACY] ✓ Total deleted: 123.45 MB
```

---

## 📊 Prometheus Setup

### Vytvoř prometheus.yml

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'mincovna-shadow'
    static_configs:
      - targets: ['localhost:9303']
  
  - job_name: 'mincovna-watchdog'
    static_configs:
      - targets: ['localhost:9304']
  
  - job_name: 'mincovna-privacy'
    static_configs:
      - targets: ['localhost:9305']
```

### Spusť Prometheus

```bash
# Linux
./prometheus --config.file=prometheus.yml

# Windows
prometheus.exe --config.file=prometheus.yml
```

### Kontroluj web UI

http://localhost:9090

---

## 🔐 Security Checklist

```
[ ] Shadow Node běží a monitoruje Primary
[ ] Watchdog vytvořil baseline (watchdog_baseline.json)
[ ] Privacy daemon naplánován na 4:23
[ ] Prometheus scrape všechny metriky
[ ] Zero-cookie auth aktivní
[ ] E2E encryption (TLS 1.3)
```

---

## 📁 Důležité soubory

```
vakuova-mincovna/
├── src/
│   ├── mincovna.adb              # Ada/SPARK core
│   ├── shadow_node.py            # High availability
│   ├── spark_watchdog.py         # Security (Mossad ALF++)
│   └── privacy_purge_423.py      # Privacy (4:23 protocol)
│
├── start_shadow.bat/.sh          # Spustit Shadow Node
├── start_watchdog.bat/.sh        # Spustit Watchdog
├── start_privacy.bat/.sh         # Spustit Privacy
│
├── watchdog_baseline.json        # Security baseline (auto)
├── watchdog_threats_*.json       # Detected threats (auto)
│
└── prometheus/
    └── prometheus.yml            # Monitoring config
```

---

## 🎯 Další kroky

### 1. Deploy Shadow na Ubuntu

```bash
# Viz DEPLOY_UBUNTU.md
scp -r vakuova-mincovna/ user@ubuntu-pc:/opt/
ssh user@ubuntu-pc
cd /opt/vakuova-mincovna
./start_shadow.sh
```

### 2. Nastavit Grafana dashboards

- Shadow Node monitoring
- Watchdog threat detection
- Privacy purge tracking
- Failover events

### 3. Integrace s n8n

- Webhook pro threats
- Email notifications
- Automated responses

---

## 🆘 Troubleshooting

### Shadow Node nevidí Primary

```bash
# Kontroluj že Primary běží na 9302
curl http://localhost:9302/metrics

# Pokud ne, Primary není spuštěný
```

### Watchdog baseline chybí

```bash
# První scan vytvoří baseline automaticky
python src/spark_watchdog.py --once

# Baseline uložen jako watchdog_baseline.json
```

### Privacy daemon nefunguje

```bash
# Kontroluj dependencies
pip install schedule

# Test okamžitý purge
python src/privacy_purge_423.py --now
```

---

## 📞 Dokumentace

- **SYSTEM_OVERVIEW.md** - Komplexní přehled systému
- **SHADOW_NODE.md** - Shadow Node dokumentace
- **SECURITY_WATCHDOG.md** - Watchdog dokumentace
- **PRIVACY_PROTOCOL_423.md** - Privacy dokumentace
- **TESTING_GUIDE.md** - Testing guide
- **DEPLOY_UBUNTU.md** - Ubuntu deployment

---

## 🎉 Výsledek

Po provedení tohoto quickstartu máš:

✅ **Shadow Node** - automatický failover  
✅ **Watchdog** - 5-úrovňový security scan  
✅ **Privacy** - 4:23 metadata purge  
✅ **Prometheus** - real-time monitoring  
✅ **Zero cookies** - 100% privacy  

**První článek je připraven k nasazení!** 🏗️✨

---

**Start:** `start_shadow.bat` + `start_watchdog.bat` + `start_privacy.bat`  
**Monitor:** http://localhost:9303/metrics, :9304, :9305  
**Done!** 🚀
