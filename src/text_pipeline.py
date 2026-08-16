"""
Text Pipeline — Universal Translation Layer (UTL)

End-to-end text translation pipeline wiring:
    TextInterceptor → LanguageDetector → Ada Validator (subprocess) →
    TranslationEngine → OverlayRenderer

Features:
- Platform-specific startup (Windows UI Automation / Linux AT-SPI)
- OCR fallback for non-accessible applications
- Prometheus metrics for full pipeline observability
- <150ms text interception latency target tracking
- Bidirectional operation (input + output simultaneously)

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 2.1

Autor: Pan Jeskyně
Asistent: Kiro
"""

import sys
import time
import logging
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, List

# === LOGGING ===

logger = logging.getLogger(__name__)
LOG_PREFIX = "[TEXT_PIPELINE]"

# === LOCAL IMPORTS ===

from text_interceptor import (
    TextInterceptor,
    TextEvent,
    Direction,
    Rect,
    AccessibilityElement,
    UIAutomationInterceptor,
    ATSPIInterceptor,
    create_interceptor,
)
from language_detector import LanguageDetector, LanguageResult
from translation_engine import TranslationEngine, TranslationResult, TranslationMethod
from overlay_renderer import (
    OverlayRenderer,
    TextStyle,
    OverlayMode,
    DirectCompositionRenderer,
    X11OverlayRenderer,
    create_renderer,
)
from overlay_renderer import Rect as OverlayRect
from ocr_module import OCRModule, ScreenRegion, OCRResult

# === PROMETHEUS METRICS ===

try:
    from prometheus_client import Counter, Histogram, Gauge

    utl_text_pipeline_latency_seconds = Histogram(
        "utl_text_pipeline_latency_seconds",
        "End-to-end text pipeline latency in seconds (target <150ms)",
        ["direction", "stage"],
        buckets=[0.01, 0.025, 0.05, 0.075, 0.1, 0.125, 0.15, 0.2, 0.3, 0.5, 1.0],
    )

    utl_text_pipeline_events_total = Counter(
        "utl_text_pipeline_events_total",
        "Total text pipeline events processed",
        ["direction", "result"],  # result: translated, passthrough, ocr_fallback, error
    )

    utl_text_pipeline_errors_total = Counter(
        "utl_text_pipeline_errors_total",
        "Total text pipeline errors",
        ["stage"],  # stage: detection, validation, translation, rendering, ocr
    )

    _METRICS_AVAILABLE = True
except ImportError:
    utl_text_pipeline_latency_seconds = None
    utl_text_pipeline_events_total = None
    utl_text_pipeline_errors_total = None
    _METRICS_AVAILABLE = False

# === CONSTANTS ===

# Target latency for end-to-end text interception pipeline
LATENCY_TARGET_MS = 150

# Minimum text length for language detection to be reliable
MIN_TEXT_LENGTH_FOR_DETECTION = 5

# Default overlay style
DEFAULT_STYLE = TextStyle(
    font_family="Segoe UI" if sys.platform == "win32" else "DejaVu Sans",
    font_size=14,
    color=(255, 255, 255, 255),
    background=(30, 30, 30, 220),
)


# === PIPELINE STATE ENUM ===


class PipelineState(Enum):
    """Current state of the text pipeline."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"


# === TEXT PIPELINE CLASS ===


class TextPipeline:
    """End-to-end text translation pipeline.

    Connects:
        TextInterceptor → LanguageDetector → Ada Validator (subprocess) →
        TranslationEngine → OverlayRenderer

    With OCR fallback for non-accessible applications.

    Platform-specific startup:
    - Windows: UIAutomationInterceptor + DirectCompositionRenderer
    - Linux: ATSPIInterceptor + X11OverlayRenderer

    Exposes Prometheus metrics:
    - utl_text_pipeline_latency_seconds
    - utl_text_pipeline_events_total
    - utl_text_pipeline_errors_total
    """

    def __init__(
        self,
        user_language: str = "cs",
        overlay_mode: OverlayMode = OverlayMode.REPLACE,
        overlay_style: Optional[TextStyle] = None,
        ocr_enabled: bool = True,
        ocr_languages: Optional[List[str]] = None,
    ):
        """Initialize the text translation pipeline.

        Automatically selects platform-specific backends based on sys.platform.

        Args:
            user_language: User's native language (ISO 639-1 code).
            overlay_mode: Overlay display mode (REPLACE, TOOLTIP, SIDE_BY_SIDE).
            overlay_style: Default text style for overlays.
            ocr_enabled: Whether to enable OCR fallback for non-accessible apps.
            ocr_languages: Languages for OCR detection (default: user's language + 'en').
        """
        self._user_language = user_language.lower().strip()
        self._overlay_mode = overlay_mode
        self._overlay_style = overlay_style or DEFAULT_STYLE
        self._ocr_enabled = ocr_enabled
        self._state = PipelineState.STOPPED
        self._lock = threading.Lock()
        self._platform = sys.platform

        # --- Component initialization ---

        # 1. Text Interceptor (platform-specific)
        self._interceptor: TextInterceptor = create_interceptor(
            user_language=self._user_language
        )

        # 2. Language Detector
        self._detector = LanguageDetector()

        # 3. Translation Engine (with Ada subprocess validation)
        self._translator = TranslationEngine()

        # 4. Overlay Renderer (platform-specific)
        self._renderer: OverlayRenderer = create_renderer()
        self._renderer.set_mode(self._overlay_mode)

        # 5. OCR Module (fallback)
        self._ocr: Optional[OCRModule] = None
        if self._ocr_enabled:
            ocr_langs = ocr_languages or [self._user_language, "en"]
            # Deduplicate
            ocr_langs = list(dict.fromkeys(ocr_langs))
            self._ocr = OCRModule(languages=ocr_langs, gpu=True)

        # --- Statistics ---
        self._events_processed = 0
        self._events_translated = 0
        self._events_passthrough = 0
        self._events_ocr_fallback = 0
        self._events_error = 0
        self._total_latency_ms = 0.0

        logger.info(
            f"{LOG_PREFIX} Pipeline initialized: "
            f"platform={self._platform}, "
            f"user_lang={self._user_language}, "
            f"interceptor={type(self._interceptor).__name__}, "
            f"renderer={type(self._renderer).__name__}, "
            f"ocr_enabled={self._ocr_enabled}"
        )

    # === LIFECYCLE ===

    def start(self) -> None:
        """Start the text translation pipeline.

        - Registers text event callbacks on the interceptor
        - Starts the interceptor (begins capturing accessibility events)
        - Sets pipeline state to RUNNING
        """
        with self._lock:
            if self._state == PipelineState.RUNNING:
                logger.warning(f"{LOG_PREFIX} Pipeline already running")
                return
            self._state = PipelineState.STARTING

        logger.info(f"{LOG_PREFIX} Starting text pipeline...")

        # Register callbacks for bidirectional operation (Req 1.6)
        self._interceptor.on_text_output(self._on_text_output)
        self._interceptor.on_text_input(self._on_text_input)

        # Start the interceptor (platform-specific)
        self._interceptor.start()

        with self._lock:
            self._state = PipelineState.RUNNING

        logger.info(f"{LOG_PREFIX} Text pipeline RUNNING")

    def stop(self) -> None:
        """Stop the text translation pipeline.

        - Stops the interceptor
        - Hides all overlays
        - Sets pipeline state to STOPPED
        """
        with self._lock:
            if self._state == PipelineState.STOPPED:
                logger.warning(f"{LOG_PREFIX} Pipeline already stopped")
                return

        logger.info(f"{LOG_PREFIX} Stopping text pipeline...")

        self._interceptor.stop()
        self._renderer.hide_all()

        with self._lock:
            self._state = PipelineState.STOPPED

        logger.info(
            f"{LOG_PREFIX} Text pipeline STOPPED "
            f"(processed={self._events_processed}, "
            f"translated={self._events_translated}, "
            f"passthrough={self._events_passthrough}, "
            f"ocr={self._events_ocr_fallback}, "
            f"errors={self._events_error})"
        )

    @property
    def state(self) -> PipelineState:
        """Current pipeline state."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Whether the pipeline is currently active."""
        return self._state == PipelineState.RUNNING

    # === TEXT EVENT HANDLERS ===

    def _on_text_output(self, event: TextEvent) -> None:
        """Handle text output event (text displayed to user).

        Requirement 1.5: When text in a foreign language is displayed to
        the user, translate it to the user's configured native language.
        """
        self._process_event(event)

    def _on_text_input(self, event: TextEvent) -> None:
        """Handle text input event (user typing).

        Requirement 1.4: When the user types text in their native language,
        translate it to the detected target language before delivery.
        """
        self._process_event(event)

    def _process_event(self, event: TextEvent) -> None:
        """Process a single text event through the full pipeline.

        Pipeline steps:
        1. Language detection
        2. Pass-through check (Req 1.7: native language unchanged)
        3. Ada validation (subprocess)
        4. Translation via TranslationEngine
        5. Overlay rendering (Req 2.1: <150ms display latency)

        Tracks latency against the <150ms target.
        """
        start_time = time.perf_counter()
        direction_label = event.direction.value

        self._events_processed += 1

        try:
            text = event.text
            if not text or len(text.strip()) < MIN_TEXT_LENGTH_FOR_DETECTION:
                # Too short to process meaningfully
                self._record_event(direction_label, "passthrough")
                self._events_passthrough += 1
                return

            # --- Step 1: Language Detection ---
            lang_result = self._detector.detect_text(text)

            # --- Step 2: Native language pass-through (Req 1.7) ---
            if not self._detector.should_translate(lang_result, self._user_language):
                self._record_event(direction_label, "passthrough")
                self._events_passthrough += 1
                self._observe_latency(start_time, direction_label, "passthrough")
                return

            # --- Step 3 & 4: Translation (includes Ada validation internally) ---
            # Determine source and target based on direction
            if event.direction == Direction.OUTPUT:
                # Foreign text displayed to user → translate TO user's language
                source_lang = lang_result.language
                target_lang = self._user_language
            else:
                # User typing in native language → translate FROM user's language
                # to the detected language of the conversation partner
                source_lang = self._user_language
                target_lang = lang_result.language

            translation_result = self._translator.translate(
                text=text,
                source_lang=source_lang,
                target_lang=target_lang,
            )

            # --- Step 5: Overlay Rendering ---
            overlay_rect = OverlayRect(
                x=event.position.x,
                y=event.position.y,
                width=event.position.width,
                height=event.position.height,
            )

            self._renderer.show_translation(
                original_rect=overlay_rect,
                translated=translation_result.translated_text,
                style=self._overlay_style,
                element_id=event.element_id,
            )

            # --- Metrics & Latency ---
            self._events_translated += 1
            self._record_event(direction_label, "translated")
            self._observe_latency(start_time, direction_label, "full_pipeline")

        except Exception as e:
            self._events_error += 1
            logger.error(f"{LOG_PREFIX} Pipeline error processing event: {e}")
            self._record_event(direction_label, "error")
            self._record_error("pipeline")
            self._observe_latency(start_time, direction_label, "error")

    # === OCR FALLBACK ===

    def process_ocr_region(self, region: ScreenRegion) -> List[str]:
        """Process a screen region via OCR fallback.

        Used when the target application does not expose text via
        accessibility APIs (Requirement 1.3).

        Args:
            region: ScreenRegion containing the image data to OCR.

        Returns:
            List of translated text strings extracted from the region.
        """
        if self._ocr is None or not self._ocr.is_available:
            logger.warning(f"{LOG_PREFIX} OCR fallback not available")
            return []

        start_time = time.perf_counter()
        translated_texts: List[str] = []

        try:
            # Extract text via OCR
            ocr_results = self._ocr.extract_text(region)

            if not ocr_results:
                logger.debug(f"{LOG_PREFIX} OCR: no text detected in region")
                return []

            for ocr_result in ocr_results:
                text = ocr_result.text
                if not text or len(text.strip()) < MIN_TEXT_LENGTH_FOR_DETECTION:
                    continue

                # Detect language
                lang_result = self._detector.detect_text(text)

                # Check if translation needed
                if not self._detector.should_translate(lang_result, self._user_language):
                    translated_texts.append(text)
                    continue

                # Translate
                translation = self._translator.translate(
                    text=text,
                    source_lang=lang_result.language,
                    target_lang=self._user_language,
                )

                translated_texts.append(translation.translated_text)

                # Render overlay at OCR bounding box position
                bbox = ocr_result.bounding_box
                overlay_rect = OverlayRect(
                    x=region.rect.x + bbox.x,
                    y=region.rect.y + bbox.y,
                    width=bbox.width,
                    height=bbox.height,
                )
                self._renderer.show_translation(
                    original_rect=overlay_rect,
                    translated=translation.translated_text,
                    style=self._overlay_style,
                    element_id=f"ocr_{bbox.x}_{bbox.y}_{int(time.time() * 1000)}",
                )

            self._events_ocr_fallback += len(translated_texts)
            self._record_event("ocr", "ocr_fallback")
            self._observe_latency(start_time, "ocr", "ocr_extraction")

            return translated_texts

        except Exception as e:
            logger.error(f"{LOG_PREFIX} OCR fallback error: {e}")
            self._record_error("ocr")
            return []

    # === DIRECT TRANSLATION API ===

    def translate_text(
        self,
        text: str,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        position: Optional[OverlayRect] = None,
        element_id: Optional[str] = None,
    ) -> Optional[TranslationResult]:
        """Translate text directly (without interceptor event).

        Useful for programmatic translation calls from other components.

        Args:
            text: Text to translate.
            source_lang: Source language (auto-detected if None).
            target_lang: Target language (user_language if None).
            position: Screen position for overlay (no overlay if None).
            element_id: Element ID for overlay tracking.

        Returns:
            TranslationResult, or None if translation not needed/failed.
        """
        start_time = time.perf_counter()

        if not text or len(text.strip()) < MIN_TEXT_LENGTH_FOR_DETECTION:
            return None

        try:
            # Auto-detect source language if not provided
            if source_lang is None:
                lang_result = self._detector.detect_text(text)
                source_lang = lang_result.language

                # Check if translation needed
                if not self._detector.should_translate(
                    lang_result, target_lang or self._user_language
                ):
                    return None

            target = target_lang or self._user_language

            # Translate (includes Ada validation internally)
            result = self._translator.translate(
                text=text,
                source_lang=source_lang,
                target_lang=target,
            )

            # Render overlay if position provided
            if position is not None:
                eid = element_id or f"direct_{int(time.time() * 1000)}"
                self._renderer.show_translation(
                    original_rect=position,
                    translated=result.translated_text,
                    style=self._overlay_style,
                    element_id=eid,
                )

            self._observe_latency(start_time, "direct", "full_pipeline")
            return result

        except Exception as e:
            logger.error(f"{LOG_PREFIX} Direct translation error: {e}")
            self._record_error("translation")
            return None

    # === CONFIGURATION ===

    @property
    def user_language(self) -> str:
        """User's configured native language."""
        return self._user_language

    @user_language.setter
    def user_language(self, lang: str) -> None:
        """Update user's native language.

        Also updates the interceptor's language setting.
        """
        self._user_language = lang.lower().strip()
        self._interceptor.user_language = self._user_language
        logger.info(f"{LOG_PREFIX} User language updated to: {self._user_language}")

    @property
    def overlay_mode(self) -> OverlayMode:
        """Current overlay display mode."""
        return self._overlay_mode

    @overlay_mode.setter
    def overlay_mode(self, mode: OverlayMode) -> None:
        """Change overlay display mode."""
        self._overlay_mode = mode
        self._renderer.set_mode(mode)

    @property
    def overlay_style(self) -> TextStyle:
        """Current overlay text style."""
        return self._overlay_style

    @overlay_style.setter
    def overlay_style(self, style: TextStyle) -> None:
        """Update overlay text style."""
        self._overlay_style = style

    @property
    def platform(self) -> str:
        """Current platform identifier."""
        return self._platform

    @property
    def interceptor_backend(self) -> str:
        """Name of the active interceptor backend."""
        return type(self._interceptor).__name__

    @property
    def renderer_backend(self) -> str:
        """Name of the active renderer backend."""
        return type(self._renderer).__name__

    @property
    def ocr_available(self) -> bool:
        """Whether OCR fallback is available."""
        return self._ocr is not None and self._ocr.is_available

    # === STATISTICS ===

    @property
    def stats(self) -> dict:
        """Pipeline statistics."""
        avg_latency = (
            self._total_latency_ms / max(1, self._events_processed)
        )
        return {
            "state": self._state.value,
            "platform": self._platform,
            "user_language": self._user_language,
            "interceptor": self.interceptor_backend,
            "renderer": self.renderer_backend,
            "ocr_available": self.ocr_available,
            "events_processed": self._events_processed,
            "events_translated": self._events_translated,
            "events_passthrough": self._events_passthrough,
            "events_ocr_fallback": self._events_ocr_fallback,
            "events_error": self._events_error,
            "average_latency_ms": round(avg_latency, 2),
            "latency_target_ms": LATENCY_TARGET_MS,
        }

    # === INTERNAL HELPERS ===

    def _observe_latency(
        self, start_time: float, direction: str, stage: str
    ) -> None:
        """Record latency measurement and check against target."""
        elapsed_s = time.perf_counter() - start_time
        elapsed_ms = elapsed_s * 1000
        self._total_latency_ms += elapsed_ms

        if utl_text_pipeline_latency_seconds is not None:
            utl_text_pipeline_latency_seconds.labels(
                direction=direction, stage=stage
            ).observe(elapsed_s)

        if elapsed_ms > LATENCY_TARGET_MS:
            logger.warning(
                f"{LOG_PREFIX} Latency {elapsed_ms:.1f}ms exceeds "
                f"target {LATENCY_TARGET_MS}ms "
                f"(direction={direction}, stage={stage})"
            )

    def _record_event(self, direction: str, result: str) -> None:
        """Record pipeline event metric."""
        if utl_text_pipeline_events_total is not None:
            utl_text_pipeline_events_total.labels(
                direction=direction, result=result
            ).inc()

    def _record_error(self, stage: str) -> None:
        """Record pipeline error metric."""
        if utl_text_pipeline_errors_total is not None:
            utl_text_pipeline_errors_total.labels(stage=stage).inc()


# === FACTORY FUNCTION ===


def create_text_pipeline(
    user_language: str = "cs",
    overlay_mode: OverlayMode = OverlayMode.REPLACE,
    ocr_enabled: bool = True,
) -> TextPipeline:
    """Create a fully wired text translation pipeline for the current platform.

    This is the main entry point for creating a text pipeline. It
    automatically selects the correct platform backends:
    - Windows: UIAutomationInterceptor + DirectCompositionRenderer
    - Linux: ATSPIInterceptor + X11OverlayRenderer

    Args:
        user_language: User's native language (ISO 639-1 code).
        overlay_mode: Overlay display mode.
        ocr_enabled: Whether to enable OCR fallback.

    Returns:
        Fully configured TextPipeline instance.
    """
    logger.info(
        f"{LOG_PREFIX} Creating text pipeline: "
        f"platform={sys.platform}, "
        f"user_lang={user_language}, "
        f"mode={overlay_mode.value}, "
        f"ocr={ocr_enabled}"
    )
    return TextPipeline(
        user_language=user_language,
        overlay_mode=overlay_mode,
        ocr_enabled=ocr_enabled,
    )


# === MAIN GUARD ===


def main():
    """Self-test entry point for Text Pipeline module."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    print(f"{LOG_PREFIX} Text Pipeline end-to-end self-test")
    print(f"{LOG_PREFIX} Platform: {sys.platform}")
    print()

    # Create pipeline
    pipeline = create_text_pipeline(user_language="cs", ocr_enabled=True)
    print(f"{LOG_PREFIX} Pipeline created:")
    print(f"{LOG_PREFIX}   State: {pipeline.state.value}")
    print(f"{LOG_PREFIX}   Interceptor: {pipeline.interceptor_backend}")
    print(f"{LOG_PREFIX}   Renderer: {pipeline.renderer_backend}")
    print(f"{LOG_PREFIX}   OCR available: {pipeline.ocr_available}")
    print(f"{LOG_PREFIX}   Platform: {pipeline.platform}")
    print()

    # Test direct translation API
    print(f"{LOG_PREFIX} Testing direct translation...")
    result = pipeline.translate_text(
        text="This is a test of the end-to-end text translation pipeline",
        position=OverlayRect(100, 200, 400, 30),
        element_id="test_elem_1",
    )
    if result:
        print(f"{LOG_PREFIX}   Translated: '{result.translated_text[:60]}...'")
        print(f"{LOG_PREFIX}   Method: {result.method.value}")
        print(f"{LOG_PREFIX}   Confidence: {result.confidence}")
        print(f"{LOG_PREFIX}   Validation: {result.validation_result}")
    else:
        print(f"{LOG_PREFIX}   Translation not needed or failed")
    print()

    # Test native language pass-through
    print(f"{LOG_PREFIX} Testing native language pass-through...")
    result_native = pipeline.translate_text(
        text="Toto je test českého textu, který by měl projít bez překladu",
    )
    assert result_native is None, "Native text should not be translated"
    print(f"{LOG_PREFIX}   Native text correctly passed through (None returned)")
    print()

    # Test pipeline start/stop lifecycle
    print(f"{LOG_PREFIX} Testing pipeline lifecycle...")
    pipeline.start()
    assert pipeline.is_running
    print(f"{LOG_PREFIX}   Started: state={pipeline.state.value}")

    # Simulate a text event
    from text_interceptor import Rect as TIRect

    test_event = TextEvent(
        source_app="TestApp",
        element_id="test_output_1",
        text="Dies ist ein Test der Textübersetzungspipeline",
        position=TIRect(100, 150, 350, 25),
        timestamp=time.time(),
        direction=Direction.OUTPUT,
    )
    pipeline._process_event(test_event)
    print(f"{LOG_PREFIX}   Processed test event (German text)")
    print()

    # Check stats
    stats = pipeline.stats
    print(f"{LOG_PREFIX} Pipeline statistics:")
    for key, value in stats.items():
        print(f"{LOG_PREFIX}   {key}: {value}")
    print()

    # Test configuration changes
    pipeline.user_language = "en"
    assert pipeline.user_language == "en"
    pipeline.user_language = "cs"

    pipeline.overlay_mode = OverlayMode.TOOLTIP
    assert pipeline.overlay_mode == OverlayMode.TOOLTIP
    pipeline.overlay_mode = OverlayMode.REPLACE

    # Stop pipeline
    pipeline.stop()
    assert not pipeline.is_running
    print(f"{LOG_PREFIX}   Stopped: state={pipeline.state.value}")
    print()

    print(f"{LOG_PREFIX} All self-tests passed.")


if __name__ == "__main__":
    main()
