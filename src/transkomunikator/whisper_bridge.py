"""
Transkomunikátor — Whisper STT Bridge
========================================

Wraps faster-whisper (or openai-whisper fallback) for speech-to-text.
Provides language detection with confidence scoring and automatic
second-pass for low-confidence detections.

Requirements: 12.1, 12.2
Standard 700: 12g stříbra = 1 mince
Autor: Pan Jeskyně
Asistent: Kiro
"""

from __future__ import annotations

import logging
import time
from typing import Optional, Tuple

import numpy as np

from .models import TranscriptionResult

# === LOGGING ===

logger = logging.getLogger(__name__)
_LOG = "[WHISPER]"

# === PROMETHEUS METRICS ===

try:
    from prometheus_client import Counter, Histogram
    transkomunikator_stt_latency_ms = Histogram(
        'transkomunikator_stt_latency_ms',
        'Whisper STT transcription latency in milliseconds',
        buckets=[50, 100, 200, 500, 1000, 2000, 5000]
    )
    transkomunikator_stt_errors_total = Counter(
        'transkomunikator_stt_errors_total',
        'Total Whisper STT errors'
    )
except ImportError:
    transkomunikator_stt_latency_ms = None
    transkomunikator_stt_errors_total = None


# === CONSTANTS ===

MIN_SAMPLE_RATE: int = 16000
LANGUAGE_DETECT_FRAMES: int = 30
CONFIDENCE_THRESHOLD: float = 0.9
SECOND_PASS_FRAMES: int = 60


# === WHISPER BRIDGE ===

class WhisperBridge:
    """Whisper STT wrapper for Transkomunikátor pipeline.

    Uses faster-whisper for efficient local inference. Falls back to
    openai-whisper if faster-whisper is unavailable.

    Language detection runs on the first 30 frames. If confidence < 0.9,
    a second pass with a longer window (60 frames) is performed.

    Requirements: 12.1, 12.2
    """

    def __init__(
        self,
        model_size: str = "base",
        device: str = "auto",
        compute_type: str = "int8",
    ):
        """Initialize WhisperBridge.

        Args:
            model_size: Whisper model size (tiny, base, small, medium, large-v3).
            device: Device for inference ('cpu', 'cuda', 'auto').
            compute_type: Compute type ('int8', 'float16', 'float32').
        """
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._model = None
        self._loaded = False
        self._transcription_count: int = 0

        logger.info(
            f"{_LOG} Initialized (model={model_size}, device={device}, "
            f"compute={compute_type})"
        )

    def load_model(self) -> bool:
        """Load the Whisper model into memory.

        Returns:
            True if model loaded successfully, False otherwise.
        """
        if self._loaded:
            return True

        try:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self._model_size,
                device=self._device,
                compute_type=self._compute_type,
            )
            self._loaded = True
            logger.info(f"{_LOG} Model loaded: {self._model_size}")
            return True
        except ImportError:
            logger.warning(f"{_LOG} faster-whisper not available, trying openai-whisper")
            try:
                import whisper
                self._model = whisper.load_model(self._model_size)
                self._loaded = True
                logger.info(f"{_LOG} OpenAI Whisper model loaded: {self._model_size}")
                return True
            except ImportError:
                logger.error(f"{_LOG} No whisper implementation available")
                return False
        except Exception as e:
            logger.error(f"{_LOG} Failed to load model: {e}")
            return False

    def unload_model(self) -> None:
        """Unload the Whisper model to free memory."""
        self._model = None
        self._loaded = False
        logger.info(f"{_LOG} Model unloaded")

    @property
    def is_loaded(self) -> bool:
        """Whether the model is currently loaded."""
        return self._loaded

    def transcribe(
        self,
        pcm: bytes,
        sample_rate: int = MIN_SAMPLE_RATE,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe PCM audio to text.

        Args:
            pcm: Raw PCM audio bytes (16-bit signed, little-endian).
            sample_rate: Audio sample rate (must be >= 16000).
            language: Force language code (auto-detect if None).

        Returns:
            TranscriptionResult with text, language, and confidence.
        """
        if sample_rate < MIN_SAMPLE_RATE:
            raise ValueError(f"sample_rate must be >= {MIN_SAMPLE_RATE}, got {sample_rate}")

        start_time = time.perf_counter()

        # Ensure model is loaded
        if not self._loaded:
            if not self.load_model():
                return TranscriptionResult(
                    text="",
                    language=language or "unknown",
                    confidence=0.0,
                )

        # Convert PCM bytes to numpy float32 array
        audio = self._pcm_to_float32(pcm)

        # Resample to 16000 Hz if needed
        if sample_rate != 16000:
            audio = self._resample(audio, sample_rate, 16000)

        try:
            text, detected_lang, confidence = self._run_transcription(audio, language)
        except Exception as e:
            logger.error(f"{_LOG} Transcription failed: {e}")
            if transkomunikator_stt_errors_total is not None:
                transkomunikator_stt_errors_total.inc()
            return TranscriptionResult(
                text="",
                language=language or "unknown",
                confidence=0.0,
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        self._transcription_count += 1

        if transkomunikator_stt_latency_ms is not None:
            transkomunikator_stt_latency_ms.observe(elapsed_ms)

        logger.debug(
            f"{_LOG} Transcribed in {elapsed_ms:.0f}ms: "
            f"lang={detected_lang} conf={confidence:.2f} text='{text[:50]}'"
        )

        return TranscriptionResult(
            text=text,
            language=detected_lang,
            confidence=confidence,
            timestamp_ms=int(time.time() * 1000),
            duration_ms=int(len(pcm) / (sample_rate * 2) * 1000),
        )

    def detect_language(self, pcm: bytes, sample_rate: int = MIN_SAMPLE_RATE) -> Tuple[str, float]:
        """Detect the language of the audio.

        Runs detection on the first 30 frames. If confidence < 0.9,
        performs a second pass with a longer window (60 frames).

        Args:
            pcm: Raw PCM audio bytes.
            sample_rate: Audio sample rate.

        Returns:
            Tuple of (language_code, confidence).
        """
        if not self._loaded:
            if not self.load_model():
                return ("unknown", 0.0)

        audio = self._pcm_to_float32(pcm)
        if sample_rate != 16000:
            audio = self._resample(audio, sample_rate, 16000)

        # First pass: short window
        samples_per_frame = 16000 * 20 // 1000  # 20ms per frame
        short_window = audio[:samples_per_frame * LANGUAGE_DETECT_FRAMES]

        lang, confidence = self._detect_language_internal(short_window)

        # If low confidence, try longer window
        if confidence < CONFIDENCE_THRESHOLD:
            long_window = audio[:samples_per_frame * SECOND_PASS_FRAMES]
            if len(long_window) > len(short_window):
                lang2, confidence2 = self._detect_language_internal(long_window)
                if confidence2 > confidence:
                    lang, confidence = lang2, confidence2
                    logger.info(
                        f"{_LOG} Second-pass detection improved: "
                        f"{lang} ({confidence:.2f})"
                    )

        return (lang, confidence)

    def get_status(self) -> dict:
        """Get WhisperBridge status."""
        return {
            "loaded": self._loaded,
            "model_size": self._model_size,
            "device": self._device,
            "compute_type": self._compute_type,
            "transcription_count": self._transcription_count,
        }

    # === PRIVATE METHODS ===

    def _pcm_to_float32(self, pcm: bytes) -> np.ndarray:
        """Convert 16-bit PCM bytes to float32 numpy array normalized to [-1, 1]."""
        audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32)
        audio /= 32768.0
        return audio

    def _resample(self, audio: np.ndarray, orig_rate: int, target_rate: int) -> np.ndarray:
        """Simple linear interpolation resampling."""
        if orig_rate == target_rate:
            return audio
        ratio = target_rate / orig_rate
        new_length = int(len(audio) * ratio)
        indices = np.linspace(0, len(audio) - 1, new_length)
        return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)

    def _run_transcription(
        self,
        audio: np.ndarray,
        language: Optional[str],
    ) -> Tuple[str, str, float]:
        """Run transcription using the loaded model.

        Returns:
            Tuple of (text, language, confidence).
        """
        try:
            # faster-whisper API
            from faster_whisper import WhisperModel
            if isinstance(self._model, WhisperModel):
                segments, info = self._model.transcribe(
                    audio,
                    language=language,
                    beam_size=5,
                    vad_filter=True,
                )
                text_parts = []
                for segment in segments:
                    text_parts.append(segment.text)
                text = " ".join(text_parts).strip()
                return (text, info.language, info.language_probability)
        except (ImportError, TypeError, AttributeError):
            pass

        try:
            # openai-whisper API
            import whisper
            result = self._model.transcribe(
                audio,
                language=language,
                fp16=False,
            )
            text = result.get("text", "").strip()
            lang = result.get("language", language or "unknown")
            # openai-whisper doesn't provide per-transcription confidence easily
            return (text, lang, 0.85)
        except (ImportError, TypeError, AttributeError):
            pass

        # Neither API worked
        raise RuntimeError("No Whisper API available for transcription")

    def _detect_language_internal(self, audio: np.ndarray) -> Tuple[str, float]:
        """Run language detection on audio segment.

        Returns:
            Tuple of (language_code, confidence).
        """
        try:
            from faster_whisper import WhisperModel
            if isinstance(self._model, WhisperModel):
                # faster-whisper: use detect_language
                # Pad audio to 30 seconds if shorter
                target_len = 16000 * 30
                if len(audio) < target_len:
                    padded = np.zeros(target_len, dtype=np.float32)
                    padded[:len(audio)] = audio
                    audio = padded

                # Use transcribe with a small segment for detection
                _, info = self._model.transcribe(
                    audio,
                    beam_size=1,
                    vad_filter=False,
                )
                return (info.language, info.language_probability)
        except (ImportError, TypeError, AttributeError):
            pass

        try:
            import whisper
            # openai-whisper: use detect_language
            audio_padded = whisper.pad_or_trim(audio)
            mel = whisper.log_mel_spectrogram(audio_padded).to(self._model.device)
            _, probs = self._model.detect_language(mel)
            best_lang = max(probs, key=probs.get)
            return (best_lang, probs[best_lang])
        except (ImportError, TypeError, AttributeError):
            pass

        return ("unknown", 0.0)


# === ENTRY POINT ===

def main() -> None:
    """Self-test demonstrating WhisperBridge (without model loading)."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    print("=" * 60)
    print("  WhisperBridge — Self-test (no model)")
    print("=" * 60)
    print()

    bridge = WhisperBridge(model_size="base")
    status = bridge.get_status()
    print(f"  Model: {status['model_size']}")
    print(f"  Loaded: {status['loaded']}")
    print(f"  Device: {status['device']}")
    print()

    # Test PCM conversion
    pcm = b"\x00\x00" * 16000  # 1 second silence at 16kHz
    audio = bridge._pcm_to_float32(pcm)
    print(f"  PCM → float32: {len(audio)} samples, range [{audio.min():.2f}, {audio.max():.2f}]")

    # Test resampling
    resampled = bridge._resample(audio, 16000, 8000)
    print(f"  Resample 16k→8k: {len(audio)} → {len(resampled)} samples")

    print()
    print("  WhisperBridge self-test PASSED (model not loaded — no GPU required)")


if __name__ == "__main__":
    main()
