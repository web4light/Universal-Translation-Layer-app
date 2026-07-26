"""
Language Detector — Universal Translation Layer (UTL)

Detekce jazyka pro textový a audio pipeline Karel IV.
- detect_text(text) -> LanguageResult: detekce jazyka z textu (langdetect backend)
- detect_audio(audio) -> LanguageResult: stub pro audio detekci
- should_translate(result, user_lang) -> bool: rozhodnutí zda překládat (95% threshold)
- Per-contact/per-channel language preference cache

Autor: Pan Jeskyne
Asistent: Kiro
"""

import time
import logging
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict

# === LOGGING ===

logger = logging.getLogger(__name__)
LOG_PREFIX = "[LANG_DETECT]"

# === PROMETHEUS METRICS ===

try:
    from prometheus_client import Histogram, Gauge

    utl_language_detection_confidence = Gauge(
        'utl_language_detection_confidence',
        'Confidence score of the last language detection (0.0 - 1.0)'
    )

    utl_language_detection_latency_seconds = Histogram(
        'utl_language_detection_latency_seconds',
        'Latency of language detection operations in seconds',
        buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
    )
except ImportError:
    utl_language_detection_confidence = None
    utl_language_detection_latency_seconds = None

# === LANGDETECT BACKEND ===

try:
    from langdetect import detect_langs as _langdetect_detect_langs
    from langdetect import DetectorFactory
    # Deterministic results for consistent behavior
    DetectorFactory.seed = 0
    _LANGDETECT_AVAILABLE = True
except ImportError:
    _LANGDETECT_AVAILABLE = False

# === CONSTANTS ===

CONFIDENCE_THRESHOLD_TRANSLATE = 0.95   # 95% confidence to trigger translation
CONFIDENCE_THRESHOLD_LOW = 0.80         # Below 80% = low confidence indicator

# Supported languages (ISO 639-1 codes) — minimum 30 per requirement
SUPPORTED_LANGUAGES = [
    "af", "ar", "bg", "bn", "ca", "cs", "cy", "da", "de", "el",
    "en", "es", "et", "fa", "fi", "fr", "gu", "he", "hi", "hr",
    "hu", "id", "it", "ja", "kn", "ko", "lt", "lv", "mk", "ml",
    "mr", "ne", "nl", "no", "pa", "pl", "pt", "ro", "ru", "sk",
    "sl", "so", "sq", "sv", "sw", "ta", "te", "th", "tl", "tr",
    "uk", "ur", "vi", "zh-cn", "zh-tw",
]


# === DATA MODELS ===

@dataclass
class LanguageResult:
    """Result of a language detection operation.

    Attributes:
        language: ISO 639-1 language code (e.g. 'en', 'cs', 'de')
        confidence: Detection confidence score 0.0 - 1.0
        alternatives: List of (language_code, confidence) tuples for runner-up detections
    """

    language: str
    confidence: float
    alternatives: List[Tuple[str, float]] = field(default_factory=list)

    def __post_init__(self):
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")
        self.language = self.language.lower().strip()

    @property
    def is_low_confidence(self) -> bool:
        """True when confidence < 80% — indicates uncertain detection."""
        return self.confidence < CONFIDENCE_THRESHOLD_LOW

    def __repr__(self) -> str:
        return (f"LanguageResult(language='{self.language}', "
                f"confidence={self.confidence:.3f}, "
                f"alternatives={self.alternatives})")


# === LANGUAGE PREFERENCE CACHE ===

@dataclass
class LanguagePreference:
    """Cached language preference for a contact or channel."""

    language: str
    confidence: float
    last_seen: float  # Unix timestamp
    detection_count: int = 1


# === LANGUAGE DETECTOR CLASS ===

class LanguageDetector:
    """Fast language detection for text and audio streams.

    Uses langdetect library as the backend for text detection.
    Provides per-contact/per-channel caching to skip repeated detection overhead.
    Exposes Prometheus metrics for confidence and latency monitoring.
    """

    def __init__(self):
        """Initialize the Language Detector."""
        self._preference_cache: Dict[str, LanguagePreference] = {}
        self._cache_hit_count: int = 0
        self._cache_miss_count: int = 0

        if not _LANGDETECT_AVAILABLE:
            logger.warning(
                f"{LOG_PREFIX} langdetect library not available. "
                "Detection will return unknown with 0.0 confidence. "
                "Install with: pip install langdetect"
            )

    # === TEXT DETECTION ===

    def detect_text(self, text: str) -> LanguageResult:
        """Detect the language of a text string.

        Args:
            text: Input text to analyze. Minimum ~10 characters recommended
                  for reliable detection.

        Returns:
            LanguageResult with detected language, confidence, and alternatives.
            If langdetect is not installed, returns 'unknown' with 0.0 confidence.
        """
        start_time = time.perf_counter()

        try:
            result = self._do_detect_text(text)
        except Exception as e:
            logger.error(f"{LOG_PREFIX} Detection failed: {e}")
            result = LanguageResult(language="unknown", confidence=0.0)
        finally:
            elapsed = time.perf_counter() - start_time
            if utl_language_detection_latency_seconds is not None:
                utl_language_detection_latency_seconds.observe(elapsed)

        if utl_language_detection_confidence is not None:
            utl_language_detection_confidence.set(result.confidence)

        return result

    def _do_detect_text(self, text: str) -> LanguageResult:
        """Internal detection logic."""
        if not text or not text.strip():
            return LanguageResult(language="unknown", confidence=0.0)

        if not _LANGDETECT_AVAILABLE:
            return LanguageResult(language="unknown", confidence=0.0)

        # langdetect returns list of Language objects with .lang and .prob
        detections = _langdetect_detect_langs(text)

        if not detections:
            return LanguageResult(language="unknown", confidence=0.0)

        primary = detections[0]
        alternatives = [
            (d.lang, round(d.prob, 4))
            for d in detections[1:]
        ]

        return LanguageResult(
            language=primary.lang,
            confidence=round(primary.prob, 4),
            alternatives=alternatives
        )

    # === AUDIO DETECTION (STUB) ===

    def detect_audio(self, audio) -> LanguageResult:
        """Detect the language from an audio stream/array.

        This is a stub implementation. Full audio language detection
        will be integrated when the audio pipeline (Whisper STT) is wired.

        Args:
            audio: Audio data (numpy array or bytes). Currently unused.

        Returns:
            LanguageResult with 'unknown' language and 0.0 confidence (stub).
        """
        start_time = time.perf_counter()

        # Stub: audio detection not yet implemented
        logger.info(f"{LOG_PREFIX} Audio language detection is a stub — returning unknown")
        result = LanguageResult(language="unknown", confidence=0.0)

        elapsed = time.perf_counter() - start_time
        if utl_language_detection_latency_seconds is not None:
            utl_language_detection_latency_seconds.observe(elapsed)
        if utl_language_detection_confidence is not None:
            utl_language_detection_confidence.set(result.confidence)

        return result

    # === TRANSLATION DECISION ===

    def should_translate(self, result: LanguageResult, user_lang: str) -> bool:
        """Determine whether translation is needed based on detection result.

        Translation is triggered when:
        1. Detected language differs from user's language
        2. Detection confidence is >= 95% (CONFIDENCE_THRESHOLD_TRANSLATE)

        When detected language matches user's language, translation is bypassed
        regardless of confidence (Requirement 15.3).

        When confidence < 95%, translation is NOT triggered even if languages
        differ — the original content should be shown alongside best-effort
        translation with a confidence indicator (Requirement 15.5).

        Args:
            result: LanguageResult from detect_text() or detect_audio()
            user_lang: User's configured native language (ISO 639-1 code)

        Returns:
            True if translation should be performed, False otherwise.
        """
        user_lang_normalized = user_lang.lower().strip()

        # Same language — bypass translation entirely (Req 15.3)
        if result.language == user_lang_normalized:
            return False

        # Unknown detection — don't translate
        if result.language == "unknown":
            return False

        # Confidence must be >= 95% to trigger translation (Req 15.1)
        if result.confidence < CONFIDENCE_THRESHOLD_TRANSLATE:
            return False

        return True

    # === LANGUAGE PREFERENCE CACHE ===

    def get_cached_language(self, contact_or_channel: str) -> Optional[LanguageResult]:
        """Get cached language preference for a contact or channel.

        If the contact/channel has been seen before, returns the cached
        language without running detection again — reducing overhead for
        repeated interactions (Requirement 15.4).

        Args:
            contact_or_channel: Unique identifier for the contact or channel.

        Returns:
            LanguageResult from cache, or None if not cached.
        """
        pref = self._preference_cache.get(contact_or_channel)
        if pref is not None:
            self._cache_hit_count += 1
            return LanguageResult(
                language=pref.language,
                confidence=pref.confidence
            )
        self._cache_miss_count += 1
        return None

    def update_cache(self, contact_or_channel: str, result: LanguageResult) -> None:
        """Update the language preference cache for a contact or channel.

        Stores the detected language so future interactions with the same
        contact/channel can skip detection overhead.

        Args:
            contact_or_channel: Unique identifier for the contact or channel.
            result: LanguageResult from a recent detection.
        """
        existing = self._preference_cache.get(contact_or_channel)
        if existing is not None:
            existing.language = result.language
            existing.confidence = result.confidence
            existing.last_seen = time.time()
            existing.detection_count += 1
        else:
            self._preference_cache[contact_or_channel] = LanguagePreference(
                language=result.language,
                confidence=result.confidence,
                last_seen=time.time(),
                detection_count=1
            )

    def clear_cache(self) -> None:
        """Clear all cached language preferences."""
        self._preference_cache.clear()
        self._cache_hit_count = 0
        self._cache_miss_count = 0

    @property
    def cache_size(self) -> int:
        """Number of entries in the language preference cache."""
        return len(self._preference_cache)

    @property
    def cache_stats(self) -> Dict[str, int]:
        """Cache hit/miss statistics."""
        return {
            "hits": self._cache_hit_count,
            "misses": self._cache_miss_count,
            "size": self.cache_size
        }

    # === UTILITY ===

    @staticmethod
    def supported_languages() -> List[str]:
        """Return list of supported language codes (ISO 639-1)."""
        return list(SUPPORTED_LANGUAGES)


# === MAIN GUARD ===

def main():
    """Self-test entry point for Language Detector module."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    detector = LanguageDetector()

    print(f"{LOG_PREFIX} Language Detector self-test")
    print(f"{LOG_PREFIX} langdetect available: {_LANGDETECT_AVAILABLE}")
    print(f"{LOG_PREFIX} Supported languages: {len(SUPPORTED_LANGUAGES)}")

    # Test basic detection
    if _LANGDETECT_AVAILABLE:
        result_en = detector.detect_text("This is a test of the language detection system")
        print(f"{LOG_PREFIX} English test: {result_en}")

        result_cs = detector.detect_text("Toto je test detekce jazyka v ceskem textu")
        print(f"{LOG_PREFIX} Czech test: {result_cs}")

        result_de = detector.detect_text("Dies ist ein Test der Spracherkennungssystem")
        print(f"{LOG_PREFIX} German test: {result_de}")

        # Test should_translate
        print(f"{LOG_PREFIX} should_translate(en, 'cs'): "
              f"{detector.should_translate(result_en, 'cs')}")
        print(f"{LOG_PREFIX} should_translate(cs, 'cs'): "
              f"{detector.should_translate(result_cs, 'cs')}")
    else:
        result_fallback = detector.detect_text("Hello world")
        print(f"{LOG_PREFIX} Fallback (no langdetect): {result_fallback}")

    # Test audio stub
    audio_result = detector.detect_audio(None)
    print(f"{LOG_PREFIX} Audio stub: {audio_result}")

    # Test cache
    test_result = LanguageResult(language="en", confidence=0.98)
    detector.update_cache("user@example.com", test_result)
    cached = detector.get_cached_language("user@example.com")
    assert cached is not None
    assert cached.language == "en"
    print(f"{LOG_PREFIX} Cache test: {cached}")
    print(f"{LOG_PREFIX} Cache stats: {detector.cache_stats}")

    # Test empty/edge cases
    empty_result = detector.detect_text("")
    assert empty_result.language == "unknown"
    assert empty_result.confidence == 0.0
    print(f"{LOG_PREFIX} Empty text: {empty_result}")

    print(f"{LOG_PREFIX} All self-tests passed.")


if __name__ == '__main__':
    main()
