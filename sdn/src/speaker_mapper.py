"""Speaker Mapper module for Universal Translation Layer.

Identifies speakers in audio streams using pyannote.audio embeddings
and assigns consistent synthetic voice profiles per session.

Requirements: 3.6
"""

from __future__ import annotations

import hashlib
import logging
import struct
import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from prometheus_client import Gauge, Histogram

logger = logging.getLogger(__name__)

# ============================================================================
# PROMETHEUS METRIKY
# ============================================================================

diarization_latency = Histogram(
    "utl_diarization_latency_seconds",
    "Latency of speaker identification (embedding extraction + matching)",
    buckets=[0.01, 0.025, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0],
)

speaker_count_gauge = Gauge(
    "utl_speaker_count",
    "Number of distinct speakers detected in the current session",
)

# Type alias for speaker identification
SpeakerID = str

# Cosine similarity threshold for matching speakers
_SIMILARITY_THRESHOLD = 0.75

# Embedding dimension for pyannote speaker embeddings
_EMBEDDING_DIM = 512


@dataclass
class VoiceProfile:
    """Synthetic voice profile assigned to a detected speaker.

    Attributes:
        speaker_id: Unique identifier for this speaker within the session.
        pitch_shift: Pitch modification in semitones (-12.0 to +12.0).
        speed_factor: Speech rate multiplier (0.5 to 2.0).
        timbre_embedding: Embedding vector characterizing voice timbre.
    """

    speaker_id: SpeakerID
    pitch_shift: float
    speed_factor: float
    timbre_embedding: np.ndarray = field(repr=False)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VoiceProfile):
            return NotImplemented
        return (
            self.speaker_id == other.speaker_id
            and self.pitch_shift == other.pitch_shift
            and self.speed_factor == other.speed_factor
            and np.array_equal(self.timbre_embedding, other.timbre_embedding)
        )


class SpeakerMapper:
    """Identifies speakers and assigns consistent synthetic voices.

    Uses pyannote.audio for speaker embedding extraction and maintains
    a session-local mapping of speaker embeddings to SpeakerIDs.
    Each detected speaker receives a deterministic VoiceProfile that
    remains consistent throughout the session.
    """

    def __init__(self, similarity_threshold: float = _SIMILARITY_THRESHOLD) -> None:
        """Initialize SpeakerMapper.

        Args:
            similarity_threshold: Cosine similarity threshold for matching
                a new embedding to an existing speaker. Values above this
                threshold are considered the same speaker.
        """
        self._similarity_threshold = similarity_threshold
        self._model: Optional[object] = None
        self._speaker_embeddings: dict[SpeakerID, np.ndarray] = {}
        self._voice_profiles: dict[SpeakerID, VoiceProfile] = {}
        self._next_speaker_idx: int = 0

    def _load_model(self) -> None:
        """Lazy-load the pyannote.audio embedding model.

        Falls back gracefully between GPU and CPU.
        """
        if self._model is not None:
            return

        try:
            import torch
            from pyannote.audio import Inference

            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info("Loading pyannote speaker embedding model on %s", device)

            self._model = Inference(
                "pyannote/embedding",
                window="whole",
                device=torch.device(device),
            )
            logger.info("Speaker embedding model loaded successfully on %s", device)
        except ImportError as exc:
            logger.warning(
                "pyannote.audio or torch not available, using fallback embedding: %s",
                exc,
            )
            self._model = _FallbackEmbeddingModel()
        except Exception as exc:  # pylint: disable=broad-except
            logger.error(
                "Failed to load pyannote model, using fallback: %s", exc
            )
            self._model = _FallbackEmbeddingModel()

    def _extract_embedding(self, audio_segment: np.ndarray) -> np.ndarray:
        """Extract speaker embedding from audio segment.

        Args:
            audio_segment: Audio data as numpy array (mono, float32).

        Returns:
            Speaker embedding vector.
        """
        self._load_model()

        if isinstance(self._model, _FallbackEmbeddingModel):
            return self._model.extract(audio_segment)

        try:
            # pyannote Inference expects dict with 'waveform' and 'sample_rate'
            import torch

            waveform = torch.tensor(audio_segment, dtype=torch.float32)
            if waveform.ndim == 1:
                waveform = waveform.unsqueeze(0)

            embedding = self._model(
                {"waveform": waveform, "sample_rate": 16000}
            )
            return np.array(embedding, dtype=np.float32)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Embedding extraction failed, using fallback: %s", exc)
            fallback = _FallbackEmbeddingModel()
            return fallback.extract(audio_segment)

    def identify_speaker(self, audio_segment: np.ndarray) -> SpeakerID:
        """Identify the speaker in the given audio segment.

        Compares the extracted embedding against all known speakers in
        the session. If a match is found above the similarity threshold,
        returns the existing SpeakerID. Otherwise assigns a new speaker.

        Args:
            audio_segment: Audio data as numpy array (mono, float32).

        Returns:
            SpeakerID identifying the detected speaker.
        """
        start_time = time.perf_counter()

        embedding = self._extract_embedding(audio_segment)
        embedding_normalized = _normalize(embedding)

        # Compare against existing speaker embeddings
        best_match_id: Optional[SpeakerID] = None
        best_similarity: float = -1.0

        for speaker_id, stored_embedding in self._speaker_embeddings.items():
            similarity = _cosine_similarity(embedding_normalized, stored_embedding)
            if similarity > best_similarity:
                best_similarity = similarity
                best_match_id = speaker_id

        if best_match_id is not None and best_similarity >= self._similarity_threshold:
            logger.debug(
                "Matched speaker %s with similarity %.3f",
                best_match_id,
                best_similarity,
            )
            elapsed = time.perf_counter() - start_time
            diarization_latency.observe(elapsed)
            return best_match_id

        # No match found — register new speaker
        new_id = self._register_new_speaker(embedding_normalized)
        logger.info(
            "Registered new speaker %s (best existing similarity: %.3f)",
            new_id,
            best_similarity,
        )

        elapsed = time.perf_counter() - start_time
        diarization_latency.observe(elapsed)
        speaker_count_gauge.set(self.speaker_count)
        return new_id

    def _register_new_speaker(self, embedding: np.ndarray) -> SpeakerID:
        """Register a new speaker with their embedding.

        Args:
            embedding: Normalized speaker embedding vector.

        Returns:
            Newly assigned SpeakerID.
        """
        speaker_id = f"speaker_{self._next_speaker_idx:03d}"
        self._next_speaker_idx += 1

        self._speaker_embeddings[speaker_id] = embedding
        self._voice_profiles[speaker_id] = _generate_voice_profile(
            speaker_id, embedding
        )
        return speaker_id

    def get_voice(self, speaker_id: SpeakerID) -> VoiceProfile:
        """Get the voice profile for a known speaker.

        Args:
            speaker_id: The SpeakerID returned by identify_speaker.

        Returns:
            VoiceProfile assigned to this speaker.

        Raises:
            KeyError: If speaker_id is not found in the current session.
        """
        if speaker_id not in self._voice_profiles:
            raise KeyError(
                f"Speaker '{speaker_id}' not found in current session. "
                f"Known speakers: {list(self._voice_profiles.keys())}"
            )
        return self._voice_profiles[speaker_id]

    def reset_session(self) -> None:
        """Clear all speaker mappings for a new session.

        Removes all stored embeddings and voice profiles, resetting
        the mapper to a clean state.
        """
        self._speaker_embeddings.clear()
        self._voice_profiles.clear()
        self._next_speaker_idx = 0
        speaker_count_gauge.set(0)
        logger.info("Speaker mapper session reset")

    @property
    def known_speakers(self) -> list[SpeakerID]:
        """Return list of all known speaker IDs in the current session."""
        return list(self._speaker_embeddings.keys())

    @property
    def speaker_count(self) -> int:
        """Return number of speakers detected in the current session."""
        return len(self._speaker_embeddings)


class _FallbackEmbeddingModel:
    """Fallback embedding model when pyannote.audio is unavailable.

    Uses simple audio features (energy, zero-crossing rate, spectral centroid)
    to produce a basic embedding for speaker discrimination. Not as accurate
    as pyannote but allows the pipeline to function without GPU/model.
    """

    def extract(self, audio_segment: np.ndarray) -> np.ndarray:
        """Extract a basic embedding from audio features.

        Args:
            audio_segment: Audio data as numpy array.

        Returns:
            Embedding vector of dimension _EMBEDDING_DIM.
        """
        if audio_segment.size == 0:
            return np.zeros(_EMBEDDING_DIM, dtype=np.float32)

        audio = audio_segment.astype(np.float32).flatten()

        # Compute basic audio features
        rms_energy = float(np.sqrt(np.mean(audio**2)))
        zero_crossings = float(
            np.sum(np.abs(np.diff(np.sign(audio)))) / (2 * len(audio))
        )

        # Spectral features via FFT
        fft_vals = np.abs(np.fft.rfft(audio))
        if fft_vals.sum() > 0:
            freqs = np.fft.rfftfreq(len(audio))
            spectral_centroid = float(np.sum(freqs * fft_vals) / np.sum(fft_vals))
            spectral_spread = float(
                np.sqrt(
                    np.sum(((freqs - spectral_centroid) ** 2) * fft_vals)
                    / np.sum(fft_vals)
                )
            )
        else:
            spectral_centroid = 0.0
            spectral_spread = 0.0

        # Build a deterministic embedding from features using hash expansion
        feature_bytes = struct.pack(
            "ffff", rms_energy, zero_crossings, spectral_centroid, spectral_spread
        )
        embedding = _hash_expand(feature_bytes, _EMBEDDING_DIM)
        return embedding


def _normalize(vec: np.ndarray) -> np.ndarray:
    """L2-normalize a vector."""
    norm = np.linalg.norm(vec)
    if norm < 1e-10:
        return vec
    return vec / norm


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two normalized vectors."""
    return float(np.dot(a, b))


def _hash_expand(data: bytes, dim: int) -> np.ndarray:
    """Expand bytes into a fixed-dimension vector using iterative hashing.

    Args:
        data: Input bytes to expand.
        dim: Target dimensionality.

    Returns:
        Float32 numpy array of the given dimension, L2-normalized.
    """
    result = np.zeros(dim, dtype=np.float32)
    idx = 0
    counter = 0
    while idx < dim:
        hash_input = data + struct.pack("I", counter)
        digest = hashlib.sha256(hash_input).digest()
        # Each SHA-256 digest gives 32 bytes; interpret as unsigned ints
        # and map to [-1, 1] range for stable float values
        for i in range(0, 32, 4):
            if idx >= dim:
                break
            # Interpret 4 bytes as uint32 and normalize to [-1, 1]
            uint_val = struct.unpack("I", digest[i : i + 4])[0]
            result[idx] = (uint_val / 2147483647.5) - 1.0
            idx += 1
        counter += 1
    return _normalize(result)


def _generate_voice_profile(
    speaker_id: SpeakerID, embedding: np.ndarray
) -> VoiceProfile:
    """Generate a deterministic VoiceProfile from a speaker embedding.

    The profile parameters are derived from the embedding so that
    the same speaker always gets the same voice characteristics.

    Args:
        speaker_id: Identifier for this speaker.
        embedding: Normalized speaker embedding vector.

    Returns:
        Deterministic VoiceProfile for TTS synthesis.
    """
    # Use embedding values to derive pitch and speed deterministically
    # Map first few embedding dimensions to voice parameters
    # pitch_shift: range [-6.0, +6.0] semitones
    pitch_shift = float(np.clip(embedding[0] * 6.0, -6.0, 6.0))

    # speed_factor: range [0.8, 1.2]
    speed_factor = float(np.clip(0.8 + embedding[1] * 0.4, 0.8, 1.2))

    # timbre_embedding: use a slice of the speaker embedding
    timbre_embedding = embedding[:128].copy() if len(embedding) >= 128 else embedding.copy()

    return VoiceProfile(
        speaker_id=speaker_id,
        pitch_shift=pitch_shift,
        speed_factor=speed_factor,
        timbre_embedding=timbre_embedding,
    )
