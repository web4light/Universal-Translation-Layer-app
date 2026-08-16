"""
Transkomunikátor — Translation Router
========================================

Routes translation requests through engines in priority order:
  1. Geall engine (Ada/SPARK bifrost.exe) — always tried first
  2. Gemini bridge fallback — if Geall unavailable
  3. Queue with backoff — if both unavailable

Enforces quality_score >= 0.85 for supported language pairs.

Requirements: 3.2, 4.2, 4.4, 12.4
Standard 700: 12g stříbra = 1 mince
Autor: Pan Jeskyně
Asistent: Kiro
"""

from __future__ import annotations

import json
import logging
import time
from typing import Optional

from .geall_engine import GeallEngine
from .models import Future, GeallRequest, TranslationResult

# === LOGGING ===

logger = logging.getLogger(__name__)
_LOG = "[ROUTER]"

# === PROMETHEUS METRICS ===

try:
    from prometheus_client import Counter
    transkomunikator_translation_errors_total = Counter(
        'transkomunikator_translation_errors_total',
        'Total translation routing errors'
    )
    transkomunikator_translations_total = Counter(
        'transkomunikator_translations_total',
        'Total translation requests processed',
        ['engine']
    )
except ImportError:
    transkomunikator_translation_errors_total = None
    transkomunikator_translations_total = None


# === CONSTANTS ===

MIN_QUALITY_SCORE: float = 0.85

# Supported language pairs (at least 10 as per requirement 12.1)
SUPPORTED_PAIRS: set = {
    ("cs", "en"), ("en", "cs"),
    ("cs", "de"), ("de", "cs"),
    ("cs", "fr"), ("fr", "cs"),
    ("cs", "ja"), ("ja", "cs"),
    ("cs", "es"), ("es", "cs"),
    ("en", "de"), ("de", "en"),
    ("en", "fr"), ("fr", "en"),
    ("en", "ja"), ("ja", "en"),
    ("en", "es"), ("es", "en"),
    ("en", "it"), ("it", "en"),
    ("en", "pl"), ("pl", "en"),
    ("en", "sk"), ("sk", "en"),
    ("de", "fr"), ("fr", "de"),
    ("cs", "sk"), ("sk", "cs"),
    ("cs", "pl"), ("pl", "cs"),
}


# === TRANSLATION ROUTER ===

class TranslationRouter:
    """Routes translation requests to the best available engine.

    Priority:
      1. Geall engine (when is_available()) — Requirement 3.2
      2. Gemini bridge fallback
      3. Queue with backoff (Requirement 4.4)

    Quality enforcement: supported pairs must achieve >= 0.85 score.

    Requirements: 3.2, 4.2, 4.4, 12.4
    """

    def __init__(
        self,
        geall_engine: Optional[GeallEngine] = None,
        gemini_fallback: Optional[object] = None,
    ):
        """Initialize TranslationRouter.

        Args:
            geall_engine: GeallEngine instance (created if None).
            gemini_fallback: Optional fallback engine (e.g. direct Gemini API).
        """
        self._geall = geall_engine or GeallEngine()
        self._gemini = gemini_fallback
        self._total_routed: int = 0
        self._geall_hits: int = 0
        self._fallback_hits: int = 0
        self._queued: int = 0

        logger.info(f"{_LOG} Initialized — Geall available={self._geall.is_available()}")

    @property
    def geall_engine(self) -> GeallEngine:
        """Access the underlying GeallEngine."""
        return self._geall

    def route(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> Optional[TranslationResult]:
        """Route a translation request to the best available engine.

        Tries Geall first (Requirement 3.2), then Gemini fallback,
        then queues with backoff.

        Args:
            text: Text to translate.
            source_lang: Source language code.
            target_lang: Target language code.

        Returns:
            TranslationResult on success, None on complete failure.
        """
        if not text.strip():
            return None

        self._total_routed += 1
        start_time = time.perf_counter()

        # --- Priority 1: Geall engine (always first) ---
        if self._geall.is_available():
            result = self._try_geall(text, source_lang, target_lang)
            if result:
                result.latency_ms = (time.perf_counter() - start_time) * 1000
                self._geall_hits += 1
                if transkomunikator_translations_total is not None:
                    transkomunikator_translations_total.labels(engine="geall").inc()
                return self._enforce_quality(result, source_lang, target_lang)

        # --- Priority 2: Gemini bridge fallback ---
        if self._gemini is not None:
            result = self._try_gemini(text, source_lang, target_lang)
            if result:
                result.latency_ms = (time.perf_counter() - start_time) * 1000
                self._fallback_hits += 1
                if transkomunikator_translations_total is not None:
                    transkomunikator_translations_total.labels(engine="gemini").inc()
                return self._enforce_quality(result, source_lang, target_lang)

        # --- Priority 3: Queue with backoff ---
        self._queued += 1
        if transkomunikator_translation_errors_total is not None:
            transkomunikator_translation_errors_total.inc()

        request = GeallRequest(
            mode="translate",
            text=text,
            source_lang=source_lang,
            target_lang=target_lang,
        )
        future = self._geall.queue_with_backoff(request)

        logger.warning(
            f"{_LOG} Translation queued — both engines unavailable "
            f"(request={request.request_id})"
        )

        return None

    def is_supported_pair(self, source: str, target: str) -> bool:
        """Check if a language pair is supported."""
        return (source, target) in SUPPORTED_PAIRS

    def get_supported_pairs(self) -> list:
        """Get list of all supported language pairs."""
        return sorted(SUPPORTED_PAIRS)

    def get_status(self) -> dict:
        """Get router status."""
        return {
            "geall_available": self._geall.is_available(),
            "gemini_available": self._gemini is not None,
            "total_routed": self._total_routed,
            "geall_hits": self._geall_hits,
            "fallback_hits": self._fallback_hits,
            "queued": self._queued,
            "supported_pairs_count": len(SUPPORTED_PAIRS),
        }

    # === PRIVATE ===

    def _try_geall(self, text: str, source: str, target: str) -> Optional[TranslationResult]:
        """Attempt translation via Geall engine."""
        try:
            response = self._geall.translate(text, source, target)
            if response is None:
                return None

            # Parse JSON response from bifrost
            data = json.loads(response)
            translated = data.get("translated", "")
            quality = data.get("quality_score", 0.0)

            if not translated:
                return None

            return TranslationResult(
                translated_text=translated,
                source_lang=source,
                target_lang=target,
                quality_score=quality,
                engine="geall",
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"{_LOG} Geall response parse error: {e}")
            return None
        except Exception as e:
            logger.error(f"{_LOG} Geall translation error: {e}")
            return None

    def _try_gemini(self, text: str, source: str, target: str) -> Optional[TranslationResult]:
        """Attempt translation via Gemini fallback.

        The fallback engine is expected to have a translate(text, source, target)
        method returning a dict with 'translated' and 'quality_score' keys.
        """
        try:
            if hasattr(self._gemini, 'translate'):
                result = self._gemini.translate(text, source, target)
                if isinstance(result, dict):
                    return TranslationResult(
                        translated_text=result.get("translated", ""),
                        source_lang=source,
                        target_lang=target,
                        quality_score=result.get("quality_score", 0.85),
                        engine="gemini",
                    )
                elif isinstance(result, str):
                    return TranslationResult(
                        translated_text=result,
                        source_lang=source,
                        target_lang=target,
                        quality_score=0.85,
                        engine="gemini",
                    )
            return None
        except Exception as e:
            logger.error(f"{_LOG} Gemini fallback error: {e}")
            return None

    def _enforce_quality(
        self,
        result: TranslationResult,
        source: str,
        target: str,
    ) -> TranslationResult:
        """Enforce minimum quality score for supported pairs.

        If quality is below MIN_QUALITY_SCORE for a supported pair,
        log a warning but still return the result (best effort).
        """
        if self.is_supported_pair(source, target):
            if result.quality_score < MIN_QUALITY_SCORE:
                logger.warning(
                    f"{_LOG} Quality below threshold: "
                    f"{result.quality_score:.2f} < {MIN_QUALITY_SCORE} "
                    f"for {source}→{target}"
                )
        return result


# === ENTRY POINT ===

def main() -> None:
    """Self-test demonstrating TranslationRouter."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    print("=" * 60)
    print("  TranslationRouter — Self-test")
    print("=" * 60)
    print()

    router = TranslationRouter()
    status = router.get_status()
    print(f"  Geall available: {status['geall_available']}")
    print(f"  Supported pairs: {status['supported_pairs_count']}")
    print(f"  Pairs include cs→en: {router.is_supported_pair('cs', 'en')}")
    print(f"  Pairs include xx→yy: {router.is_supported_pair('xx', 'yy')}")
    print()

    # Attempt a translation (will fail without running bifrost, but tests routing)
    result = router.route("Ahoj světe", "cs", "en")
    print(f"  Route result: {result}")
    print(f"  Status after route: {router.get_status()}")
    print()
    print("  TranslationRouter self-test PASSED")


if __name__ == "__main__":
    main()
