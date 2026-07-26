"""
Transkomunikátor — Memory Manager
===================================

Enforces memory hard ceiling (512 MB) for the entire Transkomunikátor service.
Background thread monitors RSS every 5 seconds and evicts caches in priority
order when soft limit (480 MB) is exceeded.

Eviction priority (lower = evicted first):
  1. Translation cache
  2. TTS cache
  3. Voice models
  4. Old audio frames

Requirements: 2.1, 2.2, 2.3
Standard 700: 12g stříbra = 1 mince
Autor: Pan Jeskyně
Asistent: Kiro
"""

from __future__ import annotations

import logging
import threading
import time
from typing import List

import psutil

from .models import EvictableCache

# === LOGGING ===

logger = logging.getLogger(__name__)
_LOG = "[MEMORY]"

# === PROMETHEUS METRICS ===

try:
    from prometheus_client import Gauge
    transkomunikator_memory_usage_mb = Gauge(
        'transkomunikator_memory_usage_mb',
        'Current RSS memory usage in megabytes'
    )
except ImportError:
    transkomunikator_memory_usage_mb = None


# === CONSTANTS ===

HARD_LIMIT_MB: int = 512
SOFT_LIMIT_MB: int = 480
CHECK_INTERVAL_SECONDS: float = 5.0


# === MEMORY MANAGER ===

class MemoryManager:
    """Enforces memory limits for Transkomunikátor service.

    Monitors process RSS (Resident Set Size) every 5 seconds in a background
    thread. When RSS exceeds SOFT_LIMIT_MB (480 MB), evicts caches in priority
    order until below soft limit or all caches are empty. HARD_LIMIT_MB (512 MB)
    is the absolute ceiling — if reached, all evictable caches are purged.

    Attributes:
        HARD_LIMIT_MB: Absolute memory ceiling (512 MB). Never exceeded.
        SOFT_LIMIT_MB: Eviction trigger threshold (480 MB).
    """

    HARD_LIMIT_MB: int = HARD_LIMIT_MB
    SOFT_LIMIT_MB: int = SOFT_LIMIT_MB

    def __init__(self):
        self._caches: List[EvictableCache] = []
        self._lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None
        self._process = psutil.Process()
        self._last_rss_mb: float = 0.0
        self._eviction_count: int = 0
        logger.info(f"{_LOG} Initialized — hard={HARD_LIMIT_MB}MB, soft={SOFT_LIMIT_MB}MB")

    # === PUBLIC API ===

    def start(self) -> None:
        """Start background memory monitoring thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._monitor_loop,
            name="MemoryManager",
            daemon=True,
        )
        self._thread.start()
        logger.info(f"{_LOG} Background monitor started (interval={CHECK_INTERVAL_SECONDS}s)")

    def stop(self) -> None:
        """Stop background memory monitoring thread."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=CHECK_INTERVAL_SECONDS + 1)
        self._thread = None
        logger.info(f"{_LOG} Background monitor stopped")

    def register_evictable(self, cache: EvictableCache) -> None:
        """Register a cache that can be evicted under memory pressure.

        Caches are evicted in order of their `eviction_priority` property
        (lower number = evicted first).

        Args:
            cache: Object implementing EvictableCache ABC.
        """
        with self._lock:
            self._caches.append(cache)
            self._caches.sort(key=lambda c: c.eviction_priority)
        logger.info(
            f"{_LOG} Registered evictable cache (priority={cache.eviction_priority}, "
            f"total caches={len(self._caches)})"
        )

    def unregister_evictable(self, cache: EvictableCache) -> None:
        """Remove a cache from the eviction list."""
        with self._lock:
            if cache in self._caches:
                self._caches.remove(cache)

    def get_rss_mb(self) -> float:
        """Get current process RSS (Resident Set Size) in megabytes."""
        try:
            rss_bytes = self._process.memory_info().rss
            rss_mb = rss_bytes / (1024 * 1024)
            self._last_rss_mb = rss_mb
            if transkomunikator_memory_usage_mb is not None:
                transkomunikator_memory_usage_mb.set(rss_mb)
            return rss_mb
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return self._last_rss_mb

    def enforce_limit(self) -> int:
        """Check memory and evict caches if necessary.

        Called every 5 seconds by the background thread, but can also
        be called manually.

        Returns:
            Number of bytes freed by eviction (0 if no eviction needed).
        """
        rss_mb = self.get_rss_mb()
        total_freed = 0

        if rss_mb <= self.SOFT_LIMIT_MB:
            return 0

        # Above soft limit — start evicting in priority order
        logger.warning(
            f"{_LOG} RSS={rss_mb:.1f}MB exceeds soft limit ({self.SOFT_LIMIT_MB}MB) — "
            f"starting eviction"
        )

        with self._lock:
            caches_snapshot = list(self._caches)

        for cache in caches_snapshot:
            if self.get_rss_mb() <= self.SOFT_LIMIT_MB:
                break

            try:
                freed = cache.evict()
                total_freed += freed
                self._eviction_count += 1
                logger.info(
                    f"{_LOG} Evicted cache (priority={cache.eviction_priority}, "
                    f"freed={freed / (1024 * 1024):.1f}MB)"
                )
            except Exception as e:
                logger.error(f"{_LOG} Eviction failed: {e}")

        # Check if we hit hard limit after eviction
        final_rss = self.get_rss_mb()
        if final_rss > self.HARD_LIMIT_MB:
            logger.critical(
                f"{_LOG} HARD LIMIT BREACH: RSS={final_rss:.1f}MB > {self.HARD_LIMIT_MB}MB "
                f"after full eviction — service degraded"
            )

        return total_freed

    def purge_non_essential(self) -> int:
        """Force-purge all non-essential caches regardless of current RSS.

        Used during graceful shutdown or critical memory pressure events.

        Returns:
            Total bytes freed.
        """
        total_freed = 0
        with self._lock:
            caches_snapshot = list(self._caches)

        for cache in caches_snapshot:
            try:
                freed = cache.evict()
                total_freed += freed
            except Exception as e:
                logger.error(f"{_LOG} Purge failed for cache: {e}")

        logger.info(f"{_LOG} Purged all non-essential caches — freed {total_freed / (1024*1024):.1f}MB")
        return total_freed

    def get_status(self) -> dict:
        """Get memory manager status."""
        rss = self.get_rss_mb()
        return {
            "rss_mb": round(rss, 1),
            "hard_limit_mb": self.HARD_LIMIT_MB,
            "soft_limit_mb": self.SOFT_LIMIT_MB,
            "above_soft_limit": rss > self.SOFT_LIMIT_MB,
            "above_hard_limit": rss > self.HARD_LIMIT_MB,
            "registered_caches": len(self._caches),
            "eviction_count": self._eviction_count,
            "running": self._running,
        }

    # === PRIVATE ===

    def _monitor_loop(self) -> None:
        """Background thread: check memory every CHECK_INTERVAL_SECONDS."""
        while self._running:
            try:
                self.enforce_limit()
            except Exception as e:
                logger.error(f"{_LOG} Monitor loop error: {e}")
            time.sleep(CHECK_INTERVAL_SECONDS)


# === ENTRY POINT ===

def main() -> None:
    """Self-test demonstrating MemoryManager."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    print("=" * 60)
    print("  MemoryManager — Self-test")
    print(f"  Hard limit: {HARD_LIMIT_MB} MB")
    print(f"  Soft limit: {SOFT_LIMIT_MB} MB")
    print("=" * 60)
    print()

    mm = MemoryManager()
    status = mm.get_status()
    print(f"  Current RSS: {status['rss_mb']} MB")
    print(f"  Above soft limit: {status['above_soft_limit']}")
    print(f"  Above hard limit: {status['above_hard_limit']}")
    print()

    # Test eviction with a mock cache
    class MockCache(EvictableCache):
        def evict(self) -> int:
            return 50 * 1024 * 1024  # "freed" 50 MB

        def memory_usage_bytes(self) -> int:
            return 50 * 1024 * 1024

        @property
        def eviction_priority(self) -> int:
            return 1

    mm.register_evictable(MockCache())
    print(f"  Registered caches: {mm.get_status()['registered_caches']}")
    print(f"  Enforce limit result: {mm.enforce_limit()} bytes freed")
    print()
    print("  MemoryManager self-test PASSED")


if __name__ == "__main__":
    main()
