# Deployment na Ubuntu 26.06

## 🚀 Instalace Vakuové Mincovny na čistém Ubuntu systému

### 1. Příprava systému

```bash
# Update systému
sudo apt update && sudo apt upgrade -y

# Základní nástroje
sudo apt install -y build-essential git curl wget
```

### 2. Instalace GNAT/SPARK (Ada 2022)

```bash
# Stáhnout GNAT Community Edition
cd ~/Downloads
wget https://community.download.adacore.com/v1/latest/gnat-community-2024-x86_64-linux-bin

# Nebo použij AdaDev2024.zip který máš
# Rozbal a nainstaluj:
chmod +x gnat-*-linux-bin
./gnat-*-linux-bin

# Přidat do PATH
echo 'export PATH="/opt/GNAT/2024/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Ověřit instalaci
gprbuild --version
gnatprove --version
```

### 3. Instalace Python dependencies

```bash
# Python 3 (měl by být už nainstalovaný v Ubuntu 26.06)
python3 --version

# Pip
sudo apt install -y python3-pip

# Prometheus client
pip3 install prometheus_client
```

### 4. Zkopírovat Vakuovou Mincovnu

```bash
# Z Windows na Ubuntu (použij USB/sdílení/git)
# Nebo:
cd ~
mkdir -p projects
cd projects

# Zkopíruj celou složku vakuova-mincovna sem
```

### 5. Build a spuštění

```bash
cd ~/projects/vakuova-mincovna

# Dát práva ke spuštění
chmod +x start.sh

# Spustit!
./start.sh
```

## 📊 Očekávaný výstup

```
=== VAKUOVÁ MINCOVNA - INICIALIZACE ===

[1/4] Kontrola GNAT/SPARK...
  ✓ GNAT/SPARK nalezen
  
[2/4] Build Ada/SPARK Core...
  Compiling: mincovna.adb
  Binding: mincovna.bexch
  Linking: mincovna
  ✓ Build úspěšný
  
[3/4] Kontrola Python dependencies...
  ✓ Python3 nalezen
  ✓ Dependencies OK
  
[4/4] Spouštění Faucet Bridge...

=== FAUCET BRIDGE - VAKUOVÁ MINCOVNA ===
[PROMETHEUS] Spouštím HTTP server na portu 9302
[FAUCET] Most připraven
[SPARK] Matematická jistota: AKTIVNÍ
[GNAT] Formální verifikace: AKTIVNÍ
========================================

[TEST] Spouštím testovací ražbu...
--- VAKUOVÁ MINCOVNA INICIALIZOVÁNA ---
[GNAT] Formální verifikace aktivní
[SPARK] Matematická jistota: AKTIVNÍ
[MINCOVNA] První mince vyražena!
=== VAKUOVÁ MINCOVNA - STATUS ===
Standard 700:  1.20000000000000E+01g stříbra
Celkové stříbro:  1.20000000000000E+01g
Razených mincí:  1
================================
[FAUCET] Spotřeba externích zdrojů: NIC
--- SYSTÉM PŘIPRAVEN K AUTONOMNÍMU PROVOZU ---
[OK] Testovací mince vyražena

[STATUS] Vyraženo mincí: 1
[STATUS] Celkové stříbro: 12.0g
[STATUS] Standard 700: 12.0g
[STATUS] Zdraví systému: OK

[FAUCET] Spotřeba externích zdrojů: NIC
[READY] Systém připraven k autonomnímu provozu

Prometheus metriky: http://localhost:9302/metrics
```

## 🔍 Verifikace že běží

### V novém terminálu:

```bash
# Zkontrolovat Prometheus metriky
curl http://localhost:9302/metrics | grep mincovna

# Měl by vrátit:
# mincovna_minted_coins_total 1.0
# mincovna_total_silver_grams 12.0
# mincovna_system_health 1.0
```

## 🎯 Další kroky po úspěšném startu

### 1. Instalace Prometheus

```bash
# Stáhnout Prometheus
cd ~/Downloads
wget https://github.com/prometheus/prometheus/releases/download/v2.45.0/prometheus-2.45.0.linux-amd64.tar.gz
tar xvfz prometheus-*.tar.gz
cd prometheus-*/

# Zkopírovat config z vakuova-mincovna
cp ~/projects/vakuova-mincovna/prometheus/prometheus.yml ./

# Spustit Prometheus
./prometheus --config.file=prometheus.yml
```

Prometheus web UI: http://localhost:9090

### 2. Instalace Grafana

```bash
# Přidat Grafana repository
sudo apt-get install -y software-properties-common
sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -

# Instalovat
sudo apt-get update
sudo apt-get install grafana

# Spustit
sudo systemctl start grafana-server
sudo systemctl enable grafana-server
```

Grafana web UI: http://localhost:3000  
(default login: admin/admin)

### 3. Konfigurace Grafana

1. Přidej Prometheus jako data source:
   - URL: http://localhost:9090
   - Access: Server

2. Importuj dashboard pro Mincovnu:
   - Vytvoř nový dashboard
   - Přidej panely pro metriky:
     - `mincovna_minted_coins_total`
     - `mincovna_total_silver_grams`
     - `mincovna_system_health`
     - `mincovna_mint_duration_seconds`

## 🐛 Troubleshooting

### GNAT nenalezen
```bash
# Zkontroluj PATH
echo $PATH | grep GNAT

# Pokud není, přidej:
export PATH="/opt/GNAT/2024/bin:$PATH"
```

### Port 9302 already in use
```bash
# Najdi proces
sudo lsof -i :9302

# Zabij ho
sudo kill -9 <PID>
```

### Python modul nenalezen
```bash
# Reinstaluj dependencies
pip3 install --upgrade prometheus_client
```

### Build chyby Ada
```bash
# Zkontroluj GNAT verzi
gnatmake --version

# Mělo by být >= GNAT Community 2024
# Pokud ne, stáhni novější verzi
```

## 📦 Alternativa: Docker deployment

Vytvoř `Dockerfile`:

```dockerfile
FROM ubuntu:26.06

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    python3 \
    python3-pip \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install GNAT (vyžaduje manuální download)
# ADD gnat-community-2024-x86_64-linux-bin /tmp/
# RUN chmod +x /tmp/gnat-* && /tmp/gnat-* --prefix=/opt/GNAT

# Install Python deps
RUN pip3 install prometheus_client

# Copy project
COPY . /app
WORKDIR /app

# Build
RUN gprbuild -P mincovna.gpr

# Expose Prometheus port
EXPOSE 9302

# Run
CMD ["python3", "src/faucet_bridge.py"]
```

Pak:
```bash
docker build -t vakuova-mincovna .
docker run -p 9302:9302 vakuova-mincovna
```

## 🎉 Úspěch!

Když vidíš:
```
[READY] Systém připraven k autonomnímu provozu
Prometheus metriky: http://localhost:9302/metrics
```

**První článek je postaven a běží!** 🏗️✨

Od tohoto momentu se systém začne autonomně rozšiřovat podle tvé vize.

---

**Pro podporu:** Veškerá dokumentace je v `BUILD.md` a `SYSTEM_OVERVIEW.md`
