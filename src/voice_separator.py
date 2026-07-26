#!/usr/bin/env python3
"""
Voice Separator — Source Separation (Vocals / Music / SFX)
UTL Stream Dubbing Pipeline Stage 2

Separates mixed audio into dialog, music, and sound effects
using Demucs v4. Allows dubbing only the dialog while preserving
original music and SFX.

Requirements: 3.2
Author: Pan Jeskyne
"""

import time
import numpy as np
from dataclasses import dataclass
from typing import Optional
from prometheus_client import Counter, Histogram

# === PROMETHEUS METRICS ===

utl_separation_chunks_total = Counter(
    'utl_separation_chunks_total',
    'Total audio chunks processed by voice separator'
)
utl_separation_latency_seconds = Histogram(
    'utl_separation_latency_seconds',
    'Voice separation latency per chunk',
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0]
)

# === DATA MODELS ===


@dataclass
class SeparatedAudio:
    """Result of source separation."""
    vocals: np.ndarray       # Isolated dialog/speech
    music: np.ndarray        # Background music
    sfx: np.ndarray          # Sound effects
    sample_rate: int
    duration_ms: int = 0


# === VOICE SEPARATOR ===

class VoiceSeparator:
    """
    Separates audio into vocals, music, and SFX using Demucs v4.

    Demucs (Facebook/Meta) performs state-of-the-art music source
    separation. We use it to isolate dialog from background audio
    in streams (Netflix, YouTube, games).

    Target: <500ms processing latency per 500ms chunk.

    Fallback: if Demucs is not available or separation fails,
    passes original audio through unchanged (vocals = full audio,
    music/sfx = silence).
    """

    def __init__(self, model_name: str = "htdemucs",
                 device: str = "cuda",
                 sample_rate: int = 16000):
        """
        Initialize Voice Separator.

        Args:
            model_name: Demucs model name (htdemucs = hybrid transformer)
            device: Processing device ("cuda" or "cpu")
            sample_rate: Expected input sample rate (default 16000)
        """
        self.model_name = model_name
        self.device = device
        self.sample_rate = sample_rate
        self._model = None
        self._available = False
        self._actual_device = None

        self._load_model()

    def _load_model(self):
        """Load Demucs model with CUDA support, fallback to CPU."""
        try:
            import torch
            from demucs.pretrained import get_model

            # Try CUDA first
            if self.device == "cuda" and torch.cuda.is_available():
                self._model = get_model(self.model_name)
                self._model.to(torch.device("cuda"))
                self._actual_device = "cuda"
                print(f"[VOICE_SEP] Demucs {self.model_name} loaded (CUDA)")
            else:
                self._model = get_model(self.model_name)
                self._model.to(torch.device("cpu"))
                self._actual_device = "cpu"
                print(f"[VOICE_SEP] Demucs {self.model_name} loaded (CPU)")

            self._available = True

        except ImportError:
            print("[VOICE_SEP] demucs not installed — passthrough mode")
            print("[VOICE_SEP] Install: pip install demucs")
        except Exception as e:
            print(f"[VOICE_SEP] Model load error: {e} — passthrough mode")

    # === SEPARATION ===

    def separate(self, audio_chunk: np.ndarray,
                 sample_rate: int = None) -> SeparatedAudio:
        """
        Separate audio chunk into vocal/music/SFX tracks.

        Accepts numpy array input (float32, range [-1, 1]).
        Shape can be:
          - (samples,) for mono
          - (channels, samples) for multi-channel

        If separation fails for any reason, passes original audio
        through as vocals with silent music/sfx tracks.

        Args:
            audio_chunk: Float32 numpy array of audio samples
            sample_rate: Sample rate override (defaults to self.sample_rate)

        Returns:
            SeparatedAudio with isolated tracks
        """
        start_time = time.time()
        sr = sample_rate if sample_rate is not None else self.sample_rate

        # Normalize input to float32
        audio = np.asarray(audio_chunk, dtype=np.float32)

        # Determine mono representation for fallback/output sizing
        if audio.ndim == 2:
            # (channels, samples) -> mono by averaging channels
            mono = audio.mean(axis=0)
            num_samples = audio.shape[1]
        else:
            mono = audio
            num_samples = len(audio)

        duration_ms = int(num_samples / sr * 1000) if sr > 0 else 0

        if not self._available or self._model is None:
            # Passthrough mode — vocals = full audio, music/sfx = silence
            result = self._passthrough(mono, sr, duration_ms)
            self._record_metrics(start_time)
            return result

        # Full Demucs separation
        try:
            result = self._demucs_separate(audio, sr, duration_ms)
        except Exception as e:
            print(f"[VOICE_SEP] Separation error: {e} — passthrough")
            result = self._passthrough(mono, sr, duration_ms)

        self._record_metrics(start_time)
        return result

    # === INTERNAL METHODS ===

    def _demucs_separate(self, audio: np.ndarray, sample_rate: int,
                         duration_ms: int) -> SeparatedAudio:
        """Run Demucs v4 model for source separation."""
        import torch
        from demucs.apply import apply_model

        # Prepare tensor: needs (batch=1, channels=2, samples)
        if audio.ndim == 1:
            # Mono -> duplicate to stereo
            waveform = torch.tensor(audio, dtype=torch.float32).unsqueeze(0)
            waveform = waveform.expand(2, -1).unsqueeze(0)
        elif audio.ndim == 2:
            # (channels, samples) -> ensure stereo
            if audio.shape[0] == 1:
                waveform = torch.tensor(
                    np.concatenate([audio, audio], axis=0),
                    dtype=torch.float32
                ).unsqueeze(0)
            elif audio.shape[0] == 2:
                waveform = torch.tensor(audio, dtype=torch.float32).unsqueeze(0)
            else:
                # More than 2 channels -> take first 2
                waveform = torch.tensor(
                    audio[:2], dtype=torch.float32
                ).unsqueeze(0)
        else:
            raise ValueError(f"[VOICE_SEP] Unexpected audio shape: {audio.shape}")

        device = torch.device(self._actual_device)
        waveform = waveform.to(device)

        # Apply model
        with torch.no_grad():
            sources = apply_model(self._model, waveform, device=device)

        # sources shape: (batch, num_sources, channels, samples)
        # htdemucs sources: drums, bass, other, vocals
        sources_np = sources.squeeze(0).cpu().numpy()

        # Extract tracks (mono — average channels)
        vocals = sources_np[3].mean(axis=0)   # vocals
        music = (sources_np[1] + sources_np[2]).mean(axis=0)  # bass + other
        sfx = sources_np[0].mean(axis=0)      # drums/percussion as SFX

        return SeparatedAudio(
            vocals=vocals,
            music=music,
            sfx=sfx,
            sample_rate=sample_rate,
            duration_ms=duration_ms
        )

    def _passthrough(self, mono_audio: np.ndarray, sample_rate: int,
                     duration_ms: int) -> SeparatedAudio:
        """Fallback: pass full audio as vocals, silence for music/sfx."""
        return SeparatedAudio(
            vocals=mono_audio.copy(),
            music=np.zeros_like(mono_audio),
            sfx=np.zeros_like(mono_audio),
            sample_rate=sample_rate,
            duration_ms=duration_ms
        )

    def _record_metrics(self, start_time: float):
        """Record Prometheus metrics for this separation."""
        utl_separation_chunks_total.inc()
        latency = time.time() - start_time
        utl_separation_latency_seconds.observe(latency)
        if latency > 0.5:
            print(f"[VOICE_SEP] WARNING: latency {latency:.2f}s > 500ms target")

    # === PROPERTIES ===

    @property
    def is_available(self) -> bool:
        """Check if Demucs model is loaded and ready."""
        return self._available


# === ENTRY POINT ===

def main():
    """Test voice separator with a generated audio chunk."""
    print("[VOICE_SEP] Testing voice separator...")

    separator = VoiceSeparator(device="cpu", sample_rate=16000)

    # Generate test chunk (500ms at 16kHz — sine wave + noise)
    duration = 0.5
    sr = 16000
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)

    # Simulate mixed audio: speech (440Hz) + music (220Hz) + noise
    speech = np.sin(2 * np.pi * 440 * t) * 0.5
    music = np.sin(2 * np.pi * 220 * t) * 0.3
    noise = np.random.randn(len(t)) * 0.1
    mixed = (speech + music + noise).astype(np.float32)

    # Separate (numpy array input)
    result = separator.separate(mixed, sample_rate=sr)

    print(f"  Vocals RMS: {np.sqrt(np.mean(result.vocals**2)):.4f}")
    print(f"  Music RMS:  {np.sqrt(np.mean(result.music**2)):.4f}")
    print(f"  SFX RMS:    {np.sqrt(np.mean(result.sfx**2)):.4f}")
    print(f"  Duration:   {result.duration_ms}ms")
    print(f"  Available:  {separator.is_available}")
    print("[VOICE_SEP] Test complete")


if __name__ == '__main__':
    main()
