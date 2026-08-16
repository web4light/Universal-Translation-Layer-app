"""
Application Lifecycle & Resource Manager — Universal Translation Layer (UTL)

Manages application lifecycle states, resource allocation, and graceful
startup/shutdown for the Karel IV. platform.

- Lifecycle states: INITIALIZING → READY → RUNNING → PAUSING → STOPPED
- Resource tracking: CPU, RAM, GPU allocation per component
- Graceful shutdown: ordered component teardown
- Health check endpoint for Prometheus/Watchdog

Autor: Pan Jeskyně
Asistent: Kiro
"""

import time
import logging
import threading
import psutil
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable

# === LOGGING ===

logger = logging.getLogger(__name__)
LOG_PREFIX = "[LIFECYCLE]"

# === PROMETHEUS METRICS ===

try:
    from prometheus_client import Gauge, Counter, Info

    utl_app_state = Info(
        'utl_app_state',
        'Current application lifecycle state'
    )

    utl_app_uptime_seconds = Gauge(
        'utl_app_uptime_seconds',
        'Application uptime in seconds'
    )

    utl_resource_cpu_percent = Gauge(
        'utl_resource_cpu_percent',
        'CPU usage percent',
        ['component']
    )

    utl_resource_ram_mb = Gauge(
        'utl_resource_ram_mb',
        'RAM usage in MB',
        ['component']
    )

    utl_lifecycle_transitions_total = Counter(
        'utl_lifecycle_transitions_total',
        'Total lifecycle state transitions',
        ['from_state', 'to_state']
    )
except ImportError:
    utl_app_state = None
    utl_app_uptime_seconds = None
    utl_resource_cpu_percent = None
    utl_resource_ram_mb = None
    utl_lifecycle_transitions_total = None

# === CONSTANTS ===

HEALTH_CHECK_INTERVAL_S = 10
RESOURCE_POLL_INTERVAL_S = 5


# === ENUMS ===

class AppState(Enum):
    """Application lifecycle states."""
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSING = "pausing"
    STOPPED = "stopped"
    ERROR = "error"


# === DATA MODELS ===

@dataclass
class ComponentInfo:
    """Information about a registered component."""
    name: str
    startup_fn: Optional[Callable] = None
    shutdown_fn: Optional[Callable] = None
    health_fn: Optional[Callable] = None
    started: bool = False
    healthy: bool = True
    priority: int = 50  # Lower = starts first, shuts down last


@dataclass
class ResourceSnapshot:
    """Snapshot of current resource usage."""
    cpu_percent: float = 0.0
    ram_mb: float = 0.0
    ram_percent: float = 0.0
    gpu_percent: float = 0.0
    disk_free_gb: float = 0.0
    timestamp: float = field(default_factory=time.time)


# === APP LIFECYCLE CLASS ===

class AppLifecycle:
    """Manages application lifecycle and resource allocation.

    Provides ordered startup/shutdown of components, resource monitoring,
    health checks, and graceful state transitions.

    Lifecycle: INITIALIZING -> READY -> RUNNING -> PAUSING -> STOPPED
    """

    def __init__(self):
        """Initialize the lifecycle manager."""
        self._lock = threading.RLock()
        self._state = AppState.INITIALIZING
        self._started_at: Optional[float] = None
        self._components: Dict[str, ComponentInfo] = {}
        self._resource_thread: Optional[threading.Thread] = None
        self._resource_running = False
        self._last_snapshot = ResourceSnapshot()

        logger.info(f"{LOG_PREFIX} Lifecycle manager initialized")

    # === STATE MANAGEMENT ===

    @property
    def state(self) -> AppState:
        """Current application state."""
        return self._state

    @property
    def uptime_seconds(self) -> float:
        """Seconds since application started running."""
        if self._started_at is None:
            return 0.0
        return time.time() - self._started_at

    def transition_to(self, new_state: AppState) -> bool:
        """Transition to a new lifecycle state.

        Valid transitions:
        - INITIALIZING -> READY
        - READY -> RUNNING
        - RUNNING -> PAUSING
        - PAUSING -> STOPPED
        - Any -> ERROR
        - ERROR -> INITIALIZING (reset)

        Returns:
            True if transition was valid and executed
        """
        valid_transitions = {
            AppState.INITIALIZING: [AppState.READY, AppState.ERROR],
            AppState.READY: [AppState.RUNNING, AppState.ERROR],
            AppState.RUNNING: [AppState.PAUSING, AppState.ERROR],
            AppState.PAUSING: [AppState.STOPPED, AppState.ERROR],
            AppState.STOPPED: [AppState.INITIALIZING],
            AppState.ERROR: [AppState.INITIALIZING],
        }

        with self._lock:
            allowed = valid_transitions.get(self._state, [])
            if new_state not in allowed:
                logger.warning(
                    f"{LOG_PREFIX} Invalid transition: "
                    f"{self._state.value} -> {new_state.value}"
                )
                return False

            old_state = self._state
            self._state = new_state

            if utl_lifecycle_transitions_total:
                utl_lifecycle_transitions_total.labels(
                    from_state=old_state.value,
                    to_state=new_state.value,
                ).inc()

            if utl_app_state:
                utl_app_state.info({"state": new_state.value})

            logger.info(
                f"{LOG_PREFIX} State: {old_state.value} -> {new_state.value}"
            )
            return True

    # === COMPONENT REGISTRATION ===

    def register_component(self, name: str,
                           startup_fn: Callable = None,
                           shutdown_fn: Callable = None,
                           health_fn: Callable = None,
                           priority: int = 50) -> None:
        """Register a component for lifecycle management.

        Args:
            name: Component name (unique identifier)
            startup_fn: Function to call during startup (optional)
            shutdown_fn: Function to call during shutdown (optional)
            health_fn: Function to check health (returns bool, optional)
            priority: Startup priority (lower = first to start, last to stop)
        """
        with self._lock:
            self._components[name] = ComponentInfo(
                name=name,
                startup_fn=startup_fn,
                shutdown_fn=shutdown_fn,
                health_fn=health_fn,
                priority=priority,
            )
            logger.info(f"{LOG_PREFIX} Component registered: {name} (priority={priority})")

    # === STARTUP / SHUTDOWN ===

    def startup(self) -> bool:
        """Start all registered components in priority order.

        Transitions: INITIALIZING -> READY -> RUNNING
        Returns True if all components started successfully.
        """
        if self._state != AppState.INITIALIZING:
            logger.warning(f"{LOG_PREFIX} Cannot startup from state {self._state.value}")
            return False

        # Sort components by priority (lower = first)
        sorted_components = sorted(
            self._components.values(), key=lambda c: c.priority
        )

        # Transition to READY
        self.transition_to(AppState.READY)

        # Start components
        for component in sorted_components:
            if component.startup_fn:
                try:
                    component.startup_fn()
                    component.started = True
                    logger.info(f"{LOG_PREFIX} Started: {component.name}")
                except Exception as e:
                    logger.error(f"{LOG_PREFIX} Failed to start {component.name}: {e}")
                    component.healthy = False
                    self.transition_to(AppState.ERROR)
                    return False
            else:
                component.started = True

        # Transition to RUNNING
        self.transition_to(AppState.RUNNING)
        self._started_at = time.time()

        # Start resource monitoring
        self._start_resource_monitoring()

        logger.info(f"{LOG_PREFIX} All {len(sorted_components)} components started")
        return True

    def shutdown(self) -> bool:
        """Gracefully shut down all components in reverse priority order.

        Transitions: RUNNING -> PAUSING -> STOPPED
        """
        if self._state not in (AppState.RUNNING, AppState.ERROR):
            logger.warning(f"{LOG_PREFIX} Cannot shutdown from state {self._state.value}")
            return False

        self.transition_to(AppState.PAUSING)

        # Stop resource monitoring
        self._stop_resource_monitoring()

        # Shutdown components in reverse priority (high priority = shut down first)
        sorted_components = sorted(
            self._components.values(), key=lambda c: c.priority, reverse=True
        )

        for component in sorted_components:
            if component.started and component.shutdown_fn:
                try:
                    component.shutdown_fn()
                    component.started = False
                    logger.info(f"{LOG_PREFIX} Stopped: {component.name}")
                except Exception as e:
                    logger.error(f"{LOG_PREFIX} Error stopping {component.name}: {e}")

        self.transition_to(AppState.STOPPED)
        logger.info(f"{LOG_PREFIX} Shutdown complete. Uptime was {self.uptime_seconds:.1f}s")
        return True

    # === HEALTH CHECK ===

    def health_check(self) -> Dict[str, bool]:
        """Run health check on all registered components.

        Returns:
            Dict mapping component name to health status (True=healthy)
        """
        results = {}
        with self._lock:
            for name, component in self._components.items():
                if component.health_fn:
                    try:
                        results[name] = component.health_fn()
                    except Exception:
                        results[name] = False
                else:
                    results[name] = component.started and component.healthy

        return results

    def is_healthy(self) -> bool:
        """Overall application health — True only if all components healthy."""
        checks = self.health_check()
        return all(checks.values()) if checks else self._state == AppState.RUNNING

    # === RESOURCE MONITORING ===

    def get_resources(self) -> ResourceSnapshot:
        """Get current resource usage snapshot."""
        return self._last_snapshot

    def _start_resource_monitoring(self) -> None:
        """Start background resource monitoring thread."""
        self._resource_running = True
        self._resource_thread = threading.Thread(
            target=self._resource_loop,
            name="ResourceMonitor",
            daemon=True,
        )
        self._resource_thread.start()

    def _stop_resource_monitoring(self) -> None:
        """Stop resource monitoring."""
        self._resource_running = False
        if self._resource_thread:
            self._resource_thread.join(timeout=3.0)

    def _resource_loop(self) -> None:
        """Background loop collecting resource metrics."""
        while self._resource_running:
            try:
                process = psutil.Process()
                mem = process.memory_info()

                self._last_snapshot = ResourceSnapshot(
                    cpu_percent=process.cpu_percent(interval=1.0),
                    ram_mb=mem.rss / (1024 * 1024),
                    ram_percent=process.memory_percent(),
                    timestamp=time.time(),
                )

                if utl_app_uptime_seconds:
                    utl_app_uptime_seconds.set(self.uptime_seconds)

            except Exception as e:
                logger.debug(f"{LOG_PREFIX} Resource poll error: {e}")

            time.sleep(RESOURCE_POLL_INTERVAL_S)

    # === STATUS ===

    def get_status(self) -> Dict:
        """Full status report."""
        return {
            "state": self._state.value,
            "uptime_s": self.uptime_seconds,
            "components": len(self._components),
            "healthy": self.is_healthy(),
            "resources": {
                "cpu_percent": self._last_snapshot.cpu_percent,
                "ram_mb": self._last_snapshot.ram_mb,
            },
        }


# === MAIN GUARD ===

def main():
    """Self-test entry point for Application Lifecycle module."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    print(f"{LOG_PREFIX} Application Lifecycle self-test")

    lifecycle = AppLifecycle()
    assert lifecycle.state == AppState.INITIALIZING

    # Register mock components
    started_components = []

    lifecycle.register_component(
        "database",
        startup_fn=lambda: started_components.append("database"),
        shutdown_fn=lambda: started_components.remove("database"),
        health_fn=lambda: "database" in started_components,
        priority=10,
    )
    lifecycle.register_component(
        "mesh_orchestrator",
        startup_fn=lambda: started_components.append("mesh"),
        shutdown_fn=lambda: started_components.remove("mesh"),
        health_fn=lambda: "mesh" in started_components,
        priority=20,
    )
    lifecycle.register_component(
        "translation_engine",
        startup_fn=lambda: started_components.append("translation"),
        shutdown_fn=lambda: started_components.remove("translation"),
        priority=30,
    )

    # Startup
    assert lifecycle.startup() is True
    assert lifecycle.state == AppState.RUNNING
    assert len(started_components) == 3
    print(f"{LOG_PREFIX} Startup OK: {started_components}")

    # Health check
    health = lifecycle.health_check()
    assert health["database"] is True
    assert health["mesh_orchestrator"] is True
    print(f"{LOG_PREFIX} Health check: {health}")

    # Resources
    time.sleep(1.5)
    res = lifecycle.get_resources()
    print(f"{LOG_PREFIX} Resources: CPU={res.cpu_percent}%, RAM={res.ram_mb:.1f}MB")

    # Invalid transition
    assert lifecycle.transition_to(AppState.INITIALIZING) is False
    print(f"{LOG_PREFIX} Invalid transition rejected: OK")

    # Shutdown
    assert lifecycle.shutdown() is True
    assert lifecycle.state == AppState.STOPPED
    assert len(started_components) == 0
    print(f"{LOG_PREFIX} Shutdown OK")

    print(f"{LOG_PREFIX} Status: {lifecycle.get_status()}")
    print(f"{LOG_PREFIX} All self-tests passed.")


if __name__ == '__main__':
    main()
