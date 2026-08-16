"""Audio Capture module for UTL Stream Dubbing Pipeline.

Captures system audio via platform-specific APIs (WASAPI on Windows,
PulseAudio on Linux) and produces 500ms audio chunks for downstream
Voice Separator processing.

Requirements: 3.1
"""

import platform
import queue
import threading
import time
from abc import ABC, abstractmethod

import numpy as np
from prometheus_client import Counter, Gauge, Histogram

# Prometheus metrics
utl_audio_capture_chunks_total = Counter(
    "utl_audio_capture_chunks_total",
    "Total number of audio chunks captured",
)
utl_audio_capture_queue_size = Gauge(
    "utl_audio_capture_queue_size",
    "Current number of chunks in the capture queue",
)
utl_audio_capture_latency_seconds = Histogram(
    "utl_audio_capture_latency_seconds",
    "Time to capture one audio chunk",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0),
)

# Constants
DEFAULT_SAMPLE_RATE = 44100
DEFAULT_CHANNELS = 2
CHUNK_DURATION_MS = 500
MAX_QUEUE_SIZE = 64


class AudioCaptureError(Exception):
    """Raised when audio capture encounters an unrecoverable error."""


class AudioCaptureBackend(ABC):
    """Abstract base class for platform-specific audio capture backends."""

    def __init__(
        self,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        channels: int = DEFAULT_CHANNELS,
        chunk_duration_ms: int = CHUNK_DURATION_MS,
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_duration_ms = chunk_duration_ms
        self.chunk_size = int(sample_rate * chunk_duration_ms / 1000)
        self._running = False
        self._queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=MAX_QUEUE_SIZE)
        self._thread: threading.Thread | None = None

    @abstractmethod
    def _open_stream(self) -> None:
        """Open the platform-specific audio stream. Called on capture thread."""

    @abstractmethod
    def _read_chunk(self) -> np.ndarray:
        """Read one chunk from the audio stream.

        Returns:
            numpy array of shape (chunk_size, channels) with float32 samples.
        """

    @abstractmethod
    def _close_stream(self) -> None:
        """Close the platform-specific audio stream."""

    def start(self) -> None:
        """Start audio capture in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop audio capture and release resources."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def get_chunk(self) -> np.ndarray:
        """Get the next 500ms audio chunk.

        Returns:
            numpy array of shape (chunk_size, channels), dtype float32.

        Raises:
            AudioCaptureError: If no chunk is available within timeout.
        """
        try:
            chunk = self._queue.get(timeout=1.0)
            utl_audio_capture_queue_size.set(self._queue.qsize())
            return chunk
        except queue.Empty:
            raise AudioCaptureError("No audio chunk available (timeout)")

    @property
    def is_running(self) -> bool:
        """Whether the capture is currently active."""
        return self._running

    def _capture_loop(self) -> None:
        """Main capture loop running on the background thread."""
        try:
            self._open_stream()
        except Exception as exc:
            self._running = False
            raise AudioCaptureError(f"Failed to open audio stream: {exc}") from exc

        try:
            while self._running:
                start_time = time.perf_counter()
                try:
                    chunk = self._read_chunk()
                except Exception:
                    if self._running:
                        # Brief pause before retry on transient errors
                        time.sleep(0.01)
                    continue

                elapsed = time.perf_counter() - start_time
                utl_audio_capture_latency_seconds.observe(elapsed)

                try:
                    self._queue.put_nowait(chunk)
                    utl_audio_capture_chunks_total.inc()
                    utl_audio_capture_queue_size.set(self._queue.qsize())
                except queue.Full:
                    # Drop oldest chunk to keep pipeline moving
                    try:
                        self._queue.get_nowait()
                    except queue.Empty:
                        pass
                    self._queue.put_nowait(chunk)
                    utl_audio_capture_chunks_total.inc()
        finally:
            self._close_stream()


class WASAPICapture(AudioCaptureBackend):
    """Windows audio capture via WASAPI loopback.

    Uses the pycaw/comtypes COM interface to capture system audio
    output (loopback mode) on Windows.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._stream = None
        self._client = None
        self._capture_client = None

    def _open_stream(self) -> None:
        """Open WASAPI loopback capture via COM."""
        try:
            import comtypes  # noqa: F401
            from pycaw.pycaw import AudioUtilities, IAudioClient, IAudioCaptureClient
            from pycaw.constants import CLSID_MMDeviceEnumerator
            from comtypes import CLSCTX_ALL
            import ctypes
        except ImportError as exc:
            raise AudioCaptureError(
                "WASAPI capture requires 'pycaw' and 'comtypes' packages. "
                "Install with: pip install pycaw comtypes"
            ) from exc

        try:
            # Get default audio render device for loopback
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioClient._iid_, CLSCTX_ALL, None
            )
            self._client = interface.QueryInterface(IAudioClient)

            # Get mix format (native device format)
            mix_format = self._client.GetMixFormat()
            self.sample_rate = mix_format.contents.nSamplesPerSec
            self.channels = mix_format.contents.nChannels
            self.chunk_size = int(self.sample_rate * self.chunk_duration_ms / 1000)

            # Initialize in loopback mode
            # AUDCLNT_STREAMFLAGS_LOOPBACK = 0x00020000
            AUDCLNT_STREAMFLAGS_LOOPBACK = 0x00020000
            buffer_duration = 10_000_000  # 1 second in 100ns units
            self._client.Initialize(
                0,  # AUDCLNT_SHAREMODE_SHARED
                AUDCLNT_STREAMFLAGS_LOOPBACK,
                buffer_duration,
                0,
                mix_format,
                None,
            )

            self._capture_client = self._client.QueryInterface(IAudioCaptureClient)
            self._client.Start()
        except Exception as exc:
            raise AudioCaptureError(f"WASAPI initialization failed: {exc}") from exc

    def _read_chunk(self) -> np.ndarray:
        """Read one 500ms chunk from WASAPI loopback buffer."""
        samples_needed = self.chunk_size * self.channels
        collected = []
        collected_samples = 0

        while collected_samples < samples_needed:
            if not self._running:
                break
            try:
                packet_length = self._capture_client.GetNextPacketSize()
                if packet_length == 0:
                    time.sleep(0.005)
                    continue

                data, num_frames, flags = self._capture_client.GetBuffer()
                if data is not None and num_frames > 0:
                    # Convert raw buffer to numpy array
                    import ctypes

                    buffer_size = num_frames * self.channels
                    arr = np.ctypeslib.as_array(
                        (ctypes.c_float * buffer_size).from_address(data)
                    ).copy()
                    collected.append(arr.reshape(-1, self.channels))
                    collected_samples += num_frames * self.channels
                self._capture_client.ReleaseBuffer(num_frames)
            except Exception:
                time.sleep(0.005)

        if not collected:
            return np.zeros((self.chunk_size, self.channels), dtype=np.float32)

        result = np.concatenate(collected, axis=0)
        # Trim or pad to exact chunk size
        if result.shape[0] >= self.chunk_size:
            return result[: self.chunk_size].astype(np.float32)
        else:
            padded = np.zeros((self.chunk_size, self.channels), dtype=np.float32)
            padded[: result.shape[0]] = result
            return padded

    def _close_stream(self) -> None:
        """Stop and release WASAPI resources."""
        try:
            if self._client is not None:
                self._client.Stop()
        except Exception:
            pass
        self._client = None
        self._capture_client = None


class PulseAudioCapture(AudioCaptureBackend):
    """Linux audio capture via PulseAudio monitor source.

    Captures the output of the default PulseAudio sink by connecting
    to its monitor source, providing system audio loopback.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._pa_instance = None
        self._stream = None

    def _open_stream(self) -> None:
        """Open PulseAudio monitor source stream."""
        try:
            import pulsectl
        except ImportError as exc:
            raise AudioCaptureError(
                "PulseAudio capture requires 'pulsectl' package. "
                "Install with: pip install pulsectl"
            ) from exc

        try:
            self._pa_instance = pulsectl.Pulse("utl-audio-capture")

            # Find the default sink's monitor source
            server_info = self._pa_instance.server_info()
            default_sink_name = server_info.default_sink_name
            monitor_source_name = f"{default_sink_name}.monitor"

            # Verify monitor source exists
            sources = self._pa_instance.source_list()
            monitor_found = any(s.name == monitor_source_name for s in sources)
            if not monitor_found:
                # Fallback: use first available monitor source
                monitors = [s for s in sources if s.name.endswith(".monitor")]
                if not monitors:
                    raise AudioCaptureError("No PulseAudio monitor source found")
                monitor_source_name = monitors[0].name

            self._monitor_source_name = monitor_source_name
        except AudioCaptureError:
            raise
        except Exception as exc:
            raise AudioCaptureError(
                f"PulseAudio initialization failed: {exc}"
            ) from exc

        # Open a parec-style subprocess for raw audio capture
        import subprocess

        self._parec_process = subprocess.Popen(
            [
                "parec",
                "--format=float32le",
                f"--rate={self.sample_rate}",
                f"--channels={self.channels}",
                f"--device={self._monitor_source_name}",
                "--raw",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

    def _read_chunk(self) -> np.ndarray:
        """Read one 500ms chunk from PulseAudio monitor."""
        bytes_per_sample = 4  # float32
        bytes_needed = self.chunk_size * self.channels * bytes_per_sample

        raw_data = b""
        while len(raw_data) < bytes_needed:
            if not self._running:
                break
            remaining = bytes_needed - len(raw_data)
            data = self._parec_process.stdout.read(remaining)
            if not data:
                time.sleep(0.005)
                continue
            raw_data += data

        if len(raw_data) < bytes_needed:
            # Pad with silence if we didn't get enough data
            raw_data += b"\x00" * (bytes_needed - len(raw_data))

        arr = np.frombuffer(raw_data[:bytes_needed], dtype=np.float32)
        return arr.reshape(self.chunk_size, self.channels)

    def _close_stream(self) -> None:
        """Terminate parec subprocess and close PulseAudio connection."""
        if hasattr(self, "_parec_process") and self._parec_process is not None:
            try:
                self._parec_process.terminate()
                self._parec_process.wait(timeout=2.0)
            except Exception:
                try:
                    self._parec_process.kill()
                except Exception:
                    pass
            self._parec_process = None

        if self._pa_instance is not None:
            try:
                self._pa_instance.close()
            except Exception:
                pass
            self._pa_instance = None


class AudioCapture:
    """System audio capture via WASAPI (Windows) / PulseAudio (Linux).

    Auto-detects the current platform and selects the appropriate backend.
    Produces 500ms audio chunks (numpy arrays) for downstream processing.

    Usage:
        capture = AudioCapture()
        capture.start()
        chunk = capture.get_chunk()  # Returns 500ms audio as np.ndarray
        capture.stop()
    """

    def __init__(
        self,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        channels: int = DEFAULT_CHANNELS,
        chunk_duration_ms: int = CHUNK_DURATION_MS,
    ):
        self._backend = self._create_backend(
            sample_rate=sample_rate,
            channels=channels,
            chunk_duration_ms=chunk_duration_ms,
        )

    @staticmethod
    def _create_backend(**kwargs) -> AudioCaptureBackend:
        """Auto-detect platform and create appropriate backend."""
        system = platform.system()
        if system == "Windows":
            return WASAPICapture(**kwargs)
        elif system == "Linux":
            return PulseAudioCapture(**kwargs)
        else:
            raise AudioCaptureError(
                f"Unsupported platform: {system}. "
                "Only Windows (WASAPI) and Linux (PulseAudio) are supported."
            )

    def start(self) -> None:
        """Start capturing system audio."""
        self._backend.start()

    def stop(self) -> None:
        """Stop capturing and release resources."""
        self._backend.stop()

    def get_chunk(self) -> np.ndarray:
        """Returns 500ms audio chunk as numpy array.

        Returns:
            np.ndarray of shape (chunk_size, channels), dtype float32.
            Default: (22050, 2) for 44100 Hz stereo at 500ms.
        """
        return self._backend.get_chunk()

    @property
    def is_running(self) -> bool:
        """Whether audio capture is currently active."""
        return self._backend.is_running

    @property
    def sample_rate(self) -> int:
        """Current sample rate in Hz."""
        return self._backend.sample_rate

    @property
    def channels(self) -> int:
        """Number of audio channels."""
        return self._backend.channels

    @property
    def chunk_size(self) -> int:
        """Number of samples per chunk."""
        return self._backend.chunk_size
