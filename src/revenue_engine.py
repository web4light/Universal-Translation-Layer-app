#!/usr/bin/env python3
"""
Autonomous Revenue Engine — Asgard Lab se živí sám.

Systém autonomně:
  1. Přijímá platby od zákazníků (předplatné)
  2. Sleduje náklady (Gemini API, Cloud Run, úložiště)
  3. Počítá profit
  4. Reinvestuje do hardware (když profit > práh)
  5. Škáluje se nahoru (více GPU, více jazyků)

Cíl: Systém si sám kupuje hardware a rozšiřuje kapacitu.
     Člověk jen kontroluje, že se nerozbil.

Ceník:
  GEALL_111  = 111 CZK/měsíc (AI asistent)
  KAREL_222  = 222 CZK/měsíc (real-time překlad + voice)
  DUBBING_333 = 333 CZK/měsíc (stream dubbing)
  FAMILY_423 = 423 CZK/měsíc (vše, celá rodina)
  
  Znakový jazyk = ZDARMA (vždy, pro neslyšící komunitu)

Náklady:
  Gemini API     ~ 0.075 USD / 1M input tokens
  Cloud Run      ~ 0.00002400 USD / vCPU-second
  Storage        ~ 0.020 USD / GB / month
  GPU (T4)       ~ 0.35 USD / hour (on-demand)

Autor: Pan Jeskyně
Organizace: Rebirth Phoenix Foundation Charter
"""

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional
from prometheus_client import Counter, Gauge

# ============================================================================
# METRIKY
# ============================================================================

revenue_total = Counter(
    'asgard_revenue_czk_total',
    'Celkový příjem v CZK'
)

costs_total = Counter(
    'asgard_costs_usd_total',
    'Celkové náklady v USD',
    ['category']
)

profit_gauge = Gauge(
    'asgard_profit_czk',
    'Aktuální měsíční profit v CZK'
)

subscribers_gauge = Gauge(
    'asgard_subscribers_total',
    'Počet aktivních předplatitelů',
    ['tier']
)

hardware_budget = Gauge(
    'asgard_hardware_budget_usd',
    'Rozpočet na nákup hardware'
)

# ============================================================================
# CENOVÝ MODEL
# ============================================================================

class Tier(Enum):
    GEALL_111 = 111
    KAREL_222 = 222
    DUBBING_333 = 333
    FAMILY_423 = 423


# Náklady za jednoho uživatele / měsíc (USD)
COST_PER_USER = {
    Tier.GEALL_111: 0.50,      # Jen text AI → levné
    Tier.KAREL_222: 2.00,      # Real-time voice → Gemini + TTS
    Tier.DUBBING_333: 4.00,    # Stream dubbing → hodně Gemini + GPU
    Tier.FAMILY_423: 6.00,     # Vše × rodina
}

CZK_TO_USD = 0.042  # Kurz CZK/USD (cca 24 CZK = 1 USD)

# ============================================================================
# DATOVÉ MODELY
# ============================================================================

@dataclass
class Subscriber:
    user_id: str
    tier: Tier
    started: float = field(default_factory=time.time)
    active: bool = True
    translations_used: int = 0
    dubbing_minutes: float = 0.0


@dataclass
class MonthlyReport:
    month: str  # "2026-08"
    subscribers: Dict[str, int] = field(default_factory=dict)
    revenue_czk: float = 0.0
    costs_usd: float = 0.0
    profit_czk: float = 0.0
    hardware_purchased: List[str] = field(default_factory=list)
    auto_scaled: bool = False


@dataclass
class HardwareItem:
    name: str
    price_usd: float
    purpose: str
    purchased: Optional[str] = None  # ISO date
    
    
# Hardware shopping list (systém si sám vybírá co koupit)
HARDWARE_CATALOG = [
    HardwareItem("NVIDIA T4 16GB", 2200, "CUDA dubbing acceleration"),
    HardwareItem("NVIDIA A10 24GB", 3500, "Multi-language parallel dubbing"),
    HardwareItem("RAM 64GB DDR5", 180, "More concurrent users"),
    HardwareItem("NVMe 2TB", 150, "Subtitle/audio storage"),
    HardwareItem("Raspberry Pi 5 8GB", 80, "Edge translation node"),
    HardwareItem("10GbE NIC", 120, "Faster mesh communication"),
]


# ============================================================================
# AUTONOMNÍ ENGINE
# ============================================================================

class RevenueEngine:
    """
    Autonomní finanční engine.
    
    Sleduje příjmy, náklady, a když profit překročí práh,
    automaticky "nakupuje" hardware pro rozšíření kapacity.
    """

    def __init__(self, data_dir: Path = Path("/home/pj/Universal-Translation-Layer/data/revenue")):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.subscribers: Dict[str, Subscriber] = {}
        self.monthly_reports: List[MonthlyReport] = []
        self.hardware_owned: List[HardwareItem] = []
        self.hardware_budget_usd: float = 0.0
        
        # Prahy pro autonomní rozhodování
        self.REINVEST_THRESHOLD_USD = 100.0  # Nad $100 profitu → nakupuj
        self.SCALE_THRESHOLD_USERS = 50      # Nad 50 users → škáluj
        
        self._load_state()
    
    def add_subscriber(self, user_id: str, tier: Tier) -> Subscriber:
        """Nový předplatitel."""
        sub = Subscriber(user_id=user_id, tier=tier)
        self.subscribers[user_id] = sub
        subscribers_gauge.labels(tier=tier.name).inc()
        revenue_total.inc(tier.value)
        self._save_state()
        return sub
    
    def remove_subscriber(self, user_id: str):
        """Odhlásit předplatitele."""
        if user_id in self.subscribers:
            sub = self.subscribers[user_id]
            sub.active = False
            subscribers_gauge.labels(tier=sub.tier.name).dec()
            self._save_state()
    
    def calculate_monthly(self) -> MonthlyReport:
        """Spočítat měsíční report."""
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        
        # Příjmy
        revenue = sum(
            sub.tier.value for sub in self.subscribers.values() if sub.active
        )
        
        # Náklady
        costs = sum(
            COST_PER_USER[sub.tier]
            for sub in self.subscribers.values() if sub.active
        )
        
        # Fixní náklady (Cloud Run minimum + storage)
        fixed_costs = 5.0  # $5/měsíc minimum
        total_costs = costs + fixed_costs
        
        # Profit
        revenue_usd = revenue * CZK_TO_USD
        profit_usd = revenue_usd - total_costs
        profit_czk = profit_usd / CZK_TO_USD
        
        # Reinvestice
        purchased = []
        if profit_usd > self.REINVEST_THRESHOLD_USD:
            self.hardware_budget_usd += profit_usd * 0.3  # 30% do hardware
            purchased = self._auto_purchase_hardware()
        
        # Auto-scale
        active_count = sum(1 for s in self.subscribers.values() if s.active)
        auto_scaled = active_count > self.SCALE_THRESHOLD_USERS
        
        report = MonthlyReport(
            month=month,
            subscribers={
                tier.name: sum(
                    1 for s in self.subscribers.values()
                    if s.active and s.tier == tier
                )
                for tier in Tier
            },
            revenue_czk=revenue,
            costs_usd=total_costs,
            profit_czk=profit_czk,
            hardware_purchased=purchased,
            auto_scaled=auto_scaled
        )
        
        self.monthly_reports.append(report)
        
        # Update metriky
        profit_gauge.set(profit_czk)
        hardware_budget.set(self.hardware_budget_usd)
        costs_total.labels(category="api").inc(costs)
        costs_total.labels(category="infra").inc(fixed_costs)
        
        self._save_state()
        return report
    
    def _auto_purchase_hardware(self) -> List[str]:
        """Autonomně nakoupit hardware z rozpočtu."""
        purchased = []
        
        for item in HARDWARE_CATALOG:
            if item.price_usd <= self.hardware_budget_usd:
                # Koupit!
                self.hardware_budget_usd -= item.price_usd
                item.purchased = datetime.now(timezone.utc).isoformat()
                self.hardware_owned.append(item)
                purchased.append(f"{item.name} (${item.price_usd}) — {item.purpose}")
                
                # Nekupovat víc než 1 věc naráz (konzervativní)
                break
        
        return purchased
    
    def get_status(self) -> dict:
        """Stav autonomního systému."""
        active = [s for s in self.subscribers.values() if s.active]
        revenue_monthly = sum(s.tier.value for s in active)
        costs_monthly = sum(COST_PER_USER[s.tier] for s in active) + 5.0
        
        return {
            "subscribers": {
                "total": len(active),
                "by_tier": {
                    tier.name: sum(1 for s in active if s.tier == tier)
                    for tier in Tier
                }
            },
            "financials": {
                "monthly_revenue_czk": revenue_monthly,
                "monthly_costs_usd": round(costs_monthly, 2),
                "monthly_profit_czk": round((revenue_monthly * CZK_TO_USD - costs_monthly) / CZK_TO_USD, 0),
                "hardware_budget_usd": round(self.hardware_budget_usd, 2)
            },
            "hardware_owned": [
                {"name": h.name, "purpose": h.purpose, "purchased": h.purchased}
                for h in self.hardware_owned
            ],
            "autonomy": {
                "self_sustaining": revenue_monthly * CZK_TO_USD > costs_monthly,
                "can_purchase_hardware": self.hardware_budget_usd > 80,
                "next_purchase": next(
                    (h.name for h in HARDWARE_CATALOG
                     if h.price_usd <= self.hardware_budget_usd),
                    None
                )
            }
        }
    
    def _save_state(self):
        """Uložit stav na disk."""
        state = {
            "subscribers": {
                uid: {
                    "tier": s.tier.name,
                    "started": s.started,
                    "active": s.active,
                    "translations_used": s.translations_used,
                    "dubbing_minutes": s.dubbing_minutes
                }
                for uid, s in self.subscribers.items()
            },
            "hardware_budget_usd": self.hardware_budget_usd,
            "hardware_owned": [asdict(h) for h in self.hardware_owned],
        }
        
        state_file = self.data_dir / "engine_state.json"
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def _load_state(self):
        """Načíst stav z disku."""
        state_file = self.data_dir / "engine_state.json"
        if not state_file.exists():
            return
        
        try:
            with open(state_file) as f:
                state = json.load(f)
            
            for uid, data in state.get("subscribers", {}).items():
                self.subscribers[uid] = Subscriber(
                    user_id=uid,
                    tier=Tier[data["tier"]],
                    started=data["started"],
                    active=data["active"],
                    translations_used=data.get("translations_used", 0),
                    dubbing_minutes=data.get("dubbing_minutes", 0.0)
                )
            
            self.hardware_budget_usd = state.get("hardware_budget_usd", 0.0)
            
            for h in state.get("hardware_owned", []):
                self.hardware_owned.append(HardwareItem(**h))
                
        except Exception:
            pass  # Start fresh if corrupted


# ============================================================================
# DEPLOY SCRIPT — nasazení na Google Cloud Run
# ============================================================================

DEPLOY_SCRIPT = """#!/bin/bash
# Asgard Lab — Production Deployment to Google Cloud Run
# Autonomní systém: přijímá platby, škáluje se, kupuje hardware

set -e

PROJECT="karel-iv"
REGION="europe-west1"
SERVICE="asgard-lab"
IMAGE="gcr.io/$PROJECT/$SERVICE"

echo "🚀 Deploying Asgard Lab to Cloud Run..."

# Enable APIs
gcloud services enable run.googleapis.com containerregistry.googleapis.com --project=$PROJECT

# Build
gcloud builds submit --tag $IMAGE --project=$PROJECT

# Deploy
gcloud run deploy $SERVICE \\
  --image $IMAGE \\
  --platform managed \\
  --region $REGION \\
  --project $PROJECT \\
  --allow-unauthenticated \\
  --memory 2Gi \\
  --cpu 2 \\
  --min-instances 1 \\
  --max-instances 10 \\
  --set-env-vars "GEMINI_API_KEY=$GEMINI_API_KEY,GROQ_API_KEY=$GROQ_API_KEY" \\
  --timeout 300

echo "✅ Deployed!"
echo "URL: $(gcloud run services describe $SERVICE --region=$REGION --project=$PROJECT --format='value(status.url)')"
"""


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    engine = RevenueEngine()
    
    print("=" * 55)
    print("💰 ASGARD LAB — Autonomous Revenue Engine")
    print("=" * 55)
    print()
    
    status = engine.get_status()
    print(f"  Subscribers: {status['subscribers']['total']}")
    print(f"  Monthly revenue: {status['financials']['monthly_revenue_czk']} CZK")
    print(f"  Monthly costs: ${status['financials']['monthly_costs_usd']}")
    print(f"  Profit: {status['financials']['monthly_profit_czk']} CZK")
    print(f"  Hardware budget: ${status['financials']['hardware_budget_usd']}")
    print(f"  Self-sustaining: {status['autonomy']['self_sustaining']}")
    print()
    
    if status['hardware_owned']:
        print("  Hardware owned:")
        for h in status['hardware_owned']:
            print(f"    - {h['name']} ({h['purpose']})")
    
    print()
    print("=" * 55)
