# 🔐 Privacy Protocol 4:23

## Koncept

**Každý den ve 4:23 AM se mažou všechny metadata!**

- ❌ Žádné cookies
- ❌ Žádné trvalé IP adresy
- ❌ Žádné long-term logy
- ✅ E2E encryption (TLS 1.3 + WireGuard)
- ✅ RAM-only sessions (max 24h)
- ✅ Zero tracking

---

## 🕐 Co se maže ve 4:23?

### Metadata (SMAŽE SE):
- IP adresy z logů
- Timestamps (kromě blockchain)
- Session data (RAM sessions starší 24h)
- Log files (rotace)
- Temp files (/tmp, /var/tmp)
- Cache (.cache, /var/cache)

### Kritická data (ZACHOVÁ SE):
- Blockchain data (Sepolia ETH)
- Mincovna state (Ada/SPARK)
- Coin records (Standard 700)
- Security baseline (watchdog)

---

## 🚀 Použití

### Okamžitý purge (testing)

```bash
# Linux/Ubuntu
python3 src/privacy_purge_423.py --now

# Windows
python src\privacy_purge_423.py --now
```

### Daemon mode (automatický 4:23 purge)

```bash
# Linux/Ubuntu
./start_privacy.sh

# Windows
start_privacy.bat
```

---

## 🔒 Zero-Cookie Authentication

### RAM-only sessions

```python
from privacy_purge_423 import ZeroCookieAuth

auth = ZeroCookieAuth()

# Vytvoř session (pouze v RAM)
session_id = auth.create_session(user_id="user123")

# Validuj session
if auth.validate_session(session_id):
    print("Session platná")

# Session automaticky expiruje po 24h
```

**Vlastnosti:**
- Žádné cookies
- Žádná localStorage
- Žádná sessionStorage
- Pouze RAM (data zmizí po restartu)
- Max lifetime: 24 hodin

---

## 🗑️ Secure Wipe (DOD 5220.22-M)

Protocol 4:23 používá **3-pass secure wipe**:

```
Pass 1: Random data (os.urandom)
Pass 2: 0xFF (all bits set)
Pass 3: 0x00 (all bits clear)
Final:  os.remove()
```

Data nelze obnovit ani forenzními nástroji!

---

## 📊 Prometheus Metriky

```prometheus
# Celkový počet purge operací
privacy_purges_total

# Smazaná data (podle typu)
privacy_metadata_deleted_mb_total{data_type="temp"}
privacy_metadata_deleted_mb_total{data_type="logs"}

# Poslední purge
privacy_last_purge_timestamp

# Příští plánovaný purge
privacy_next_purge_timestamp

# Aktivní RAM sessions
privacy_active_sessions
```

**Port:** 9305

---

## 🛠️ Konfigurace

Edituj `src/privacy_purge_423.py`:

```python
# Čas purge
PURGE_TIME = "04:23"  # HH:MM formát

# Max session age
SESSION_MAX_AGE = 86400  # 24 hodin (sekund)

# Cesty k purgování
METADATA_PATHS = [
    "/tmp",
    "/var/log",
    "/var/cache",
]

# Co se nikdy nemaže
PRESERVE_PATHS = [
    "blockchain",
    "mincovna_state",
    "watchdog_baseline.json",
]
```

---

## 🔐 E2E Encryption

### TLS 1.3

```yaml
# nginx.conf (pro Primary Node)
ssl_protocols TLSv1.3;
ssl_ciphers 'TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256';
ssl_prefer_server_ciphers off;
```

### WireGuard (pro Shadow sync)

```bash
# /etc/wireguard/wg0.conf
[Interface]
PrivateKey = <primary-private-key>
Address = 10.0.0.1/24

[Peer]
PublicKey = <shadow-public-key>
AllowedIPs = 10.0.0.2/32
Endpoint = shadow-ip:51820
```

---

## 📅 Cron job (automatická 4:23)

### systemd timer (Linux)

```ini
# /etc/systemd/system/privacy-423.service
[Unit]
Description=Privacy Protocol 4:23
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/vakuova-mincovna/src/privacy_purge_423.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Aktivace
sudo systemctl enable privacy-423.service
sudo systemctl start privacy-423.service
```

---

## 🎯 Use Cases

### Scénář 1: Normální provoz
```
00:00 → Systém běží
04:23 → Automatický purge
04:24 → Systém běží dál (bez metadat)
```

### Scénář 2: Restart před 4:23
```
03:00 → Restart serveru
03:01 → RAM sessions zmizely (restart)
04:23 → Purge běží normálně
```

### Scénář 3: Testing
```
$ python3 src/privacy_purge_423.py --now
[PRIVACY] Purging NOW...
[PRIVACY] ✓ Temp files: 123.45 MB deleted
[PRIVACY] ✓ Logs: 67.89 MB deleted
```

---

## 🌐 Integrace s Web4

### n8n Workflow

```json
{
  "name": "Privacy Purge Alert",
  "nodes": [
    {
      "type": "prometheus",
      "query": "privacy_purges_total"
    },
    {
      "type": "webhook",
      "url": "https://your-webhook.com/privacy-alert"
    }
  ]
}
```

---

## 📊 Grafana Dashboard

```json
{
  "title": "Privacy Protocol 4:23",
  "panels": [
    {
      "title": "Last Purge",
      "target": "privacy_last_purge_timestamp"
    },
    {
      "title": "Next Purge",
      "target": "privacy_next_purge_timestamp"
    },
    {
      "title": "Active Sessions",
      "target": "privacy_active_sessions"
    },
    {
      "title": "Deleted Data (MB)",
      "target": "privacy_metadata_deleted_mb_total"
    }
  ]
}
```

---

## 🛡️ Best Practices

1. **Backup kritických dat před purge** (blockchain, mincovna state)
2. **Test purge v non-prod prostředí** (--now flag)
3. **Monitor Prometheus metriky** (kontrola že purge běží)
4. **E2E encryption vždy zapnutá** (TLS 1.3 + WireGuard)
5. **Zero cookies = zero tracking** (100% privacy)

---

## 🎉 Výsledek

✅ **Denní 4:23 purge** - Automatické mazání metadat  
✅ **Zero cookies** - RAM-only authentication  
✅ **E2E encryption** - TLS 1.3 + WireGuard  
✅ **Secure wipe** - DOD 5220.22-M standard  
✅ **24h sessions** - Max lifetime  
✅ **Prometheus monitoring** - Real-time tracking  

**První článek je skutečně PRIVATE!** 🔐✨

---

**Příští krok:** Spusť privacy daemon → Testuj 4:23 purge
