"""
Wire Karel IV. Engine — Universal Translation Layer (UTL)

Integration module: connects all UTL components into the Karel IV.
real-time voice translator product.

Pipeline: Mic → Virtual Soundcard → Whisper STT → Ada/SPARK validation
→ Gemini translation → Coqui TTS (user voice clone) → Headphones

Autor: Pan Jeskyně
Asistent: Kiro
Standard: Karel IV. — "Mluví všemi jazyky. Najednou."
"""

import logging
import time
from typing import Optional

# === LOGGING ===

logger = logging.getLogger(__name__)
LOG_PREFIX = "[KAREL_IV]"

# === LOCAL IMPORTS ===

from app_lifecycle import AppLifecycle, AppState
from wire_text_pipeline import TextPipeline
from wire_audio_pipeline import AudioPipeline
from wire_mesh import MeshLayer
from subscription_manager import SubscriptionManager, SubscriptionTier
from privacy_protocol import PrivacyProtocol
from stream_dubber import DubbingMode


# === KAREL IV ENGINE CLASS ===

class KarelIVEngine:
    """Karel IV. — Real-time AI Voice Translator Engine.

    "Mluví všemi jazyky. Najednou."

    Integrates all UTL components into the final product:
    - Text translation with overlay
    - Audio dubbing (real-time voice replacement)
    - Stream dubbing (Netflix/YouTube)
    - Privacy (zero persistence)
    - Mesh networking (P2P distributed processing)
    - Subscription management (111-423 CZK/month)
    """

    def __init__(self, target_lang: str = "cs"):
        self._target_lang = target_lang
        self._lifecycle = AppLifecycle()
        self._text_pipeline: Optional[TextPipeline] = None
        self._audio_pipeline: Optional[AudioPipeline] = None
        self._mesh: Optional[MeshLayer] = None
        self._subscriptions = SubscriptionManager()
        self._privacy = PrivacyProtocol()

        # Register components for lifecycle management
        self._lifecycle.register_component(
            "privacy", priority=5,
            startup_fn=self._start_privacy,
            shutdown_fn=self._stop_privacy,
        )
        self._lifecycle.register_component(
            "mesh", priority=10,
            startup_fn=self._start_mesh,
            shutdown_fn=self._stop_mesh,
        )
        self._lifecycle.register_component(
            "text_pipeline", priority=20,
            startup_fn=self._start_text,
        )
        self._lifecycle.register_component(
            "audio_pipeline", priority=30,
            startup_fn=self._start_audio,
            shutdown_fn=self._stop_audio,
        )

        logger.info(f"{LOG_PREFIX} Karel IV. Engine initialized (target={target_lang})")

    # === PUBLIC API ===

    def start(self) -> bool:
        """Start the Karel IV. engine."""
        success = self._lifecycle.startup()
        if success:
            logger.info(f"{LOG_PREFIX} Karel IV. is RUNNING — mluví všemi jazyky")
        return success

    def stop(self) -> bool:
        """Stop the Karel IV. engine."""
        success = self._lifecycle.shutdown()
        if success:
            logger.info(f"{LOG_PREFIX} Karel IV. stopped")
        return success

    def check_user_access(self, user_id: str, feature: str) -> bool:
        """Check if user has access to a feature."""
        return self._subscriptions.check_access(user_id, feature)

    def activate_user(self, user_id: str, tier: SubscriptionTier) -> None:
        """Activate subscription for a user."""
        self._subscriptions.activate(user_id, tier)

    @property
    def state(self) -> AppState:
        return self._lifecycle.state

    def get_status(self) -> dict:
        return {
            "engine": "Karel IV.",
            "state": self._lifecycle.state.value,
            "target_lang": self._target_lang,
            "uptime_s": self._lifecycle.uptime_seconds,
            "healthy": self._lifecycle.is_healthy(),
        }

    # === COMPONENT STARTUP/SHUTDOWN ===

    def _start_privacy(self):
        self._privacy.schedule_purge()

    def _stop_privacy(self):
        self._privacy.stop_purge()

    def _start_mesh(self):
        self._mesh = MeshLayer(local_node_id="karel_primary")
        self._mesh.start()

    def _stop_mesh(self):
        if self._mesh:
            self._mesh.stop()

    def _start_text(self):
        self._text_pipeline = TextPipeline(target_lang=self._target_lang)

    def _start_audio(self):
        self._audio_pipeline = AudioPipeline(target_lang=self._target_lang)

    def _stop_audio(self):
        if self._audio_pipeline:
            self._audio_pipeline.stop_dubbing()


# === MAIN GUARD ===

def main():
    """Self-test."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    print(f"{LOG_PREFIX} Karel IV. Engine wiring self-test")

    engine = KarelIVEngine(target_lang="cs")
    assert engine.state == AppState.INITIALIZING

    # Start engine
    success = engine.start()
    assert success
    assert engine.state == AppState.RUNNING
    print(f"{LOG_PREFIX} Engine started: {engine.get_status()}")

    # Test subscription
    engine.activate_user("jakub", SubscriptionTier.FAMILY)
    assert engine.check_user_access("jakub", "dubbing") is True
    assert engine.check_user_access("nobody", "dubbing") is False
    print(f"{LOG_PREFIX} Subscription check: OK")

    # Stop
    engine.stop()
    assert engine.state == AppState.STOPPED
    print(f"{LOG_PREFIX} Engine stopped")
    print(f"{LOG_PREFIX} Done.")


if __name__ == '__main__':
    main()
