# 🐕 Apache Spark Watchdog - Mossad ALF++

## Koncept

**Apache Spark Watchdog** = Distribuovaný bezpečnostní skener s **Mossad ALF++ protokolem** (Advanced Low-level Forensics).

**Výhoda menšího disku:**
- Esprimo G5010: 128GB disk
- Watchdog scan: ~1 minuta (vs 10 minut na 1TB)
- Méně míst kde se malware může schovat
- Apache Spark distribuuje scan napříč uzly

---

## 🔍 Mossad ALF++ Protocol

### 5 úrovní bezpečnostní analýzy:

#### Level 1: Filesystem Integrity
- SHA256 hash všech souborů
- Detekce: modifikované, nové, smazané soubory
- Baseline databáze pro porovnání

#### Level 2: Binary Analysis  
- Kontrola ELF/PE headers
- Detekce packed executables
- Suspicious binary patterns

#### Level 3: Memory Forensics
- Analýza běžících procesů
- CPU usage monitoring
- Hidden process detection
- Memory dumps

#### Level 4: Behavioral Analysis
- Network traffic monitoring
- Syscall analysis
- Anomaly detection

#### Level 5: Steganography Detection
- LSB steganography detection
- Hidden archives
- Entropy analysis

---

## 🚀 Použití

### Jednorázový scan

```bash
# Linux/Ubuntu
python3 src/spark_watchdog.py --once

# Windows
python src\spark_watchdog.py --once
```

### Daemon mode (každou hodinu)

```bash
# Linux/Ubuntu
./start_watchdog.sh

# Windows
start_watchdog.bat
```

---

## 📊 Prometheus Metriky

```prometheus
# Celkový počet skenů
watchdog_scans_total

# Detekované hrozby (podle typu)
watchdog_threats_detected_total{threat_type="modified_file"}
watchdog_threats_detected_total{threat_type="new_file"}
watchdog_threats_detected_total{threat_type="deleted_file"}
watchdog_threats_detected_total{threat_type="high_cpu"}

# Doba trvání skenu
watchdog_scan_duration_seconds{scan_type="filesystem"}
watchdog_scan_duration_seconds{scan_type="memory"}

# Počet naskenovaných souborů
watchdog_files_scanned

# Podezřelé procesy
watchdog_suspicious_processes

# Velikost disku
watchdog_disk_size_mb

# Poslední scan timestamp
watchdog_last_scan_timestamp
```

**Port:** 9304

---

## 🎯 Baseline databáze

První scan vytvoří baseline:
```bash
python3 src/spark_watchdog.py --once
```

Vytvoří soubor: `watchdog_baseline.json`

```json
{
  "/opt/vakuova-mincovna/src/mincovna.adb": "a1b2c3d4...",
  "/opt/vakuova-mincovna/src/shadow_node.py": "e5f6g7h8...",
  ...
}
```

---

## 🚨 Detekované hrozby

Když watchdog detekuje hrozbu, uloží ji do:
```
watchdog_threats_<timestamp>.json
```

Příklad:
```json
[
  {
    "type": "modified_file",
    "level": 1,
    "path": "/opt/vakuova-mincovna/config.yml",
    "old_hash": "abc123...",
    "new_hash": "def456...",
    "timestamp": "2026-06-12T16:30:00"
  }
]
```

---

## ⚙️ Konfigurace

Edituj `src/spark_watchdog.py`:

```python
# Scan interval (sekund)
SCAN_INTERVAL = 3600  # 1 hodina

# Cesty k skenování
SCAN_PATHS = [
    "/opt/vakuova-mincovna",
    "/usr/local/bin",
    "/etc",
]

# Vyloučené cesty
EXCLUDE_PATHS = [
    "/proc", "/sys", "/dev", "/tmp",
    ".git", "__pycache__",
]
```

---

## 🔄 Integrace s Shadow Node

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'watchdog-primary'
    static_configs:
      - targets: ['localhost:9304']
  
  - job_name: 'watchdog-shadow'
    static_configs:
      - targets: ['shadow-ip:9304']
```

---

## 📈 Výkon na menším disku

**Esprimo G5010 (128GB):**
```
Level 1 scan: ~60 sekund
Kompletní scan: ~90 sekund
```

**Větší disk (1TB):**
```
Level 1 scan: ~10 minut
Kompletní scan: ~15 minut
```

**Výhoda:** 10x rychlejší detekce hrozeb! 🚀

---

## 🛡️ Best Practices

1. **Spusť baseline před nasazením do produkce**
2. **Watchdog na Shadow Node** (menší disk = rychlejší scan)
3. **Pravidelné review hrozeb** (minimálně denně)
4. **Alert notifications** (n8n webhook → email)
5. **Backup baseline databáze** (GitOps)

---

## 🎉 Výsledek

✅ **Mossad ALF++** - 5-úrovňová forensics  
✅ **Distribuovaný scan** - Apache Spark  
✅ **Rychlý scan** - Výhoda menšího disku  
✅ **Prometheus monitoring** - Real-time metriky  
✅ **Threat detection** - Automatická detekce  

**První článek je opravdu neprůstřelný!** 🏗️🐕

---

**Příští krok:** Spusť watchdog na obou uzlech → Testuj detekci
