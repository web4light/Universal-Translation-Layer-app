# 🌐 Vakuová Mincovna - Network Configuration

## Síťová topologie

```
Internet (wireless)
    ↓
Router
    ↓
Rack (patch panel 24-port + Gigabit switch + UPS)
    ↓
Druhý switch (pracovní místnost / dolík)
    ├── asterisk  192.168.123.191  (i7, Windows, Ethernet) ← PRIMARY
    ├── Esprimo   192.168.123.169  (i5, Ubuntu, Ethernet)
    │             192.168.123.172  (i5, Ubuntu, WiFi AX200) ← SHADOW
    └── NAS       192.168.123.121  (WD MyCloud EX2 Ultra)
```

UPS v racku zajišťuje napájení při výpadku — Shadow Node failover funguje i bez proudu.

### i7 "asterisk" (Windows 11)
```
IP Address:  192.168.123.191
Hostname:    asterisk
OS:          Windows 11
Network:     Ethernet only (kabel → router)
Role:        PRIMARY NODE  ← stabilní, kabelové připojení
Ports:       9302 (Primary), 9090 (Prometheus)
```

### i5 FUJITSU ESPRIMO G5010 (Ubuntu)
```
IP Address:  192.168.123.172  (WiFi AX200 — rychlejší, použít pro Shadow)
             192.168.123.169  (Ethernet — pravděpodobně 100Mbit, pomalejší)
Hostname:    (TBD)
OS:          Ubuntu 26.06
Network:     Ethernet 100Mbit + WiFi Intel AX200 WiFi 6 + Bluetooth
Role:        SHADOW NODE
Ports:       9303 (Shadow), 9304 (Watchdog), 9305 (Privacy)
Note:        Shadow Node na .172 (WiFi AX200 rychlejší než Ethernet)
             Ověřit: ethtool eth0 | grep Speed
```

### WD MyCloud EX2 Ultra (NAS)
```
IP Address:  192.168.123.121
Network:     Gigabit Ethernet
Role:        Storage (logs, backups, prometheus data)
Ports:       SMB 445, NFS 2049, Web UI 80
```

---

## 🔧 Konfigurace Shadow Node

### Pro lokální test (oba na i7):
**Soubor:** `src/shadow_node.py`
```python
PRIMARY_URL = "http://localhost:9302/metrics"
```

### Pro produkci (i5 → i7 přes síť):
**Soubor:** `src/shadow_node.py`
```python
PRIMARY_URL = "http://192.168.123.121:9302/metrics"
```

**NEBO přes environment variable:**
```cmd
set PRIMARY_URL=http://192.168.123.121:9302/metrics
start_shadow.bat
```

---

## 🔥 Firewall konfigurace

### i5 Ubuntu (192.168.123.121)

```bash
# Povolit Primary Node port
sudo ufw allow 9302/tcp comment "Mincovna Primary Node"

# Povolit Prometheus (volitelné)
sudo ufw allow 9090/tcp comment "Prometheus"

# Povolit SSH pro remote management
sudo ufw allow ssh

# Aplikovat pravidla
sudo ufw enable

# Kontrola
sudo ufw status
```

**Výstup by měl být:**
```
Status: active

To                         Action      From
--                         ------      ----
9302/tcp                   ALLOW       Anywhere      # Mincovna Primary Node
9090/tcp                   ALLOW       Anywhere      # Prometheus
22/tcp                     ALLOW       Anywhere      # SSH
```

---

### i7 Windows (asterisk)

```cmd
REM Povolit Shadow Node port
netsh advfirewall firewall add rule name="Mincovna Shadow" dir=in action=allow protocol=TCP localport=9303

REM Povolit Grafana (volitelné)
netsh advfirewall firewall add rule name="Grafana" dir=in action=allow protocol=TCP localport=3000

REM Povolit Watchdog (volitelné)
netsh advfirewall firewall add rule name="Mincovna Watchdog" dir=in action=allow protocol=TCP localport=9304

REM Kontrola
netsh advfirewall firewall show rule name=all | findstr Mincovna
```

---

## 🧪 Network Test

### 1. Ping test z i7 (Windows) na i5 (Ubuntu)

```cmd
ping 192.168.123.121
```

**Očekávaný výsledek:**
```
Pinging 192.168.123.121 with 32 bytes of data:
Reply from 192.168.123.121: bytes=32 time=2ms TTL=64
Reply from 192.168.123.121: bytes=32 time=1ms TTL=64
```

---

### 2. Test Primary Node endpointu z i7

**Na i5 Ubuntu - spustit Primary Node:**
```bash
cd ~/vakuova-mincovna
./start.sh
```

**Na i7 Windows - test přístupu:**
```cmd
curl http://192.168.123.121:9302/metrics
```

**NEBO v prohlížeči:**
```
http://192.168.123.121:9302/metrics
```

**Očekávaný výsledek:**
```
# HELP mincovna_minted_coins_total Celkový počet vyražených mincí
# TYPE mincovna_minted_coins_total counter
mincovna_minted_coins_total 45.0
# HELP mincovna_total_silver_grams Celkové množství zpracovaného stříbra (gramy)
# TYPE mincovna_total_silver_grams gauge
mincovna_total_silver_grams 540.0
...
```

---

### 3. Test Shadow Node synchronizace

**Na i5 Ubuntu:**
```bash
./start.sh  # Primary běží
```

**Na i7 Windows - upravit Shadow:**
```cmd
cd c:\Users\pan_jeskyne\Favorites\vakuova-mincovna\src
notepad shadow_node.py
```

**Změnit řádek:**
```python
PRIMARY_URL = "http://192.168.123.121:9302/metrics"
```

**Spustit Shadow:**
```cmd
cd c:\Users\pan_jeskyne\Favorites\vakuova-mincovna
start_shadow.bat
```

**Očekávaný výstup:**
```
🌑 SHADOW NODE - STÍNOVACÍ UZEL
========================================
[SHADOW] Prometheus endpoint: http://localhost:9303/metrics
[SHADOW] Monitoring Primary: http://192.168.123.121:9302/metrics
[SHADOW] Heartbeat interval: 5s
[SHADOW] Failover timeout: 15s
...
[SHADOW] ✓ Sync OK: 45 mincí, 540.0g stříbra
```

---

## 📊 Monitoring URLs

### Z i7 Windows můžeš sledovat:

**Primary Node (i5 Ubuntu):**
```
http://192.168.123.121:9302/metrics
```

**Shadow Node (lokální i7):**
```
http://localhost:9303/metrics
```

**Prometheus (pokud na i5):**
```
http://192.168.123.121:9090
```

**Grafana (pokud na i7):**
```
http://localhost:3000
```

---

## 🔄 Deployment Scenarios

### Scenario 1: Local Test (oba na i7)
```
PRIMARY_URL = "http://localhost:9302/metrics"

i7 Terminal 1: start.bat
i7 Terminal 2: start_shadow.bat

→ Test před cross-machine deployment
```

---

### Scenario 2: Production (i5 Primary + i7 Shadow)
```
PRIMARY_URL = "http://192.168.123.121:9302/metrics"

i5 Ubuntu:     ./start.sh        (Primary běží 24/7)
i7 Windows:    start_shadow.bat  (Shadow on-demand)

→ Produkční setup
```

---

### Scenario 3: Reverse (i7 Primary + i5 Shadow)
```
PRIMARY_URL = "http://[i7-IP]:9302/metrics"

i7 Windows:    start.bat         (Primary)
i5 Ubuntu:     ./start_shadow.sh (Shadow)

→ Možné, ale NEDOPORUČENO (i7 high power)
```

---

## 🔐 Security Best Practices

### 1. SSH Key Authentication (i5 Ubuntu)

**Na i7 Windows - generovat SSH klíč:**
```cmd
ssh-keygen -t ed25519 -C "asterisk-to-fujitsu"
```

**Copy public key na i5:**
```cmd
type %USERPROFILE%\.ssh\id_ed25519.pub | ssh user@192.168.123.121 "cat >> ~/.ssh/authorized_keys"
```

**Test:**
```cmd
ssh user@192.168.123.121
```

---

### 2. Firewall - pouze potřebné porty

**i5 Ubuntu (minimální surface):**
```bash
# POUZE tyto porty:
sudo ufw allow 22/tcp     # SSH
sudo ufw allow 9302/tcp   # Primary Node
# Žádné další porty!
```

**i7 Windows (gaming PC = více software):**
```cmd
REM Povolit jen Shadow port
netsh advfirewall firewall add rule name="Mincovna Shadow" dir=in action=allow protocol=TCP localport=9303
```

---

### 3. Network Isolation (volitelné)

**Vytvoř dedicated VLAN pro Mincovnu:**
```
VLAN 10: Mincovna Network
- i5: 192.168.10.121
- i7: 192.168.10.50
```

---

## 🚨 Troubleshooting

### Problém: "Connection refused"

**Na i5 Ubuntu - kontrola:**
```bash
# Je Primary Node běžící?
ps aux | grep python
ps aux | grep faucet_bridge

# Je port otevřený?
sudo netstat -tulpn | grep 9302

# Je firewall OK?
sudo ufw status

# Test lokálně na i5:
curl http://localhost:9302/metrics
```

**Na i7 Windows - kontrola:**
```cmd
REM Ping funguje?
ping 192.168.123.121

REM Port otevřený?
telnet 192.168.123.121 9302

REM Nebo:
Test-NetConnection -ComputerName 192.168.123.121 -Port 9302
```

---

### Problém: "Sync errors"

**Shadow log ukazuje:**
```
[SHADOW] ✗ Sync chyba: Connection timeout
shadow_sync_errors_total += 1
```

**Řešení:**
1. Zkontroluj že Primary běží
2. Zkontroluj firewall (ufw allow 9302/tcp)
3. Zkontroluj network (ping funguje?)
4. Zkontroluj PRIMARY_URL v shadow_node.py

---

### Problém: "High latency"

**Shadow log:**
```
[SHADOW] ⚠️ Sync latency: 150ms
```

**Normální:**
- LAN: 1-10ms
- WiFi: 5-50ms
- > 100ms: problém!

**Řešení:**
1. Použij kabelové připojení (Ethernet)
2. Zkontroluj router (QoS settings)
3. Zkontroluj WiFi interference

---

## 📝 Quick Reference

### Zjistit IP adresy

**i5 Ubuntu:**
```bash
ip addr show
# nebo
hostname -I
```

**i7 Windows:**
```cmd
ipconfig
```

---

### Upravit Shadow Node URL

**Edit soubor:**
```cmd
notepad c:\Users\pan_jeskyne\Favorites\vakuova-mincovna\src\shadow_node.py
```

**Změnit řádek:**
```python
PRIMARY_URL = "http://192.168.123.121:9302/metrics"
```

---

### Test Connection

**Z i7 Windows:**
```cmd
REM Ping
ping 192.168.123.121

REM HTTP test
curl http://192.168.123.121:9302/metrics

REM Port test
Test-NetConnection -ComputerName 192.168.123.121 -Port 9302
```

---

## ✅ Network Setup Checklist

### Před spuštěním cross-machine:

- [ ] i5 má statickou IP: `192.168.123.121`
- [ ] i7 IP adresa zjištěna: `ipconfig`
- [ ] Ping z i7 → i5 funguje
- [ ] Firewall na i5: `sudo ufw allow 9302/tcp`
- [ ] Firewall na i7: port 9303 otevřen
- [ ] PRIMARY_URL v shadow_node.py upraven
- [ ] Primary Node běží na i5
- [ ] Shadow Node testován na i7
- [ ] Metriky viditelné z i7: `http://192.168.123.121:9302/metrics`
- [ ] Sync funguje: Shadow log ukazuje "✓ Sync OK"

---

## 🎯 Next Steps

### 1. Local Test (i7 only) - TEĎKA
```cmd
PRIMARY_URL = "http://localhost:9302/metrics"
start.bat + start_shadow.bat
```

### 2. Cross-Machine Test - PO local testu
```cmd
PRIMARY_URL = "http://192.168.123.121:9302/metrics"
i5: ./start.sh
i7: start_shadow.bat
```

### 3. Production - PO úspěšném testu
```bash
# i5: Systemd service (autostart)
sudo systemctl enable mincovna-primary
```

---

**IP adresa i5:** `192.168.123.121` ✅  
**Standard 700:** 12g stříbra = 1 mince  
**Autor:** Pan Jeskyně + Kiro AI

🌐✨
