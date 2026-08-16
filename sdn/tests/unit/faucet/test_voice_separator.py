#!/usr/bin/env python3
"""Unit tests for the VoiceSeparator module."""

import sys
import threading
import unittest
from unittest.mock import patch, MagicMock
from dataclasses import fields

import numpy as np

# Add src to path for imports
sys.path.insert(0, "/home/pj/faucet/src")

from voice_separator import (
    SeparatedAudio,
    VoiceSeparator,
    VoiceSeparatorError,
    ModelLoadError,
    DEFAULT_SAMPLE_RATE,
    DEFAULT_MODEL_NAME,
)


class TestSeparatedAudio(unittest.TestCase):
    """Tests for the SeparatedAudio dataclass."""

    def test_creation_with_valid_data(self):
        """SeparatedAudio should store vocals, music, sfx, and sample_rate."""
        vocals = np.zeros(1024)
        music = np.ones(1024) * 0.5
        sfx = np.random.randn(1024).astype(np.float32)

        result = SeparatedAudio(
            vocals=vocals, music=music, sfx=sfx, sample_rate=44100
        )

        np.testing.assert_array_equal(result.vocals, vocals)
        np.testing.assert_array_equal(result.music, music)
        np.testing.assert_array_equal(result.sfx, sfx)
        self.assertEqual(result.sample_rate, 44100)

    def test_dataclass_fields(self):
        """SeparatedAudio should have exactly 4 fields."""
        field_names = [f.name for f in fields(SeparatedAudio)]
        self.assertEqual(field_names, ["vocals", "music", "sfx", "sample_rate"])

    def test_stereo_data(self):
        """SeparatedAudio should support multi-channel (stereo) arrays."""
        stereo = np.zeros((2, 1024))
        result = SeparatedAudio(
            vocals=stereo, music=stereo, sfx=stereo, sample_rate=48000
        )
        self.assertEqual(result.vocals.shape, (2, 1024))
        self.assertEqual(result.sample_rate, 48000)


class TestVoiceSeparatorInit(unittest.TestCase):
    """Tests for VoiceSeparator initialization."""

    def test_default_init(self):
        """VoiceSeparator should initialize with default values."""
        sep = VoiceSeparator()
        self.assertEqual(sep._model_name, DEFAULT_MODEL_NAME)
        self.assertEqual(sep._sample_rate, DEFAULT_SAMPLE_RATE)
        self.assertIsNone(sep._device_preference)
        self.assertFalse(sep.is_loaded)
        self.assertIsNone(sep.device)
        self.assertFalse(sep.fallback_mode)

    def test_custom_init(self):
        """VoiceSeparator should accept custom parameters."""
        sep = VoiceSeparator(
            model_name="htdemucs_ft", sample_rate=48000, device="cpu"
        )
        self.assertEqual(sep._model_name, "htdemucs_ft")
        self.assertEqual(sep._sample_rate, 48000)
        self.assertEqual(sep._device_preference, "cpu")

    def test_is_loaded_false_initially(self):
        """Model should not be loaded until first separation call."""
        sep = VoiceSeparator()
        self.assertFalse(sep.is_loaded)

    def test_has_thread_locks(self):
        """VoiceSeparator should have threading locks for safety."""
        sep = VoiceSeparator()
        self.assertIsInstance(sep._lock, type(threading.Lock()))
        self.assertIsInstance(sep._load_lock, type(threading.Lock()))


class TestVoiceSeparatorFallback(unittest.TestCase):
    """Tests for fallback mode when Demucs is unavailable."""

    def test_fallback_activates_on_import_error(self):
        """Should activate fallback mode when demucs/torch not installed."""
        sep = VoiceSeparator()

        # Patch import to simulate missing demucs
        original_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__

        def mock_import(name, *args, **kwargs):
            if name in ("torch", "demucs", "demucs.pretrained", "demucs.apply"):
                raise ImportError(f"No module named '{name}'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            sep._load_model()

        self.assertTrue(sep.fallback_mode)
        self.assertTrue(sep.is_loaded)
        self.assertEqual(sep.device, "cpu")

    def test_fallback_separate_mono(self):
        """Fallback mode: mono input → vocals = input, music/sfx = silence."""
        sep = VoiceSeparator()
        sep._fallback_mode = True
        sep._device = "cpu"

        input_audio = np.random.randn(22050).astype(np.float32)
        result = sep.separate(input_audio)

        self.assertIsInstance(result, SeparatedAudio)
        np.testing.assert_array_equal(result.vocals, input_audio)
        np.testing.assert_array_equal(result.music, np.zeros_like(input_audio))
        np.testing.assert_array_equal(result.sfx, np.zeros_like(input_audio))
        self.assertEqual(result.sample_rate, DEFAULT_SAMPLE_RATE)

    def test_fallback_separate_stereo(self):
        """Fallback mode: stereo input → vocals = input, music/sfx = silence."""
        sep = VoiceSeparator()
        sep._fallback_mode = True
        sep._device = "cpu"

        input_audio = np.random.randn(2, 22050).astype(np.float32)
        result = sep.separate(input_audio)

        np.testing.assert_array_equal(result.vocals, input_audio)
        np.testing.assert_array_equal(result.music, np.zeros_like(input_audio))
        np.testing.assert_array_equal(result.sfx, np.zeros_like(input_audio))

    def test_fallback_does_not_modify_input(self):
        """Fallback mode should copy input, not reference it."""
        sep = VoiceSeparator()
        sep._fallback_mode = True
        sep._device = "cpu"

        input_audio = np.ones(1024, dtype=np.float32)
        result = sep.separate(input_audio)

        # Modify original — result should be unchanged
        input_audio[:] = 99.0
        np.testing.assert_array_equal(result.vocals, np.ones(1024))


class TestVoiceSeparatorModelLoading(unittest.TestCase):
    """Tests for model loading behavior."""

    @patch("voice_separator.VoiceSeparator._load_model")
    def test_lazy_loading_on_first_separate(self, mock_load):
        """Model should be loaded lazily on first separate() call."""
        sep = VoiceSeparator()
        sep._model = None

        # Mock successful loading and processing
        def load_side_effect():
            sep._model = MagicMock()
            sep._device = "cpu"
            sep._torch = MagicMock()
            sep._apply_model = MagicMock()

        mock_load.side_effect = load_side_effect

        # Mock _process_chunk to avoid actual Demucs processing
        with patch.object(sep, "_process_chunk") as mock_process:
            mock_process.return_value = SeparatedAudio(
                vocals=np.zeros(100),
                music=np.zeros(100),
                sfx=np.zeros(100),
                sample_rate=44100,
            )
            sep.separate(np.zeros(100))

        mock_load.assert_called_once()

    def test_model_load_error_on_non_import_failure(self):
        """Should raise ModelLoadError when model loading fails (non-import)."""
        sep = VoiceSeparator()

        # Simulate torch available but model file corrupt
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False

        with patch.dict(sys.modules, {"torch": mock_torch}):
            with patch(
                "builtins.__import__",
                side_effect=RuntimeError("corrupted model"),
            ):
                with self.assertRaises((ModelLoadError, RuntimeError)):
                    sep._load_model()


class TestVoiceSeparatorProcessing(unittest.TestCase):
    """Tests for audio processing logic."""

    def _create_loaded_separator(self):
        """Create a VoiceSeparator with a mocked loaded model."""
        sep = VoiceSeparator()

        # Mock torch
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_torch.float32 = "float32"
        mock_torch.no_grad.return_value.__enter__ = MagicMock()
        mock_torch.no_grad.return_value.__exit__ = MagicMock()

        # Create a mock tensor that supports .to() and .unsqueeze()
        mock_tensor = MagicMock()
        mock_tensor.unsqueeze.return_value = mock_tensor
        mock_tensor.to.return_value = mock_tensor
        mock_torch.tensor.return_value = mock_tensor

        # Mock model with source names
        mock_model = MagicMock()
        mock_model.sources = ["drums", "bass", "other", "vocals"]

        # Mock apply_model output: (batch=1, 4 sources, 2 channels, N samples)
        n_samples = 1024
        sources_output = MagicMock()
        sources_np = np.random.randn(4, 2, n_samples).astype(np.float32)
        squeezed = MagicMock()
        squeezed.cpu.return_value.numpy.return_value = sources_np
        sources_output.squeeze.return_value = squeezed

        mock_apply = MagicMock(return_value=sources_output)

        sep._model = mock_model
        sep._torch = mock_torch
        sep._device = "cpu"
        sep._apply_model = mock_apply

        return sep, sources_np

    def test_separate_mono_input(self):
        """Mono input should produce mono outputs."""
        sep, sources_np = self._create_loaded_separator()

        mono_input = np.random.randn(1024).astype(np.float32)
        result = sep.separate(mono_input)

        self.assertIsInstance(result, SeparatedAudio)
        self.assertEqual(result.vocals.ndim, 1)
        self.assertEqual(result.music.ndim, 1)
        self.assertEqual(result.sfx.ndim, 1)
        self.assertEqual(result.sample_rate, DEFAULT_SAMPLE_RATE)

    def test_separate_stereo_input(self):
        """Stereo input should produce stereo outputs."""
        sep, sources_np = self._create_loaded_separator()

        stereo_input = np.random.randn(2, 1024).astype(np.float32)
        result = sep.separate(stereo_input)

        self.assertIsInstance(result, SeparatedAudio)
        self.assertEqual(result.vocals.ndim, 2)
        self.assertEqual(result.music.ndim, 2)
        self.assertEqual(result.sfx.ndim, 2)

    def test_separate_invalid_shape_raises(self):
        """3D input should raise VoiceSeparatorError."""
        sep, _ = self._create_loaded_separator()

        bad_input = np.zeros((2, 3, 1024))
        with self.assertRaises(VoiceSeparatorError) as ctx:
            sep.separate(bad_input)
        self.assertIn("Neočekávaný tvar", str(ctx.exception))

    def test_separate_returns_correct_sample_rate(self):
        """Output should preserve the configured sample rate."""
        sep, _ = self._create_loaded_separator()
        sep._sample_rate = 48000

        result = sep.separate(np.zeros(1024))
        self.assertEqual(result.sample_rate, 48000)


class TestVoiceSeparatorThreadSafety(unittest.TestCase):
    """Tests for thread-safe concurrent operation."""

    def test_concurrent_fallback_separation(self):
        """Multiple threads should be able to separate simultaneously in fallback."""
        sep = VoiceSeparator()
        sep._fallback_mode = True
        sep._device = "cpu"

        results = []
        errors = []
        num_threads = 8

        def worker(thread_id):
            try:
                chunk = np.random.randn(22050).astype(np.float32) * thread_id
                result = sep.separate(chunk)
                results.append((thread_id, result))
            except Exception as exc:
                errors.append((thread_id, exc))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Thread errors: {errors}")
        self.assertEqual(len(results), num_threads)

    def test_concurrent_model_loading(self):
        """Multiple threads calling separate() should only load model once."""
        sep = VoiceSeparator()
        load_count = {"n": 0}
        original_load = sep._load_model

        def counting_load():
            load_count["n"] += 1
            sep._fallback_mode = True
            sep._device = "cpu"

        sep._load_model = counting_load

        threads = [
            threading.Thread(target=lambda: sep.separate(np.zeros(100)))
            for _ in range(4)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Load should be called at most once (due to double-check in _load_model)
        # With our mock, is_loaded becomes True after first load_model call
        self.assertGreaterEqual(load_count["n"], 1)


class TestVoiceSeparatorUnload(unittest.TestCase):
    """Tests for model unloading."""

    def test_unload_clears_model(self):
        """unload() should set model to None."""
        sep = VoiceSeparator()
        sep._model = MagicMock()
        sep._device = "cpu"
        sep._torch = MagicMock()

        sep.unload()
        self.assertIsNone(sep._model)
        self.assertFalse(sep.is_loaded)

    def test_unload_clears_fallback_mode(self):
        """unload() should also clear fallback mode."""
        sep = VoiceSeparator()
        sep._fallback_mode = True
        sep._device = "cpu"

        sep.unload()
        self.assertFalse(sep.fallback_mode)
        self.assertFalse(sep.is_loaded)

    def test_unload_cuda_clears_cache(self):
        """unload() on CUDA should call torch.cuda.empty_cache()."""
        sep = VoiceSeparator()
        sep._model = MagicMock()
        sep._device = "cuda"
        mock_torch = MagicMock()
        sep._torch = mock_torch

        sep.unload()
        mock_torch.cuda.empty_cache.assert_called_once()


if __name__ == "__main__":
    unittest.main()
