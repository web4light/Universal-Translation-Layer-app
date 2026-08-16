# 🧪 Testing Guide - Vakuová Mincovna

## Testování Primary + Shadow Node

Tato příručka ti ukáže jak otestovat všechny funkce systému.

---

## 🎯 Test 1: Základní funkčnost Primary Node

### Cíl
Ověřit že Primary Node správně běží a exportuje metriky.

### Postup

1. **Spusť Primary Node:**
```cmd
cd c:\Users\pan_jeskyne\Favorites\vakuova-mincovna
start.bat
```

2. **Otevři prohlížeč:**
```
http://localhost:9302/metrics
```

3. **Očekávaný výstup:**
```prometheus
# Vakuová Mincovna - Primary Node
# Standard 700: 12g stříbra

# Celkový počet vyražených mincí
mincovna_minted_coins_total 0.0

# Celkové množství stříbra (gramy)
mincovna_total_silver_grams 0.0

# Zdraví systému (1.0 = OK, 0.0 = problém)
mincovna_system_health 1.0

# Formální verifikace (1.0 = ověřeno, 0.0 = chyba)
mincovna_formal_verification_status 1.0
```

### ✅ Test PASSED pokud
- Port 9302 je dostupný
- Metriky jsou viditelné
- `mincovna_system_health 1.0`
- `mincovna_formal_verification_status 1.0`

---

## 🎯 Test 2: Základní funkčnost Shadow Node

### Cíl
Ověřit že Shadow Node správně monitoruje Primary.

### Postup

1. **Primary Node musí běžet** (z Test 1)

2. **Otevři DRUHÝ terminál a spusť Shadow Node:**
```cmd
cd c:\Users\pan_jeskyne\Favorites\vakuova-mincovna
start_shadow.bat
```

3. **V terminálu Shadow Node uvidíš:**
```
🌑 SHADOW NODE - STÍNOVACÍ UZEL
[SHADOW] Prometheus endpoint: http://localhost:9303/metrics
[SHADOW] Monitoring Primary: http://localhost:9302/metrics
[SHADOW] Režim: MONITORING
[SHADOW] ✓ Sync OK: 0 mincí, 0.0g stříbra
```

4. **Otevři prohlížeč:**
```
http://localhost:9303/metrics
```

5. **Očekávaný výstup:**
```prometheus
# Shadow Node metriky

# Je Shadow Node primární? (0=shadow, 1=primary)
shadow_is_primary 0.0

# Zdraví Primary Node z pohledu Shadow
shadow_primary_health 1.0

# Synchronizované mince
shadow_synced_coins 0.0

# Synchronizované stříbro (gramy)
shadow_synced_silver_grams 0.0

# Timestamp poslední synchronizace
shadow_last_sync_timestamp 1686563428.5
```

### ✅ Test PASSED pokud
- Port 9303 je dostupný
- `shadow_is_primary 0.0` (je v shadow módu)
- `shadow_primary_health 1.0` (vidí Primary Node)
- V terminálu jsou pravidelné sync zprávy

---

## 🎯 Test 3: Synchronizace mezi uzly

### Cíl
Ověřit že Shadow Node synchronizuje data z Primary.

### Postup

1. **Oba uzly musí běžet** (Primary + Shadow)

2. **Sleduj Shadow terminál 60 sekund**

3. **Očekávaný výstup (každých 5 sekund):**
```
[12:34:05] [SHADOW] ✓ Sync OK: 0 mincí, 0.0g stříbra
[12:34:10] [SHADOW] ✓ Sync OK: 0 mincí, 0.0g stříbra
[12:34:15] [SHADOW] ✓ Sync OK: 0 mincí, 0.0g stříbra
```

4. **Zkontroluj metriky Shadow:**
```
http://localhost:9303/metrics
```

Najdi:
```
shadow_last_sync_timestamp 1686563489.3
```

Číslo se musí zvyšovat každých 5 sekund!

### ✅ Test PASSED pokud
- Shadow Node hlásí "✓ Sync OK" každých 5s
- `shadow_last_sync_timestamp` se aktualizuje
- Žádné "✗ Sync chyba" zprávy
- `shadow_sync_errors_total` je 0

---

## 🎯 Test 4: FAILOVER - Shadow převezme kontrolu

### Cíl
Ověřit že Shadow Node automaticky převezme roli Primary když spadne.

### Postup

1. **Oba uzly musí běžet** (Primary + Shadow)

2. **V terminálu s Primary Node stiskni `Ctrl+C`**
   - Primary Node se UKONČÍ

3. **Sleduj Shadow terminál - do 20 sekund uvidíš:**
```
[SHADOW] ⚠️  Primary Node timeout: 15.2s
============================================================
🚨 FAILOVER EVENT - SHADOW NODE PŘEBÍRÁ KONTROLU! 🚨
============================================================
[SHADOW→PRIMARY] Status změněn na PRIMARY
[SHADOW→PRIMARY] Poslední známý stav:
  • Mince: 0
  • Stříbro: 0.0g
  • Health: 1

[SHADOW→PRIMARY] Systém pokračuje bez přerušení!
============================================================
```

4. **Zkontroluj metriky Shadow:**
```
http://localhost:9303/metrics
```

Očekávané změny:
```
shadow_is_primary 1.0        ← ZMĚNILO SE Z 0 NA 1!
shadow_primary_health 0.0    ← ZMĚNILO SE Z 1 NA 0!
```

### ✅ Test PASSED pokud
- Shadow detekuje pád Primary do 20 sekund
- Shadow hlásí "FAILOVER EVENT"
- `shadow_is_primary` změnilo na 1.0
- `shadow_primary_health` změnilo na 0.0

---

## 🎯 Test 5: RECOVERY - Primary se vrátil

### Cíl
Ověřit že Shadow vrátí kontrolu když se Primary vrátí online.

### Postup

1. **Shadow Node je v PRIMARY módu** (z Test 4)

2. **Znovu spusť Primary Node:**
```cmd
start.bat
```

3. **Sleduj Shadow terminál - do 10 sekund uvidíš:**
```
============================================================
🔄 PRIMARY NODE SE VRÁTIL - Vracím se do Shadow módu
============================================================
[PRIMARY→SHADOW] Kontrola předána zpět Primary Node
[PRIMARY→SHADOW] Obnovuji synchronizaci...
============================================================

[SHADOW] ✓ Sync OK: 0 mincí, 0.0g stříbra
```

4. **Zkontroluj metriky Shadow:**
```
http://localhost:9303/metrics
```

Očekávané změny:
```
shadow_is_primary 0.0        ← VRÁTILO SE Z 1 NA 0!
shadow_primary_health 1.0    ← VRÁTILO SE Z 0 NA 1!
```

### ✅ Test PASSED pokud
- Shadow detekuje návrat Primary do 10 sekund
- Shadow hlásí "PRIMARY NODE SE VRÁTIL"
- `shadow_is_primary` změnilo zpět na 0.0
- `shadow_primary_health` změnilo zpět na 1.0
- Synchronizace pokračuje normálně

---

## 🎯 Test 6: Síťová dostupnost

### Cíl
Ověřit že Shadow může komunikovat s Primary přes síť.

### Postup (pouze pokud Shadow je na JINÉM počítači)

1. **Na Windows (Primary):**

Zjisti IP adresu:
```cmd
ipconfig
```
Najdi IPv4 adresu (např. `192.168.1.100`)

2. **Otevři firewall:**
```cmd
netsh advfirewall firewall add rule name="Mincovna Primary" dir=in action=allow protocol=TCP localport=9302
```

3. **Na Ubuntu/druhý PC (Shadow):**

Edituj `src/shadow_node.py`:
```python
PRIMARY_URL = "http://192.168.1.100:9302/metrics"
```

4. **Spusť Shadow Node:**
```bash
./start_shadow.sh
```

5. **Test dostupnosti:**
```bash
curl http://192.168.1.100:9302/metrics
```

### ✅ Test PASSED pokud
- `curl` vrátí metriky Primary Node
- Shadow Node hlásí "✓ Sync OK"
- `shadow_primary_health 1.0`

---

## 🎯 Test 7: Zátěžový test synchronizace

### Cíl
Ověřit že synchronizace funguje i pod zátěží.

### Postup

1. **Oba uzly běží**

2. **Sleduj Shadow terminál 5 minut**

3. **Spočítej:**
   - Počet úspěšných sync: `✓ Sync OK`
   - Počet chybných sync: `✗ Sync chyba`

4. **Zkontroluj metriky:**
```
http://localhost:9303/metrics
```

Najdi:
```
shadow_sync_errors_total 0
```

### ✅ Test PASSED pokud
- Žádné chybné synchronizace za 5 minut
- `shadow_sync_errors_total 0`
- `shadow_primary_health 1.0` po celou dobu

---

## 🎯 Test 8: Rychlost detekce failover

### Cíl
Změřit jak rychle Shadow detekuje pád Primary.

### Postup

1. **Oba uzly běží**

2. **Připrav stopky**

3. **Spusť stopky a OKAMŽITĚ stiskni `Ctrl+C` v Primary terminálu**

4. **Zastaň stopky když Shadow hlásí "FAILOVER EVENT"**

5. **Očekávaný čas: 15-20 sekund**
   - Heartbeat každých 5s
   - Timeout po 15s
   - Celkem ~15-20s

### ✅ Test PASSED pokud
- Failover detekce < 25 sekund
- Shadow převzal kontrolu úspěšně

---

## 🎯 Test 9: Multiple Failover/Recovery cykly

### Cíl
Ověřit stabilitu při opakovaných failover událostech.

### Postup

1. **Spusť Primary + Shadow**

2. **Opakuj 5×:**
   - Vypni Primary (`Ctrl+C`)
   - Počkej 30 sekund (Shadow převezme)
   - Zapni Primary (`start.bat`)
   - Počkej 30 sekund (Shadow vrátí kontrolu)

3. **Sleduj Shadow terminál**

### ✅ Test PASSED pokud
- Všech 5 failover cyklů proběhlo úspěšně
- Shadow se vždy vrátil do shadow módu
- Žádné chyby synchronizace
- Žádné zamrznutí nebo crash

---

## 🎯 Test 10: Prometheus monitoring obou uzlů

### Cíl
Ověřit že Prometheus sbírá metriky z obou uzlů.

### Postup

1. **Edituj `prometheus\prometheus.yml`:**

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'mincovna-primary'
    static_configs:
      - targets: ['localhost:9302']
  
  - job_name: 'mincovna-shadow'
    static_configs:
      - targets: ['localhost:9303']
```

2. **Spusť Prometheus:**
```cmd
cd prometheus
prometheus --config.file=prometheus.yml
```

3. **Otevři Prometheus UI:**
```
http://localhost:9090
```

4. **Test queries:**

**Který uzel je Primary?**
```
shadow_is_primary
```

**Celkové mince (oba uzly):**
```
mincovna_minted_coins_total
```

**Zdraví obou uzlů:**
```
up{job=~"mincovna-.*"}
```

### ✅ Test PASSED pokud
- Prometheus vidí oba uzly (status UP)
- Query `shadow_is_primary` vrací 0 nebo 1
- Query `up` vrací 1 pro oba jobs

---

## 📊 Test Results Summary

Po dokončení všech testů vyplň:

```
TEST 1: Primary Node funkčnost         [ ] PASS  [ ] FAIL
TEST 2: Shadow Node funkčnost          [ ] PASS  [ ] FAIL
TEST 3: Synchronizace                  [ ] PASS  [ ] FAIL
TEST 4: Failover (Shadow→Primary)      [ ] PASS  [ ] FAIL
TEST 5: Recovery (Primary←Shadow)      [ ] PASS  [ ] FAIL
TEST 6: Síťová dostupnost              [ ] PASS  [ ] FAIL  [ ] N/A
TEST 7: Zátěžový test                  [ ] PASS  [ ] FAIL
TEST 8: Rychlost failover              [ ] PASS  [ ] FAIL
TEST 9: Multiple failover cykly        [ ] PASS  [ ] FAIL
TEST 10: Prometheus monitoring         [ ] PASS  [ ] FAIL
```

### Výsledek
- **10/10 PASS** = Systém je připraven na produkci! 🎉
- **8-9/10 PASS** = Téměř hotovo, oprav drobné problémy
- **< 8/10 PASS** = Zkontroluj konfiguraci a závislosti

---

## 🐛 Common Issues

### Problem: Port již používán
```
OSError: [Errno 48] Address already in use
```

**Řešení Windows:**
```cmd
netstat -ano | findstr :9302
taskkill /PID <PID> /F
```

**Řešení Ubuntu:**
```bash
lsof -i :9302
kill -9 <PID>
```

### Problem: Python modul chybí
```
ModuleNotFoundError: No module named 'prometheus_client'
```

**Řešení:**
```cmd
pip install prometheus_client requests
```

### Problem: Shadow nevidí Primary
```
[SHADOW] ✗ Sync chyba: Connection refused
```

**Řešení:**
1. Zkontroluj že Primary běží
2. Zkontroluj URL v `shadow_node.py`
3. Zkontroluj firewall (pokud síťové)

---

## 🎯 Production Readiness Checklist

Po úspěšném dokončení testů:

### Primary Node (Windows)
- [ ] `start.bat` spouští bez chyb
- [ ] Port 9302 je dostupný
- [ ] Metriky jsou exportovány
- [ ] `mincovna_system_health 1.0`
- [ ] Ada/SPARK verifikace AKTIVNÍ

### Shadow Node (Ubuntu 26.06)
- [ ] `start_shadow.sh` spouští bez chyb
- [ ] Port 9303 je dostupný
- [ ] Může se připojit k Primary
- [ ] Synchronizace funguje
- [ ] Failover < 25s
- [ ] Recovery funguje

### Monitoring
- [ ] Prometheus sbírá z obou uzlů
- [ ] Grafana dashboard (volitelné)
- [ ] Alerty nastaveny (volitelné)

---

## 🎉 Gratulace!

Pokud všechny testy prošly, máš **produkčně připravený** systém:

✅ Primary Node (Windows)
✅ Shadow Node (Ubuntu 26.06)
✅ Automatický failover
✅ High availability
✅ Matematická verifikace (Ada/SPARK)
✅ "Faucet nic" princip

**První článek** je NEPRŮSTŘELNÝ! 🏗️✨

Systém je připraven na autonomní provoz.

---

**Autor:** Pan Jeskyně  
**Asistent:** Kiro (Claude Sonnet 4.5)  
**Standard:** 700 (12g stříbra)  
**Datum:** 2026-06-12

