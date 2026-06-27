# 💾 Vakuová Mincovna - NAS Integration

## Hardware Setup

### WD MyCloud EX2 Ultra
```
Model:         Western Digital MyCloud EX2 Ultra
Storage:       3 TB RAID 1 (mirrored redundance)
IP Address:    192.168.123.121
Network:       Gigabit Ethernet
Power:         ~10W (ultra low consumption)
Protocols:     SMB, NFS, FTP, WebDAV
Web UI:        http://192.168.123.121
```

---

## 🎯 Využití NAS v Mincovně

### 1. Centralizované Úložiště
```
MyCloud EX2 Ultra (192.168.123.121)
    │
    ├─► /Mincovna/
    │   ├─ logs/           # Logy z Primary + Shadow
    │   ├─ backups/        # Automatické zálohy
    │   ├─ prometheus/     # Prometheus data
    │   ├─ grafana/        # Grafana dashboards
    │   └─ metadata/       # Metadata před purgem
    │
    └─► /Shared/
        └─ transfer/       # Transfer mezi počítači
```

---

## 🔧 Připojení NAS

### i7 Windows (asterisk)

**Mount přes SMB:**
```cmd
REM Mapovat NAS jako síťový disk (např. Z:)
net use Z: \\192.168.123.121\Mincovna /user:admin /persistent:yes

REM Nebo v Průzkumníku:
REM Tento počítač → Připojit síťovou jednotku
REM \\192.168.123.121\Mincovna
```

**Automatický mount při startu:**
```cmd
REM Vytvořit .bat script:
echo net use Z: \\192.168.123.121\Mincovna /user:admin > mount_nas.bat

REM Přidat do Startup:
copy mount_nas.bat "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\"
```

---

### i5 Ubuntu (FUJITSU)

**Mount přes NFS (rychlejší než SMB):**
```bash
# Install NFS client
sudo apt install nfs-common

# Vytvořit mount point
sudo mkdir -p /mnt/nas

# Mount NAS
sudo mount -t nfs 192.168.123.121:/nfs/Mincovna /mnt/nas

# Test
ls -la /mnt/nas
```

**Automatický mount při bootu:**
```bash
# Editovat /etc/fstab
sudo nano /etc/fstab

# Přidat řádek:
192.168.123.121:/nfs/Mincovna /mnt/nas nfs defaults,_netdev 0 0

# Test mount
sudo mount -a
```

---

## 📝 Centralizované Logování

### Upravit faucet_bridge.py pro NAS logging

**Přidat do `src/faucet_bridge.py`:**
```python
import logging
from logging.handlers import RotatingFileHandler
import os

# NAS log path (Windows)
NAS_LOG_PATH_WIN = "Z:/logs/primary_node.log"

# NAS log path (Linux)
NAS_LOG_PATH_LINUX = "/mnt/nas/logs/primary_node.log"

# Auto-detect OS
if os.name == 'nt':  # Windows
    LOG_PATH = NAS_LOG_PATH_WIN
else:  # Linux
    LOG_PATH = NAS_LOG_PATH_LINUX

# Setup logging
logger = logging.getLogger('Mincovna')
handler = RotatingFileHandler(
    LOG_PATH,
    maxBytes=10*1024*1024,  # 10 MB
    backupCount=5
)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Log místo print
logger.info("[PRIMARY] Inicializace dokončena")
```

---

### Shadow Node logging na NAS

**Upravit `src/shadow_node.py`:**
```python
# Windows: Z:/logs/shadow_node.log
# Linux:   /mnt/nas/logs/shadow_node.log

logger.info("[SHADOW] Sync OK: 45 mincí")
```

---

## 💾 Automatické Backups na NAS

### Backup script (Windows)

**Soubor:** `backup_to_nas.bat`
```cmd
@echo off
REM Backup Vakuové Mincovny na NAS

set SOURCE=c:\Users\pan_jeskyne\Favorites\vakuova-mincovna
set NAS=Z:\backups
set TIMESTAMP=%date:~-4,4%%date:~-7,2%%date:~-10,2%_%time:~0,2%%time:~3,2%
set BACKUP=%NAS%\mincovna_backup_%TIMESTAMP%

echo [BACKUP] Vytvářím zálohu na NAS...
echo [BACKUP] Zdroj: %SOURCE%
echo [BACKUP] Cíl: %BACKUP%

REM Vytvořit backup složku
mkdir "%BACKUP%"

REM Zkopírovat soubory
xcopy "%SOURCE%\src" "%BACKUP%\src\" /E /I /Y
xcopy "%SOURCE%\*.bat" "%BACKUP%\" /Y
xcopy "%SOURCE%\*.sh" "%BACKUP%\" /Y
xcopy "%SOURCE%\*.md" "%BACKUP%\" /Y
xcopy "%SOURCE%\*.gpr" "%BACKUP%\" /Y
xcopy "%SOURCE%\prometheus" "%BACKUP%\prometheus\" /E /I /Y

echo [BACKUP] Hotovo!
echo [BACKUP] Záloha: %BACKUP%

REM Smazat backupy starší než 30 dní
forfiles /p "%NAS%" /m mincovna_backup_* /d -30 /c "cmd /c rmdir /s /q @path"

pause
```

---

### Backup script (Linux)

**Soubor:** `backup_to_nas.sh`
```bash
#!/bin/bash
# Backup Vakuové Mincovny na NAS

SOURCE=~/vakuova-mincovna
NAS=/mnt/nas/backups
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP=$NAS/mincovna_backup_$TIMESTAMP

echo "[BACKUP] Vytvářím zálohu na NAS..."
echo "[BACKUP] Zdroj: $SOURCE"
echo "[BACKUP] Cíl: $BACKUP"

# Vytvořit backup složku
mkdir -p "$BACKUP"

# Zkopírovat soubory
rsync -av --exclude='obj' --exclude='*.o' \
    "$SOURCE/" "$BACKUP/"

echo "[BACKUP] Hotovo!"
echo "[BACKUP] Záloha: $BACKUP"

# Smazat backupy starší než 30 dní
find "$NAS" -name "mincovna_backup_*" -type d -mtime +30 -exec rm -rf {} \;
```

---

### Automatické backupy

**Windows - Task Scheduler:**
```cmd
REM Spustit každý den ve 2:00
schtasks /create /tn "Mincovna Backup" /tr "c:\Users\pan_jeskyne\Favorites\vakuova-mincovna\backup_to_nas.bat" /sc daily /st 02:00
```

**Linux - Cron:**
```bash
# Editovat crontab
crontab -e

# Přidat řádek (backup každý den ve 2:00)
0 2 * * * /home/pan_jeskyne/vakuova-mincovna/backup_to_nas.sh
```

---

## 📊 Prometheus Data na NAS

### Konfigurace Prometheus pro NAS storage

**Upravit `prometheus/prometheus.yml`:**
```yaml
global:
  scrape_interval: 15s

# Storage na NAS (větší kapacita)
storage:
  tsdb:
    path: /mnt/nas/prometheus/data  # Linux
    # NEBO
    # Z:\prometheus\data             # Windows
    retention.time: 90d              # 3 měsíce dat
    retention.size: 50GB             # Max 50 GB
```

**Spustit Prometheus s NAS storage:**
```bash
# Linux
prometheus \
  --config.file=/home/pan_jeskyne/vakuova-mincovna/prometheus/prometheus.yml \
  --storage.tsdb.path=/mnt/nas/prometheus/data \
  --storage.tsdb.retention.time=90d

# Windows
prometheus.exe ^
  --config.file=c:\Users\pan_jeskyne\Favorites\vakuova-mincovna\prometheus\prometheus.yml ^
  --storage.tsdb.path=Z:\prometheus\data ^
  --storage.tsdb.retention.time=90d
```

---

## 🔒 Privacy Protocol 4:23 - NAS Archive

### Před purgem → archivovat na NAS

**Upravit `src/privacy_purge_423.py`:**
```python
import shutil
from datetime import datetime

NAS_ARCHIVE_PATH_WIN = "Z:/metadata/archive"
NAS_ARCHIVE_PATH_LINUX = "/mnt/nas/metadata/archive"

def archive_before_purge(metadata):
    """
    Archivovat metadata na NAS před purgem
    """
    # Auto-detect OS
    if os.name == 'nt':
        archive_path = NAS_ARCHIVE_PATH_WIN
    else:
        archive_path = NAS_ARCHIVE_PATH_LINUX
    
    # Timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_file = f"{archive_path}/metadata_{timestamp}.json"
    
    # Vytvořit složku pokud neexistuje
    os.makedirs(archive_path, exist_ok=True)
    
    # Uložit metadata
    with open(archive_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"[PRIVACY] Metadata archivována: {archive_file}")
    
    # Po 90 dnech smazat z NAS (GDPR compliance)
    cleanup_old_archives(archive_path, days=90)

def cleanup_old_archives(path, days=90):
    """
    Smazat archivy starší než X dní
    """
    import time
    now = time.time()
    cutoff = now - (days * 86400)
    
    for filename in os.listdir(path):
        filepath = os.path.join(path, filename)
        if os.path.getmtime(filepath) < cutoff:
            os.remove(filepath)
            print(f"[PRIVACY] Starý archiv smazán: {filename}")
```

---

## 🌐 Web UI na NAS

### MyCloud Dashboard

**Přístup:**
```
http://192.168.123.121
```

**Můžeš vytvořit:**
1. `/Mincovna/` share - pro projekt
2. `/Logs/` share - pro logy (read-only pro viewing)
3. `/Backups/` share - automatické zálohy
4. `/Prometheus/` share - Prometheus data

---

## 📈 Grafana Dashboard na NAS

### Option 1: Grafana na i7 (Windows)

**Dashboard configuration stored on NAS:**
```
Z:\grafana\dashboards\mincovna_dashboard.json
```

---

### Option 2: Grafana v Dockeru na NAS

**Pokud MyCloud podporuje Docker:**
```bash
# SSH na NAS
ssh admin@192.168.123.121

# Spustit Grafana container
docker run -d \
  --name=grafana \
  -p 3000:3000 \
  -v /shares/Mincovna/grafana:/var/lib/grafana \
  grafana/grafana
```

**Přístup:**
```
http://192.168.123.121:3000
```

---

## 🔄 Synchronizace přes NAS

### Transfer mezi i7 a i5

**Na i7 Windows:**
```cmd
REM Vytvořit package
package.bat

REM Zkopírovat na NAS
copy vakuova-mincovna-package.zip Z:\transfer\
```

**Na i5 Ubuntu:**
```bash
# Mount NAS
sudo mount -t nfs 192.168.123.121:/nfs/Mincovna /mnt/nas

# Zkopírovat z NAS
cp /mnt/nas/transfer/vakuova-mincovna-package.zip ~/
unzip vakuova-mincovna-package.zip
```

---

## 💡 NAS Výhody

### 1. Centralizované úložiště
```
✅ Všechny logy na jednom místě
✅ i7 + i5 ukládají na stejné NAS
✅ Snadný přístup z obou počítačů
```

### 2. Redundance (RAID 1)
```
✅ 3 TB mirrored → data jsou duplicitní
✅ Pokud jeden disk spadne → druhý funguje
✅ Bezpečnost dat
```

### 3. Nízká spotřeba
```
✅ ~10W power consumption
✅ Může běžet 24/7
✅ ~0.24 kWh/den = ~7 kWh/měsíc = ~42 Kč/měsíc
```

### 4. Backup automatizace
```
✅ Scheduled backups každý den
✅ Retention policy (30 dní)
✅ Žádná ruční práce
```

---

## 🏗️ Architektura s NAS

```
┌──────────────────────────────────────────────────────────┐
│                    NETWORK TOPOLOGY                       │
└──────────────────────────────────────────────────────────┘

┌─────────────┐          ┌──────────────┐          ┌─────────────┐
│ i5 FUJITSU  │          │  WD MyCloud  │          │ i7 asterisk │
│ Ubuntu      │          │  EX2 Ultra   │          │ Windows     │
│ PRIMARY     │◄────────►│  3TB RAID    │◄────────►│ SHADOW      │
│ :9302       │          │ 192.168...21 │          │ :9303       │
└─────────────┘          └──────────────┘          └─────────────┘
      │                         │                         │
      │                         │                         │
      └─────── LOGS ────────────┤                         │
                                │                         │
                      ┌─────────┴─────────┐               │
                      │  NAS Storage:     │               │
                      │                   │               │
                      │  • Logs           │               │
                      │  • Backups        │───────────────┘
                      │  • Prometheus     │
                      │  • Grafana        │
                      │  • Metadata       │
                      │  • Transfer       │
                      └───────────────────┘
```

---

## 📁 NAS Folder Structure

```
MyCloud EX2 Ultra (192.168.123.121)
│
└─ /Mincovna/
   │
   ├─ logs/
   │  ├─ primary_node.log         # i5 Primary logs
   │  ├─ shadow_node.log          # i7 Shadow logs
   │  ├─ watchdog.log             # Security logs
   │  └─ privacy_protocol.log     # Privacy logs
   │
   ├─ backups/
   │  ├─ mincovna_backup_20260613_020000/
   │  ├─ mincovna_backup_20260614_020000/
   │  └─ ... (30 days retention)
   │
   ├─ prometheus/
   │  ├─ data/                    # Prometheus TSDB
   │  └─ snapshots/
   │
   ├─ grafana/
   │  ├─ dashboards/
   │  │  └─ mincovna_dashboard.json
   │  └─ datasources/
   │
   ├─ metadata/
   │  ├─ archive/                 # Pre-purge archives
   │  │  ├─ metadata_20260613_042300.json
   │  │  └─ ... (90 days then deleted)
   │  └─ current/
   │
   └─ transfer/
      ├─ vakuova-mincovna-package.zip
      └─ updates/
```

---

## 🚀 Quick Start s NAS

### 1. Připoj NAS (Windows)
```cmd
net use Z: \\192.168.123.121\Mincovna /user:admin
```

### 2. Vytvoř strukturu
```cmd
mkdir Z:\logs
mkdir Z:\backups
mkdir Z:\prometheus
mkdir Z:\grafana
mkdir Z:\metadata
mkdir Z:\transfer
```

### 3. Test zápisu
```cmd
echo test > Z:\logs\test.txt
type Z:\logs\test.txt
```

### 4. Spusť Mincovnu
```cmd
start.bat
start_shadow.bat
```

Logy automaticky jdou na NAS! ✅

---

**NAS IP:** `192.168.123.121` (MyCloud EX2 Ultra)  
**Storage:** 3 TB RAID 1 (mirrored)  
**Power:** ~10W (~42 Kč/měsíc)  
**Standard 700:** 12g stříbra = 1 mince

💾✨
