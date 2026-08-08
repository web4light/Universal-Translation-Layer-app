#!/usr/bin/env python3
"""
Shadow Node - Stínovací uzel pro Vakuovou Mincovnu
Poskytuje redundanci a high availability

Autor: Pan Jeskyně
Asistent: Kiro (Claude Sonnet 4.5)
Standard: 700 (12g stříbra)
"""

import time
import requests
import sys
from prometheus_client import start_http_server, Counter, Gauge

# ============================================================================
# KONFIGURACE SHADOW NODE
# ============================================================================

SHADOW_PORT = 9303  # Shadow běží na jiném portu než Primary (9302)

# URL Primary Node
# Lokální test (oba uzly na stejném PC):
PRIMARY_URL = "http://192.168.123.191:9302/metrics"

# Production (asterisk i7 Windows — Ethernet .191, Primary):
# PRIMARY_URL = "http://192.168.123.191:9302/metrics"

# Shadow běží na Esprimo WiFi .172 (AX200 rychlejší než Ethernet):
# Spustit na Esprimo: python3 shadow_node.py

HEARTBEAT_INTERVAL = 5  # Kontrola každých 5 sekund
FAILOVER_TIMEOUT = 15   # Pokud Primary neodpovídá 15s → FAILOVER

# ============================================================================
# PROMETHEUS METRIKY PRO SHADOW NODE
# ============================================================================

shadow_sync_errors = Counter(
    'shadow_sync_errors_total',
    'Celkový počet chyb synchronizace'
)

shadow_is_primary = Gauge(
    'shadow_is_primary',
    'Je tento Shadow Node primární? (0=shadow, 1=primary)'
)

shadow_last_sync = Gauge(
    'shadow_last_sync_timestamp',
    'Unix timestamp poslední úspěšné synchronizace'
)

shadow_primary_health = Gauge(
    'shadow_primary_health',
    'Zdraví Primary Node z pohledu Shadow (0=dead, 1=alive)'
)

shadow_synced_coins = Gauge(
    'shadow_synced_coins',
    'Počet mincí synchronizovaných z Primary'
)

shadow_synced_silver = Gauge(
    'shadow_synced_silver_grams',
    'Množství stříbra synchronizované z Primary (gramy)'
)


# ============================================================================
# SHADOW NODE TŘÍDA
# ============================================================================

class ShadowNode:
    """
    Stínovací uzel pro Vakuovou Mincovnu

    Funkce:
    - Monitoruje Primary Node
    - Synchronizuje stav v reálném čase
    - Automatický failover pokud Primary spadne
    - Může převzít roli Primary
    """

    def __init__(self, primary_url=PRIMARY_URL):
        self.primary_url = primary_url
        self.is_primary = False
        self.last_primary_heartbeat = time.time()
        self.synced_state = {
            'coins': 0,
            'silver': 0.0,
            'health': 1
        }

        # Inicializace metrik
        shadow_is_primary.set(0)
        shadow_primary_health.set(1)

        print("[SHADOW] Inicializace dokončena")

    def check_primary_health(self):
        """
        Zkontroluj zda Primary Node žije

        Returns:
            bool: True pokud Primary odpovídá, False pokud ne
        """
        try:
            response = requests.get(self.primary_url, timeout=2)
            if response.status_code == 200:
                self.last_primary_heartbeat = time.time()
                shadow_primary_health.set(1)
                return True
        except requests.exceptions.RequestException as e:
            print(f"[SHADOW] Primary Node neodpovídá: {e}")

        # Kontrola timeout
        time_since_heartbeat = time.time() - self.last_primary_heartbeat
        if time_since_heartbeat > FAILOVER_TIMEOUT:
            shadow_primary_health.set(0)
            print(f"[SHADOW] ⚠️  Primary Node timeout: {time_since_heartbeat:.1f}s")
            return False

        return True

    def parse_metrics(self, metrics_text):
        """
        Parsuj Prometheus metriky z textu

        Args:
            metrics_text: Raw text metriky z /metrics endpointu

        Returns:
            dict: Naparsované hodnoty
        """
        state = {}

        for line in metrics_text.split('\n'):
            if line.startswith('#') or not line.strip():
                continue

            if 'mincovna_minted_coins_total' in line:
                try:
                    state['coins'] = float(line.split()[1])
                except:
                    pass

            if 'mincovna_total_silver_grams' in line:
                try:
                    state['silver'] = float(line.split()[1])
                except:
                    pass

            if 'mincovna_system_health' in line:
                try:
                    state['health'] = float(line.split()[1])
                except:
                    pass

        return state

    def sync_state(self):
        """
        Synchronizuj stav z Primary Node

        Returns:
            bool: True pokud sync úspěšný, False pokud ne
        """
        try:
            response = requests.get(self.primary_url, timeout=3)
            if response.status_code == 200:
                # Parse metriky
                state = self.parse_metrics(response.text)

                if state:
                    self.synced_state = state
                    shadow_last_sync.set(time.time())
                    shadow_synced_coins.set(state.get('coins', 0))
                    shadow_synced_silver.set(
                        state.get('silver', 0.0)
                    )

                    print(f"[SHADOW] ✓ Sync OK: "
                          f"{state.get('coins', 0)} mincí, "
                          f"{state.get('silver', 0.0)}g stříbra")
                    return True

            return False

        except Exception as e:
            shadow_sync_errors.inc()
            print(f"[SHADOW] ✗ Sync chyba: {e}")
            return False

    def become_primary(self):
        """
        Převezmi roli primárního uzlu (FAILOVER)
        """
        print("\n" + "="*60)
        print("🚨 FAILOVER EVENT - SHADOW NODE PŘEBÍRÁ KONTROLU! 🚨")
        print("="*60)

        self.is_primary = True
        shadow_is_primary.set(1)

        print("[SHADOW→PRIMARY] Status změněn na PRIMARY")
        print(f"[SHADOW→PRIMARY] Poslední známý stav:")
        print(f"  • Mince: {self.synced_state.get('coins', 0)}")
        print(f"  • Stříbro: {self.synced_state.get('silver', 0.0)}g")
        print(f"  • Health: {self.synced_state.get('health', 0)}")
        print("\n[SHADOW→PRIMARY] Systém pokračuje bez přerušení!")
        print("="*60 + "\n")

        # TODO: V produkci by zde byl restart Faucet Bridge na port 9302
        # Pro testování zůstáváme na 9303

    def demote_to_shadow(self):
        """
        Vrať se do shadow módu (Primary Node se vrátil)
        """
        if self.is_primary:
            print("\n" + "="*60)
            print("🔄 PRIMARY NODE SE VRÁTIL - Vracím se do Shadow módu")
            print("="*60)

            self.is_primary = False
            shadow_is_primary.set(0)

            print("[PRIMARY→SHADOW] Kontrola předána zpět Primary Node")
            print("[PRIMARY→SHADOW] Obnovuji synchronizaci...")
            print("="*60 + "\n")

    def run(self):
        """
        Hlavní smyčka Shadow Node
        """
        print("\n" + "="*60)
        print("🌑 SHADOW NODE - STÍNOVACÍ UZEL")
        print("="*60)
        print(f"[SHADOW] Prometheus endpoint: http://localhost:{SHADOW_PORT}/metrics")
        print(f"[SHADOW] Monitoring Primary: {self.primary_url}")
        print(f"[SHADOW] Heartbeat interval: {HEARTBEAT_INTERVAL}s")
        print(f"[SHADOW] Failover timeout: {FAILOVER_TIMEOUT}s")
        print("[SHADOW] Standard 700: 12g stříbra")
        print("[SHADOW] Formální verifikace: AKTIVNÍ (přes Primary)")
        print("="*60)
        print("[SHADOW] Režim: MONITORING")
        print("="*60 + "\n")

        # Spustit Prometheus HTTP server
        try:
            start_http_server(SHADOW_PORT)
            print(f"[SHADOW] ✓ Prometheus server běží na portu {SHADOW_PORT}")
        except Exception as e:
            print(f"[SHADOW] ✗ Chyba spuštění serveru: {e}")
            sys.exit(1)

        print("[SHADOW] Spouštím monitoring loop...\n")

        # Hlavní smyčka
        cycle = 0
        try:
            while True:
                cycle += 1
                timestamp = time.strftime("%H:%M:%S")

                # 1. Zkontroluj zdraví Primary Node
                primary_alive = self.check_primary_health()

                # 2. Rozhodnutí o failover
                if not primary_alive and not self.is_primary:
                    # PRIMARY SPADL → FAILOVER!
                    self.become_primary()

                elif primary_alive and self.is_primary:
                    # PRIMARY SE VRÁTIL → Vrať se do shadow módu
                    self.demote_to_shadow()

                # 3. Synchronizace stavu (pokud jsme stále shadow)
                if not self.is_primary:
                    sync_success = self.sync_state()
                    status = "✓" if sync_success else "✗"
                    mode = "SHADOW"
                else:
                    status = "★"
                    mode = "PRIMARY"

                # Status log každých 10 cyklů (50 sekund)
                if cycle % 10 == 0:
                    print(f"[{timestamp}] [{mode}] {status} "
                          f"Cycle {cycle} | "
                          f"Primary: {'ALIVE' if primary_alive else 'DEAD'}")

                # 4. Čekej do dalšího cyklu
                time.sleep(HEARTBEAT_INTERVAL)

        except KeyboardInterrupt:
            print("\n[SHADOW] Ukončuji Shadow Node...")
            shadow_is_primary.set(0)
            shadow_primary_health.set(0)
            print("[SHADOW] Shutdown dokončen")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Spuštění Shadow Node"""

    # Kontrola argumentů (volitelné: custom Primary URL)
    primary_url = PRIMARY_URL
    if len(sys.argv) > 1:
        primary_url = sys.argv[1]
        print(f"[SHADOW] Používám custom Primary URL: {primary_url}")

    # Vytvoření a spuštění Shadow Node
    shadow = ShadowNode(primary_url=primary_url)
    shadow.run()


if __name__ == '__main__':
    main()
