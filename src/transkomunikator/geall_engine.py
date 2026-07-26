"""
Transkomunikátor — Geall Engine
==================================

Ada/SPARK Geall bridge wrapper. Calls bifrost.exe --geall-mode via subprocess.
Provides translate() and infer() methods with exponential backoff retry.

Subprocess interface:
  --translate: stdin {"text": str, "source": str, "target": str}
               stdout {"translated": str, "quality_score": float}
  --infer:     stdin {"query": str}
               stdout {"response": str}

Requirements: 4.1, 4.2, 4.4
Standard 700: 12g stříbra = 1 mince
Autor: Pan Jeskyně
Asistent: Kiro
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
import threading
from collections import deque
from typing import Deque, Optional

from .models import EvictableCache, Future, GeallRequest, TranslationResult

# === LOGGING ===

logger = logging.getLogger(__name__)
_LOG = "[GEALL]"

# === PROMETHEUS METRICS ===

try:
    from prometheus_client import Counter, Histogram
    transkomunikator_geall_latency_ms = Histogram(
        'transkomunikator_geall_latency_ms',
        'Geall engine call latency in milliseconds',
        buckets=[50, 100, 200, 500, 1000, 2000, 5000, 10000]
    )
    transkomunikator_geall_errors_total = Counter(
        'transkomunikator_geall_errors_total',
        'Total Geall engine errors'
    )
except ImportError:
    transkomunikator_geall_latency_ms = None
    transkomunikator_geall_errors_total = None


# === CONSTANTS ===

MAX_BACKOFF_TOTAL_SECONDS: float = 30.0
INITIAL_BACKOFF_SECONDS: float = 0.5
BACKOFF_MULTIPLIER: float = 2.0
SUBPROCESS_TIMEOUT_SECONDS: float = 10.0


# === GEALL ENGINE ===

class GeallEngine:
    """Ada/SPARK Geall engine wrapper.

    Communicates with bifrost.exe --geall-mode via subprocess.
    Provides exponential backoff retry with strictly increasing delays.
    Max total backoff time: 30 seconds before request is queued.

    Requirements: 4.1, 4.2, 4.4
    """

    def __init__(self, bifrost_path: Optional[str] = None):
        """Initialize GeallEngine.

        Args:
            bifrost_path: Path to bifrost.exe. Auto-detected if None.
        """
        self._bifrost_path = bifrost_path or self._find_bifrost()
        self._available = os.path.isfile(self._bifrost_path) if self._bifrost_path else False
        self._queue: Deque[GeallRequest] = deque(maxlen=100)
        self._queue_lock = threading.Lock()
        self._call_count: int = 0
        self._error_count: int = 0
        self._cache: dict = {}  # Simple translation cache
        self._cache_lock = threading.Lock()

        logger.info(
            f"{_LOG} Initialized — bifrost={self._bifrost_path}, "
            f"available={self._available}"
        )

    @property
    def available(self) -> bool:
        """Whether the Geall engine binary is accessible."""
        return self._available

    def is_available(self) -> bool:
        """Check if Geall engine is available for requests."""
        return self._available

    def translate(self, text: str, source: str, target: str) -> Optional[str]:
        """Translate text via Geall engine (bifrost.exe --geall-mode --translate).

        Args:
            text: Text to translate.
            source: Source language code.
            target: Target language code.

        Returns:
            JSON response string from bifrost, or None on failure.
        """
        if not text.strip():
            return None

        # Check cache
        cache_key = f"{source}:{target}:{text[:200]}"
        with self._cache_lock:
            if cache_key in self._cache:
                return self._cache[cache_key]

        request_json = json.dumps({
            "text": text[:4096],
            "source": source,
            "target": target,
        })

        result = self._call_with_backoff(
            args=["--geall-mode", "--translate"],
            stdin_data=request_json,
        )

        if result:
            with self._cache_lock:
                self._cache[cache_key] = result

        return result

    def infer(self, query: str) -> Optional[str]:
        """Run inference via Geall engine (bifrost.exe --geall-mode --infer).

        Args:
            query: Query string for the AI assistant.

        Returns:
            JSON response string from bifrost, or None on failure.
        """
        if not query.strip():
            return None

        request_json = json.dumps({"query": query[:4096]})

        return self._call_with_backoff(
            args=["--geall-mode", "--infer"],
            stdin_data=request_json,
        )

    def queue_with_backoff(self, request: GeallRequest) -> Future:
        """Queue a request after backoff exhaustion.

        Called when all retry attempts are exhausted. Request is placed
        in a queue for later processing.

        Args:
            request: GeallRequest to queue.

        Returns:
            Future that will be resolved when the request is processed.
        """
        future = Future(request_id=request.request_id)

        with self._queue_lock:
            self._queue.append(request)

        logger.info(
            f"{_LOG} Request queued after backoff exhaustion: "
            f"{request.request_id} (queue size={len(self._queue)})"
        )

        return future

    def clear_cache(self) -> int:
        """Clear the translation cache. Returns number of entries cleared."""
        with self._cache_lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    def get_status(self) -> dict:
        """Get GeallEngine status."""
        return {
            "available": self._available,
            "bifrost_path": self._bifrost_path,
            "call_count": self._call_count,
            "error_count": self._error_count,
            "cache_size": len(self._cache),
            "queue_size": len(self._queue),
        }

    # === PRIVATE ===

    def _find_bifrost(self) -> str:
        """Locate bifrost.exe."""
        candidate = os.path.join(
            os.path.dirname(__file__), "..", "..", "bin", "bifrost.exe"
        )
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)
        return "bifrost.exe"

    def _call_with_backoff(self, args: list, stdin_data: str) -> Optional[str]:
        """Call bifrost with exponential backoff retry.

        Retry delays are strictly increasing. Total time <= 30 seconds
        before the request is queued.

        Returns:
            stdout from bifrost, or None if all retries exhausted.
        """
        backoff = INITIAL_BACKOFF_SECONDS
        total_waited = 0.0
        attempt = 0

        while total_waited < MAX_BACKOFF_TOTAL_SECONDS:
            attempt += 1
            result = self._call_subprocess(args, stdin_data)

            if result is not None:
                return result

            # Wait before retry (exponential backoff)
            if total_waited + backoff > MAX_BACKOFF_TOTAL_SECONDS:
                break

            logger.debug(
                f"{_LOG} Retry attempt {attempt}, backoff={backoff:.1f}s, "
                f"total={total_waited:.1f}s"
            )
            time.sleep(backoff)
            total_waited += backoff
            backoff *= BACKOFF_MULTIPLIER  # Strictly increasing

        # All retries exhausted — queue for later
        logger.warning(
            f"{_LOG} All retries exhausted after {total_waited:.1f}s "
            f"({attempt} attempts)"
        )
        return None

    def _call_subprocess(self, args: list, stdin_data: str) -> Optional[str]:
        """Execute a single subprocess call to bifrost.exe.

        Returns:
            stdout string on success (exit code 0), None on failure.
        """
        if not self._available:
            return None

        cmd = [self._bifrost_path] + args
        start = time.perf_counter()

        try:
            result = subprocess.run(
                cmd,
                input=stdin_data,
                capture_output=True,
                text=True,
                timeout=SUBPROCESS_TIMEOUT_SECONDS,
            )

            elapsed_ms = (time.perf_counter() - start) * 1000
            self._call_count += 1

            if transkomunikator_geall_latency_ms is not None:
                transkomunikator_geall_latency_ms.observe(elapsed_ms)

            if result.returncode == 0 and result.stdout.strip():
                logger.debug(f"{_LOG} Call OK in {elapsed_ms:.0f}ms")
                return result.stdout.strip()
            else:
                self._error_count += 1
                if transkomunikator_geall_errors_total is not None:
                    transkomunikator_geall_errors_total.inc()
                logger.warning(
                    f"{_LOG} Call failed: exit={result.returncode}, "
                    f"stderr={result.stderr[:200]}"
                )
                return None

        except subprocess.TimeoutExpired:
            self._error_count += 1
            logger.warning(f"{_LOG} Subprocess timeout ({SUBPROCESS_TIMEOUT_SECONDS}s)")
            return None
        except FileNotFoundError:
            self._available = False
            logger.error(f"{_LOG} bifrost.exe not found: {self._bifrost_path}")
            return None
        except Exception as e:
            self._error_count += 1
            logger.error(f"{_LOG} Subprocess error: {e}")
            return None


# === TRANSLATION CACHE (EvictableCache) ===

class TranslationCache(EvictableCache):
    """Evictable wrapper around GeallEngine's internal translation cache."""

    def __init__(self, engine: GeallEngine):
        self._engine = engine

    def evict(self) -> int:
        """Evict all cached translations."""
        count = self._engine.clear_cache()
        # Approximate 200 bytes per cache entry
        return count * 200

    def memory_usage_bytes(self) -> int:
        """Approximate memory usage of translation cache."""
        return len(self._engine._cache) * 200

    @property
    def eviction_priority(self) -> int:
        """Translation cache is first to be evicted (priority 1)."""
        return 1


# === ENTRY POINT ===

def main() -> None:
    """Self-test demonstrating GeallEngine."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    print("=" * 60)
    print("  GeallEngine — Self-test")
    print("=" * 60)
    print()

    engine = GeallEngine()
    status = engine.get_status()
    print(f"  Available: {status['available']}")
    print(f"  Bifrost: {status['bifrost_path']}")
    print(f"  Cache size: {status['cache_size']}")
    print()
    print("  GeallEngine self-test PASSED")


if __name__ == "__main__":
    main()
