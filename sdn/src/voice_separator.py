#!/usr/bin/env python3
"""
Voice Separator — Demucs v4-based source separation.

Isolates dialog (vocals) from music and sound effects in audio streams.
Part of the UTL Stream Audio Dubbing pipeline.

Pipeline position:
  AudioCapture → [VoiceSeparator] → SpeakerMapper → STT → Translation → TTS → AudioMixer

Target: <500ms per-chunk processing latency on GPU.

Autor: Pan Jeskyně (AsgardLab)
Asistent: Kiro
License: GPL 3.0 + Commercial (see LICENSE)
"""

import time
import logging
import threading
from dataclasses import dataclass
from typing import Optional

import numpy as np
from prometheus_client import Histogram, Counter

# ============================================================================
# PROMETHEUS METRIKY
# ============================================================================

voice_separation_latency = Histogram(
    "utl_voice_separation_latency_seconds",
    "Per-chunk voice separation processing latency",
    buckets=[0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 2.0],
)

voice_separation_chunks = Counter(
    "utl_voice_separation_chunks_total",
    "Total number of audio chunks processed by voice separator",
    ["status"],
)

# ============================================================================
# KONFIGURACE
# ============================================================================

DEFAULT_SAMPLE_RATE = 44100
DEFAULT_MODEL_NAME = "htdemucs"  # Demucs v4 hybrid transformer model
LATENCY_TARGET_MS = 500

logger = logging.getLogger(__name__)


# ============================================================================
# DATOVÉ MODELY
# ============================================================================


@dataclass
class SeparatedAudio:
    """Result of source separation — isolated audio tracks.

    Attributes:
        vocals: Isolated dialog/vocal track as numpy array.
        music: Background music track as numpy array.
        sfx: Sound effects and ambient track as numpy array.
        sample_rate: Sample rate of all tracks (Hz).
    """

    vocals: np.ndarray
    music: np.ndarray
    sfx: np.ndarray
    sample_rate: int


# ============================================================================
# VOICE SEPARATOR
# ============================================================================


class VoiceSeparatorError(Exception):
    """Raised when voice separation fails."""


class ModelLoadError(VoiceSeparatorError):
    """Raised when Demucs model cannot be loaded."""


class VoiceSeparator:
    """Demucs v4-based source separation: vocals vs music vs SFX.

    Loads the model lazily on first use. Automatically selects GPU if
    available, falling back to CPU. If Demucs dependencies are not
    available, operates in fallback mode (vocals = input, empty music/sfx).

    Thread-safe: multiple threads can call separate() concurrently.

    Usage:
        separator = VoiceSeparator()
        result = separator.separate(audio_chunk)
        # result.vocals, result.music, result.sfx
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        device: Optional[str] = None,
    ):
        """Initialize VoiceSeparator.

        Args:
            model_name: Demucs model variant to use (default: htdemucs).
            sample_rate: Expected input sample rate in Hz.
            device: Force device ('cuda' or 'cpu'). None = auto-detect.
        """
        self._model_name = model_name
        self._sample_rate = sample_rate
        self._device_preference = device
        self._model = None
        self._device = None
        self._fallback_mode = False
        self._lock = threading.Lock()
        self._load_lock = threading.Lock()

    @property
    def is_loaded(self) -> bool:
        """Whether the model has been loaded (or fallback mode is active)."""
        return self._model is not None or self._fallback_mode

    @property
    def device(self) -> Optional[str]:
        """Current device the model is running on."""
        return self._device

    @property
    def fallback_mode(self) -> bool:
        """Whether the separator is running in fallback (pass-through) mode."""
        return self._fallback_mode

    def _load_model(self) -> None:
        """Load Demucs v4 model lazily on first use.

        If Demucs/torch are not available, activates fallback mode where
        vocals = input audio and music/sfx = silence.

        Raises:
            ModelLoadError: If model loading fails for reasons other than
                missing dependencies (e.g. corrupted model files).
        """
        with self._load_lock:
            # Double-check after acquiring lock (another thread may have loaded)
            if self._model is not None or self._fallback_mode:
                return

            try:
                import torch
                from demucs.pretrained import get_model
                from demucs.apply import apply_model

                # Store apply_model reference for use in separate()
                self._apply_model = apply_model

                # Determine device: prefer GPU, fall back to CPU
                if self._device_preference:
                    self._device = self._device_preference
                elif torch.cuda.is_available():
                    self._device = "cuda"
                    logger.info("VoiceSeparator: GPU (CUDA) dostupné, používám GPU akceleraci")
                else:
                    self._device = "cpu"
                    logger.info("VoiceSeparator: GPU nedostupné, používám CPU (latence může být vyšší)")

                # Load the pretrained Demucs v4 model
                self._model = get_model(self._model_name)
                self._model.to(torch.device(self._device))
                self._model.eval()

                self._torch = torch

                logger.info(
                    "VoiceSeparator: Model '%s' načten na zařízení '%s'",
                    self._model_name,
                    self._device,
                )

            except ImportError as exc:
                # Fallback mode: Demucs/torch not installed
                self._fallback_mode = True
                self._device = "cpu"
                logger.warning(
                    "VoiceSeparator: Demucs nedostupný (%s), aktivuji fallback režim "
                    "(vocals = vstupní audio, music/sfx = ticho)",
                    exc,
                )

            except Exception as exc:
                raise ModelLoadError(
                    f"Nepodařilo se načíst model '{self._model_name}': {exc}"
                ) from exc

    def separate(self, audio_chunk: np.ndarray) -> SeparatedAudio:
        """Separate an audio chunk into vocals, music, and SFX tracks.

        Thread-safe: uses internal lock to serialize model inference calls.
        Concurrent callers will wait while another chunk is being processed.

        Args:
            audio_chunk: Input audio as numpy array. Shape can be:
                - (samples,) for mono
                - (channels, samples) for multi-channel

        Returns:
            SeparatedAudio with isolated vocals, music, and sfx tracks.

        Raises:
            ModelLoadError: If model cannot be loaded on first call
                (only when Demucs IS available but loading fails).
            VoiceSeparatorError: If separation processing fails.
        """
        # Lazy model loading (thread-safe via _load_lock inside _load_model)
        if not self.is_loaded:
            self._load_model()

        # Validate input shape early (no lock needed)
        if audio_chunk.ndim not in (1, 2):
            raise VoiceSeparatorError(
                f"Neočekávaný tvar vstupního audio: {audio_chunk.shape}. "
                "Očekáván 1D (mono) nebo 2D (channels, samples)."
            )

        start_time = time.perf_counter()

        try:
            # Fallback mode: vocals = input, no separation
            if self._fallback_mode:
                result = self._fallback_separate(audio_chunk)
            else:
                # Serialize model inference for thread-safety
                with self._lock:
                    result = self._process_chunk(audio_chunk)

            elapsed = time.perf_counter() - start_time

            # Record metrics
            voice_separation_latency.observe(elapsed)
            voice_separation_chunks.labels(status="success").inc()

            if elapsed > LATENCY_TARGET_MS / 1000.0:
                logger.warning(
                    "VoiceSeparator: Latence %.0fms překračuje cíl %dms",
                    elapsed * 1000,
                    LATENCY_TARGET_MS,
                )

            return result

        except VoiceSeparatorError:
            voice_separation_chunks.labels(status="error").inc()
            raise
        except Exception as exc:
            voice_separation_chunks.labels(status="error").inc()
            raise VoiceSeparatorError(
                f"Separace selhala: {exc}"
            ) from exc

    def _fallback_separate(self, audio_chunk: np.ndarray) -> SeparatedAudio:
        """Fallback separation: pass input as vocals, silence for music/sfx.

        Used when Demucs is not available.

        Args:
            audio_chunk: Raw audio numpy array (1D or 2D).

        Returns:
            SeparatedAudio with vocals = input, music = silence, sfx = silence.
        """
        silence = np.zeros_like(audio_chunk)
        return SeparatedAudio(
            vocals=audio_chunk.copy(),
            music=silence,
            sfx=silence,
            sample_rate=self._sample_rate,
        )

    def _process_chunk(self, audio_chunk: np.ndarray) -> SeparatedAudio:
        """Internal processing of a single audio chunk through Demucs.

        Args:
            audio_chunk: Raw audio numpy array.

        Returns:
            SeparatedAudio with separated tracks.
        """
        torch = self._torch

        # Normalize input shape to (channels, samples)
        if audio_chunk.ndim == 1:
            # Mono → stereo (Demucs expects stereo)
            waveform = np.stack([audio_chunk, audio_chunk])
        elif audio_chunk.ndim == 2:
            waveform = audio_chunk
        else:
            raise VoiceSeparatorError(
                f"Neočekávaný tvar vstupního audio: {audio_chunk.shape}. "
                "Očekáván 1D (mono) nebo 2D (channels, samples)."
            )

        # Convert to torch tensor: (batch=1, channels, samples)
        tensor = torch.tensor(waveform, dtype=torch.float32).unsqueeze(0)
        tensor = tensor.to(self._device)

        # Apply Demucs separation
        with torch.no_grad():
            sources = self._apply_model(
                self._model, tensor, device=self._device, progress=False
            )

        # sources shape: (batch=1, num_sources, channels, samples)
        # Demucs htdemucs sources: drums, bass, other, vocals
        sources_np = sources.squeeze(0).cpu().numpy()

        # Map Demucs output to our three categories:
        # - vocals: source index 3 (vocals)
        # - music: source index 0 + 1 (drums + bass)
        # - sfx: source index 2 (other — includes SFX, ambient)
        source_names = self._model.sources  # e.g. ['drums', 'bass', 'other', 'vocals']

        vocals_idx = source_names.index("vocals") if "vocals" in source_names else -1
        other_idx = source_names.index("other") if "other" in source_names else -1

        # Extract vocals
        if vocals_idx >= 0:
            vocals = sources_np[vocals_idx]
        else:
            vocals = np.zeros_like(waveform)

        # Extract SFX (mapped from "other" source)
        if other_idx >= 0:
            sfx = sources_np[other_idx]
        else:
            sfx = np.zeros_like(waveform)

        # Music = everything except vocals and SFX
        music = np.zeros_like(waveform)
        for i, name in enumerate(source_names):
            if name not in ("vocals", "other"):
                music += sources_np[i]

        # If input was mono, return mono output
        if audio_chunk.ndim == 1:
            vocals = vocals.mean(axis=0)
            music = music.mean(axis=0)
            sfx = sfx.mean(axis=0)

        return SeparatedAudio(
            vocals=vocals,
            music=music,
            sfx=sfx,
            sample_rate=self._sample_rate,
        )

    def unload(self) -> None:
        """Unload model from memory to free GPU/RAM resources.

        Thread-safe: acquires lock before modifying state.
        """
        with self._lock:
            if self._model is not None:
                del self._model
                self._model = None
                if self._device == "cuda":
                    try:
                        self._torch.cuda.empty_cache()
                    except Exception:
                        pass
                logger.info("VoiceSeparator: Model uvolněn z paměti")
            self._fallback_mode = False
