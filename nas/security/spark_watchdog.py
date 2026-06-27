#!/usr/bin/env python3
"""
Apache Spark Watchdog - Distribuovaný bezpečnostní skener
Mossad ALF++ Protocol (Advanced Low-level Forensics)

5 úrovní kontroly:
1. Filesystem - SHA256 hashing všech souborů
2. Binary Analysis - kontrola binárních souborů
3. Memory Forensics - analýza běžících procesů
4. Behavioral - detekce anomálií v chování
5. Steganography - detekce skrytých dat

Autor: Pan Jeskyně
Asistent: Kiro (Claude Sonnet 4.5)
Standard: 700 (12g stříbra)
"""

import os
import sys
import time
import hashlib
import psutil
import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from prometheus_client import start_http_server, Counter, Gauge, Histogram

# ============================================================================
# KONFIGURACE WATCHDOG
# ============================================================================

WATCHDOG_PORT = 9304  # Prometheus port pro watchdog metriky
SCAN_INTERVAL = 3600  # Každou hodinu (3600s)
BASELINE_FILE = "watchdog_baseline.json"  # Reference hash databáze

# Cesty k skenování (menší disk = rychlejší scan)
SCAN_PATHS = [
    "/opt/vakuova-mincovna",  # Produkční složka
    "/usr/local/bin",         # System binaries
    "/etc",                   # Konfigurace
]

# Vyloučené cesty (performance)
EXCLUDE_PATHS = [
    "/proc", "/sys", "/dev", "/tmp",
    ".git", "__pycache__", "node_modules"
]

# ============================================================================
# PROMETHEUS METRIKY
# ============================================================================

watchdog_scans_total = Counter(
    'watchdog_scans_total',
    'Celkový počet dokončených skenů'
)

watchdog_threats_detected = Counter(
    'watchdog_threats_detected_total',
    'Celkový počet detekovaných hrozeb',
    ['threat_type']
)

watchdog_scan_duration = Histogram(
    'watchdog_scan_duration_seconds',
    'Doba trvání skenu v sekundách',
    ['scan_type']
)

watchdog_files_scanned = Gauge(
    'watchdog_files_scanned',
    'Počet souborů naskenovaných při posledním skenu'
)

watchdog_suspicious_processes = Gauge(
    'watchdog_suspicious_processes',
    'Počet podezřelých procesů'
)

watchdog_disk_size_mb = Gauge(
    'watchdog_disk_size_mb',
    'Celková velikost disku v MB'
)

watchdog_last_scan = Gauge(
    'watchdog_last_scan_timestamp',
    'Unix timestamp posledního skenu'
)


# ============================================================================
# MOSSAD ALF++ PROTOKOL
# ============================================================================

class MossadALFPlusPlus:
    """
    Advanced Low-level Forensics Protocol
    
    5 úrovní bezpečnostní analýzy:
    1. Filesystem integrity (SHA256)
    2. Binary analysis (ELF headers, PE headers)
    3. Memory forensics (procesy, paměť)
    4. Behavioral analysis (network, syscalls)
    5. Steganography detection (skrytá data)
    """
    
    def __init__(self, scan_paths=SCAN_PATHS, exclude_paths=EXCLUDE_PATHS):
        self.scan_paths = scan_paths
        self.exclude_paths = exclude_paths
        self.baseline = self.load_baseline()
        self.threats = []
        
        print("[WATCHDOG] Mossad ALF++ Protocol inicializován")
        print(f"[WATCHDOG] Scan paths: {len(scan_paths)}")
        print(f"[WATCHDOG] Baseline entries: {len(self.baseline)}")
    
    def load_baseline(self):
        """Načti referenční databázi hash"""
        if os.path.exists(BASELINE_FILE):
            try:
                with open(BASELINE_FILE, 'r') as f:
                    baseline = json.load(f)
                    print(f"[WATCHDOG] ✓ Baseline načten: "
                          f"{len(baseline)} souborů")
                    return baseline
            except Exception as e:
                print(f"[WATCHDOG] ✗ Chyba načtení baseline: {e}")
        
        print("[WATCHDOG] ⚠ Baseline neexistuje, vytvoří se při prvním skenu")
        return {}
    
    def save_baseline(self, hashes):
        """Ulož referenční databázi hash"""
        try:
            with open(BASELINE_FILE, 'w') as f:
                json.dump(hashes, f, indent=2)
            print(f"[WATCHDOG] ✓ Baseline uložen: {len(hashes)} souborů")
        except Exception as e:
            print(f"[WATCHDOG] ✗ Chyba uložení baseline: {e}")
    
    def should_exclude(self, path):
        """Kontrola zda cesta má být vyloučena"""
        path_str = str(path)
        for exclude in self.exclude_paths:
            if exclude in path_str:
                return True
        return False
    
    def calculate_sha256(self, filepath):
        """Vypočítej SHA256 hash souboru"""
        try:
            sha256 = hashlib.sha256()
            with open(filepath, 'rb') as f:
                # Čti po blocích (efektivní pro velké soubory)
                for block in iter(lambda: f.read(4096), b''):
                    sha256.update(block)
            return sha256.hexdigest()
        except Exception as e:
            print(f"[WATCHDOG] ✗ Hash error {filepath}: {e}")
            return None
    
    def level1_filesystem_scan(self):
        """
        LEVEL 1: Filesystem Integrity Check
        
        Kontrola všech souborů proti baseline hash databázi.
        Detekuje: modifikované, nové, smazané soubory.
        """
        print("\n" + "="*60)
        print("🔍 LEVEL 1: FILESYSTEM INTEGRITY SCAN")
        print("="*60)
        
        start_time = time.time()
        current_hashes = {}
        files_scanned = 0
        
        for scan_path in self.scan_paths:
            if not os.path.exists(scan_path):
                print(f"[WATCHDOG] ⚠ Path neexistuje: {scan_path}")
                continue
            
            print(f"[WATCHDOG] Scanning: {scan_path}")
            
            for root, dirs, files in os.walk(scan_path):
                # Filtruj vyloučené adresáře
                dirs[:] = [d for d in dirs
                          if not self.should_exclude(os.path.join(root, d))]
                
                for filename in files:
                    filepath = os.path.join(root, filename)
                    
                    if self.should_exclude(filepath):
                        continue
                    
                    # Vypočítej hash
                    file_hash = self.calculate_sha256(filepath)
                    if file_hash:
                        current_hashes[filepath] = file_hash
                        files_scanned += 1
                        
                        # Kontrola proti baseline
                        if filepath in self.baseline:
                            if self.baseline[filepath] != file_hash:
                                # MODIFIKOVANÝ SOUBOR!
                                threat = {
                                    'type': 'modified_file',
                                    'level': 1,
                                    'path': filepath,
                                    'old_hash': self.baseline[filepath],
                                    'new_hash': file_hash,
                                    'timestamp': datetime.now().isoformat()
                                }
                                self.threats.append(threat)
                                watchdog_threats_detected.labels(
                                    threat_type='modified_file'
                                ).inc()
                                print(f"[WATCHDOG] 🚨 MODIFIED: {filepath}")
                        else:
                            if self.baseline:  # Jen pokud máme baseline
                                # NOVÝ SOUBOR!
                                threat = {
                                    'type': 'new_file',
                                    'level': 1,
                                    'path': filepath,
                                    'hash': file_hash,
                                    'timestamp': datetime.now().isoformat()
                                }
                                self.threats.append(threat)
                                watchdog_threats_detected.labels(
                                    threat_type='new_file'
                                ).inc()
                                print(f"[WATCHDOG] ⚠ NEW: {filepath}")
        
        # Kontrola smazaných souborů
        if self.baseline:
            for baseline_path in self.baseline.keys():
                if baseline_path not in current_hashes:
                    # SMAZANÝ SOUBOR!
                    threat = {
                        'type': 'deleted_file',
                        'level': 1,
                        'path': baseline_path,
                        'old_hash': self.baseline[baseline_path],
                        'timestamp': datetime.now().isoformat()
                    }
                    self.threats.append(threat)
                    watchdog_threats_detected.labels(
                        threat_type='deleted_file'
                    ).inc()
                    print(f"[WATCHDOG] 🚨 DELETED: {baseline_path}")
        
        duration = time.time() - start_time
        watchdog_scan_duration.labels(scan_type='filesystem').observe(duration)
        watchdog_files_scanned.set(files_scanned)
        
        print(f"\n[WATCHDOG] Level 1 completed:")
        print(f"  • Files scanned: {files_scanned}")
        print(f"  • Duration: {duration:.2f}s")
        print(f"  • Threats: {len(self.threats)}")
        
        # Ulož nový baseline
        if not self.baseline:  # První scan
            self.save_baseline(current_hashes)
            self.baseline = current_hashes
        
        return current_hashes
    
    def level2_binary_analysis(self):
        """
        LEVEL 2: Binary Analysis
        
        Kontrola binárních souborů (ELF, PE).
        Detekuje: packed executables, suspicious headers.
        """
        print("\n" + "="*60)
        print("🔍 LEVEL 2: BINARY ANALYSIS")
        print("="*60)
        
        start_time = time.time()
        
        # TODO: Implementace ELF/PE header analysis
        # Pro produkci: použít pefile, pyelftools
        
        print("[WATCHDOG] Level 2: TODO - Binary analysis")
        
        duration = time.time() - start_time
        watchdog_scan_duration.labels(scan_type='binary').observe(duration)
    
    def level3_memory_forensics(self):
        """
        LEVEL 3: Memory Forensics
        
        Analýza běžících procesů.
        Detekuje: neznámé procesy, high CPU, hidden processes.
        """
        print("\n" + "="*60)
        print("🔍 LEVEL 3: MEMORY FORENSICS")
        print("="*60)
        
        start_time = time.time()
        suspicious_count = 0
        
        # Whitelist známých procesů
        known_processes = [
            'python3', 'python', 'systemd', 'sshd', 'bash',
            'prometheus', 'grafana-server', 'gnatstudio'
        ]
        
        print("[WATCHDOG] Analyzing running processes...")
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent',
                                         'memory_percent']):
            try:
                pinfo = proc.info
                pname = pinfo['name']
                
                # Kontrola CPU usage
                if pinfo['cpu_percent'] > 80.0:
                    threat = {
                        'type': 'high_cpu_process',
                        'level': 3,
                        'pid': pinfo['pid'],
                        'name': pname,
                        'cpu_percent': pinfo['cpu_percent'],
                        'timestamp': datetime.now().isoformat()
                    }
                    self.threats.append(threat)
                    watchdog_threats_detected.labels(
                        threat_type='high_cpu'
                    ).inc()
                    suspicious_count += 1
                    print(f"[WATCHDOG] 🚨 HIGH CPU: {pname} "
                          f"({pinfo['cpu_percent']}%)")
                
                # Kontrola neznámých procesů
                if not any(known in pname for known in known_processes):
                    # TODO: Deep analysis pro neznámé procesy
                    pass
                
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        duration = time.time() - start_time
        watchdog_scan_duration.labels(scan_type='memory').observe(duration)
        watchdog_suspicious_processes.set(suspicious_count)
        
        print(f"\n[WATCHDOG] Level 3 completed:")
        print(f"  • Suspicious processes: {suspicious_count}")
        print(f"  • Duration: {duration:.2f}s")
    
    def level4_behavioral_analysis(self):
        """
        LEVEL 4: Behavioral Analysis
        
        Analýza síťové aktivity a syscalls.
        Detekuje: neautorizované spojení, syscall anomálie.
        """
        print("\n" + "="*60)
        print("🔍 LEVEL 4: BEHAVIORAL ANALYSIS")
        print("="*60)
        
        start_time = time.time()
        
        # TODO: Implementace network monitoring
        # Pro produkci: použít scapy, bpf
        
        print("[WATCHDOG] Level 4: TODO - Behavioral analysis")
        
        duration = time.time() - start_time
        watchdog_scan_duration.labels(scan_type='behavioral').observe(duration)
    
    def level5_steganography_detection(self):
        """
        LEVEL 5: Steganography Detection
        
        Detekce skrytých dat v souborech.
        Detekuje: LSB steganography, hidden archives.
        """
        print("\n" + "="*60)
        print("🔍 LEVEL 5: STEGANOGRAPHY DETECTION")
        print("="*60)
        
        start_time = time.time()
        
        # TODO: Implementace stego detection
        # Pro produkci: statistická analýza, entropy check
        
        print("[WATCHDOG] Level 5: TODO - Steganography detection")
        
        duration = time.time() - start_time
        watchdog_scan_duration.labels(scan_type='steganography').observe(
            duration
        )
    
    def full_scan(self):
        """
        Spusť kompletní 5-úrovňový scan
        """
        print("\n" + "="*60)
        print("🐕 APACHE SPARK WATCHDOG - MOSSAD ALF++")
        print("="*60)
        print(f"[WATCHDOG] Start time: {datetime.now().isoformat()}")
        print(f"[WATCHDOG] Scan paths: {self.scan_paths}")
        
        # Zjisti velikost disku
        try:
            total, used, free = psutil.disk_usage('/')
            disk_size_mb = total / (1024 * 1024)
            watchdog_disk_size_mb.set(disk_size_mb)
            print(f"[WATCHDOG] Disk size: {disk_size_mb:.0f} MB")
            print(f"[WATCHDOG] Výhoda menšího disku: "
                  f"Rychlejší scan, méně míst pro malware!")
        except Exception as e:
            print(f"[WATCHDOG] ⚠ Disk info error: {e}")
        
        self.threats = []  # Reset threats
        
        # Spusť všechny úrovně
        self.level1_filesystem_scan()
        self.level2_binary_analysis()
        self.level3_memory_forensics()
        self.level4_behavioral_analysis()
        self.level5_steganography_detection()
        
        # Výsledky
        print("\n" + "="*60)
        print("📊 SCAN SUMMARY")
        print("="*60)
        print(f"[WATCHDOG] Total threats detected: {len(self.threats)}")
        
        threat_types = defaultdict(int)
        for threat in self.threats:
            threat_types[threat['type']] += 1
        
        for threat_type, count in threat_types.items():
            print(f"[WATCHDOG]   • {threat_type}: {count}")
        
        watchdog_scans_total.inc()
        watchdog_last_scan.set(time.time())
        
        # Ulož hrozby do souboru
        if self.threats:
            threat_file = f"watchdog_threats_{int(time.time())}.json"
            try:
                with open(threat_file, 'w') as f:
                    json.dump(self.threats, f, indent=2)
                print(f"\n[WATCHDOG] 🚨 Threats saved to: {threat_file}")
            except Exception as e:
                print(f"[WATCHDOG] ✗ Error saving threats: {e}")
        
        print("="*60 + "\n")
        
        return self.threats


# ============================================================================
# WATCHDOG DAEMON
# ============================================================================

class WatchdogDaemon:
    """
    Daemon pro pravidelné spouštění watchdog skenů
    """
    
    def __init__(self, scan_interval=SCAN_INTERVAL):
        self.scan_interval = scan_interval
        self.watchdog = MossadALFPlusPlus()
    
    def run(self):
        """Hlavní loop"""
        print("\n" + "="*60)
        print("🐕 APACHE SPARK WATCHDOG DAEMON")
        print("="*60)
        print(f"[DAEMON] Scan interval: {self.scan_interval}s "
              f"({self.scan_interval/60:.0f} min)")
        print(f"[DAEMON] Prometheus port: {WATCHDOG_PORT}")
        print(f"[DAEMON] Protocol: Mossad ALF++")
        print("="*60 + "\n")
        
        # Spusť Prometheus HTTP server
        try:
            start_http_server(WATCHDOG_PORT)
            print(f"[DAEMON] ✓ Prometheus server running on "
                  f"port {WATCHDOG_PORT}")
        except Exception as e:
            print(f"[DAEMON] ✗ Server error: {e}")
            sys.exit(1)
        
        # Hlavní loop
        cycle = 0
        try:
            while True:
                cycle += 1
                print(f"\n[DAEMON] === SCAN CYCLE {cycle} ===\n")
                
                # Spusť scan
                threats = self.watchdog.full_scan()
                
                # Alert pokud hrozby
                if threats:
                    print(f"\n[DAEMON] 🚨 ALERT: "
                          f"{len(threats)} threats detected!")
                    # TODO: Poslat notifikaci (email, webhook, n8n)
                else:
                    print(f"\n[DAEMON] ✓ No threats detected")
                
                # Čekej do dalšího skenu
                print(f"\n[DAEMON] Next scan in {self.scan_interval}s...")
                time.sleep(self.scan_interval)
                
        except KeyboardInterrupt:
            print("\n[DAEMON] Shutting down watchdog...")
            print("[DAEMON] Shutdown complete")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Spuštění Apache Spark Watchdog"""
    
    # Kontrola argumentů
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        # Jednorázový scan
        print("[WATCHDOG] Running single scan...")
        watchdog = MossadALFPlusPlus()
        start_http_server(WATCHDOG_PORT)
        threats = watchdog.full_scan()
        sys.exit(0 if not threats else 1)
    else:
        # Daemon mode
        daemon = WatchdogDaemon()
        daemon.run()


if __name__ == '__main__':
    main()
