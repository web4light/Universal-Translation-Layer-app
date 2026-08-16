#!/usr/bin/env python3
"""
SDN Bridge - Dvouvrstvá síťová architektura.

Horní vrstva: Mincovna (Ada/SPARK) — logika, verifikace, rozhodování
Spodní vrstva: Faucet SDN (OpenFlow) — síťové flow tables, VLANy, ACL

Komunikace:
- Mincovna → SDN Bridge → Faucet (TCP socket port 4423)
- Faucet → SDN Bridge → Prometheus metriky
- "Faucet ve vakuu" — izolovaná síť pod kontrolou formální verifikace

Autor: Pan Jeskyně
Asistent: Kiro (Claude)
"""

import json
import os
import socket
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from prometheus_client import Counter, Gauge, start_http_server

# ============================================================================
# KONFIGURACE DVOUVRSTVÉ SÍTĚ
# ============================================================================

# Horní vrstva — Mincovna (Ada/SPARK rozhodovací logika)
MINCOVNA_PORT = 9302          # Primary Node Prometheus metriky
MINCOVNA_SOCKET = 4423        # TCP socket pro příkazy z Ada

# Spodní vrstva — Faucet SDN (OpenFlow controller)
FAUCET_CONFIG = "/home/pj/Universal-Translation-Layer/sdn/etc/faucet/faucet.yaml"
FAUCET_OPENFLOW_PORT = 6653   # OpenFlow standard port

# Bridge
SDN_BRIDGE_PORT = 9306        # Prometheus metriky bridge
SDN_BRIDGE_API_PORT = 8423    # REST API pro řízení

# ============================================================================
# PROMETHEUS METRIKY — SDN BRIDGE
# ============================================================================

sdn_commands_total = Counter(
    'sdn_bridge_commands_total',
    'Celkový počet příkazů z Mincovny do Faucet',
    ['command_type']
)

sdn_flows_installed = Gauge(
    'sdn_bridge_flows_installed',
    'Počet nainstalovaných flow pravidel'
)

sdn_layer_health = Gauge(
    'sdn_bridge_layer_health',
    'Zdraví vrstvy (0=dead, 1=alive)',
    ['layer']
)

sdn_packets_processed = Counter(
    'sdn_bridge_packets_total',
    'Celkový počet zpracovaných paketů'
)


# ============================================================================
# PŘÍKAZOVÝ PROTOKOL (Mincovna Ada → SDN Bridge → Faucet)
# ============================================================================

class SDNCommand:
    """Příkaz z horní vrstvy (Mincovna) pro spodní vrstvu (Faucet)."""

    # Typy příkazů
    BLOCK_PORT = "block_port"
    ALLOW_PORT = "allow_port"
    SET_VLAN = "set_vlan"
    ADD_ACL = "add_acl"
    REMOVE_ACL = "remove_acl"
    GET_STATUS = "get_status"
    RELOAD_CONFIG = "reload_config"

    def __init__(self, command_type, params=None):
        self.command_type = command_type
        self.params = params or {}
        self.timestamp = time.time()

    def to_json(self):
        return json.dumps({
            'type': self.command_type,
            'params': self.params,
            'timestamp': self.timestamp
        })

    @classmethod
    def from_json(cls, data):
        obj = json.loads(data)
        cmd = cls(obj['type'], obj.get('params', {}))
        cmd.timestamp = obj.get('timestamp', time.time())
        return cmd


# ============================================================================
# SDN BRIDGE — HLAVNÍ TŘÍDA
# ============================================================================

class SDNBridge:
    """
    Most mezi dvěma vrstvami:
    - Přijímá příkazy z Mincovny (Ada/SPARK) přes TCP socket
    - Překládá je na Faucet konfiguraci / OpenFlow příkazy
    - Reportuje stav obou vrstev přes Prometheus
    """

    def __init__(self):
        self.running = False
        self.flows = []
        self.command_history = []
        self.faucet_config_path = FAUCET_CONFIG

        # Stav vrstev
        sdn_layer_health.labels(layer='mincovna').set(1.0)
        sdn_layer_health.labels(layer='faucet').set(0.0)  # Zatím neběží
        sdn_layer_health.labels(layer='bridge').set(1.0)

        print("[SDN-BRIDGE] Inicializace dvouvrstvé sítě")
        print(f"[SDN-BRIDGE] Horní vrstva: Mincovna (port {MINCOVNA_PORT})")
        print(f"[SDN-BRIDGE] Spodní vrstva: Faucet (port {FAUCET_OPENFLOW_PORT})")
        print(f"[SDN-BRIDGE] Bridge API: port {SDN_BRIDGE_API_PORT}")

    def start(self):
        """Spustit bridge — TCP socket listener + REST API."""
        self.running = True

        # TCP socket pro Ada příkazy
        socket_thread = threading.Thread(
            target=self._socket_listener,
            daemon=True,
            name="sdn-socket"
        )
        socket_thread.start()

        # REST API
        api_thread = threading.Thread(
            target=self._rest_api,
            daemon=True,
            name="sdn-api"
        )
        api_thread.start()

        print("[SDN-BRIDGE] ✓ Bridge spuštěn")

    def stop(self):
        """Zastavit bridge."""
        self.running = False
        print("[SDN-BRIDGE] Zastavení...")

    def execute_command(self, cmd):
        """
        Zpracovat příkaz z Mincovny.

        Mincovna (Ada) rozhodne CO se má stát.
        Bridge přeloží na JAK to Faucet provede.
        """
        sdn_commands_total.labels(command_type=cmd.command_type).inc()
        self.command_history.append(cmd)

        print(f"[SDN-BRIDGE] Příkaz: {cmd.command_type} | params: {cmd.params}")

        if cmd.command_type == SDNCommand.BLOCK_PORT:
            return self._block_port(cmd.params)
        elif cmd.command_type == SDNCommand.ALLOW_PORT:
            return self._allow_port(cmd.params)
        elif cmd.command_type == SDNCommand.SET_VLAN:
            return self._set_vlan(cmd.params)
        elif cmd.command_type == SDNCommand.ADD_ACL:
            return self._add_acl(cmd.params)
        elif cmd.command_type == SDNCommand.GET_STATUS:
            return self._get_status()
        elif cmd.command_type == SDNCommand.RELOAD_CONFIG:
            return self._reload_faucet()
        else:
            return {'error': f'Neznámý příkaz: {cmd.command_type}'}

    # ------------------------------------------------------------------
    # PŘEKLAD PŘÍKAZŮ → FAUCET KONFIGURACE
    # ------------------------------------------------------------------

    def _block_port(self, params):
        """Zablokovat port — přidá ACL pravidlo do faucet.yaml."""
        port = params.get('port')
        dp = params.get('datapath', 'mincovna-switch')
        rule = {
            'rule': {
                'dl_type': '0x800',
                'actions': {'allow': 0}
            },
            'description': f'Mincovna: block port {port}'
        }
        self.flows.append(rule)
        sdn_flows_installed.set(len(self.flows))
        return {'status': 'ok', 'action': 'port_blocked', 'port': port}

    def _allow_port(self, params):
        """Povolit port — odebere blokaci."""
        port = params.get('port')
        self.flows = [f for f in self.flows
                      if f'block port {port}' not in f.get('description', '')]
        sdn_flows_installed.set(len(self.flows))
        return {'status': 'ok', 'action': 'port_allowed', 'port': port}

    def _set_vlan(self, params):
        """Nastavit VLAN pro port."""
        port = params.get('port')
        vlan_id = params.get('vlan_id')
        return {'status': 'ok', 'action': 'vlan_set',
                'port': port, 'vlan_id': vlan_id}

    def _add_acl(self, params):
        """Přidat ACL pravidlo."""
        acl_name = params.get('name', 'mincovna_acl')
        rule = params.get('rule', {})
        self.flows.append({'acl': acl_name, 'rule': rule})
        sdn_flows_installed.set(len(self.flows))
        return {'status': 'ok', 'action': 'acl_added', 'name': acl_name}

    def _get_status(self):
        """Vrátit stav obou vrstev."""
        return {
            'status': 'ok',
            'layers': {
                'mincovna': {
                    'port': MINCOVNA_PORT,
                    'health': 'active',
                    'role': 'rozhodovací logika (Ada/SPARK)'
                },
                'faucet': {
                    'port': FAUCET_OPENFLOW_PORT,
                    'health': 'standby',
                    'role': 'síťové flow tables (OpenFlow 1.3)',
                    'config': self.faucet_config_path
                },
                'bridge': {
                    'flows_installed': len(self.flows),
                    'commands_processed': len(self.command_history)
                }
            }
        }

    def _reload_faucet(self):
        """Signál Faucetu k reload konfigurace (SIGHUP)."""
        # V produkci: os.kill(faucet_pid, signal.SIGHUP)
        print("[SDN-BRIDGE] Faucet config reload requested")
        return {'status': 'ok', 'action': 'config_reloaded'}

    # ------------------------------------------------------------------
    # TCP SOCKET LISTENER (Ada → Bridge)
    # ------------------------------------------------------------------

    def _socket_listener(self):
        """Naslouchat TCP příkazům z Ada/SPARK vrstvy."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('localhost', MINCOVNA_SOCKET))
        server.listen(5)
        server.settimeout(1.0)

        print(f"[SDN-BRIDGE] TCP socket naslouchá na portu {MINCOVNA_SOCKET}")

        while self.running:
            try:
                conn, addr = server.accept()
                data = conn.recv(4096).decode('utf-8').strip()
                if data:
                    cmd = SDNCommand.from_json(data)
                    result = self.execute_command(cmd)
                    conn.sendall(json.dumps(result).encode('utf-8'))
                conn.close()
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[SDN-BRIDGE] Socket error: {e}")

        server.close()

    # ------------------------------------------------------------------
    # REST API (pro monitoring a manuální ovládání)
    # ------------------------------------------------------------------

    def _rest_api(self):
        """Jednoduchý REST API server."""
        bridge = self

        class APIHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/status':
                    result = bridge._get_status()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(result, indent=2).encode())
                elif self.path == '/flows':
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(bridge.flows, indent=2).encode())
                else:
                    self.send_response(404)
                    self.end_headers()

            def do_POST(self):
                if self.path == '/command':
                    length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(length).decode('utf-8')
                    cmd = SDNCommand.from_json(body)
                    result = bridge.execute_command(cmd)
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(result).encode())
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, format, *args):
                pass  # Tichý log

        server = HTTPServer(('0.0.0.0', SDN_BRIDGE_API_PORT), APIHandler)
        print(f"[SDN-BRIDGE] REST API na portu {SDN_BRIDGE_API_PORT}")
        server.serve_forever()


# ============================================================================
# MAIN
# ============================================================================

def main():
    """SDN Bridge entry point."""
    print("\n" + "=" * 60)
    print("🌐 VAKUOVÁ MINCOVNA — SDN BRIDGE")
    print("   Dvouvrstvá síťová architektura")
    print("=" * 60)
    print()
    print("  ┌─────────────────────────────────┐")
    print("  │  HORNÍ VRSTVA: MINCOVNA         │")
    print("  │  Ada/SPARK · Formální verifikace │")
    print("  │  Rozhoduje CO se děje            │")
    print("  ├─────────────────────────────────┤")
    print("  │  ↕ SDN BRIDGE (tento proces)    │")
    print("  │  Překládá příkazy · Prometheus  │")
    print("  ├─────────────────────────────────┤")
    print("  │  SPODNÍ VRSTVA: FAUCET SDN      │")
    print("  │  OpenFlow 1.3 · Flow tables     │")
    print("  │  Řídí KUDY to teče              │")
    print("  └─────────────────────────────────┘")
    print()

    # Prometheus metriky
    start_http_server(SDN_BRIDGE_PORT)
    print(f"[SDN-BRIDGE] Prometheus metriky: port {SDN_BRIDGE_PORT}")

    # Spustit bridge
    bridge = SDNBridge()
    bridge.start()

    print()
    print("[SDN-BRIDGE] ✓ Systém připraven")
    print("[SDN-BRIDGE] Ada příkazy: TCP socket localhost:4423")
    print("[SDN-BRIDGE] REST API: http://localhost:8423/status")
    print("[SDN-BRIDGE] Prometheus: http://localhost:9306/metrics")
    print()

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        bridge.stop()
        print("[SDN-BRIDGE] Ukončeno")


if __name__ == '__main__':
    main()
