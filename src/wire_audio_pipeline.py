"""
Wire Audio Pipeline End-to-End — Universal Translation Layer (UTL)

Integration module: connects AudioCapture → VoiceSeparator → SpeakerMapper →
StreamDubber into a complete audio dubbing pipeline with Smart TV support.

Autor: Pan Jeskyně
Asistent: Kiro
"""

import logging
import time
from typing import Optional

# === LOGGING ===

logger = logging.getLogger(__name__)
LOG_PREFIX = "[WIRE_AUDIO]"

# === LOCAL IMPORTS ===

from stream_dubber import StreamDubber, DubbingMode, SubtitleEvent
from smart_tv_dubbing import SmartTVDubbing, TVSourceType, DubbingQuality

# === PROMETHEUS METRICS ===

try:
    from prometheus_client import Counter

    utl_audio_pipeline_sessions_total = Counter(
        'utl_audio_pipeline_sessions_total',
        'Total audio pipeline sessions',
        ['mode']
    )
except ImportError:
    utl_audio_pipeline_sessions_total = None


# === AUDIO PIPELINE CLASS ===

class AudioPipeline:
    """End-to-end audio dubbing pipeline.

    Combines StreamDubber (core pipeline) with SmartTVDubbing (TV extensions)
    into a unified interface.
    """

    def __init__(self, target_lang: str = "cs"):
        self._target_lang = target_lang
        self._dubber = StreamDubber(target_lang=target_lang)
        self._tv = SmartTVDubbing(target_lang=target_lang)

        logger.info(f"{LOG_PREFIX} Audio pipeline wired (target={target_lang})")

    def start_dubbing(self, mode: DubbingMode = DubbingMode.DUB,
                      target_lang: str = None) -> None:
        """Start the core dubbing pipeline."""
        lang = target_lang or self._target_lang
        self._dubber.set_mode(mode)
        self._dubber.start(target_lang=lang)

        if utl_audio_pipeline_sessions_total:
            utl_audio_pipeline_sessions_total.labels(mode=mode.value).inc()

        logger.info(f"{LOG_PREFIX} Dubbing started: mode={mode.value}, lang={lang}")

    def stop_dubbing(self) -> None:
        """Stop the dubbing pipeline."""
        self._dubber.stop()
        logger.info(f"{LOG_PREFIX} Dubbing stopped")

    def start_tv_session(self, source: TVSourceType,
                         quality: DubbingQuality = DubbingQuality.BALANCED,
                         room: str = "living_room") -> str:
        """Start a Smart TV dubbing session."""
        session_id = self._tv.start_session(
            source_type=source,
            target_lang=self._target_lang,
            quality=quality,
            room_name=room,
        )
        return session_id

    def stop_tv_session(self, session_id: str) -> bool:
        """Stop a Smart TV session."""
        return self._tv.stop_session(session_id)

    @property
    def dubber(self) -> StreamDubber:
        """Access core dubber."""
        return self._dubber

    @property
    def tv(self) -> SmartTVDubbing:
        """Access Smart TV module."""
        return self._tv

    def get_status(self) -> dict:
        """Combined pipeline status."""
        return {
            "dubber": self._dubber.pipeline_status,
            "tv": self._tv.get_status(),
        }


# === MAIN GUARD ===

def main():
    """Self-test."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    print(f"{LOG_PREFIX} Audio Pipeline wiring self-test")

    pipeline = AudioPipeline(target_lang="cs")
    print(f"{LOG_PREFIX} Status: {pipeline.get_status()}")

    # Quick TV session test
    sid = pipeline.start_tv_session(TVSourceType.MANUAL)
    print(f"{LOG_PREFIX} TV session: {sid}")
    pipeline.stop_tv_session(sid)

    print(f"{LOG_PREFIX} Done.")


if __name__ == '__main__':
    main()
