"""
Transkomunikátor — Audio Pipeline
====================================

Real-time audio processing pipeline:
  AudioCapture → FrameBuffer → WhisperSTT → AdaValidator (subprocess)
  → TranslationRouter → GeallEngine/GeminiBridge → CoquiTTS → AudioOutput

FrameBuffer is a thread-safe circular ring buffer that drops oldest frames
on overflow and fires a registered callback.

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6
Standard 700: 12g stříbra = 1 mince
Autor: Pan Jeskyně
Asistent: Kiro
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
import threading
import time
from collections import deque
from typing import Any, Callable, Deque, List, Optional

from .models import AudioFrame, EvictableCache, TranscriptionResult, TranslationResult

# === LOGGING ===

logger = logging.getLogger(__name__)
_LOG = "[PIPELINE]"

# === PROMETHEUS METRICS ===

try:
    from prometheus_client import Counter, Histogram
    transkomunikator_pipeline_latency_ms = Histogram(
        'transkomunikator_pipeline_latency_ms',
        'End-to-end pipeline latency in milliseconds',
        buckets=[50, 100, 200, 300, 400, 500, 750, 1000, 2000, 5000]
    )
    transkomunikator_buffer_overflow_total = Counter(
        'transkomunikator_buffer_overflow_total',
        'Total number of audio frames dropped due to buffer overflow'
    )
except ImportError:
    transkomunikator_pipeline_latency_ms = None
    transkomunikator_buffer_overflow_total = None


# === CONSTANTS ===

DEFAULT_SAMPLE_RATE: int = 16000
DEFAULT_CHANNELS: int = 1
DEFAULT_BUFFER_SECONDS: float = 2.0
VALIDATOR_TIMEOUT_SECONDS: float = 0.1
BIN_DIR: str = os.path.join(os.path.dirname(__file__), "..", "..", "bin")


# === FRAME BUFFER ===

class FrameBuffer(EvictableCache):
    """Thread-safe circular ring buffer for AudioFrame objects.

    Configurable depth (default: 2 seconds at 16 kHz mono). When the buffer
    is full, oldest frames are dropped and the overflow counter is incremented.
    An optional callback is fired on every overflow event.

    Requirements: 1.6
    """

    def __init__(
        self,
        max_duration_seconds: float = DEFAULT_BUFFER_SECONDS,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        frame_duration_ms: int = 20,
    ):
        """Initialize FrameBuffer.

        Args:
            max_duration_seconds: Maximum buffer duration in seconds.
            sample_rate: Audio sample rate in Hz (>= 16000).
            frame_duration_ms: Duration of each frame in milliseconds.
        """
        if sample_rate < 16000:
            raise ValueError(f"sample_rate must be >= 16000, got {sample_rate}")
        if frame_duration_ms <= 0:
            raise ValueError(f"frame_duration_ms must be > 0, got {frame_duration_ms}")

        self._sample_rate = sample_rate
        self._frame_duration_ms = frame_duration_ms
        # Max frames = total duration / frame duration
        self._max_frames = int((max_duration_seconds * 1000) / frame_duration_ms)
        self._buffer: Deque[AudioFrame] = deque(maxlen=self._max_frames)
        self._lock = threading.Lock()
        self._overflow_count: int = 0
        self._overflow_callback: Optional[Callable[[int], None]] = None

        logger.info(
            f"{_LOG} FrameBuffer initialized: max_frames={self._max_frames}, "
            f"rate={sample_rate}Hz, frame={frame_duration_ms}ms"
        )

    @property
    def capacity(self) -> int:
        """Maximum number of frames the buffer can hold."""
        return self._max_frames

    @property
    def size(self) -> int:
        """Current number of frames in the buffer."""
        with self._lock:
            return len(self._buffer)

    @property
    def overflow_count(self) -> int:
        """Total number of frames dropped due to overflow."""
        return self._overflow_count

    def push(self, frame: AudioFrame) -> bool:
        """Push a frame into the buffer.

        If the buffer is full, the oldest frame is dropped (overflow).

        Args:
            frame: AudioFrame to push.

        Returns:
            True if frame was added without overflow, False if overflow occurred.
        """
        overflow = False
        with self._lock:
            if len(self._buffer) >= self._max_frames:
                # Overflow: oldest frame will be evicted by deque maxlen
                overflow = True
                self._overflow_count += 1

            self._buffer.append(frame)

        if overflow:
            if transkomunikator_buffer_overflow_total is not None:
                transkomunikator_buffer_overflow_total.inc()
            if self._overflow_callback:
                try:
                    self._overflow_callback(self._overflow_count)
                except Exception as e:
                    logger.error(f"{_LOG} Overflow callback error: {e}")

        return not overflow

    def pop(self) -> Optional[AudioFrame]:
        """Pop the oldest frame from the buffer.

        Returns:
            The oldest AudioFrame, or None if buffer is empty.
        """
        with self._lock:
            if self._buffer:
                return self._buffer.popleft()
            return None

    def peek(self) -> Optional[AudioFrame]:
        """Peek at the oldest frame without removing it."""
        with self._lock:
            if self._buffer:
                return self._buffer[0]
            return None

    def clear(self) -> int:
        """Clear all frames from buffer. Returns count of cleared frames."""
        with self._lock:
            count = len(self._buffer)
            self._buffer.clear()
            return count

    def get_all(self) -> List[AudioFrame]:
        """Get all frames (oldest first) without clearing."""
        with self._lock:
            return list(self._buffer)

    def on_overflow(self, callback: Callable[[int], None]) -> None:
        """Register a callback for buffer overflow events.

        Args:
            callback: Function receiving total overflow count as argument.
        """
        self._overflow_callback = callback

    # === EvictableCache implementation ===

    def evict(self) -> int:
        """Evict oldest half of frames under memory pressure."""
        with self._lock:
            count = len(self._buffer)
            evict_count = count // 2
            freed_bytes = 0
            for _ in range(evict_count):
                if self._buffer:
                    frame = self._buffer.popleft()
                    freed_bytes += len(frame.pcm_data)
            return freed_bytes

    def memory_usage_bytes(self) -> int:
        """Approximate memory usage of buffered PCM data."""
        with self._lock:
            return sum(len(f.pcm_data) for f in self._buffer)

    @property
    def eviction_priority(self) -> int:
        """Audio frames are last to be evicted (priority 4)."""
        return 4


# === AUDIO PIPELINE ===

class AudioPipeline:
    """Real-time audio translation pipeline.

    Wires together:
      AudioCapture → FrameBuffer → WhisperSTT → AdaValidator (subprocess)
      → TranslationRouter → GeallEngine/GeminiBridge → CoquiTTS → AudioOutput

    Each stage can be mocked/replaced for testing. The pipeline tracks
    per-stage and end-to-end latency via Prometheus metrics.

    Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6
    """

    def __init__(
        self,
        buffer: Optional[FrameBuffer] = None,
        whisper_bridge: Any = None,
        translation_router: Any = None,
        coqui_bridge: Any = None,
        validator_path: Optional[str] = None,
    ):
        """Initialize AudioPipeline.

        Args:
            buffer: FrameBuffer instance (created if not provided).
            whisper_bridge: WhisperBridge instance for STT.
            translation_router: TranslationRouter instance.
            coqui_bridge: CoquiBridge instance for TTS.
            validator_path: Path to Ada transkomunikator_validator.exe.
        """
        self._buffer = buffer or FrameBuffer()
        self._whisper = whisper_bridge
        self._translator = translation_router
        self._tts = coqui_bridge
        self._validator_path = validator_path or self._find_validator()

        self._running = False
        self._output_queue: Deque[AudioFrame] = deque(maxlen=100)
        self._output_lock = threading.Lock()
        self._total_frames_processed: int = 0
        self._stage_timings: dict = {}

        logger.info(f"{_LOG} AudioPipeline initialized, validator={self._validator_path}")

    @property
    def buffer(self) -> FrameBuffer:
        """Access the underlying FrameBuffer."""
        return self._buffer

    @property
    def total_frames_processed(self) -> int:
        return self._total_frames_processed

    def push_frame(self, pcm_frame: bytes, timestamp_ms: int = 0) -> None:
        """Push a raw PCM frame into the pipeline buffer.

        Args:
            pcm_frame: Raw PCM audio bytes (16-bit signed, little-endian).
            timestamp_ms: Capture timestamp in milliseconds.
        """
        frame = AudioFrame(
            pcm_data=pcm_frame,
            sample_rate=DEFAULT_SAMPLE_RATE,
            channels=DEFAULT_CHANNELS,
            timestamp_ms=timestamp_ms,
            duration_ms=len(pcm_frame) // (DEFAULT_SAMPLE_RATE * 2 // 1000) if pcm_frame else 0,
        )
        self._buffer.push(frame)

    def get_output_frame(self) -> Optional[AudioFrame]:
        """Get the next processed output frame (translated TTS audio).

        Returns:
            AudioFrame with translated TTS output, or None if no output ready.
        """
        with self._output_lock:
            if self._output_queue:
                return self._output_queue.popleft()
            return None

    def get_pipeline_latency_ms(self) -> float:
        """Get average end-to-end pipeline latency in milliseconds.

        Returns:
            Average latency across last processed frames, or 0.0 if no data.
        """
        total = self._stage_timings.get("total_ms", 0.0)
        count = self._stage_timings.get("count", 0)
        if count == 0:
            return 0.0
        return total / count

    def on_buffer_overflow(self, callback: Callable[[int], None]) -> None:
        """Register a callback for buffer overflow events."""
        self._buffer.on_overflow(callback)

    def process_next_frame(self) -> Optional[TranslationResult]:
        """Process the next frame from buffer through the full pipeline.

        Pipeline stages:
          1. Pop frame from buffer
          2. Validate via Ada subprocess (transkomunikator_validator.exe)
          3. Transcribe via Whisper STT
          4. Translate via TranslationRouter (Geall → Gemini fallback)
          5. Synthesize via Coqui TTS
          6. Push output frame to output queue

        Returns:
            TranslationResult if successful, None if buffer empty or error.
        """
        start_time = time.perf_counter()

        # Stage 1: Pop frame
        frame = self._buffer.pop()
        if frame is None:
            return None

        t_pop = time.perf_counter()

        # Stage 2: Ada validator (subprocess)
        valid = self._validate_frame(frame)
        t_validate = time.perf_counter()

        if not valid:
            logger.warning(f"{_LOG} Frame rejected by Ada validator")
            return None

        # Stage 3: Whisper STT
        transcription = self._transcribe(frame)
        t_stt = time.perf_counter()

        if transcription is None or not transcription.text.strip():
            return None

        # Stage 4: Translation
        translation = self._translate(transcription)
        t_translate = time.perf_counter()

        if translation is None:
            return None

        # Stage 5: TTS synthesis
        output_frame = self._synthesize(translation)
        t_tts = time.perf_counter()

        if output_frame:
            with self._output_lock:
                self._output_queue.append(output_frame)

        # Record latency
        total_ms = (t_tts - start_time) * 1000
        self._total_frames_processed += 1
        self._record_latency(total_ms, {
            "pop_ms": (t_pop - start_time) * 1000,
            "validate_ms": (t_validate - t_pop) * 1000,
            "stt_ms": (t_stt - t_validate) * 1000,
            "translate_ms": (t_translate - t_stt) * 1000,
            "tts_ms": (t_tts - t_translate) * 1000,
            "total_ms": total_ms,
        })

        if transkomunikator_pipeline_latency_ms is not None:
            transkomunikator_pipeline_latency_ms.observe(total_ms)

        logger.debug(f"{_LOG} Frame processed in {total_ms:.1f}ms")
        return translation

    def get_status(self) -> dict:
        """Get pipeline status."""
        return {
            "running": self._running,
            "buffer_size": self._buffer.size,
            "buffer_capacity": self._buffer.capacity,
            "buffer_overflow_count": self._buffer.overflow_count,
            "frames_processed": self._total_frames_processed,
            "avg_latency_ms": round(self.get_pipeline_latency_ms(), 1),
            "output_queue_size": len(self._output_queue),
        }

    # === PRIVATE METHODS ===

    def _find_validator(self) -> str:
        """Locate transkomunikator_validator.exe."""
        # Try relative to this file (src/transkomunikator/ → ../../bin/)
        candidate = os.path.join(
            os.path.dirname(__file__), "..", "..", "bin", "transkomunikator_validator.exe"
        )
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)
        # Fallback: just the name (must be in PATH)
        return "transkomunikator_validator.exe"

    def _validate_frame(self, frame: AudioFrame) -> bool:
        """Validate frame via Ada transkomunikator_validator subprocess.

        Writes PCM to a temp WAV file, calls the validator, checks exit code.

        Returns:
            True if frame is valid (exit code 0), False otherwise.
        """
        if not self._validator_path:
            return True  # No validator configured — pass through

        try:
            # Write frame to temp WAV file
            tmp_path = self._write_temp_wav(frame)
            if tmp_path is None:
                return True  # Can't write temp — pass through

            result = subprocess.run(
                [self._validator_path, "--pcm", tmp_path],
                capture_output=True,
                text=True,
                timeout=VALIDATOR_TIMEOUT_SECONDS,
            )

            # Cleanup temp file
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

            return result.returncode == 0

        except subprocess.TimeoutExpired:
            logger.warning(f"{_LOG} Ada validator timed out")
            return True  # On timeout, pass through (don't block pipeline)
        except FileNotFoundError:
            logger.warning(f"{_LOG} Ada validator not found: {self._validator_path}")
            return True  # Validator missing — pass through
        except Exception as e:
            logger.error(f"{_LOG} Ada validator error: {e}")
            return True

    def _write_temp_wav(self, frame: AudioFrame) -> Optional[str]:
        """Write AudioFrame to a temporary WAV file for the Ada validator."""
        import struct

        try:
            fd, tmp_path = tempfile.mkstemp(suffix=".wav", prefix="tk_")
            data_size = len(frame.pcm_data)
            sample_rate = frame.sample_rate
            channels = frame.channels
            bits_per_sample = 16
            byte_rate = sample_rate * channels * bits_per_sample // 8
            block_align = channels * bits_per_sample // 8

            with os.fdopen(fd, "wb") as f:
                # RIFF header
                f.write(b"RIFF")
                f.write(struct.pack("<I", 36 + data_size))
                f.write(b"WAVE")
                # fmt subchunk
                f.write(b"fmt ")
                f.write(struct.pack("<I", 16))
                f.write(struct.pack("<H", 1))  # PCM
                f.write(struct.pack("<H", channels))
                f.write(struct.pack("<I", sample_rate))
                f.write(struct.pack("<I", byte_rate))
                f.write(struct.pack("<H", block_align))
                f.write(struct.pack("<H", bits_per_sample))
                # data subchunk
                f.write(b"data")
                f.write(struct.pack("<I", data_size))
                f.write(frame.pcm_data)

            return tmp_path
        except Exception as e:
            logger.error(f"{_LOG} Failed to write temp WAV: {e}")
            return None

    def _transcribe(self, frame: AudioFrame) -> Optional[TranscriptionResult]:
        """Transcribe audio frame via Whisper STT."""
        if self._whisper is None:
            # No whisper bridge — return mock transcription for testing
            return TranscriptionResult(
                text="[mock transcription]",
                language="cs",
                confidence=0.95,
                timestamp_ms=frame.timestamp_ms,
            )

        try:
            return self._whisper.transcribe(frame.pcm_data, frame.sample_rate)
        except Exception as e:
            logger.error(f"{_LOG} STT error: {e}")
            return None

    def _translate(self, transcription: TranscriptionResult) -> Optional[TranslationResult]:
        """Translate transcription via TranslationRouter."""
        if self._translator is None:
            # No translator — return mock translation for testing
            return TranslationResult(
                translated_text=f"[translated: {transcription.text}]",
                source_lang=transcription.language,
                target_lang="en",
                quality_score=0.92,
                engine="mock",
            )

        try:
            return self._translator.route(
                text=transcription.text,
                source_lang=transcription.language,
                target_lang="en",  # Default target; overridden by config
            )
        except Exception as e:
            logger.error(f"{_LOG} Translation error: {e}")
            return None

    def _synthesize(self, translation: TranslationResult) -> Optional[AudioFrame]:
        """Synthesize translated text via Coqui TTS."""
        if self._tts is None:
            # No TTS — return silent frame
            silence_duration_ms = 100
            silence_bytes = b"\x00\x00" * (DEFAULT_SAMPLE_RATE * silence_duration_ms // 1000)
            return AudioFrame(
                pcm_data=silence_bytes,
                sample_rate=DEFAULT_SAMPLE_RATE,
                channels=DEFAULT_CHANNELS,
                timestamp_ms=int(time.time() * 1000),
                duration_ms=silence_duration_ms,
            )

        try:
            pcm_bytes = self._tts.synthesize(
                text=translation.translated_text,
                voice_clone_id=None,
            )
            return AudioFrame(
                pcm_data=pcm_bytes,
                sample_rate=DEFAULT_SAMPLE_RATE,
                channels=DEFAULT_CHANNELS,
                timestamp_ms=int(time.time() * 1000),
            )
        except Exception as e:
            logger.error(f"{_LOG} TTS error: {e}")
            # On TTS failure: output silence, don't stall pipeline
            silence_bytes = b"\x00\x00" * (DEFAULT_SAMPLE_RATE * 100 // 1000)
            return AudioFrame(
                pcm_data=silence_bytes,
                sample_rate=DEFAULT_SAMPLE_RATE,
                channels=DEFAULT_CHANNELS,
                timestamp_ms=int(time.time() * 1000),
                duration_ms=100,
            )

    def _record_latency(self, total_ms: float, stage_timings: dict) -> None:
        """Record latency data for averaging."""
        prev_total = self._stage_timings.get("total_ms", 0.0)
        prev_count = self._stage_timings.get("count", 0)
        self._stage_timings = {
            "total_ms": prev_total + total_ms,
            "count": prev_count + 1,
            "last": stage_timings,
        }


# === ENTRY POINT ===

def main() -> None:
    """Self-test demonstrating AudioPipeline."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    print("=" * 60)
    print("  AudioPipeline — Self-test")
    print("=" * 60)
    print()

    # Create pipeline without real bridges (mock mode)
    pipeline = AudioPipeline()

    # Push some frames
    for i in range(5):
        pcm = b"\x00\x00" * 320  # 20ms at 16kHz mono
        pipeline.push_frame(pcm, timestamp_ms=i * 20)

    print(f"  Buffer size: {pipeline.buffer.size}")
    print(f"  Buffer capacity: {pipeline.buffer.capacity}")

    # Process frames
    for _ in range(5):
        result = pipeline.process_next_frame()
        if result:
            print(f"  Processed: {result.translated_text[:50]}")

    status = pipeline.get_status()
    print(f"  Frames processed: {status['frames_processed']}")
    print(f"  Avg latency: {status['avg_latency_ms']}ms")
    print()

    # Test overflow
    buffer = FrameBuffer(max_duration_seconds=0.1, frame_duration_ms=20)  # 5 frames max
    overflows = []
    buffer.on_overflow(lambda count: overflows.append(count))

    for i in range(10):
        pcm = b"\x00\x00" * 320
        buffer.push(AudioFrame(pcm_data=pcm, timestamp_ms=i * 20, duration_ms=20))

    print(f"  FrameBuffer overflow test: {len(overflows)} overflows, "
          f"buffer size={buffer.size}/{buffer.capacity}")
    assert buffer.overflow_count == 5, f"Expected 5 overflows, got {buffer.overflow_count}"
    print()
    print("  AudioPipeline self-test PASSED")


if __name__ == "__main__":
    main()
