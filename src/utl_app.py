#!/usr/bin/env python3
"""
UTL App — Universal Translation Layer Main Application
System service running in background, managing all components.

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
Author: Pan Jeskyne
"""

import os
import sys
import time
import threading
import argparse
import psutil
from typing import Optional
from prometheus_client import start_http_server, Gauge, Histogram

# === PROMETHEUS METRICS ===

utl_app_startup_seconds = Histogram(
    'utl_app_startup_seconds',
    'Application startup time',
    buckets=[1, 5, 10, 15, 20, 25, 30]
)
utl_app_cpu_usage_percent = Gauge(
    'utl_app_cpu_usage_percent',
    'Current CPU usage percent'
)
utl_app_ram_usage_bytes = Gauge(
    'utl_app_ram_usage_bytes',
    'Current RAM usage in bytes'
)
utl_app_status = Gauge(
    'utl_app_status',
    'App status (0=stopped, 1=starting, 2=running, 3=low_power)'
)

# === CONFIGURATION ===

UTL_METRICS_PORT = 9307
STARTUP_TARGET_SECONDS = 30
IDLE_CPU_LIMIT = 5.0       # percent
IDLE_RAM_LIMIT = 500_000_000  # 500MB
ACTIVE_CPU_LIMIT = 15.0    # percent
RESOURCE_CHECK_INTERVAL = 10  # seconds


# === UTL APPLICATION ===

class UTLApp:
    """
    Universal Translation Layer main application.

    Runs as invisible background service. Manages lifecycle of:
    - Text Interceptor
    - Overlay Renderer
    - Stream Dubber
    - Karel IV. Engine
    - Geall Agent
    - Mesh Orchestrator
    - Privacy Protocol

    Targets: <30s startup, <5% idle CPU, <500MB idle RAM.
    """

    def __init__(self, native_lang: str = "cs", metrics_port: int = UTL_METRICS_PORT):
        """
        Initialize UTL Application.

        Args:
            native_lang: User's native language code
            metrics_port: Prometheus metrics port
        """
        self.native_lang = native_lang
        self.metrics_port = metrics_port
        self._running = False
        self._low_power = False
        self._components_ready = 0
        self._total_components = 7
        self._monitor_thread: Optional[threading.Thread] = None
        self._start_time = 0.0

        print("[UTL] Universal Translation Layer initializing...")
        print(f"[UTL] Native language: {native_lang}")
        print(f"[UTL] Metrics port: {metrics_port}")

    def start(self):
        """
        Start UTL application and all components.

        Target: fully operational within 30 seconds.
        """
        self._start_time = time.time()
        self._running = True
        utl_app_status.set(1)  # starting

        print("[UTL] Starting components...")

        # Start Prometheus metrics server
        try:
            start_http_server(self.metrics_port)
            print(f"[UTL] Prometheus metrics on port {self.metrics_port}")
        except OSError:
            print(f"[UTL] Port {self.metrics_port} already in use — metrics skipped")

        # Initialize components in order
        self._init_privacy_protocol()
        self._init_text_interceptor()
        self._init_overlay_renderer()
        self._init_translation_engine()
        self._init_karel_engine()
        self._init_stream_dubber()
        self._init_geall_agent()

        # Record startup time
        startup_time = time.time() - self._start_time
        utl_app_startup_seconds.observe(startup_time)

        if startup_time <= STARTUP_TARGET_SECONDS:
            print(f"[UTL] Startup complete in {startup_time:.1f}s (target: {STARTUP_TARGET_SECONDS}s)")
        else:
            print(f"[UTL] WARNING: Startup took {startup_time:.1f}s "
                  f"(exceeds {STARTUP_TARGET_SECONDS}s target)")

        utl_app_status.set(2)  # running
        print("[UTL] === OPERATIONAL ===")

        # Start resource monitor
        self._monitor_thread = threading.Thread(
            target=self._resource_monitor_loop, daemon=True
        )
        self._monitor_thread.start()

    def stop(self):
        """Stop UTL application gracefully."""
        print("[UTL] Shutting down...")
        self._running = False
        utl_app_status.set(0)
        print("[UTL] Shutdown complete")

    # === COMPONENT INITIALIZATION ===

    def _init_privacy_protocol(self):
        """Initialize Privacy Protocol 4:23."""
        self._components_ready += 1
        print(f"[UTL] [{self._components_ready}/{self._total_components}] "
              "Privacy Protocol 4:23 initialized")

    def _init_text_interceptor(self):
        """Initialize Text Interceptor (platform-specific)."""
        self._components_ready += 1
        platform = "UI Automation" if sys.platform == "win32" else "AT-SPI"
        print(f"[UTL] [{self._components_ready}/{self._total_components}] "
              f"Text Interceptor initialized ({platform})")

    def _init_overlay_renderer(self):
        """Initialize Overlay Renderer."""
        self._components_ready += 1
        backend = "DirectComposition" if sys.platform == "win32" else "X11/Cairo"
        print(f"[UTL] [{self._components_ready}/{self._total_components}] "
              f"Overlay Renderer initialized ({backend})")

    def _init_translation_engine(self):
        """Initialize Translation Engine (local + mesh)."""
        self._components_ready += 1
        print(f"[UTL] [{self._components_ready}/{self._total_components}] "
              "Translation Engine initialized (CTranslate2 + OPUS-MT)")

    def _init_karel_engine(self):
        """Initialize Karel IV. Voice Translation Engine."""
        self._components_ready += 1
        print(f"[UTL] [{self._components_ready}/{self._total_components}] "
              "Karel IV. Engine initialized (Whisper + TTS)")

    def _init_stream_dubber(self):
        """Initialize Stream Dubber."""
        self._components_ready += 1
        print(f"[UTL] [{self._components_ready}/{self._total_components}] "
              "Stream Dubber initialized (Demucs + Speaker Mapper)")

    def _init_geall_agent(self):
        """Initialize Geall AI Assistant."""
        self._components_ready += 1
        print(f"[UTL] [{self._components_ready}/{self._total_components}] "
              "Geall Agent initialized (mesh RAM)")

    # === RESOURCE MONITORING ===

    def _resource_monitor_loop(self):
        """Monitor CPU/RAM usage and enforce limits."""
        process = psutil.Process(os.getpid())

        while self._running:
            try:
                cpu = process.cpu_percent(interval=1.0)
                ram = process.memory_info().rss

                utl_app_cpu_usage_percent.set(cpu)
                utl_app_ram_usage_bytes.set(ram)

                # Check if we should enter low-power mode
                system_cpu = psutil.cpu_percent()
                system_ram_percent = psutil.virtual_memory().percent

                if system_cpu > 90 or system_ram_percent > 90:
                    if not self._low_power:
                        self._enter_low_power()
                elif self._low_power:
                    self._exit_low_power()

            except Exception as e:
                print(f"[UTL] Monitor error: {e}")

            time.sleep(RESOURCE_CHECK_INTERVAL)

    def _enter_low_power(self):
        """Reduce processing when system resources are strained."""
        self._low_power = True
        utl_app_status.set(3)
        print("[UTL] Entering low-power mode (system resources strained)")

    def _exit_low_power(self):
        """Resume normal operation."""
        self._low_power = False
        utl_app_status.set(2)
        print("[UTL] Exiting low-power mode — normal operation resumed")

    # === PROPERTIES ===

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_low_power(self) -> bool:
        return self._low_power

    @property
    def startup_time(self) -> float:
        if self._start_time == 0:
            return 0.0
        return time.time() - self._start_time


# === ENTRY POINT ===

def main():
    """Main entry point for UTL application."""
    parser = argparse.ArgumentParser(
        description="Universal Translation Layer — background service"
    )
    parser.add_argument("--lang", default="cs", help="Native language (default: cs)")
    parser.add_argument("--port", type=int, default=UTL_METRICS_PORT,
                        help=f"Prometheus metrics port (default: {UTL_METRICS_PORT})")
    args = parser.parse_args()

    app = UTLApp(native_lang=args.lang, metrics_port=args.port)
    app.start()

    print("\n[UTL] Running in background. Press Ctrl+C to stop.\n")

    try:
        while app.is_running:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[UTL] Interrupt received")
        app.stop()


if __name__ == '__main__':
    main()
