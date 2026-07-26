#!/usr/bin/env python3
"""
Audio Capture — System Audio Loopback
UTL Stream Dubbing Pipeline Stage 1

Captures system audio output (what speakers play) for dubbing pipeline.
Platform-specific backends:
- Windows: WASAPI loopback (captures speaker output)
- Linux: PulseAudio monitor source (captures sink output)

Produces 500ms audio chunks as numpy arrays for downstream processing
by VoiceSeparator.

Requirements: 3.1
Author: Pan Jeskyne
"""

import sys
import time
import queue
import threading
import logging
from dataclasses import dataclass
from typing import Optional, Callable

import numpy as np
from prometheus_client import Counter, Histogram

# === LOGGING ===

logger = logging.getLogger(__name__)
LOG_PREFIX = "[AUDIO_CAPTURE]"

# === PROMETHEUS METRICS ===

utl_audio_capture_chunks_total = Counter(
    'utl_audio_capture_chunks_total',
    'Total audio chunks captured from system audio'
)
utl_audio_capture_latency_seconds = Histogram(
    'utl_audio_capture_latency_seconds',
    'Audio capture chunk processing latency',
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0]
)
utl_audio_capture_drops_total = Counter(
    'utl_audio_capture_drops_total',
    'Total audio chunks dropped due to full queue'
)

# === CONFIGURATION ===

DEFAULT_SAMPLE_RATE = 48000
DEFAULT_CHANNELS = 2
DEFAULT_CHUNK_MS = 500
MAX_QUEUE_SIZE = 20


# === DATA MODELS ===

@dataclass
class AudioChunk:
    """A captured audio chunk from system audio.

    Attributes:
        samples: Audio samples as numpy array, shape (num_samples, channels).
                 Values are float32 in range [-1.0, 1.0].
        sample_rate: Sample rate in Hz.
        channels: Number of audio channels.
        duration_ms: Chunk duration in milliseconds.
        timestamp: Capture timestamp (time.time() epoch seconds).
    """
    samples: np.ndarray
    sample_rate: int
    channels: int
    duration_ms: int
    timestamp: float


# === AUDIO CAPTURE ===

class AudioCapture:
    """
    Captures system audio output for the dubbing pipeline.

    Platform-specific backends:
    - Windows: WASAPI loopback (captures speaker output via soundcard)
    - Linux: PulseAudio monitor source (captures sink output via soundcard)
    - Fallback: sounddevice microphone input (if soundcard unavailable)

    Produces 500ms audio chunks at configurable sample rate
    for downstream processing by VoiceSeparator.
    """

    def __init__(self, sample_rate: int = DEFAULT_SAMPLE_RATE,
                 channels: int = DEFAULT_CHANNELS,
                 chunk_ms: int = DEFAULT_CHUNK_MS):
        """
        Initialize system audio capture.

        Args:
            sample_rate: Target sample rate in Hz (default 48000)
            channels: Number of audio channels (default 2 for stereo)
            chunk_ms: Chunk duration in milliseconds (default 500)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_ms = chunk_ms
        self.chunk_size = int(sample_rate * chunk_ms / 1000)
        self._queue: queue.Queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._platform = sys.platform
        self._on_chunk: Optional[Callable[[AudioChunk], None]] = None

        logger.info(
            f"{LOG_PREFIX} Init: {sample_rate}Hz, {channels}ch, "
            f"{chunk_ms}ms chunks, platform={self._platform}"
        )

    # === PUBLIC API ===

    def start(self) -> None:
        """Start capturing system audio in a background thread.

        The capture runs until stop() is called. Audio chunks are
        placed in an internal queue and can be retrieved via get_chunk().
        """
        if self._running:
            logger.warning(f"{LOG_PREFIX} Already running")
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._capture_loop,
            name="AudioCaptureThread",
            daemon=True
        )
        self._thread.start()
        logger.info(f"{LOG_PREFIX} Capture started")

    def stop(self) -> None:
        """Stop capturing system audio and release resources."""
        if not self._running:
            return

        self._running = False
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info(f"{LOG_PREFIX} Capture stopped")

    def get_chunk(self, timeout: float = 1.0) -> Optional[AudioChunk]:
        """
        Get next audio chunk from the capture queue.

        Blocks up to timeout seconds waiting for the next chunk.

        Args:
            timeout: Maximum seconds to wait for a chunk.

        Returns:
            AudioChunk with captured audio, or None on timeout.
        """
        try:
            chunk = self._queue.get(timeout=timeout)
            return chunk
        except queue.Empty:
            return None

    def get_chunk_nowait(self) -> Optional[AudioChunk]:
        """
        Get next audio chunk without blocking.

        Returns:
            AudioChunk if available, or None if queue is empty.
        """
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None

    def on_chunk(self, callback: Callable[[AudioChunk], None]) -> None:
        """Register a callback invoked for each captured audio chunk.

        Args:
            callback: Function called with each AudioChunk as it arrives.
        """
        self._on_chunk = callback

    # === PROPERTIES ===

    @property
    def is_running(self) -> bool:
        """Whether capture is currently active."""
        return self._running

    @property
    def queue_size(self) -> int:
        """Current number of chunks waiting in queue."""
        return self._queue.qsize()

    @property
    def is_available(self) -> bool:
        """Whether the audio capture backend is available on this platform."""
        if self._platform == 'win32' or self._platform.startswith('linux'):
            try:
                import soundcard  # noqa: F401
                return True
            except ImportError:
                pass
            try:
                import sounddevice  # noqa: F401
                return True
            except ImportError:
                pass
        return False

    # === CAPTURE LOOP ===

    def _capture_loop(self) -> None:
        """Main capture loop dispatches to platform-specific backend."""
        if self._platform == 'win32':
            self._capture_wasapi()
        elif self._platform.startswith('linux'):
            self._capture_pulseaudio()
        else:
            logger.warning(
                f"{LOG_PREFIX} Unsupported platform: {self._platform}, "
                "falling back to sounddevice"
            )
            self._capture_sounddevice()

    # === WASAPI LOOPBACK (WINDOWS) ===

    def _capture_wasapi(self) -> None:
        """
        Capture system audio via WASAPI loopback on Windows.

        WASAPI loopback captures what the speakers output —
        any application audio (Netflix, YouTube, games, etc.).
        Uses the soundcard library which wraps WASAPI internally.
        """
        try:
            import soundcard as sc
        except ImportError:
            logger.warning(
                f"{LOG_PREFIX} soundcard not installed, "
                "trying sounddevice fallback"
            )
            self._capture_sounddevice()
            return

        try:
            # Get default speaker for loopback recording
            default_speaker = sc.default_speaker()
            if default_speaker is None:
                logger.error(f"{LOG_PREFIX} No default speaker found")
                self._running = False
                return

            logger.info(
                f"{LOG_PREFIX} WASAPI loopback: {default_speaker.name}"
            )

            with default_speaker.recorder(
                samplerate=self.sample_rate,
                channels=self.channels,
                blocksize=self.chunk_size
            ) as recorder:
                while self._running:
                    start_time = time.time()

                    # Record one chunk — shape: (chunk_size, channels)
                    data = recorder.record(numframes=self.chunk_size)

                    # Create AudioChunk
                    chunk = AudioChunk(
                        samples=data.astype(np.float32),
                        sample_rate=self.sample_rate,
                        channels=self.channels,
                        duration_ms=self.chunk_ms,
                        timestamp=start_time
                    )

                    self._emit_chunk(chunk, start_time)

        except Exception as e:
            logger.error(f"{LOG_PREFIX} WASAPI error: {e}")
            self._running = False

    # === PULSEAUDIO MONITOR (LINUX) ===

    def _capture_pulseaudio(self) -> None:
        """
        Capture system audio via PulseAudio monitor on Linux.

        PulseAudio monitor source captures the output of a sink —
        equivalent to WASAPI loopback on Windows. Captures all system
        audio regardless of which application produces it.
        """
        try:
            import soundcard as sc
        except ImportError:
            logger.warning(
                f"{LOG_PREFIX} soundcard not installed, "
                "trying sounddevice fallback"
            )
            self._capture_sounddevice()
            return

        try:
            # Get default speaker (sink) — its monitor captures output
            default_speaker = sc.default_speaker()
            if default_speaker is None:
                logger.error(f"{LOG_PREFIX} No default speaker found")
                self._running = False
                return

            logger.info(
                f"{LOG_PREFIX} PulseAudio monitor: {default_speaker.name}"
            )

            with default_speaker.recorder(
                samplerate=self.sample_rate,
                channels=self.channels,
                blocksize=self.chunk_size
            ) as recorder:
                while self._running:
                    start_time = time.time()

                    # Record one chunk — shape: (chunk_size, channels)
                    data = recorder.record(numframes=self.chunk_size)

                    # Create AudioChunk
                    chunk = AudioChunk(
                        samples=data.astype(np.float32),
                        sample_rate=self.sample_rate,
                        channels=self.channels,
                        duration_ms=self.chunk_ms,
                        timestamp=start_time
                    )

                    self._emit_chunk(chunk, start_time)

        except Exception as e:
            logger.error(f"{LOG_PREFIX} PulseAudio error: {e}")
            self._running = False

    # === SOUNDDEVICE FALLBACK ===

    def _capture_sounddevice(self) -> None:
        """
        Fallback capture using sounddevice library.

        Uses microphone input instead of system audio loopback.
        This is a degraded mode when soundcard library is unavailable.
        """
        try:
            import sounddevice as sd
        except ImportError:
            logger.error(
                f"{LOG_PREFIX} Neither soundcard nor sounddevice installed. "
                "Install: pip install soundcard   or   pip install sounddevice"
            )
            self._running = False
            return

        logger.warning(
            f"{LOG_PREFIX} Using sounddevice fallback (microphone input, "
            "not system audio)"
        )

        try:
            def callback(indata, frames, time_info, status):
                if status:
                    logger.debug(f"{LOG_PREFIX} sounddevice status: {status}")

                start_time = time.time()
                chunk = AudioChunk(
                    samples=indata.copy().astype(np.float32),
                    sample_rate=self.sample_rate,
                    channels=self.channels,
                    duration_ms=self.chunk_ms,
                    timestamp=start_time
                )
                self._emit_chunk(chunk, start_time)

            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                blocksize=self.chunk_size,
                callback=callback
            ):
                while self._running:
                    time.sleep(0.05)

        except Exception as e:
            logger.error(f"{LOG_PREFIX} sounddevice error: {e}")
            self._running = False

    # === INTERNAL HELPERS ===

    def _emit_chunk(self, chunk: AudioChunk, start_time: float) -> None:
        """Put chunk into queue and invoke callback.

        Args:
            chunk: The captured AudioChunk.
            start_time: Time when capture of this chunk started.
        """
        # Enqueue
        if not self._queue.full():
            self._queue.put(chunk)
            utl_audio_capture_chunks_total.inc()
        else:
            utl_audio_capture_drops_total.inc()
            logger.debug(f"{LOG_PREFIX} Queue full, dropping chunk")

        # Record latency
        latency = time.time() - start_time
        utl_audio_capture_latency_seconds.observe(latency)

        # Invoke callback if registered
        if self._on_chunk is not None:
            try:
                self._on_chunk(chunk)
            except Exception as e:
                logger.error(f"{LOG_PREFIX} Chunk callback error: {e}")


# === ENTRY POINT ===

def main():
    """Self-test: capture system audio for 5 seconds and report stats."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(message)s"
    )

    print(f"{LOG_PREFIX} Starting test capture (5 seconds)...")
    print(f"{LOG_PREFIX} Platform: {sys.platform}")

    capture = AudioCapture(
        sample_rate=DEFAULT_SAMPLE_RATE,
        channels=DEFAULT_CHANNELS,
        chunk_ms=DEFAULT_CHUNK_MS
    )

    print(f"{LOG_PREFIX} Backend available: {capture.is_available}")

    capture.start()

    chunks_received = 0
    start = time.time()

    while time.time() - start < 5.0:
        chunk = capture.get_chunk(timeout=1.0)
        if chunk is not None:
            chunks_received += 1
            # Calculate RMS for volume indicator
            rms = float(np.sqrt(np.mean(chunk.samples ** 2)))
            print(
                f"  Chunk {chunks_received}: "
                f"shape={chunk.samples.shape}, "
                f"duration={chunk.duration_ms}ms, "
                f"RMS={rms:.4f}"
            )

    capture.stop()

    expected_chunks = int(5000 / DEFAULT_CHUNK_MS)
    print(
        f"{LOG_PREFIX} Test complete: {chunks_received}/{expected_chunks} "
        f"chunks in 5s"
    )


if __name__ == '__main__':
    main()
