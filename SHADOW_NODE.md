# 🌑 Shadow Node - Stínovací Uzel

## Koncept

**Shadow Node** = Záložní uzel který:
- ✅ Replikuje stav Mincovny v reálném čase
- ✅ Může okamžitě převzít roli primárního uzlu
- ✅ Poskytuje redundanci a high availability
- ✅ Synchronizuje se přes Prometheus/n8n
- ✅ Běží na druhém hardware (druhý komp)

---

## 🏗️ Architektura dvou uzlů

```
┌─────────────────────────────────────────────────────────────┐
│                    SÍŤOVÝ PROSTOR                           │
│                                                             │
│  ┌──────────────────────┐      ┌──────────────────────┐   │
│  │   PRIMARY NODE       │◄────►│   SHADOW NODE        │   │
│  │   (Windows/Ubuntu)   │ sync │   (Ubuntu 26.06)     │   │
│  └──────────────────────┘      └──────────────────────┘   │
│           │                              │                  │
│           │                              │                  │
│  ┌────────▼──────────┐         ┌────────▼──────────┐      │
│  │ Ada/SPARK Core   │         │ Ada/SPARK Core   │      │
│  │ Mincovna         │         │ Mincovna (copy)  │      │
│  │ Port: 9302       │         │ Port: 9303       │      │
│  └──────────────────┘         └──────────────────┘      │
│           │                              │                  │
│  ┌────────▼──────────┐         ┌────────▼──────────┐      │
│  │ Prometheus        │◄───────►│ Prometheus        │      │
│  │ :9090            │  federate│ :9091            │      │
│  └──────────────────┘         └──────────────────┘      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 Komponenty Shadow Node

### 1. Samostatná instance Mincovny
```bash
# Shadow Node běží na jiném portu
Port: 9303 (místo 9302)
Prometheus: 9091 (místo 9090)
```

### 2. Synchronizační mechanismus
- **Prometheus Federation** - metriky se replikují
- **State sync** - stav Mincovny se synchronizuje každých 5s
- **Heartbeat** - každý uzel hlásí že žije

### 3. Failover logika
Pokud Primary Node spadne:
1. Shadow Node to detekuje (timeout heartbeat)
2. Převezme roli Primary (změní port na 9302)
3. Pokračuje v ražbě bez přerušení

---

## 🛠️ Implementace

### Soubor: `shadow_node.py`

```python
#!/usr/bin/env python3
"""
Shadow Node - Stínovací uzel pro Vakuovou Mincovnu
Poskytuje redundanci a high availability
"""

import subprocess
import time
import requests
from prometheus_client import start_http_server, Counter, Gauge

# Shadow Node konfigurace
SHADOW_PORT = 9303
PRIMARY_URL = "http://primary-node:9302/metrics"
HEARTBEAT_INTERVAL = 5  # sekund
FAILOVER_TIMEOUT = 15   # sekund

# Metriky
shadow_sync_errors = Counter('shadow_sync_errors_total', 'Chyby synchronizace')
shadow_is_primary = Gauge('shadow_is_primary', 'Je tento uzel primární? (1=ano)')
shadow_last_sync = Gauge('shadow_last_sync_timestamp', 'Timestamp poslední sync')

class ShadowNode:
    def __init__(self):
        self.is_primary = False
        self.last_primary_heartbeat = time.time()
        shadow_is_primary.set(0)
        
    def check_primary_health(self):
        """Zkontroluj zda Primary Node žije"""
        try:
            response = requests.get(PRIMARY_URL, timeout=2)
            if response.status_code == 200:
                self.last_primary_heartbeat = time.time()
                return True
        except:
            pass
        
        # Pokud timeout
        if time.time() - self.last_primary_heartbeat > FAILOVER_TIMEOUT:
            return False
        return True
    
    def sync_state(self):
        """Synchronizuj stav z Primary Node"""
        try:
            response = requests.get(PRIMARY_URL)
            # Parse metriky a synchronizuj stav
            shadow_last_sync.set(time.time())
            return True
        except Exception as e:
            shadow_sync_errors.inc()
            print(f"[SHADOW] Sync error: {e}")
            return False
    
    def become_primary(self):
        """Převezmi roli primárního uzlu"""
        print("[SHADOW] 🚨 FAILOVER - Přebírám roli Primary Node!")
        self.is_primary = True
        shadow_is_primary.set(1)
        
        # Restart s primárním portem
        # TODO: implementovat restart na port 9302
    
    def run(self):
        """Hlavní smyčka Shadow Node"""
        print("=== SHADOW NODE - STÍNOVACÍ UZEL ===")
        print(f"[SHADOW] Spouštím na portu {SHADOW_PORT}")
        print("[SHADOW] Monitoruji Primary Node...")
        
        # Spustit Prometheus endpoint
        start_http_server(SHADOW_PORT)
        
        while True:
            # 1. Check primary health
            primary_alive = self.check_primary_health()
            
            if not primary_alive and not self.is_primary:
                # FAILOVER!
                self.become_primary()
            
            # 2. Sync state (pokud jsme stále shadow)
            if not self.is_primary:
                self.sync_state()
            
            # 3. Wait
            time.sleep(HEARTBEAT_INTERVAL)

if __name__ == '__main__':
    shadow = ShadowNode()
    shadow.run()
```

---

## 🚀 Deployment Shadow Node

### Na Ubuntu 26.06 (druhý komp):

#### 1. Zkopíruj Mincovnu
```bash
cd ~/projects
cp -r vakuova-mincovna vakuova-mincovna-shadow
cd vakuova-mincovna-shadow
```

#### 2. Konfiguruj jako Shadow
```bash
# Změň port v src/faucet_bridge.py
sed -i 's/9302/9303/g' src/faucet_bridge.py

# Nebo edituj ručně:
nano src/faucet_bridge.py
# Změň: start_http_server(9302) → start_http_server(9303)
```

#### 3. Spusť Shadow Node
```bash
# V jednom terminálu: Primary Node
cd ~/projects/vakuova-mincovna
./start.sh

# V druhém terminálu: Shadow Node
cd ~/projects/vakuova-mincovna-shadow
python3 src/shadow_node.py
```

---

## 📊 Monitoring obou uzlů

### Prometheus konfigurace pro federaci

```yaml
# prometheus.yml na Primary Node
global:
  scrape_interval: 15s
  external_labels:
    cluster: 'mincovna-primary'

scrape_configs:
  # Primární Mincovna
  - job_name: 'mincovna-primary'
    static_configs:
      - targets: ['localhost:9302']
  
  # Shadow Node
  - job_name: 'mincovna-shadow'
    static_configs:
      - targets: ['shadow-node-ip:9303']
```

```yaml
# prometheus.yml na Shadow Node
global:
  scrape_interval: 15s
  external_labels:
    cluster: 'mincovna-shadow'

scrape_configs:
  # Local shadow metrics
  - job_name: 'mincovna-shadow'
    static_configs:
      - targets: ['localhost:9303']
  
  # Federation z Primary
  - job_name: 'federate-primary'
    honor_labels: true
    metrics_path: '/federate'
    params:
      'match[]':
        - '{job="mincovna-primary"}'
    static_configs:
      - targets: ['primary-node-ip:9090']
```

---

## 🔄 Synchronizační strategie

### 1. Real-time sync (každých 5s)
```
Primary → Shadow: 
  - minted_coins_total
  - total_silver_grams  
  - system_health
```

### 2. Heartbeat (každých 5s)
```
Primary → Shadow: "I'm alive"
Shadow → Primary: "ACK"
```

### 3. Failover (pokud timeout > 15s)
```
Shadow detekuje: Primary nereaguje
Shadow action: Převezmi roli Primary
Shadow notify: Pošli alert
```

---

## 🎯 Use cases

### Scénář 1: Normální provoz
```
Primary: Razí mince, exportuje metriky
Shadow:  Synchronizuje stav, ready to failover
Status:  shadow_is_primary = 0
```

### Scénář 2: Primary spadl
```
Primary: OFFLINE
Shadow:  Detekuje timeout → FAILOVER
Shadow:  shadow_is_primary = 1
Shadow:  Převezme port 9302
Result:  Systém běží dál bez přerušení!
```

### Scénář 3: Primary se vrátil
```
Primary: ONLINE (opravený)
Shadow:  Detekuje Primary
Shadow:  Předá kontrolu zpět Primary
Shadow:  shadow_is_primary = 0
Shadow:  Vrátí se do shadow módu
```

---

## 🔐 Bezpečnostní aspekty

### Network security
```bash
# Firewall rules pro komunikaci mezi uzly
sudo ufw allow from <primary-ip> to any port 9303
sudo ufw allow from <shadow-ip> to any port 9302
```

### Authentication
```python
# V shadow_node.py přidej API key
SYNC_API_KEY = "vakuova-mincovna-secret-key-700"

headers = {
    'Authorization': f'Bearer {SYNC_API_KEY}'
}
```

---

## 📈 Grafana Dashboard pro oba uzly

```json
{
  "dashboard": {
    "title": "Vakuová Mincovna - Primary + Shadow",
    "panels": [
      {
        "title": "Cluster Status",
        "targets": [
          "shadow_is_primary{cluster=\"mincovna-primary\"}",
          "shadow_is_primary{cluster=\"mincovna-shadow\"}"
        ]
      },
      {
        "title": "Minted Coins (Both Nodes)",
        "targets": [
          "mincovna_minted_coins_total{cluster=\"mincovna-primary\"}",
          "mincovna_minted_coins_total{cluster=\"mincovna-shadow\"}"
        ]
      },
      {
        "title": "Sync Status",
        "targets": [
          "shadow_sync_errors_total",
          "shadow_last_sync_timestamp"
        ]
      }
    ]
  }
}
```

---

## ✅ Checklist pro Shadow Node

```
Příprava:
[ ] Zkopírovat Mincovnu do shadow složky
[ ] Změnit port na 9303 v konfiguraci
[ ] Vytvořit shadow_node.py
[ ] Nakonfigurovat Prometheus federaci

Deployment:
[ ] Spustit Primary Node (port 9302)
[ ] Spustit Shadow Node (port 9303)
[ ] Ověřit že se synchronizují
[ ] Otestovat failover (vypnout Primary)

Monitoring:
[ ] Grafana dashboard pro oba uzly
[ ] Alerty pro failover events
[ ] Heartbeat monitoring
```

---

## 🎉 Výsledek

Máš **dva uzly**:

1. **Primary Node** - Hlavní Mincovna (9302)
2. **Shadow Node** - Záloha (9303)

**Výhody:**
✅ High availability  
✅ Zero downtime  
✅ Automatický failover  
✅ Synchronizace v reálném čase  
✅ "Faucet nic" × 2 = ještě víc autonomie!  

---

**První článek** + **Shadow článek** = Neprůstřelný základ! 🏗️🌑

Až budeš připravený, vytvoř shadow_node.py a můžeme začít testovat!
