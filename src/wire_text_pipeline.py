"""
Wire Text Pipeline End-to-End — Universal Translation Layer (UTL)

Integration module: connects Language Detector → Text Interceptor →
Translation Engine → Overlay Renderer into a complete text translation pipeline.

Autor: Pan Jeskyně
Asistent: Kiro
"""

import logging
import time
from typing import Optional, Callable

# === LOGGING ===

logger = logging.getLogger(__name__)
LOG_PREFIX = "[WIRE_TEXT]"

# === LOCAL IMPORTS ===

from language_detector import LanguageDetector
from text_interceptor import create_interceptor
from translation_engine import TranslationEngine
from overlay_renderer import DirectCompositionRenderer, TextStyle, Rect

# === PROMETHEUS METRICS ===

try:
    from prometheus_client import Counter, Histogram

    utl_text_pipeline_requests_total = Counter(
        'utl_text_pipeline_requests_total',
        'Total text pipeline translation requests',
        ['status']
    )

    utl_text_pipeline_latency_seconds = Histogram(
        'utl_text_pipeline_latency_seconds',
        'End-to-end text pipeline latency',
        buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.0]
    )
except ImportError:
    utl_text_pipeline_requests_total = None
    utl_text_pipeline_latency_seconds = None


# === TEXT PIPELINE CLASS ===

class TextPipeline:
    """End-to-end text translation pipeline.

    Flow: Detect Language → Intercept Text → Translate → Render Overlay
    """

    def __init__(self, target_lang: str = "cs"):
        self._target_lang = target_lang
        self._detector = LanguageDetector()
        self._interceptor = create_interceptor(user_language=target_lang)
        self._translator = TranslationEngine()
        self._renderer = DirectCompositionRenderer()
        self._renderer.initialize()

        logger.info(f"{LOG_PREFIX} Text pipeline wired (target={target_lang})")

    def translate_and_overlay(self, text: str, rect: Rect,
                              element_id: str = "default",
                              style: TextStyle = None) -> Optional[str]:
        """Full pipeline: detect + translate + overlay.

        Returns translated text, or None if pipeline fails.
        """
        start = time.perf_counter()

        try:
            # 1. Detect language
            detected = self._detector.detect(text)

            # 2. Skip if already target language
            if detected.language == self._target_lang:
                return text

            # 3. Translate
            result = self._translator.translate(
                text=text,
                source_lang=detected.language,
                target_lang=self._target_lang,
            )

            # 4. Render overlay
            self._renderer.show_translation(
                original_rect=rect,
                translated=result.translated_text,
                style=style or TextStyle(),
                element_id=element_id,
            )

            elapsed = time.perf_counter() - start
            if utl_text_pipeline_latency_seconds:
                utl_text_pipeline_latency_seconds.observe(elapsed)
            if utl_text_pipeline_requests_total:
                utl_text_pipeline_requests_total.labels(status="success").inc()

            return result.translated_text

        except Exception as e:
            logger.error(f"{LOG_PREFIX} Pipeline error: {e}")
            if utl_text_pipeline_requests_total:
                utl_text_pipeline_requests_total.labels(status="error").inc()
            return None

    def set_target_lang(self, lang: str) -> None:
        """Change target language."""
        self._target_lang = lang

    def hide_all(self) -> None:
        """Hide all overlays."""
        self._renderer.hide_all()


# === MAIN GUARD ===

def main():
    """Self-test."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    print(f"{LOG_PREFIX} Text Pipeline wiring self-test")

    pipeline = TextPipeline(target_lang="cs")
    result = pipeline.translate_and_overlay(
        "Hello world",
        Rect(x=100, y=100, width=200, height=30),
        element_id="test",
    )
    print(f"{LOG_PREFIX} Result: {result}")
    print(f"{LOG_PREFIX} Done.")


if __name__ == '__main__':
    main()
