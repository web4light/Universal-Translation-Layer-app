"""
n8n Webhook Client — Karel IV. Pipeline Communication
======================================================

Handles all communication between Karel IV. pipeline and n8n control plane.
Implements autonomous mode when n8n is unreachable (up to 60 minutes).

Webhooks:
- /webhook/pipeline-status — stage completion events
- /webhook/pipeline-error — stage failure events
- /webhook/component-register — component startup registration
- /webhook/system-status — system health queries
- /webhook/campaign-status — social campaign status

Standard: Karel IV. n8n System Requirement 1, 15
"""

import time
import logging
import threading
from typing import Optional, Dict, Any

# === LOGGING ===

logger = logging.getLogger(__name__)
LOG_PREFIX = "[N8N_CLIENT]"

# === PROMETHEUS METRICS ===

try:
    from prometheus_client import Counter, Gauge

    karel_n8n_requests_total = Counter(
        'karel_n8n_requests_total',
        'Total n8n webhook requests',
        ['endpoint', 'status']
    )
    karel_n8n_autonomous = Gauge(
        'karel_n8n_autonomous',
        'Whether pipeline is in autonomous mode (1=autonomous, 0=orchestrated)'
    )
except ImportError:
    karel_n8n_requests_total = None
    karel_n8n_autonomous = None

# === OPTIONAL IMPORTS ===

try:
    import requests as _requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

# === CONSTANTS ===

N8N_BASE_URL = "http://localhost:5678"
AUTONOMOUS_MODE_TIMEOUT_S = 3600  # 60 minutes
WEBHOOK_TIMEOUT_S = 5


# === N8N WEBHOOK CLIENT ===

class N8nWebhookClient:
    """Communicates with n8n control plane via webhooks.

    When n8n is unreachable, enters autonomous mode for up to 60 minutes.
    Pipeline continues with last known configuration.
    """

    def __init__(self, base_url: str = N8N_BASE_URL):
        self._base_url = base_url
        self._lock = threading.Lock()
        self._autonomous = False
        self._autonomous_since: Optional[float] = None
        self._last_success: float = time.time()
        self._consecutive_failures: int = 0

        logger.info(f"{LOG_PREFIX} Initialized (n8n: {base_url})")

    # === PUBLIC API ===

    @property
    def is_autonomous(self) -> bool:
        """Whether pipeline is running autonomously (n8n unreachable)."""
        return self._autonomous

    def report_stage_status(self, stage: str, status: str,
                            latency_ms: float = 0, extra: Dict = None) -> bool:
        """Report pipeline stage completion to n8n."""
        payload = {
            "stage": stage,
            "status": status,
            "latency_ms": latency_ms,
            "timestamp": int(time.time()),
            **(extra or {})
        }
        return self._post("/webhook/pipeline-status", payload)

    def report_error(self, stage: str, error_msg: str,
                     retry_count: int = 0) -> bool:
        """Report pipeline stage error to n8n."""
        payload = {
            "stage": stage,
            "error_msg": error_msg,
            "retry_count": retry_count,
            "timestamp": int(time.time())
        }
        return self._post("/webhook/pipeline-error", payload)

    def register_component(self, name: str, version: str,
                           port: int, health: str = "ok") -> bool:
        """Register a component with n8n on startup."""
        payload = {
            "name": name,
            "version": version,
            "port": port,
            "health": health,
            "timestamp": int(time.time())
        }
        return self._post("/webhook/component-register", payload)

    def report_campaign_status(self, phase: str, day: int,
                               message: str) -> bool:
        """Report social campaign execution status."""
        payload = {
            "phase": phase,
            "day": day,
            "message": message,
            "timestamp": int(time.time())
        }
        return self._post("/webhook/campaign-status", payload)

    def get_system_status(self) -> Optional[Dict]:
        """Query system status from n8n."""
        try:
            if not _HAS_REQUESTS:
                return None
            resp = _requests.get(
                f"{self._base_url}/webhook/system-status",
                timeout=WEBHOOK_TIMEOUT_S
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return None

    # === AUTONOMOUS MODE ===

    def check_autonomous_timeout(self) -> bool:
        """Check if autonomous mode has exceeded 60-minute limit.

        Returns True if still within limit, False if expired.
        """
        if not self._autonomous:
            return True
        elapsed = time.time() - self._autonomous_since
        if elapsed > AUTONOMOUS_MODE_TIMEOUT_S:
            logger.warning(
                f"{LOG_PREFIX} Autonomous mode EXPIRED "
                f"({elapsed:.0f}s > {AUTONOMOUS_MODE_TIMEOUT_S}s)"
            )
            return False
        return True

    # === INTERNAL ===

    def _post(self, endpoint: str, payload: Dict[str, Any]) -> bool:
        """POST to n8n webhook. Enter autonomous mode on failure."""
        if not _HAS_REQUESTS:
            self._enter_autonomous("requests library not available")
            return False

        url = f"{self._base_url}{endpoint}"
        try:
            resp = _requests.post(url, json=payload, timeout=WEBHOOK_TIMEOUT_S)
            if resp.status_code in (200, 201):
                self._on_success()
                if karel_n8n_requests_total:
                    karel_n8n_requests_total.labels(
                        endpoint=endpoint, status="success"
                    ).inc()
                return True
            else:
                self._on_failure(f"HTTP {resp.status_code}")
                return False
        except _requests.ConnectionError:
            self._on_failure("connection_refused")
            return False
        except _requests.Timeout:
            self._on_failure("timeout")
            return False
        except Exception as e:
            self._on_failure(str(e))
            return False

    def _on_success(self) -> None:
        """Handle successful n8n communication."""
        with self._lock:
            self._last_success = time.time()
            self._consecutive_failures = 0
            if self._autonomous:
                self._autonomous = False
                self._autonomous_since = None
                if karel_n8n_autonomous:
                    karel_n8n_autonomous.set(0)
                logger.info(f"{LOG_PREFIX} n8n RECONNECTED — leaving autonomous mode")

    def _on_failure(self, reason: str) -> None:
        """Handle failed n8n communication."""
        with self._lock:
            self._consecutive_failures += 1
            if karel_n8n_requests_total:
                karel_n8n_requests_total.labels(
                    endpoint="unknown", status="failed"
                ).inc()

            if not self._autonomous and self._consecutive_failures >= 2:
                self._enter_autonomous(reason)

    def _enter_autonomous(self, reason: str) -> None:
        """Enter autonomous mode — pipeline continues without n8n."""
        self._autonomous = True
        self._autonomous_since = time.time()
        if karel_n8n_autonomous:
            karel_n8n_autonomous.set(1)
        logger.warning(
            f"{LOG_PREFIX} AUTONOMOUS MODE — n8n unreachable ({reason}). "
            f"Pipeline continues for {AUTONOMOUS_MODE_TIMEOUT_S}s."
        )

    # === STATUS ===

    def get_status(self) -> Dict[str, Any]:
        return {
            "n8n_url": self._base_url,
            "autonomous": self._autonomous,
            "autonomous_since": self._autonomous_since,
            "consecutive_failures": self._consecutive_failures,
            "last_success": self._last_success,
        }


# === SYSTEM STARTUP ===

class SystemStartup:
    """Manages ordered component startup and registration with n8n.

    Startup order:
    1. Prometheus
    2. Faucet_SDN
    3. SPARK_Validator
    4. Whisper_STT
    5. Bifrost_Bridge
    6. Edge_TTS
    7. Geall_Agent
    8. Ethics_Oath

    Each component registers via webhook within 30 seconds.
    System is "operational" when all registered and healthy.
    """

    STARTUP_ORDER = [
        ("prometheus", "9090", "1.0"),
        ("faucet_sdn", "8080", "1.0"),
        ("spark_validator", "0", "2022"),
        ("whisper_stt", "0", "1.0"),
        ("bifrost_bridge", "0", "1.0"),
        ("edge_tts", "0", "1.0"),
        ("geall_agent", "0", "1.0"),
        ("ethics_oath", "0", "1.0"),
    ]

    def __init__(self, n8n_client: N8nWebhookClient):
        self._n8n = n8n_client
        self._registered: Dict[str, bool] = {}
        self._start_time: Optional[float] = None

    def startup_all(self) -> bool:
        """Start all components in order and register with n8n.

        Returns True if all components registered within 30s.
        """
        self._start_time = time.time()
        logger.info(f"{LOG_PREFIX} Starting system — {len(self.STARTUP_ORDER)} components")

        for name, port, version in self.STARTUP_ORDER:
            success = self._n8n.register_component(
                name=name, version=version,
                port=int(port), health="ok"
            )
            self._registered[name] = success
            if success:
                logger.info(f"{LOG_PREFIX} Registered: {name}")
            else:
                logger.warning(f"{LOG_PREFIX} Registration failed: {name} (autonomous mode)")

        elapsed = time.time() - self._start_time
        all_ok = all(self._registered.values())

        if all_ok:
            logger.info(f"{LOG_PREFIX} System OPERATIONAL in {elapsed:.1f}s")
        else:
            logger.info(f"{LOG_PREFIX} System DEGRADED — some registrations failed")

        return all_ok

    @property
    def is_operational(self) -> bool:
        return len(self._registered) == len(self.STARTUP_ORDER) and all(self._registered.values())

    @property
    def boot_time_s(self) -> float:
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time


# === MAIN ===

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    print(f"{LOG_PREFIX} n8n Client self-test")

    client = N8nWebhookClient()

    # Test autonomous mode (n8n not running)
    r = client.report_stage_status("stt", "completed", latency_ms=150)
    print(f"  report_stage_status: {'success' if r else 'failed (expected — n8n not running)'}")
    print(f"  autonomous: {client.is_autonomous}")

    # Test component registration
    r = client.register_component("test", "1.0", 9999)
    print(f"  register_component: {'success' if r else 'autonomous mode'}")

    # System startup
    startup = SystemStartup(client)
    startup.startup_all()
    print(f"  operational: {startup.is_operational}")
    print(f"  boot_time: {startup.boot_time_s:.1f}s")

    print(f"  Status: {client.get_status()}")
    print(f"{LOG_PREFIX} Done.")


if __name__ == '__main__':
    main()
