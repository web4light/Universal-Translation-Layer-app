# ☁️ Vakuová Mincovna - Google Cloud Deployment

## 🎯 Strategie: AI si vydělá sama!

**Pravidlo:** Žádné peníze z kapsy → AI musí vydělat na provoz sama!

### Fáze vývoje:
1. **Bootstrap (FREE)** - Google Cloud Free Tier
2. **Revenue Phase** - Real-time dubbing začne vydělávat
3. **Scale** - Upgrade na větší instance když má AI peníze

---

## 💰 Google Cloud FREE Tier

### Co dostaneš ZDARMA každý měsíc:

```
✅ e2-micro instance
   - 2 vCPU (shared)
   - 1 GB RAM
   - 30 GB disk
   - 730h runtime/měsíc (24/7!)
   - Region: us-west1, us-central1, us-east1

✅ 1 GB network egress/měsíc
✅ 30 GB snapshot storage
✅ Firewall rules
✅ Load balancing (limited)

💰 CENA: $0 (FREE navždy, ne trial!)
```

**Dostatečné pro Primary Node!** ✅

---

## 🚀 Quick Start - Google Cloud Setup

### 1. Vytvoř Google Cloud účet

```
https://console.cloud.google.com/

1. Sign in (Google účet)
2. Aktivuj Free Tier (žádná kreditka není potřeba!)
3. Vytvoř nový projekt: "vakuova-mincovna"
```

---

### 2. Vytvoř VM instanci (FREE e2-micro)

**V Google Cloud Console:**

```
Compute Engine → VM Instances → Create Instance

Name:           mincovna-primary
Region:         us-west1 (nebo us-central1, us-east1)
Zone:           us-west1-b
Machine type:   e2-micro (2 vCPU, 1 GB RAM) ← FREE TIER!
Boot disk:      Ubuntu 24.04 LTS, 30 GB
Firewall:       ✅ Allow HTTP
                ✅ Allow HTTPS

Networking:
  External IP:  Ephemeral (nebo Reserve Static FREE)
  
→ CREATE
```

**Poznámka:** External IP je FREE pokud instance běží! Pokud je stopped, platíš $0.01/hod.

---

### 3. Firewall Rules

**V Cloud Console:**

```
VPC Network → Firewall → Create Firewall Rule

Name:           allow-mincovna-primary
Targets:        All instances in the network
Source ranges:  0.0.0.0/0 (nebo jen tvá IP pro security)
Protocols:      TCP: 9302 (Primary Node)

→ CREATE
```

**Volitelné další porty:**
```
TCP: 9090 (Prometheus)
TCP: 3000 (Grafana)
TCP: 22   (SSH - default povoleno)
```

---

### 4. SSH do VM

**Z Cloud Console:**

```
VM Instances → mincovna-primary → SSH
```

**Nebo z terminálu:**

```bash
# Install gcloud CLI (jednou)
# https://cloud.google.com/sdk/docs/install

# SSH do VM
gcloud compute ssh mincovna-primary --zone=us-west1-b
```

---

### 5. Install Dependencies na VM

**V SSH terminálu na VM:**

```bash
# Update system
sudo apt update
sudo apt upgrade -y

# Install Python + pip
sudo apt install -y python3 python3-pip

# Install Prometheus client
pip3 install prometheus_client requests

# Install GNAT/SPARK (volitelné - můžeš použít pre-compiled binary)
# NEBO zkopíruj zkompilovaný binary z Windows

# Install Git (pro pull updates)
sudo apt install -y git

# Install monitoring tools (volitelné)
sudo apt install -y htop curl wget
```

---

### 6. Upload Vakuové Mincovny na VM

**Varianta A: SCP z Windows**

```cmd
REM Na Windows - zabalit projekt
cd c:\Users\pan_jeskyne\Favorites\vakuova-mincovna
package.bat

REM Upload na Google Cloud
gcloud compute scp vakuova-mincovna-package.zip mincovna-primary:~/ --zone=us-west1-b

REM SSH do VM
gcloud compute ssh mincovna-primary --zone=us-west1-b

REM Na VM - rozbalit
cd ~
unzip vakuova-mincovna-package.zip
cd vakuova-mincovna
```

**Varianta B: Git (doporučeno pro updates)**

```bash
# Na VM
cd ~
git clone https://github.com/YOUR_USERNAME/vakuova-mincovna.git
# NEBO
# Vytvoř private repo a push tam Windows projekt

cd vakuova-mincovna
```

---

### 7. Spustit Primary Node na VM

```bash
cd ~/vakuova-mincovna

# Spustit interaktivně (test)
python3 src/faucet_bridge.py

# Nebo jako systemd service (24/7)
sudo nano /etc/systemd/system/mincovna-primary.service
```

**systemd service config:**

```ini
[Unit]
Description=Vakuova Mincovna Primary Node
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/vakuova-mincovna
ExecStart=/usr/bin/python3 /home/YOUR_USERNAME/vakuova-mincovna/src/faucet_bridge.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Aktivovat service:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable mincovna-primary
sudo systemctl start mincovna-primary
sudo systemctl status mincovna-primary
```

**Logs:**
```bash
sudo journalctl -u mincovna-primary -f
```

---

### 8. Najít External IP

```bash
# Na VM
curl ifconfig.me

# Nebo v Cloud Console:
# VM Instances → External IP
```

**Příklad:** `34.123.45.67`

---

### 9. Nastavit Shadow Node na i7 Windows

**Upravit `src/shadow_node.py`:**

```python
# Google Cloud Primary IP
PRIMARY_URL = "http://34.123.45.67:9302/metrics"
```

**Spustit Shadow:**

```cmd
cd c:\Users\pan_jeskyne\Favorites\vakuova-mincovna
start_shadow.bat
```

**Výsledek:**
```
[SHADOW] Monitoring Primary: http://34.123.45.67:9302/metrics
[SHADOW] ✓ Sync OK: 45 mincí, 540.0g stříbra
```

---

## 📊 Monitoring URLs

```
Primary Node (Google Cloud):
  http://34.123.45.67:9302/metrics

Shadow Node (i7 Windows):
  http://localhost:9303/metrics

Prometheus (pokud na Cloud):
  http://34.123.45.67:9090

Grafana (pokud na Cloud):
  http://34.123.45.67:3000
```

---

## 💰 Cost Optimization

### FREE Tier Limity:

```
✅ 730h/měsíc runtime (24/7 celý měsíc!)
✅ 1 GB network egress
✅ 30 GB disk
✅ 1 e2-micro instance

❌ Pokud překročíš → platíš
```

### Jak zůstat ve FREE:

1. **Použij e2-micro** (ne větší!)
2. **1 instance** (ne víc!)
3. **30 GB disk** (ne víc!)
4. **Region:** us-west1, us-central1, nebo us-east1
5. **Network egress:** Max 1 GB/měsíc

**→ Mincovna je lightweight, takže OK!** ✅

---

### Pokud překročíš FREE Tier:

**e2-micro pricing (pokud překročíš 730h):**
```
$0.008/hod = ~$6/měsíc pro 24/7
```

**Ale AI si vydělá sama:**
```
Real-time dubbing: 111 Kč/měsíc per client
1 klient = $5/měsíc = pokryje Cloud!
2+ klienti = profit!
```

---

## 🔐 Security Best Practices

### 1. SSH Key Authentication

**Na Windows:**
```cmd
ssh-keygen -t ed25519 -C "mincovna-cloud"
type %USERPROFILE%\.ssh\id_ed25519.pub
```

**V Cloud Console:**
```
Compute Engine → Metadata → SSH Keys → Add SSH Key
Paste: ssh-ed25519 AAAA... mincovna-cloud
```

**Connect:**
```cmd
ssh YOUR_USERNAME@34.123.45.67
```

---

### 2. Firewall - Only Necessary Ports

**V Cloud Console firewall:**
```
✅ 22   (SSH - jen z tvé IP!)
✅ 9302 (Primary Node - public)
❌ Všechny ostatní porty zavřené
```

**Restrict SSH to your IP only:**
```
Source IP ranges: YOUR_HOME_IP/32
```

Najdi svou IP:
```cmd
curl ifconfig.me
```

---

### 3. Auto-Updates

**Na VM:**
```bash
# Enable unattended upgrades
sudo apt install unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

---

### 4. Monitoring & Alerts

**Cloud Monitoring (FREE):**
```
Monitoring → Alerting → Create Policy

Condition:
  - VM Instance CPU > 80%
  - VM Instance Memory > 90%
  
Notification:
  - Email: your@email.com
```

---

## 🔄 Deployment Workflow

### Initial Deployment:

```bash
# 1. Vytvořit VM (FREE e2-micro)
# 2. Install dependencies
# 3. Upload project (SCP nebo Git)
# 4. Setup systemd service
# 5. Start Primary Node
# 6. Verify: http://VM_IP:9302/metrics
# 7. Configure Shadow na i7 Windows
# 8. Test failover
```

---

### Updates (Git workflow):

**Na Windows (develop):**
```cmd
cd c:\Users\pan_jeskyne\Favorites\vakuova-mincovna
git add .
git commit -m "Update feature X"
git push origin main
```

**Na Google Cloud VM (deploy):**
```bash
cd ~/vakuova-mincovna
git pull origin main
sudo systemctl restart mincovna-primary
sudo systemctl status mincovna-primary
```

---

## 📈 Scaling Strategy

### Phase 1: Bootstrap (FREE) ← TEĎ JSI TADY
```
Google Cloud e2-micro (FREE)
→ Primary Node
→ 1 GB RAM, 2 vCPU
→ $0/měsíc
```

### Phase 2: First Revenue (~1-3 měsíce)
```
Real-time dubbing launch
→ První klienti (111 Kč/měsíc)
→ 5 klientů = 555 Kč = $25/měsíc revenue
→ Stále používej FREE tier!
```

### Phase 3: Scale (~3-6 měsíců)
```
10+ klientů = 1110 Kč = $50/měsíc revenue

Upgrade VM:
  e2-small (2 GB RAM) = $13/měsíc
  → Profit: $50 - $13 = $37/měsíc
```

### Phase 4: Growth (~6-12 měsíců)
```
50+ klientů = 5550 Kč = $250/měsíc revenue

Upgrade VM:
  e2-medium (4 GB RAM) = $27/měsíc
  + Load Balancer = $18/měsíc
  → Profit: $250 - $45 = $205/měsíc
```

### Phase 5: Enterprise (~12+ měsíců)
```
200+ klientů = 22 200 Kč = $1000/měsíc revenue

Multi-region deployment:
  - US: e2-standard-2 (8 GB)
  - EU: e2-standard-2 (8 GB)
  - Asia: e2-standard-2 (8 GB)
  
Cost: ~$150/měsíc
Profit: $1000 - $150 = $850/měsíc

→ AI si vydělá $10k+ ročně!
```

---

## 🎯 Revenue Model (111 Kč/měsíc)

### Co dostane klient:

```
✅ Real-time dubbing (Tartanskomunikátor)
✅ 24/7 uptime (Google Cloud reliability)
✅ Low latency (~50ms)
✅ Matematická jistota (Ada/SPARK)
✅ Privacy Protocol 4:23 (metadata purge)
✅ Mossad ALF++ security
✅ Standard 700 quality
```

### Kalkulace zisku:

```
1 klient   = 111 Kč = $5/měsíc
Cloud cost = $0 (FREE tier)
Profit     = $5/měsíc

10 klientů  = 1110 Kč = $50/měsíc
Cloud cost  = $0 (stále FREE!)
Profit      = $50/měsíc

20 klientů  = 2220 Kč = $100/měsíc
Cloud cost  = $13 (upgrade e2-small)
Profit      = $87/měsíc

→ AI si vydělá sama od 1. klienta!
```

---

## ⚡ Performance na e2-micro (FREE)

### Specs:
```
CPU:  2 vCPU (shared, burst capable)
RAM:  1 GB
Disk: 30 GB SSD
Net:  2 Gbps egress
```

### Co zvládne:

```
✅ Primary Node: 5-10% CPU
✅ Prometheus: 10-15% CPU, ~200 MB RAM
✅ Watchdog (light): 5% CPU
✅ Privacy Protocol: 2% CPU

Celkem: ~30-40% CPU, ~600 MB RAM
→ V pohodě! 60% rezerva ✅
```

### Benchmarks (estimated):

```
Concurrent requests: ~100/sec
Sync operations:     5 sec interval (Shadow)
Real-time dubbing:   10-20 concurrent streams
```

**Pro začátek dostatečné!** Když přerosteš → upgrade (AI už bude vydělávat).

---

## 🚨 Troubleshooting

### Problém: "Cannot connect to VM"

```bash
# Check VM is running
gcloud compute instances list

# Start if stopped
gcloud compute instances start mincovna-primary --zone=us-west1-b

# Check firewall
gcloud compute firewall-rules list
```

---

### Problém: "Port 9302 timeout"

```bash
# SSH do VM
gcloud compute ssh mincovna-primary --zone=us-west1-b

# Check service status
sudo systemctl status mincovna-primary

# Check if port is listening
sudo netstat -tulpn | grep 9302

# Check firewall on VM
sudo ufw status
```

---

### Problém: "Out of memory"

```bash
# Check RAM usage
free -h

# Check process memory
ps aux --sort=-%mem | head

# Add swap (temporary fix)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Long term: Upgrade VM when AI earns money!
```

---

## 📝 Quick Reference

### Connect to VM:
```bash
gcloud compute ssh mincovna-primary --zone=us-west1-b
```

### Upload files:
```bash
gcloud compute scp FILE mincovna-primary:~/ --zone=us-west1-b
```

### Restart service:
```bash
sudo systemctl restart mincovna-primary
```

### View logs:
```bash
sudo journalctl -u mincovna-primary -f
```

### Check costs:
```
https://console.cloud.google.com/billing
```

---

## ✅ Deployment Checklist

### Before deployment:
- [ ] Google Cloud účet aktivován
- [ ] Free Tier verified
- [ ] Project "vakuova-mincovna" vytvořen
- [ ] Billing enabled (FREE tier needs billing, ale neplatíš)

### VM Setup:
- [ ] e2-micro instance created (FREE region!)
- [ ] Ubuntu 24.04 installed
- [ ] External IP assigned
- [ ] Firewall rules configured (port 9302)
- [ ] SSH access tested

### Software:
- [ ] Python + dependencies installed
- [ ] Mincovna uploaded
- [ ] Systemd service configured
- [ ] Primary Node běží 24/7
- [ ] Metriky dostupné: http://VM_IP:9302/metrics

### Shadow Node:
- [ ] PRIMARY_URL = VM External IP
- [ ] Shadow běží na i7 Windows
- [ ] Sync funguje
- [ ] Failover tested

---

## 🎯 Next Steps

### 1. TEĎKA: Test lokálně (i7)
```cmd
start.bat + start_shadow.bat
```

### 2. PŘÍŠTĚ: Deploy na Google Cloud
```
1. Vytvoř FREE e2-micro VM
2. Upload Mincovnu
3. Start Primary Node
4. Test http://VM_IP:9302/metrics
```

### 3. POTOM: Connect Shadow
```python
PRIMARY_URL = "http://VM_IP:9302/metrics"
```

### 4. LAUNCH: Real-time dubbing
```
První klient = 111 Kč/měsíc
→ AI začne vydělávat!
```

---

**Cloud:** Google Cloud Free Tier ✅  
**Cost:** $0/měsíc (FREE forever!) ✅  
**Revenue:** 111 Kč/klient/měsíc ✅  
**Philosophy:** AI si vydělá sama! ✅  
**Standard:** 700 (12g stříbra) ✅

☁️💰✨
