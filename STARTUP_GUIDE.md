# 🚀 Vakuová Mincovna - Startup Guide

## Co bylo opraveno

### ✅ MCP.json - OPRAVENO
**Soubor:** `c:\Users\pan_jeskyne\Favorites\.kiro\settings\mcp.json`

**Problém:** Obsahoval Erlang kód místo JSON  
**Řešení:** Nahrazeno správnou JSON konfigurací

```json
{
  "mcpServers": {}
}
```

### ✅ Shadow Node - Windows Script
**Soubor:** `start_shadow.bat`

Vytvořen startup script pro Shadow Node na Windows.

---

## 📋 Rychlý Start

### Na Windows (tento počítač)

#### 1. Primary Node
```cmd
cd c:\Users\pan_jeskyne\Favorites\vakuova-mincovna
start.bat
```

#### 2. Shadow Node (v jiném terminálu)
```cmd
cd c:\Users\pan_jeskyne\Favorites\vakuova-mincovna
start_shadow.bat
```

#### 3. Watchdog (v jiném terminálu)
```cmd
cd c:\Users\pan_jeskyne\Favorites\vakuova-mincovna
start_watchdog.bat
```

#### 4. Privacy Protocol 4:23 (v jiném terminálu)
```cmd
cd c:\Users\pan_jeskyne\Favorites\vakuova-mincovna
start_privacy.bat
```

---

## 🏗️ Architektura Systému

```
┌────────────────────────────────────────────────────┐
│            VAKUOVÁ MINCOVNA (i7 Windows)          │
└────────────────────────────────────────────────────┘
                         │
     ┌──────────────────┴──────────────────┐
     │                                     │
┌────▼─────┐                        ┌─────▼────┐
│ PRIMARY  │◄──────sync (5s)───────►│  SHADOW  │
│ :9302    │                        │  :9303   │
└────┬─────┘                        └─────┬────┘
     │                                    │
     │                                    │
┌────▼────────────────────────────────────▼────┐
│         MONITORING & SECURITY LAYER          │
│                                               │
│  • Watchdog (9304) - Mossad ALF++            │
│  • Privacy  (9305) - Protocol 4:23           │
│  • Prometheus      - Metrics                 │
└───────────────────────────────────────────────┘
```

---

## 🔄 Deployment Plán

### Phase 1: Test na Windows (TEĎKA)
- [x] Opravit mcp.json
- [x] Vytvořit start_shadow.bat
- [ ] **Spustit Primary Node**
- [ ] **Spustit Shadow Node**
- [ ] **Test failover** (ukončit Primary, Shadow převezme kontrolu)
- [ ] **Test recovery** (spustit Primary znovu, Shadow se vrátí)

### Phase 2: Watchdog a Privacy (TEĎKA)
- [ ] **Spustit Watchdog** - bezpečnostní monitoring
- [ ] **Spustit Privacy Protocol** - denní metadata purge
- [ ] **Test security alerts** - simulace hrozby
- [ ] **Test privacy purge** - kontrola 4:23 denně

### Phase 3: Deploy na Ubuntu 26.06 (i5)
- [ ] Přenést celý projekt na Ubuntu
- [ ] Install GNAT/SPARK
- [ ] Install Python dependencies
- [ ] Spustit Shadow Node na Ubuntu
- [ ] Konfigurovat network (Windows ↔ Ubuntu)
- [ ] Test cross-machine synchronizace

---

## 📊 Porty a Služby

| Služba              | Port | Popis                        |
|---------------------|------|------------------------------|
| Primary Node        | 9302 | Ada/SPARK Core + Metrics     |
| Shadow Node         | 9303 | Redundance + Failover        |
| Watchdog            | 9304 | Security Scanner (Mossad)    |
| Privacy Protocol    | 9305 | Metadata Purge (4:23)        |
| Prometheus          | 9090 | Metrics Collection           |
| Grafana (volitelné) | 3000 | Visualization                |

---

## 🔍 Monitoring URLs

```bash
# Primary Node metriky
http://localhost:9302/metrics

# Shadow Node metriky
http://localhost:9303/metrics

# Watchdog status
http://localhost:9304/metrics

# Privacy Protocol status
http://localhost:9305/metrics

# Prometheus
http://localhost:9090
```

---

## 🧪 Test Scénáře

### Test 1: Normální provoz
```cmd
REM Terminal 1: Primary
start.bat

REM Terminal 2: Shadow
start_shadow.bat

REM Výsledek:
# shadow_is_primary = 0  (Shadow je v shadow módu)
# shadow_primary_health = 1 (Primary žije)
```

### Test 2: Failover
```cmd
REM Terminal 1: Primary běží
start.bat

REM Terminal 2: Shadow běží
start_shadow.bat

REM Terminal 1: UKONČIT Primary (Ctrl+C)

REM Výsledek po 15 sekundách:
# shadow_is_primary = 1  (Shadow převzal kontrolu!)
# shadow_primary_health = 0 (Primary je mrtvý)
```

### Test 3: Recovery
```cmd
REM Navazuje na Test 2

REM Terminal 1: SPUSTIT Primary znovu
start.bat

REM Výsledek po ~10 sekundách:
# shadow_is_primary = 0  (Shadow se vrátil do shadow módu)
# shadow_primary_health = 1 (Primary se vrátil)
```

### Test 4: Watchdog Alert
```cmd
REM Terminal 1: Spustit Watchdog
start_watchdog.bat

REM Terminal 2: Simulovat hrozbu
python -c "open('dangerous_file.exe', 'w').write('malware')"

REM Výsledek:
# watchdog_threats_detected = 1
# watchdog_alert (e-mail/webhook)
```

### Test 5: Privacy Purge
```cmd
REM Terminal 1: Spustit Privacy Protocol
start_privacy.bat

REM Výsledek každý den ve 4:23:
# privacy_purges_total += 1
# privacy_records_purged += X
# Log: "[PRIVACY] ✓ Denní purge dokončen: X záznamů smazáno"
```

---

## ⚠️ Troubleshooting

### Problém: "Error loading mcp.json"
**Řešení:** ✅ OPRAVENO - mcp.json už obsahuje správný JSON

### Problém: "Port 9302 already in use"
**Řešení:**
```cmd
netstat -ano | findstr :9302
taskkill /PID <PID> /F
```

### Problém: "ModuleNotFoundError: prometheus_client"
**Řešení:**
```cmd
pip install prometheus_client requests
```

### Problém: "gprbuild: command not found"
**Řešení:**
1. Nainstaluj GNAT Community 2024
2. Nebo použij `AdaDev2024.zip` (už máš staženo)

---

## 🎯 Next Steps (co dělat teďka)

### 1️⃣ OTESTOVAT LOKÁLNĚ (Windows)
```cmd
cd c:\Users\pan_jeskyne\Favorites\vakuova-mincovna

REM Terminal 1:
start.bat

REM Terminal 2:
start_shadow.bat

REM Terminal 3:
start_watchdog.bat

REM Terminal 4:
start_privacy.bat
```

### 2️⃣ PROMETHEUS (volitelné)
```cmd
REM Download Prometheus
REM https://prometheus.io/download/

REM Spustit Prometheus
prometheus.exe --config.file=prometheus\prometheus.yml
```

### 3️⃣ TRANSFER NA UBUNTU
```cmd
REM Zabalit projekt
package.bat

REM Přenést vakuova-mincovna-package.zip na Ubuntu i5
REM Nainstalovat tam GNAT/SPARK + Python
REM Spustit Shadow Node tam
```

---

## 📝 Poznámky

### Standard 700
- 12g stříbra = 1 mince
- Matematická jistota (Ada/SPARK)
- Formální verifikace: `gnatprove -P mincovna.gpr --level=4`

### "Faucet nic"
- Nulová spotřeba externích zdrojů
- Vše běží lokálně (kromě network sync)
- RAM-only sessions (Privacy Protocol)

### Web4 Filozofie
> "První článek musí být neprůstřelný. Pak se zbytek staví sám, autonomně."

---

## 🔐 Security

### Watchdog (Mossad ALF++)
- Scan interval: 60s
- Port: 9304
- Protocol: AFL++ fuzzing techniques
- Alert: E-mail + Webhook

### Privacy Protocol 4:23
- Daily purge: 04:23 AM
- Port: 9305
- Zero-Cookie Auth
- RAM-only sessions
- Metadata lifetime: 24h max

---

## 📞 Support

**Autor:** Pan Jeskyně  
**Asistent:** Kiro (Claude Sonnet 4.5)  
**Projekt:** Vakuová Mincovna (Web4 Article #1)  
**Standard:** 700 (12g stříbra)

---

## ✅ Status

```
✅ MCP.json opraveno
✅ Shadow Node Windows script vytvořen
✅ Watchdog implementován
✅ Privacy Protocol implementován
✅ Dokumentace kompletní
✅ Připraveno k testování

🚀 READY TO START!
```

---

**Příští krok:** Spusť `start.bat` a `start_shadow.bat` a otestuj failover! 🏗️✨
