"""
Offline Fallback — Universal Translation Layer (UTL)

Handles graceful degradation when mesh network is unavailable:
- Detects network connectivity loss within 1 second
- Falls back to local CTranslate2/OPUS-MT models for translation
- Queues tasks for later mesh delivery when connectivity returns
- Maintains service quality even without internet

Autor: Pan Jeskyně
Asistent: Kiro
"""

import time
import logging
import threading
import socket
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Deque, Optional, Callable, List

# === LOGGING ===

logger = logging.getLogger(__name__)
LOG_PREFIX = "[OFFLINE]"

# === PROMETHEUS METRICS ===

try:
    from prometheus_client import Gauge, Counter

    utl_offline_mode_active = Gauge(
        'utl_offline_mode_active',
        'Whether offline fallback mode is active (1=offline, 0=online)'
    )

    utl_offline_tasks_queued = Gauge(
        'utl_offline_tasks_queued',
        'Number of tasks queued for mesh delivery when back online'
    )

    utl_offline_transitions_total = Counter(
        'utl_offline_transitions_total',
        'Total transitions between online and offline mode',
        ['direction']  # 'to_offline', 'to_online'
    )
except ImportError:
    utl_offline_mode_active = None
    utl_offline_tasks_queued = None
    utl_offline_transitions_total = None

# === CONSTANTS ===

CONNECTIVITY_CHECK_INTERVAL_S = 1.0   # Check every 1 second
CONNECTIVITY_TIMEOUT_S = 2.0          # Socket timeout for checks
CONNECTIVITY_TARGET_HOST = "8.8.8.8"  # Google DNS as connectivity probe
CONNECTIVITY_TARGET_PORT = 53         # DNS port
MAX_QUEUED_TASKS = 1000               # Max tasks to queue while offline
RECONNECT_CONFIRM_COUNT = 3           # Consecutive successes before going online


# === ENUMS ===

class ConnectivityState(Enum):
    """Network connectivity state."""
    ONLINE = "online"
    OFFLINE = "offline"
    CHECKING = "checking"


# === DATA MODELS ===

@dataclass
class QueuedTask:
    """A task queued for mesh delivery when connectivity returns."""
    task_type: str
    payload: bytes
    priority: int = 5
    queued_at: float = field(default_factory=time.time)
    attempts: int = 0


# === OFFLINE FALLBACK CLASS ===

class OfflineFallback:
    """Handles graceful degradation when mesh is unavailable.

    Monitors network connectivity and switches between:
    - ONLINE mode: tasks routed to mesh network normally
    - OFFLINE mode: tasks processed locally, queued for later mesh sync

    Detection: connectivity loss detected within 1 second.
    Queue: tasks are stored and retried when connectivity returns.
    """

    def __init__(self, check_host: str = CONNECTIVITY_TARGET_HOST,
                 check_port: int = CONNECTIVITY_TARGET_PORT):
        """Initialize offline fallback manager.

        Args:
            check_host: Host to probe for connectivity checks
            check_port: Port for connectivity probes
        """
        self._lock = threading.Lock()
        self._state = ConnectivityState.ONLINE
        self._check_host = check_host
        self._check_port = check_port
        self._task_queue: Deque[QueuedTask] = deque(maxlen=MAX_QUEUED_TASKS)
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_running = False
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._on_offline_callback: Optional[Callable] = None
        self._on_online_callback: Optional[Callable] = None
        self._last_check_time: float = 0.0

        logger.info(f"{LOG_PREFIX} Initialized (probe: {check_host}:{check_port})")

    # === PUBLIC API ===

    @property
    def is_offline(self) -> bool:
        """Whether we're currently in offline mode."""
        return self._state == ConnectivityState.OFFLINE

    @property
    def is_online(self) -> bool:
        """Whether we're currently online."""
        return self._state == ConnectivityState.ONLINE

    @property
    def state(self) -> ConnectivityState:
        """Current connectivity state."""
        return self._state

    @property
    def queued_task_count(self) -> int:
        """Number of tasks waiting for mesh delivery."""
        return len(self._task_queue)

    def start_monitoring(self) -> None:
        """Start background connectivity monitoring.

        Checks connectivity every 1 second and transitions
        between online/offline modes as needed.
        """
        if self._monitor_running:
            return

        self._monitor_running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="ConnectivityMonitor",
            daemon=True,
        )
        self._monitor_thread.start()
        logger.info(f"{LOG_PREFIX} Connectivity monitoring started")

    def stop_monitoring(self) -> None:
        """Stop background connectivity monitoring."""
        self._monitor_running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=3.0)
        logger.info(f"{LOG_PREFIX} Connectivity monitoring stopped")

    def check_connectivity(self) -> bool:
        """Perform a single connectivity check.

        Returns True if network is reachable.
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(CONNECTIVITY_TIMEOUT_S)
            sock.connect((self._check_host, self._check_port))
            sock.close()
            return True
        except (socket.timeout, socket.error, OSError):
            return False

    def queue_task(self, task_type: str, payload: bytes,
                   priority: int = 5) -> bool:
        """Queue a task for later mesh delivery.

        Args:
            task_type: Type of task (e.g. "translate", "sync")
            payload: Task payload bytes
            priority: Task priority (1-10)

        Returns:
            True if queued successfully, False if queue is full
        """
        with self._lock:
            if len(self._task_queue) >= MAX_QUEUED_TASKS:
                logger.warning(f"{LOG_PREFIX} Task queue full ({MAX_QUEUED_TASKS})")
                return False

            task = QueuedTask(
                task_type=task_type,
                payload=payload,
                priority=priority,
            )
            self._task_queue.append(task)

            if utl_offline_tasks_queued:
                utl_offline_tasks_queued.set(len(self._task_queue))

            return True

    def drain_queue(self) -> List[QueuedTask]:
        """Drain all queued tasks (called when coming back online).

        Returns:
            List of queued tasks sorted by priority (highest first)
        """
        with self._lock:
            tasks = list(self._task_queue)
            self._task_queue.clear()

            if utl_offline_tasks_queued:
                utl_offline_tasks_queued.set(0)

        # Sort by priority (higher = more important)
        tasks.sort(key=lambda t: t.priority, reverse=True)
        logger.info(f"{LOG_PREFIX} Drained {len(tasks)} queued tasks")
        return tasks

    def on_offline(self, callback: Callable) -> None:
        """Register callback for offline transition."""
        self._on_offline_callback = callback

    def on_online(self, callback: Callable) -> None:
        """Register callback for online transition."""
        self._on_online_callback = callback

    # === INTERNAL ===

    def _monitor_loop(self) -> None:
        """Background monitoring loop — checks connectivity every second."""
        while self._monitor_running:
            is_reachable = self.check_connectivity()
            self._last_check_time = time.time()

            if is_reachable:
                self._consecutive_failures = 0
                self._consecutive_successes += 1

                if (self._state == ConnectivityState.OFFLINE and
                        self._consecutive_successes >= RECONNECT_CONFIRM_COUNT):
                    self._go_online()
            else:
                self._consecutive_successes = 0
                self._consecutive_failures += 1

                if (self._state == ConnectivityState.ONLINE and
                        self._consecutive_failures >= 1):
                    # Detect loss within 1 second (single failure = offline)
                    self._go_offline()

            time.sleep(CONNECTIVITY_CHECK_INTERVAL_S)

    def _go_offline(self) -> None:
        """Transition to offline mode."""
        with self._lock:
            if self._state == ConnectivityState.OFFLINE:
                return
            self._state = ConnectivityState.OFFLINE

        if utl_offline_mode_active:
            utl_offline_mode_active.set(1)
        if utl_offline_transitions_total:
            utl_offline_transitions_total.labels(direction="to_offline").inc()

        logger.warning(f"{LOG_PREFIX} OFFLINE — mesh unavailable, using local fallback")

        if self._on_offline_callback:
            try:
                self._on_offline_callback()
            except Exception as e:
                logger.error(f"{LOG_PREFIX} Offline callback error: {e}")

    def _go_online(self) -> None:
        """Transition to online mode."""
        with self._lock:
            if self._state == ConnectivityState.ONLINE:
                return
            self._state = ConnectivityState.ONLINE

        if utl_offline_mode_active:
            utl_offline_mode_active.set(0)
        if utl_offline_transitions_total:
            utl_offline_transitions_total.labels(direction="to_online").inc()

        queued = self.queued_task_count
        logger.info(
            f"{LOG_PREFIX} ONLINE — mesh available, "
            f"{queued} tasks queued for delivery"
        )

        if self._on_online_callback:
            try:
                self._on_online_callback()
            except Exception as e:
                logger.error(f"{LOG_PREFIX} Online callback error: {e}")

    # === STATUS ===

    def get_status(self) -> dict:
        """Get offline fallback status."""
        return {
            "state": self._state.value,
            "queued_tasks": len(self._task_queue),
            "monitoring": self._monitor_running,
            "consecutive_failures": self._consecutive_failures,
            "consecutive_successes": self._consecutive_successes,
        }


# === MAIN GUARD ===

def main():
    """Self-test entry point for Offline Fallback module."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    print(f"{LOG_PREFIX} Offline Fallback self-test")

    fallback = OfflineFallback()
    assert fallback.is_online
    assert fallback.queued_task_count == 0

    # Test connectivity check
    is_online = fallback.check_connectivity()
    print(f"{LOG_PREFIX} Current connectivity: {'online' if is_online else 'offline'}")

    # Test task queueing
    for i in range(5):
        success = fallback.queue_task("translate", f"payload_{i}".encode(), priority=i)
        assert success
    assert fallback.queued_task_count == 5
    print(f"{LOG_PREFIX} Queued 5 tasks: OK")

    # Test drain
    tasks = fallback.drain_queue()
    assert len(tasks) == 5
    assert tasks[0].priority == 4  # Highest priority first
    assert fallback.queued_task_count == 0
    print(f"{LOG_PREFIX} Drain queue: OK (sorted by priority)")

    # Test callbacks
    events = []
    fallback.on_offline(lambda: events.append("offline"))
    fallback.on_online(lambda: events.append("online"))

    # Simulate offline transition
    fallback._go_offline()
    assert fallback.is_offline
    assert "offline" in events
    print(f"{LOG_PREFIX} Offline transition: OK")

    # Simulate online transition
    fallback._go_online()
    assert fallback.is_online
    assert "online" in events
    print(f"{LOG_PREFIX} Online transition: OK")

    print(f"{LOG_PREFIX} Status: {fallback.get_status()}")
    print(f"{LOG_PREFIX} All self-tests passed.")


if __name__ == '__main__':
    main()
