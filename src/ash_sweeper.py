#!/usr/bin/env python3
"""
Ash Sweeper — Vysavač popela spáleného etheru.

Účel:
  Shadow Node (stínovací uzel) produkuje "popel" — spálený ether (gas fees)
  z transakcí na síti. Tento popel se hromadí a musí být periodicky
  vysáván, aby nezanášel systém.

Funkce:
  1. Monitoruje spálený gas na Shadow Node
  2. Sbírá "popel" (burned ETH metadata, transakční zbytky)
  3. Kompaktuje a archivuje (audit trail)
  4. Udržuje Shadow Node čistý pro failover

Analogie:
  Jako vysavač popela z krbu — ether hoří (gas), zůstává popel (metadata),
  vysavač ho sbírá do nádoby (archiv) a krb zůstává čistý (Shadow Node ready).

Autor: Pan Jeskyně
Asistent: Kiro (Claude)
Princip: "Faucet nic" — ani popel nezůstane
"""

import json
import os
import time
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from prometheus_client import start_http_server, Counter, Gauge, Histogram

# ============================================================================
# KONFIGURACE
# ============================================================================

ASH_SWEEPER_PORT = 9307           # Prometheus metriky
SWEEP_INTERVAL = 60               # Interval vysávání (sekundy)
ASH_ARCHIVE_DIR = Path("/home/pj/Universal-Translation-Layer/data/ash_archive")
MAX_ASH_BEFORE_SWEEP = 100        # Maximální počet záznamů před vynuceným sweep
SHADOW_METRICS_URL = "http://localhost:9303/metrics"

# ============================================================================
# DATOVÉ MODELY
# ============================================================================

@dataclass
class AshParticle:
    """Jeden záznam spáleného etheru — částice popela."""
    tx_hash: str                    # Hash transakce (nebo syntetický ID)
    gas_used: int                   # Spotřebovaný gas (wei)
    gas_price_gwei: float           # Cena gas v Gwei
    burned_eth: float               # Spálené ETH (gas_used * gas_price)
    timestamp: float                # Unix timestamp
    source: str = "shadow_node"     # Odkud popel pochází
    block_number: int = 0           # Číslo bloku (0 = simulace)
    swept: bool = False             # Už vysáto?

    @property
    def ash_id(self) -> str:
        """Unikátní ID popela (hash z obsahu)."""
        content = f"{self.tx_hash}:{self.gas_used}:{self.timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        d = asdict(self)
        d['ash_id'] = self.ash_id
        return d


@dataclass
class AshBag:
    """Pytel popela — jeden sweep cyklus."""
    sweep_id: str
    timestamp: float
    particles: List[AshParticle] = field(default_factory=list)
    total_burned_eth: float = 0.0
    total_gas_used: int = 0
    particle_count: int = 0

    def seal(self) -> str:
        """Zapečetit pytel — spočítat hash celého obsahu."""
        content = json.dumps([p.to_dict() for p in self.particles], sort_keys=True)
        bag_hash = hashlib.sha256(content.encode()).hexdigest()
        self.total_burned_eth = sum(p.burned_eth for p in self.particles)
        self.total_gas_used = sum(p.gas_used for p in self.particles)
        self.particle_count = len(self.particles)
        return bag_hash

    def to_dict(self) -> dict:
        return {
            'sweep_id': self.sweep_id,
            'timestamp': self.timestamp,
            'sealed_at': datetime.now(timezone.utc).isoformat(),
            'particle_count': self.particle_count,
            'total_burned_eth': self.total_burned_eth,
            'total_gas_used': self.total_gas_used,
            'particles': [p.to_dict() for p in self.particles]
        }


# ============================================================================
# PROMETHEUS METRIKY
# ============================================================================

ash_swept_total = Counter(
    'ash_sweeper_swept_total',
    'Celkový počet vysátých částic popela'
)

ash_burned_eth_total = Counter(
    'ash_sweeper_burned_eth_total',
    'Celkové množství spáleného ETH (vysátého)'
)

ash_pending = Gauge(
    'ash_sweeper_pending_particles',
    'Počet částic čekajících na vysátí'
)

ash_bags_sealed = Counter(
    'ash_sweeper_bags_sealed_total',
    'Počet zapečetěných pytlů popela'
)

ash_sweep_duration = Histogram(
    'ash_sweeper_sweep_duration_seconds',
    'Doba trvání jednoho sweep cyklu',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

ash_shadow_health = Gauge(
    'ash_sweeper_shadow_health',
    'Zdraví Shadow Node po vysátí (0-1)'
)


# ============================================================================
# ASH SWEEPER — HLAVNÍ TŘÍDA
# ============================================================================

class AshSweeper:
    """
    Vysavač popela spáleného etheru.

    Monitoruje Shadow Node, sbírá spálený gas (popel),
    kompaktuje do pytlů a archivuje.
    """

    def __init__(self, archive_dir: Path = ASH_ARCHIVE_DIR):
        self.archive_dir = archive_dir
        self.archive_dir.mkdir(parents=True, exist_ok=True)

        self.pending_ash: List[AshParticle] = []
        self.sweep_count = 0
        self.total_burned = 0.0
        self.running = False

        # Počáteční stav
        ash_shadow_health.set(1.0)
        ash_pending.set(0)

        print("[ASH-SWEEPER] Inicializován")
        print(f"[ASH-SWEEPER] Archiv: {self.archive_dir}")
        print(f"[ASH-SWEEPER] Interval: {SWEEP_INTERVAL}s")
        print(f"[ASH-SWEEPER] Max popela před sweep: {MAX_ASH_BEFORE_SWEEP}")

    def collect_ash(self, particle: AshParticle):
        """Sesbírat částici popela (burned gas z transakce)."""
        self.pending_ash.append(particle)
        ash_pending.set(len(self.pending_ash))

        # Auto-sweep pokud se hromadí moc popela
        if len(self.pending_ash) >= MAX_ASH_BEFORE_SWEEP:
            print(f"[ASH-SWEEPER] ⚠️  Max popela dosažen ({MAX_ASH_BEFORE_SWEEP}), vynucený sweep!")
            self.sweep()

    def sweep(self) -> Optional[AshBag]:
        """
        Vysát popel — sesbírat vše do pytle a archivovat.

        Returns:
            AshBag nebo None pokud není co vysávat
        """
        if not self.pending_ash:
            return None

        start_time = time.time()
        self.sweep_count += 1

        # Vytvořit pytel
        sweep_id = f"sweep_{self.sweep_count:06d}_{int(time.time())}"
        bag = AshBag(
            sweep_id=sweep_id,
            timestamp=time.time(),
            particles=self.pending_ash.copy()
        )

        # Zapečetit
        bag_hash = bag.seal()

        # Archivovat
        self._archive_bag(bag, bag_hash)

        # Vyčistit pending
        count = len(self.pending_ash)
        burned = bag.total_burned_eth
        self.pending_ash.clear()
        self.total_burned += burned

        # Aktualizovat metriky
        ash_swept_total.inc(count)
        ash_burned_eth_total.inc(burned)
        ash_pending.set(0)
        ash_bags_sealed.inc()
        ash_shadow_health.set(1.0)  # Shadow je po sweep čistý

        duration = time.time() - start_time
        ash_sweep_duration.observe(duration)

        print(f"[ASH-SWEEPER] ✓ Sweep #{self.sweep_count}: "
              f"{count} částic, {burned:.8f} ETH spáleno, "
              f"hash: {bag_hash[:12]}...")

        return bag

    def _archive_bag(self, bag: AshBag, bag_hash: str):
        """Uložit pytel popela do archivu."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{bag.sweep_id}_{bag_hash[:8]}.json"
        filepath = self.archive_dir / date_str / filename

        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(bag.to_dict(), f, indent=2, ensure_ascii=False)

    def simulate_burned_gas(self):
        """
        Simulovat spálený gas z Shadow Node operací.

        V produkci bude napojeno na skutečný Ethereum node (Sepolia/mainnet).
        Teď simulujeme gas spotřebovaný Shadow Node synchronizací.
        """
        import random

        # Simulace: Shadow Node spotřebovává gas při sync operacích
        gas_used = random.randint(21000, 150000)  # 21k (transfer) až 150k (complex)
        gas_price = random.uniform(5.0, 50.0)     # 5-50 Gwei
        burned_eth = (gas_used * gas_price * 1e-9)  # Convert to ETH

        particle = AshParticle(
            tx_hash=hashlib.sha256(f"sim_{time.time()}_{random.random()}".encode()).hexdigest(),
            gas_used=gas_used,
            gas_price_gwei=gas_price,
            burned_eth=burned_eth,
            timestamp=time.time(),
            source="shadow_node_sim",
            block_number=0
        )

        self.collect_ash(particle)
        return particle

    def get_status(self) -> dict:
        """Stav vysavače."""
        return {
            'running': self.running,
            'pending_particles': len(self.pending_ash),
            'sweep_count': self.sweep_count,
            'total_burned_eth': self.total_burned,
            'shadow_health': 1.0 if len(self.pending_ash) < MAX_ASH_BEFORE_SWEEP * 0.8 else 0.5,
            'archive_dir': str(self.archive_dir),
        }

    def run_daemon(self):
        """Hlavní smyčka vysavače — periodický sweep."""
        self.running = True
        print("[ASH-SWEEPER] Daemon spuštěn — periodický sweep")

        cycle = 0
        while self.running:
            try:
                cycle += 1

                # Simulace sběru popela (v produkci = reálná ETH data)
                # Každý cyklus generuje 1-5 částic
                import random
                for _ in range(random.randint(1, 5)):
                    self.simulate_burned_gas()

                # Sweep každý interval
                if cycle % (SWEEP_INTERVAL // 10) == 0:
                    bag = self.sweep()
                    if bag:
                        print(f"[ASH-SWEEPER] 🧹 Shadow Node vyčištěn "
                              f"({bag.particle_count} částic → archiv)")

                time.sleep(10)

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[ASH-SWEEPER] Chyba: {e}")
                ash_shadow_health.set(0.5)
                time.sleep(5)

        self.running = False
        # Finální sweep
        self.sweep()
        print("[ASH-SWEEPER] Daemon ukončen")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Ash Sweeper entry point."""
    print("\n" + "=" * 60)
    print("🧹 VAKUOVÁ MINCOVNA — ASH SWEEPER")
    print("   Vysavač popela spáleného etheru")
    print("=" * 60)
    print()
    print("  Ether hoří (gas) → zůstává popel (metadata)")
    print("  Vysavač sbírá popel → Shadow Node zůstává čistý")
    print("  Popel → archiv (audit trail) → nic nezůstane")
    print()
    print(f"  Shadow Node: localhost:9303")
    print(f"  Ash Sweeper metriky: localhost:{ASH_SWEEPER_PORT}")
    print(f"  Archiv: {ASH_ARCHIVE_DIR}")
    print()
    print("=" * 60)

    # Prometheus metriky
    start_http_server(ASH_SWEEPER_PORT)
    print(f"[ASH-SWEEPER] Prometheus na portu {ASH_SWEEPER_PORT}")

    # Spustit vysavač
    sweeper = AshSweeper()
    sweeper.run_daemon()


if __name__ == '__main__':
    main()
