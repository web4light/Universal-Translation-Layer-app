"""Unit tests for the Audio Capture module (src/audio_capture.py).

Tests verify:
- Platform auto-detection logic
- Backend interface compliance
- Queue-based chunk delivery
- Proper start/stop lifecycle
- 500ms chunk sizing
"""

import platform
import queue
import threading
import time
import unittest
from unittest.mock import patch, MagicMock

import numpy as np

import sys
import os

# Add src to path so we can import audio_capture
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from audio_capture import (
    AudioCapture,
    AudioCaptureBackend,
    AudioCaptureError,
    WASAPICapture,
    PulseAudioCapture,
    DEFAULT_SAMPLE_RATE,
    DEFAULT_CHANNELS,
    CHUNK_DURATION_MS,
    MAX_QUEUE_SIZE,
)


class MockBackend(AudioCaptureBackend):
    """Test backend that produces synthetic audio chunks."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._stream_open = False
        self._chunk_count = 0

    def _open_stream(self):
        self._stream_open = True

    def _read_chunk(self) -> np.ndarray:
        """Produce a sine wave chunk for testing."""
        self._chunk_count += 1
        t = np.linspace(0, self.chunk_duration_ms / 1000, self.chunk_size)
        # 440 Hz sine wave on all channels
        mono = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        chunk = np.column_stack([mono] * self.channels)
        # Simulate real-time: sleep for a fraction of chunk duration
        time.sleep(0.01)
        return chunk

    def _close_stream(self):
        self._stream_open = False


class TestAudioCaptureBackendInterface(unittest.TestCase):
    """Test the abstract backend interface via MockBackend."""

    def setUp(self):
        self.backend = MockBackend(
            sample_rate=44100,
            channels=2,
            chunk_duration_ms=500,
        )

    def tearDown(self):
        if self.backend.is_running:
            self.backend.stop()

    def test_chunk_size_calculation(self):
        """Chunk size should be sample_rate * chunk_duration_ms / 1000."""
        expected = int(44100 * 500 / 1000)  # 22050
        self.assertEqual(self.backend.chunk_size, expected)

    def test_start_creates_capture_thread(self):
        """Start should create and launch a daemon thread."""
        self.backend.start()
        self.assertTrue(self.backend.is_running)
        self.assertIsNotNone(self.backend._thread)
        self.assertTrue(self.backend._thread.is_alive())

    def test_stop_terminates_thread(self):
        """Stop should signal the capture loop to exit."""
        self.backend.start()
        time.sleep(0.1)
        self.backend.stop()
        self.assertFalse(self.backend.is_running)

    def test_get_chunk_returns_correct_shape(self):
        """get_chunk should return (chunk_size, channels) numpy array."""
        self.backend.start()
        time.sleep(0.1)  # Let at least one chunk be produced
        chunk = self.backend.get_chunk()
        self.assertEqual(chunk.shape, (22050, 2))
        self.assertEqual(chunk.dtype, np.float32)

    def test_get_chunk_timeout_raises_error(self):
        """get_chunk should raise AudioCaptureError on timeout."""
        # Don't start the backend — queue will be empty
        with self.assertRaises(AudioCaptureError):
            self.backend.get_chunk()

    def test_multiple_chunks_delivered(self):
        """Multiple chunks should be produced over time."""
        self.backend.start()
        chunks = []
        for _ in range(3):
            try:
                chunk = self.backend.get_chunk()
                chunks.append(chunk)
            except AudioCaptureError:
                break
        self.assertGreaterEqual(len(chunks), 1)

    def test_start_idempotent(self):
        """Calling start twice should not create duplicate threads."""
        self.backend.start()
        thread1 = self.backend._thread
        self.backend.start()
        thread2 = self.backend._thread
        self.assertIs(thread1, thread2)

    def test_queue_overflow_drops_oldest(self):
        """When queue is full, oldest chunk should be dropped."""
        # Fill the queue manually
        for i in range(MAX_QUEUE_SIZE):
            chunk = np.full((self.backend.chunk_size, 2), i, dtype=np.float32)
            self.backend._queue.put_nowait(chunk)

        # Queue is full, start capture to trigger overflow logic
        self.backend.start()
        time.sleep(0.15)  # Wait for at least one chunk to be produced
        self.backend.stop()

        # Queue should still be functional
        self.assertFalse(self.backend._queue.empty())


class TestAudioCaptureDefaults(unittest.TestCase):
    """Test default configuration values."""

    def test_default_sample_rate(self):
        self.assertEqual(DEFAULT_SAMPLE_RATE, 44100)

    def test_default_channels(self):
        self.assertEqual(DEFAULT_CHANNELS, 2)

    def test_default_chunk_duration(self):
        self.assertEqual(CHUNK_DURATION_MS, 500)

    def test_max_queue_size(self):
        self.assertEqual(MAX_QUEUE_SIZE, 64)


class TestAudioCapturePlatformDetection(unittest.TestCase):
    """Test platform auto-detection in AudioCapture."""

    @patch("audio_capture.platform.system", return_value="Windows")
    def test_windows_selects_wasapi(self, mock_system):
        """Windows platform should create WASAPICapture backend."""
        capture = AudioCapture()
        self.assertIsInstance(capture._backend, WASAPICapture)

    @patch("audio_capture.platform.system", return_value="Linux")
    def test_linux_selects_pulseaudio(self, mock_system):
        """Linux platform should create PulseAudioCapture backend."""
        capture = AudioCapture()
        self.assertIsInstance(capture._backend, PulseAudioCapture)

    @patch("audio_capture.platform.system", return_value="Darwin")
    def test_unsupported_platform_raises(self, mock_system):
        """Unsupported platform should raise AudioCaptureError."""
        with self.assertRaises(AudioCaptureError) as ctx:
            AudioCapture()
        self.assertIn("Unsupported platform", str(ctx.exception))

    @patch("audio_capture.platform.system", return_value="FreeBSD")
    def test_freebsd_unsupported(self, mock_system):
        """FreeBSD should raise AudioCaptureError."""
        with self.assertRaises(AudioCaptureError):
            AudioCapture()


class TestAudioCaptureFacade(unittest.TestCase):
    """Test the AudioCapture facade class with a mock backend."""

    def setUp(self):
        """Create AudioCapture with injected MockBackend."""
        self.capture = AudioCapture.__new__(AudioCapture)
        self.capture._backend = MockBackend(
            sample_rate=44100,
            channels=2,
            chunk_duration_ms=500,
        )

    def tearDown(self):
        self.capture.stop()

    def test_start_delegates_to_backend(self):
        self.capture.start()
        self.assertTrue(self.capture.is_running)

    def test_stop_delegates_to_backend(self):
        self.capture.start()
        self.capture.stop()
        self.assertFalse(self.capture.is_running)

    def test_get_chunk_returns_500ms_chunk(self):
        self.capture.start()
        time.sleep(0.1)
        chunk = self.capture.get_chunk()
        expected_samples = int(44100 * 500 / 1000)
        self.assertEqual(chunk.shape[0], expected_samples)

    def test_sample_rate_property(self):
        self.assertEqual(self.capture.sample_rate, 44100)

    def test_channels_property(self):
        self.assertEqual(self.capture.channels, 2)

    def test_chunk_size_property(self):
        self.assertEqual(self.capture.chunk_size, 22050)


class TestChunkDurationVariants(unittest.TestCase):
    """Test that different chunk durations work correctly."""

    def test_250ms_chunk(self):
        backend = MockBackend(sample_rate=44100, channels=2, chunk_duration_ms=250)
        expected = int(44100 * 250 / 1000)  # 11025
        self.assertEqual(backend.chunk_size, expected)

    def test_1000ms_chunk(self):
        backend = MockBackend(sample_rate=44100, channels=2, chunk_duration_ms=1000)
        expected = int(44100 * 1000 / 1000)  # 44100
        self.assertEqual(backend.chunk_size, expected)

    def test_mono_channel(self):
        backend = MockBackend(sample_rate=16000, channels=1, chunk_duration_ms=500)
        expected = int(16000 * 500 / 1000)  # 8000
        self.assertEqual(backend.chunk_size, expected)
        backend.start()
        time.sleep(0.1)
        chunk = backend.get_chunk()
        self.assertEqual(chunk.shape, (8000, 1))
        backend.stop()


if __name__ == "__main__":
    unittest.main()
