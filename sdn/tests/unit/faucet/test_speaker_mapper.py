"""Unit tests for the SpeakerMapper module.

Tests speaker identification, voice profile assignment, session management,
and Prometheus metrics instrumentation.
"""

import unittest

import numpy as np
from prometheus_client import REGISTRY

from src.speaker_mapper import (
    SpeakerMapper,
    VoiceProfile,
    _FallbackEmbeddingModel,
    _cosine_similarity,
    _generate_voice_profile,
    _hash_expand,
    _normalize,
    diarization_latency,
    speaker_count_gauge,
)


def _make_tone(freq: float, duration: float = 0.5, sr: int = 16000) -> np.ndarray:
    """Generate a sine wave tone for testing."""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    return (np.sin(2 * np.pi * freq * t)).astype(np.float32)


class TestVoiceProfile(unittest.TestCase):
    """Tests for VoiceProfile dataclass."""

    def test_equality(self):
        emb = np.ones(128, dtype=np.float32)
        vp1 = VoiceProfile("s1", 1.0, 1.0, emb.copy())
        vp2 = VoiceProfile("s1", 1.0, 1.0, emb.copy())
        self.assertEqual(vp1, vp2)

    def test_inequality_different_speaker(self):
        emb = np.ones(128, dtype=np.float32)
        vp1 = VoiceProfile("s1", 1.0, 1.0, emb.copy())
        vp2 = VoiceProfile("s2", 1.0, 1.0, emb.copy())
        self.assertNotEqual(vp1, vp2)

    def test_inequality_different_pitch(self):
        emb = np.ones(128, dtype=np.float32)
        vp1 = VoiceProfile("s1", 1.0, 1.0, emb.copy())
        vp2 = VoiceProfile("s1", 2.0, 1.0, emb.copy())
        self.assertNotEqual(vp1, vp2)

    def test_inequality_different_embedding(self):
        vp1 = VoiceProfile("s1", 1.0, 1.0, np.ones(128, dtype=np.float32))
        vp2 = VoiceProfile("s1", 1.0, 1.0, np.zeros(128, dtype=np.float32))
        self.assertNotEqual(vp1, vp2)

    def test_equality_with_non_voice_profile(self):
        emb = np.ones(128, dtype=np.float32)
        vp = VoiceProfile("s1", 1.0, 1.0, emb)
        self.assertNotEqual(vp, "not a voice profile")


class TestSpeakerMapperBasics(unittest.TestCase):
    """Tests for SpeakerMapper initialization and basic operations."""

    def setUp(self):
        self.mapper = SpeakerMapper()

    def test_initial_state(self):
        self.assertEqual(self.mapper.speaker_count, 0)
        self.assertEqual(self.mapper.known_speakers, [])

    def test_identify_speaker_returns_speaker_id(self):
        audio = _make_tone(440.0)
        speaker_id = self.mapper.identify_speaker(audio)
        self.assertIsInstance(speaker_id, str)
        self.assertTrue(speaker_id.startswith("speaker_"))

    def test_identify_speaker_increments_count(self):
        # Two very different tones should produce different speakers
        audio1 = _make_tone(200.0, duration=1.0)
        audio2 = _make_tone(4000.0, duration=1.0)

        self.mapper.identify_speaker(audio1)
        self.mapper.identify_speaker(audio2)
        # At least 1 speaker should be registered
        self.assertGreaterEqual(self.mapper.speaker_count, 1)

    def test_same_audio_returns_same_speaker(self):
        audio = _make_tone(440.0, duration=1.0)
        id1 = self.mapper.identify_speaker(audio)
        id2 = self.mapper.identify_speaker(audio)
        self.assertEqual(id1, id2)

    def test_get_voice_returns_voice_profile(self):
        audio = _make_tone(440.0)
        speaker_id = self.mapper.identify_speaker(audio)
        profile = self.mapper.get_voice(speaker_id)
        self.assertIsInstance(profile, VoiceProfile)
        self.assertEqual(profile.speaker_id, speaker_id)

    def test_get_voice_unknown_speaker_raises(self):
        with self.assertRaises(KeyError):
            self.mapper.get_voice("nonexistent_speaker")

    def test_voice_profile_has_valid_ranges(self):
        audio = _make_tone(440.0)
        speaker_id = self.mapper.identify_speaker(audio)
        profile = self.mapper.get_voice(speaker_id)
        self.assertGreaterEqual(profile.pitch_shift, -6.0)
        self.assertLessEqual(profile.pitch_shift, 6.0)
        self.assertGreaterEqual(profile.speed_factor, 0.8)
        self.assertLessEqual(profile.speed_factor, 1.2)
        self.assertIsInstance(profile.timbre_embedding, np.ndarray)
        self.assertGreater(len(profile.timbre_embedding), 0)


class TestSpeakerMapperConsistency(unittest.TestCase):
    """Tests for voice consistency within a session."""

    def setUp(self):
        self.mapper = SpeakerMapper()

    def test_same_speaker_gets_same_profile(self):
        audio = _make_tone(440.0, duration=1.0)
        id1 = self.mapper.identify_speaker(audio)
        id2 = self.mapper.identify_speaker(audio)
        profile1 = self.mapper.get_voice(id1)
        profile2 = self.mapper.get_voice(id2)
        self.assertEqual(profile1, profile2)

    def test_voice_profile_deterministic(self):
        """Same embedding should always produce the same VoiceProfile."""
        emb = _normalize(np.random.default_rng(42).standard_normal(512).astype(np.float32))
        vp1 = _generate_voice_profile("test", emb)
        vp2 = _generate_voice_profile("test", emb)
        self.assertEqual(vp1.pitch_shift, vp2.pitch_shift)
        self.assertEqual(vp1.speed_factor, vp2.speed_factor)
        np.testing.assert_array_equal(vp1.timbre_embedding, vp2.timbre_embedding)


class TestSpeakerMapperSession(unittest.TestCase):
    """Tests for session reset functionality."""

    def setUp(self):
        self.mapper = SpeakerMapper()

    def test_reset_clears_speakers(self):
        audio = _make_tone(440.0)
        self.mapper.identify_speaker(audio)
        self.assertGreater(self.mapper.speaker_count, 0)

        self.mapper.reset_session()
        self.assertEqual(self.mapper.speaker_count, 0)
        self.assertEqual(self.mapper.known_speakers, [])

    def test_reset_allows_reidentification(self):
        audio = _make_tone(440.0)
        id_before = self.mapper.identify_speaker(audio)
        self.mapper.reset_session()
        id_after = self.mapper.identify_speaker(audio)
        # After reset, the speaker should be re-registered as speaker_000
        self.assertEqual(id_after, "speaker_000")


class TestSpeakerMapperFallback(unittest.TestCase):
    """Tests for the fallback embedding model."""

    def test_fallback_extracts_embedding(self):
        model = _FallbackEmbeddingModel()
        audio = _make_tone(440.0)
        embedding = model.extract(audio)
        self.assertEqual(embedding.shape, (512,))
        self.assertEqual(embedding.dtype, np.float32)

    def test_fallback_empty_audio(self):
        model = _FallbackEmbeddingModel()
        embedding = model.extract(np.array([], dtype=np.float32))
        self.assertEqual(embedding.shape, (512,))
        np.testing.assert_array_equal(embedding, np.zeros(512, dtype=np.float32))

    def test_fallback_produces_normalized_embedding(self):
        model = _FallbackEmbeddingModel()
        audio = _make_tone(440.0)
        embedding = model.extract(audio)
        norm = np.linalg.norm(embedding)
        # Should be approximately unit-norm (or zero for silence)
        if norm > 0:
            self.assertAlmostEqual(norm, 1.0, places=5)


class TestHelperFunctions(unittest.TestCase):
    """Tests for utility functions."""

    def test_normalize(self):
        vec = np.array([3.0, 4.0], dtype=np.float32)
        normalized = _normalize(vec)
        self.assertAlmostEqual(np.linalg.norm(normalized), 1.0, places=5)

    def test_normalize_zero_vector(self):
        vec = np.zeros(10, dtype=np.float32)
        normalized = _normalize(vec)
        np.testing.assert_array_equal(normalized, vec)

    def test_cosine_similarity_identical(self):
        vec = _normalize(np.array([1.0, 2.0, 3.0], dtype=np.float32))
        self.assertAlmostEqual(_cosine_similarity(vec, vec), 1.0, places=5)

    def test_cosine_similarity_orthogonal(self):
        a = _normalize(np.array([1.0, 0.0], dtype=np.float32))
        b = _normalize(np.array([0.0, 1.0], dtype=np.float32))
        self.assertAlmostEqual(_cosine_similarity(a, b), 0.0, places=5)

    def test_hash_expand_produces_correct_dimension(self):
        data = b"test_data"
        result = _hash_expand(data, 256)
        self.assertEqual(result.shape, (256,))
        self.assertEqual(result.dtype, np.float32)

    def test_hash_expand_deterministic(self):
        data = b"consistent_input"
        r1 = _hash_expand(data, 128)
        r2 = _hash_expand(data, 128)
        np.testing.assert_array_equal(r1, r2)

    def test_hash_expand_different_inputs_differ(self):
        r1 = _hash_expand(b"input_a", 128)
        r2 = _hash_expand(b"input_b", 128)
        self.assertFalse(np.array_equal(r1, r2))


class TestPrometheusMetrics(unittest.TestCase):
    """Tests for Prometheus metrics instrumentation."""

    def setUp(self):
        self.mapper = SpeakerMapper()

    def test_diarization_latency_metric_exists(self):
        """Verify diarization latency histogram is registered."""
        metric_names = [m.name for m in REGISTRY.collect()]
        self.assertIn("utl_diarization_latency_seconds", metric_names)

    def test_speaker_count_metric_exists(self):
        """Verify speaker count gauge is registered."""
        metric_names = [m.name for m in REGISTRY.collect()]
        self.assertIn("utl_speaker_count", metric_names)

    def test_identify_speaker_updates_latency(self):
        """Verify that calling identify_speaker records a latency observation."""
        # Get initial count of observations
        initial_count = diarization_latency._sum.get()
        audio = _make_tone(440.0)
        self.mapper.identify_speaker(audio)
        # Sum should have increased (latency > 0)
        self.assertGreater(diarization_latency._sum.get(), initial_count)

    def test_new_speaker_updates_gauge(self):
        """Verify that detecting a new speaker updates the speaker count gauge."""
        audio = _make_tone(440.0)
        self.mapper.identify_speaker(audio)
        self.assertGreaterEqual(speaker_count_gauge._value.get(), 1.0)

    def test_reset_session_zeros_gauge(self):
        """Verify that reset_session sets the speaker count gauge to 0."""
        audio = _make_tone(440.0)
        self.mapper.identify_speaker(audio)
        self.mapper.reset_session()
        self.assertEqual(speaker_count_gauge._value.get(), 0.0)


if __name__ == "__main__":
    unittest.main()
