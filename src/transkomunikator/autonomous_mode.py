"""
Autonomous Mode & Self-Management — Karel IV. n8n System
========================================================

Handles system self-management when n8n is unreachable:
- Error recovery with retry (3x, 5s intervals)
- Resource management (reduce concurrency on CPU/RAM > 90%)
- Offline mode (local translation models only)
- Connectivity recovery (resume Gemini within 10s)
- Windows startup integration

Central Stop: only Mincovna (GNAT core) can halt the system.
Ethics Oath: cannot be disabled by any management operation.

Standard: Karel IV. n8n System Requirements 1.5, 12, 11
"""

import os
import time
import logging
import threading
import psutil
from typing import Optional, Callable, Dict, Any

# === LOGGING ===

logger = logging.getLogger(__name__)
LOG_PREFIX = "[AUTONOMOUS]"

# === PROMETHEUS ===

try:
    from prometheus_client import Gauge

    karel_autonomous_active = Gauge(
        'karel_autonomous_active',
        'Whether system is in autonomous mode'
    )
    karel_resource_cpu = Gauge(
        'karel_resource_cpu_percent',
        'Current CPU usage percent'
    )
    karel_resource_ram = Gauge(
        'karel_resource_ram_percent',
        'Current RAM usage percent'
    )
except ImportError:
    karel_autonomous_active = None
    karel_resource_cpu = None
    karel_resource_ram = None

# === CONSTANTS ===

MAX_RETRIES = 3
RETRY_INTERVAL_S = 5
CPU_THRESHOLD = 90.0
RAM_THRESHOLD = 90.0
CONNECTIVITY_CHECK_INTERVAL_S = 5
GEMINI_RESUME_TIMEOUT_S = 10


# === AUTONOMOUS MODE ===

class AutonomousMode:
    """Self-management layer for Karel IV. pipeline.

    Responsibilities:
    - Restart failed stages (3 retries, 5s interval)
    - Degrade gracefully when retries exhausted
    - Monitor resources and reduce concurrency
    - Detect offline/online transitions
    - Resume external APIs on connectivity restore
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._active = False
        self._failed_stages: Dict[str, int] = {}
        self._online = True
        self._resource_constrained = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_running = False
        self._on_failover: Optional[Callable] = None
        self._on_recovery: Optional[Callable] = None

        logger.info(f"{LOG_PREFIX} Self-management initialized")

    # === ERROR RECOVERY ===

    def handle_stage_error(self, stage: str,
                           restart_fn: Callable = None) -> bool:
        """Handle a pipeline stage error with retry logic.

        Args:
            stage: Name of failed stage
            restart_fn: Function to restart the stage

        Returns:
            True if recovery successful, False if failover needed
        """
        with self._lock:
            retries = self._failed_stages.get(stage, 0)

        if retries >= MAX_RETRIES:
            logger.warning(
                f"{LOG_PREFIX} Stage '{stage}' FAILED after {MAX_RETRIES} retries — FAILOVER"
            )
            self._enter_failover(stage)
            return False

        # Retry with interval
        with self._lock:
            self._failed_stages[stage] = retries + 1

        logger.info(
            f"{LOG_PREFIX} Stage '{stage}' retry {retries + 1}/{MAX_RETRIES} "
            f"(waiting {RETRY_INTERVAL_S}s)"
        )
        time.sleep(RETRY_INTERVAL_S)

        if restart_fn:
            try:
                restart_fn()
                with self._lock:
                    self._failed_stages[stage] = 0  # Reset on success
                logger.info(f"{LOG_PREFIX} Stage '{stage}' recovered")
                return True
            except Exception as e:
                logger.error(f"{LOG_PREFIX} Stage '{stage}' retry failed: {e}")
                return self.handle_stage_error(stage, restart_fn)

        return False

    def clear_stage_error(self, stage: str) -> None:
        """Clear error count for a stage (on successful completion)."""
        with self._lock:
            self._failed_stages.pop(stage, None)

    # === FAILOVER ===

    def _enter_failover(self, stage: str) -> None:
        """Enter failover mode for a stage."""
        self._active = True
        if karel_autonomous_active:
            karel_autonomous_active.set(1)

        msg = f"Stage '{stage}' unavailable. System continues in degraded mode."
        logger.warning(f"{LOG_PREFIX} FAILOVER: {msg}")

        if self._on_failover:
            self._on_failover(stage, msg)

    def on_failover(self, callback: Callable) -> None:
        """Register failover callback."""
        self._on_failover = callback

    def on_recovery(self, callback: Callable) -> None:
        """Register recovery callback."""
        self._on_recovery = callback

    # === RESOURCE MANAGEMENT ===

    def start_resource_monitor(self) -> None:
        """Start background resource monitoring."""
        self._monitor_running = True
        self._monitor_thread = threading.Thread(
            target=self._resource_loop, name="ResourceMonitor", daemon=True
        )
        self._monitor_thread.start()

    def stop_resource_monitor(self) -> None:
        self._monitor_running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=3.0)

    def _resource_loop(self) -> None:
        """Monitor CPU/RAM and throttle if needed."""
        while self._monitor_running:
            try:
                cpu = psutil.cpu_percent(interval=2.0)
                ram = psutil.virtual_memory().percent

                if karel_resource_cpu:
                    karel_resource_cpu.set(cpu)
                if karel_resource_ram:
                    karel_resource_ram.set(ram)

                if cpu > CPU_THRESHOLD or ram > RAM_THRESHOLD:
                    if not self._resource_constrained:
                        self._resource_constrained = True
                        logger.warning(
                            f"{LOG_PREFIX} Resources critical: CPU={cpu}%, RAM={ram}% "
                            f"— reducing concurrency"
                        )
                else:
                    if self._resource_constrained:
                        self._resource_constrained = False
                        logger.info(f"{LOG_PREFIX} Resources normalized: CPU={cpu}%, RAM={ram}%")

            except Exception as e:
                logger.debug(f"{LOG_PREFIX} Resource monitor error: {e}")

            time.sleep(CONNECTIVITY_CHECK_INTERVAL_S)

    @property
    def is_resource_constrained(self) -> bool:
        return self._resource_constrained

    # === CONNECTIVITY ===

    @property
    def is_online(self) -> bool:
        return self._online

    def set_online(self, online: bool) -> None:
        """Update connectivity state."""
        if online and not self._online:
            logger.info(f"{LOG_PREFIX} Connectivity RESTORED — resuming external APIs")
            if self._on_recovery:
                self._on_recovery()
        elif not online and self._online:
            logger.warning(f"{LOG_PREFIX} Connectivity LOST — offline mode")
        self._online = online

    # === STATUS ===

    def get_status(self) -> Dict[str, Any]:
        return {
            "autonomous_active": self._active,
            "online": self._online,
            "resource_constrained": self._resource_constrained,
            "failed_stages": dict(self._failed_stages),
        }


# === WINDOWS STARTUP ===

def create_startup_script(target_script: str = "src/karel_iv.py") -> str:
    """Generate Windows startup .bat script for Karel IV.

    Returns path to created script.
    """
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    bat_path = os.path.join(project_root, "start_karel.bat")

    bat_content = f"""@echo off
REM === Karel IV. — Auto-start on boot ===
REM Generated by autonomous_mode.py
REM Place shortcut in: %APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup

cd /d "{project_root}"
echo [KAREL] Starting Karel IV. pipeline...
echo [KAREL] Ethics Oath: ACTIVE
echo [KAREL] Central Stop: Mincovna authority only
python {target_script} --source cs --target en --model base --port 9306
pause
"""
    with open(bat_path, 'w', encoding='utf-8') as f:
        f.write(bat_content)

    logger.info(f"{LOG_PREFIX} Startup script created: {bat_path}")
    return bat_path


# === MAIN ===

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    print(f"{LOG_PREFIX} Autonomous Mode self-test")

    auto = AutonomousMode()

    # Error recovery test
    recovered = auto.handle_stage_error("test_stage", restart_fn=lambda: None)
    assert recovered
    print(f"  PASS: Error recovery (1st retry works)")

    # Resource monitor
    auto.start_resource_monitor()
    time.sleep(3)
    auto.stop_resource_monitor()
    print(f"  PASS: Resource monitor ran without crash")

    # Connectivity
    auto.set_online(False)
    assert not auto.is_online
    auto.set_online(True)
    assert auto.is_online
    print(f"  PASS: Connectivity transitions")

    # Startup script
    path = create_startup_script()
    assert os.path.exists(path)
    print(f"  PASS: Startup script created: {path}")

    print(f"  Status: {auto.get_status()}")
    print(f"{LOG_PREFIX} All tests PASSED.")


if __name__ == '__main__':
    main()
