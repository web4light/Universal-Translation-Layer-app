# 📚 Vakuová Mincovna - Index dokumentace

Rychlý přehled všech dokumentů v projektu.

---

## 🚀 Začínáme

**Pro první spuštění na Windows:**
1. Přečti: [`README.md`](README.md) - Základní info o projektu
2. Spusť: `start.bat` - Primary Node
3. Spusť: `start_shadow.bat` - Shadow Node (v druhém terminálu)
4. Otevři: `http://localhost:9302/metrics` a `http://localhost:9303/metrics`

**Pro nasazení na Ubuntu 26.06:**
1. Přečti: [`DEPLOY_UBUNTU.md`](DEPLOY_UBUNTU.md)
2. Použij: [`DEPLOYMENT_CHECKLIST.md`](DEPLOYMENT_CHECKLIST.md)
3. Nebo: [`QUICKSTART_UBUNTU.txt`](QUICKSTART_UBUNTU.txt) (quick start)

---

## 📖 Dokumentace

### Základní dokumentace

| Soubor | Účel | Pro koho |
|--------|------|----------|
| [`README.md`](README.md) | Základní přehled projektu | Všichni |
| [`SYSTEM_OVERVIEW.md`](SYSTEM_OVERVIEW.md) | Kompletní přehled systému | Vývojáři, architekt |
| [`BUILD.md`](BUILD.md) | Build instrukce | Vývojáři |

### Shadow Node dokumentace

| Soubor | Účel | Pro koho |
|--------|------|----------|
| [`SHADOW_NODE.md`](SHADOW_NODE.md) | Shadow Node koncept a architektura | Všichni |
| [`SHADOW_NODE_WINDOWS.md`](SHADOW_NODE_WINDOWS.md) | Shadow Node na Windows | Windows uživatelé |
| [`TESTING_GUIDE.md`](TESTING_GUIDE.md) | Kompletní testing příručka | Testers, DevOps |

### Deployment dokumentace

| Soubor | Účel | Pro koho |
|--------|------|----------|
| [`DEPLOY_UBUNTU.md`](DEPLOY_UBUNTU.md) | Ubuntu deployment guide | DevOps, Ubuntu users |
| [`DEPLOYMENT_CHECKLIST.md`](DEPLOYMENT_CHECKLIST.md) | Step-by-step checklist | DevOps |
| [`QUICKSTART_UBUNTU.txt`](QUICKSTART_UBUNTU.txt) | Quick start pro Ubuntu | Ubuntu users |
| [`README_PRO_DRUHY_KOMP.md`](README_PRO_DRUHY_KOMP.md) | Přenos na druhý počítač | Všichni |

---

## 🛠️ Scripty

### Windows

| Script | Účel |
|--------|------|
| `start.bat` | Spustí Primary Node (port 9302) |
| `start_shadow.bat` | Spustí Shadow Node (port 9303) |
| `package.bat` | Vytvoří deployment balíček (.zip) |

### Linux/Ubuntu

| Script | Účel |
|--------|------|
| `start.sh` | Spustí Primary Node (port 9302) |
| `start_shadow.sh` | Spustí Shadow Node (port 9303) |
| `package.sh` | Vytvoří deployment balíček (.tar.gz) |

---

## 📂 Zdrojové soubory

### Ada/SPARK Core

| Soubor | Účel |
|--------|------|
| `src/mincovna.adb` | Ada/SPARK Core - matematicky ověřená logika |
| `mincovna.gpr` | GNAT project file (build config) |

### Python

| Soubor | Účel |
|--------|------|
| `src/shadow_node.py` | Shadow Node implementace |
| `src/faucet_bridge.py` | Python bridge (TBD - bude vytvořen) |

### Erlang

| Soubor | Účel |
|--------|------|
| `src/faucet_dns.erl` | Faucet DNS (Erlang) |

### Monitoring

| Soubor | Účel |
|--------|------|
| `prometheus/prometheus.yml` | Prometheus konfigurace |

---

## 🎯 Podle use case

### Chci spustit lokálně na Windows

1. [`README.md`](README.md) - Základní info
2. `start.bat` - Spusť Primary
3. `start_shadow.bat` - Spusť Shadow
4. [`TESTING_GUIDE.md`](TESTING_GUIDE.md) - Otestuj

### Chci nasadit na Ubuntu 26.06

1. [`DEPLOY_UBUNTU.md`](DEPLOY_UBUNTU.md) - Kompletní guide
2. [`QUICKSTART_UBUNTU.txt`](QUICKSTART_UBUNTU.txt) - Rychlý start
3. [`DEPLOYMENT_CHECKLIST.md`](DEPLOYMENT_CHECKLIST.md) - Checklist

### Chci přenést na druhý počítač

1. [`README_PRO_DRUHY_KOMP.md`](README_PRO_DRUHY_KOMP.md) - Návod přenosu
2. `package.bat` nebo `package.sh` - Vytvoř balíček
3. Přenes ZIP/TAR.GZ na druhý PC

### Chci pochopit architekturu

1. [`SYSTEM_OVERVIEW.md`](SYSTEM_OVERVIEW.md) - Kompletní přehled
2. [`SHADOW_NODE.md`](SHADOW_NODE.md) - Shadow Node detail
3. `src/mincovna.adb` - Podívej se na kód

### Chci testovat systém

1. [`TESTING_GUIDE.md`](TESTING_GUIDE.md) - Kompletní testing guide
2. Spusť Primary + Shadow
3. Projdi všechny testy (Test 1-10)

### Chci buildovat z kódu

1. [`BUILD.md`](BUILD.md) - Build instrukce
2. Nainstaluj GNAT/SPARK
3. `gnatmake -P mincovna.gpr`

---

## 📊 Metriky endpoints

### Primary Node
```
http://localhost:9302/metrics
```

### Shadow Node
```
http://localhost:9303/metrics
```

### Prometheus UI
```
http://localhost:9090
```

### Grafana (volitelné)
```
http://localhost:3000
```

---

## 🔑 Klíčové koncepty

### Standard 700
```
1 mince = 12 gramů stříbra
```

### "Faucet nic"
Nulová spotřeba externích zdrojů - systém je autonomní.

### Matematická jistota
Ada/SPARK formální verifikace - garantovaná absence runtime chyb.

### High Availability
Primary + Shadow uzly s automatickým failover < 20 sekund.

---

## 🎓 Learn More

### Pro začátečníky
1. [`README.md`](README.md)
2. [`QUICKSTART_UBUNTU.txt`](QUICKSTART_UBUNTU.txt)
3. Spusť `start.bat`

### Pro pokročilé
1. [`SYSTEM_OVERVIEW.md`](SYSTEM_OVERVIEW.md)
2. [`SHADOW_NODE.md`](SHADOW_NODE.md)
3. [`BUILD.md`](BUILD.md)

### Pro DevOps
1. [`DEPLOY_UBUNTU.md`](DEPLOY_UBUNTU.md)
2. [`DEPLOYMENT_CHECKLIST.md`](DEPLOYMENT_CHECKLIST.md)
3. [`TESTING_GUIDE.md`](TESTING_GUIDE.md)

---

## 🆘 Troubleshooting

**Port již používán:**
```cmd
netstat -ano | findstr :9302
taskkill /PID <PID> /F
```

**Python modul chybí:**
```cmd
pip install prometheus_client requests
```

**Shadow nevidí Primary:**
1. Zkontroluj že Primary běží
2. Zkontroluj firewall
3. Zkontroluj URL v `src/shadow_node.py`

---

## 📞 Support

**Autor:** Pan Jeskyně  
**Asistent:** Kiro (Claude Sonnet 4.5)  
**Standard:** 700 (12g stříbra)  
**Projekt:** Vakuová Mincovna

---

## ✅ Quick Checklist

Pro rychlé ověření že vše funguje:

- [ ] `start.bat` spouští Primary (9302)
- [ ] `start_shadow.bat` spouští Shadow (9303)
- [ ] `http://localhost:9302/metrics` je dostupné
- [ ] `http://localhost:9303/metrics` je dostupné
- [ ] Shadow synchronizuje (vidíš "✓ Sync OK")
- [ ] Failover test prošel (vypni Primary → Shadow převezme)

**Pokud všechno ✅ → Systém je připraven!** 🎉

---

**První článek je NEPRŮSTŘELNÝ!** 🏗️✨

Pro další kroky viz [`SYSTEM_OVERVIEW.md`](SYSTEM_OVERVIEW.md) → Roadmap
