#!/usr/bin/env python3
"""
Speaker Mapper — Speaker Diarization and Voice Profile Assignment
UTL Stream Dubbing Pipeline Stage 3

Detects individual speakers in audio and assigns each a consistent
synthetic voice throughout a session. Speaker A always sounds like
Voice 1, Speaker B like Voice 2, etc.

Requirements: 3.6
Author: Pan Jeskyne
"""

import time
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List
from prometheus_client import Counter, Histogram

# === PROMETHEUS METRICS ===

utl_speakers_detected_total = Counter(
    'utl_speakers_detected_total',
    'Total unique speakers detected across all sessions'
)
utl_speaker_mapping_latency_seconds = Histogram(
    'utl_speaker_mapping_latency_seconds',
    'Speaker identification and mapping latency',
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0]
)

# === DATA MODELS ===


@dataclass(eq=False)
class VoiceProfile:
    """Voice characteristics for a detected speaker."""
    speaker_id: str
    pitch_shift: float        # semitones (-12 to +12)
    speed_factor: float       # 0.5 to 2.0
    timbre_embedding: np.ndarray = field(default_factory=lambda: np.zeros(192))
    voice_name: str = ""      # human-readable name (e.g. "Voice-3-Male")

    def __eq__(self, other) -> bool:
        """Custom equality that handles numpy array comparison."""
        if not isinstance(other, VoiceProfile):
            return NotImplemented
        return (
            self.speaker_id == other.speaker_id
            and self.pitch_shift == other.pitch_shift
            and self.speed_factor == other.speed_factor
            and self.voice_name == other.voice_name
            and np.array_equal(self.timbre_embedding, other.timbre_embedding)
        )

    def __hash__(self):
        """Hash based on immutable fields (for use in sets/dicts if needed)."""
        return hash((self.speaker_id, self.pitch_shift, self.speed_factor, self.voice_name))


@dataclass
class SpeakerSegment:
    """A segment of audio attributed to a specific speaker."""
    speaker_id: str
    start_ms: int
    end_ms: int
    audio: np.ndarray
    confidence: float = 0.0


# === PRE-DEFINED VOICE POOL ===

# Diverse set of synthetic voice profiles for assignment
VOICE_POOL: List[dict] = [
    {"name": "Voice-1-Male-Deep", "pitch": -4.0, "speed": 0.95},
    {"name": "Voice-2-Female-High", "pitch": 5.0, "speed": 1.05},
    {"name": "Voice-3-Male-Normal", "pitch": 0.0, "speed": 1.0},
    {"name": "Voice-4-Female-Normal", "pitch": 2.0, "speed": 1.0},
    {"name": "Voice-5-Male-High", "pitch": 3.0, "speed": 1.1},
    {"name": "Voice-6-Female-Deep", "pitch": -2.0, "speed": 0.9},
    {"name": "Voice-7-Male-Fast", "pitch": -1.0, "speed": 1.2},
    {"name": "Voice-8-Female-Slow", "pitch": 4.0, "speed": 0.85},
    {"name": "Voice-9-Neutral", "pitch": 0.0, "speed": 1.0},
    {"name": "Voice-10-Child", "pitch": 8.0, "speed": 1.15},
]


# === SPEAKER MAPPER ===

class SpeakerMapper:
    """
    Maps detected speakers to consistent voice profiles.

    Uses pyannote.audio for speaker diarization when available.
    Falls back to energy-based VAD + simple clustering when not.

    Guarantees: same speaker_id -> same VoiceProfile within session
    (idempotent mapping: speaker_id → voice_profile is stable).
    """

    def __init__(self, sample_rate: int = 16000):
        """
        Initialize Speaker Mapper.

        Args:
            sample_rate: Audio sample rate (default 16kHz)
        """
        self.sample_rate = sample_rate
        self._speaker_profiles: Dict[str, VoiceProfile] = {}
        self._next_voice_idx = 0
        self._diarizer = None
        self._available = False

        self._load_diarizer()

    def _load_diarizer(self):
        """Load pyannote.audio speaker diarization model."""
        try:
            from pyannote.audio import Pipeline as PyannotePipeline

            self._diarizer = PyannotePipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1"
            )
            self._available = True
            print("[SPEAKER_MAP] pyannote.audio diarization model loaded")

        except ImportError:
            print("[SPEAKER_MAP] pyannote.audio not installed — simple mode")
            print("[SPEAKER_MAP] Install: pip install pyannote.audio")
        except Exception as e:
            print(f"[SPEAKER_MAP] Diarization model error: {e} — simple mode")

    def identify_speakers(self, audio: np.ndarray) -> List[SpeakerSegment]:
        """
        Detect and identify speakers in audio segment.

        Args:
            audio: Float32 numpy array of audio samples

        Returns:
            List of SpeakerSegment with speaker attribution
        """
        start_time = time.time()

        if self._available and self._diarizer is not None:
            segments = self._identify_pyannote(audio)
        else:
            segments = self._identify_simple(audio)

        latency = time.time() - start_time
        utl_speaker_mapping_latency_seconds.observe(latency)

        return segments

    def _identify_pyannote(self, audio: np.ndarray) -> List[SpeakerSegment]:
        """Speaker identification using pyannote.audio."""
        try:
            import torch
            import torchaudio  # noqa: F401 — required by pyannote

            # Create in-memory audio tensor
            waveform = torch.tensor(audio, dtype=torch.float32).unsqueeze(0)

            # Run diarization
            diarization = self._diarizer(
                {"waveform": waveform, "sample_rate": self.sample_rate}
            )

            segments = []
            for turn, _, speaker_label in diarization.itertracks(yield_label=True):
                start_sample = int(turn.start * self.sample_rate)
                end_sample = int(turn.end * self.sample_rate)

                # Ensure we have a profile for this speaker
                speaker_id = f"speaker_{speaker_label}"
                if speaker_id not in self._speaker_profiles:
                    self._assign_voice(speaker_id)

                segment_audio = audio[start_sample:end_sample]
                segments.append(SpeakerSegment(
                    speaker_id=speaker_id,
                    start_ms=int(turn.start * 1000),
                    end_ms=int(turn.end * 1000),
                    audio=segment_audio,
                    confidence=0.9
                ))

            return segments

        except Exception as e:
            print(f"[SPEAKER_MAP] pyannote error: {e} — falling back to simple")
            return self._identify_simple(audio)

    def _identify_simple(self, audio: np.ndarray) -> List[SpeakerSegment]:
        """
        Simple speaker identification based on energy + embedding hash.

        When pyannote is not available, treat the entire chunk as
        one speaker. Use energy profile to generate a pseudo speaker ID.
        """
        # Check if there's speech (RMS > threshold)
        rms = float(np.sqrt(np.mean(audio ** 2)))
        if rms < 0.02:
            return []  # Silence — no speakers

        # Generate pseudo speaker ID from audio characteristics
        # (This is a simplified heuristic — not real diarization)
        speaker_id = self._estimate_speaker_id(audio)

        if speaker_id not in self._speaker_profiles:
            self._assign_voice(speaker_id)

        duration_ms = int(len(audio) / self.sample_rate * 1000)
        return [SpeakerSegment(
            speaker_id=speaker_id,
            start_ms=0,
            end_ms=duration_ms,
            audio=audio,
            confidence=0.5  # Low confidence in simple mode
        )]

    def _estimate_speaker_id(self, audio: np.ndarray) -> str:
        """
        Estimate speaker ID from audio characteristics.

        Uses zero-crossing rate and spectral centroid as a simple
        fingerprint. NOT a replacement for real diarization.
        """
        # Zero crossing rate (rough pitch indicator)
        zcr = np.sum(np.abs(np.diff(np.signbit(audio)))) / len(audio)

        # Spectral centroid (rough timbre indicator)
        fft = np.abs(np.fft.rfft(audio))
        freqs = np.fft.rfftfreq(len(audio), 1.0 / self.sample_rate)
        centroid = np.sum(freqs * fft) / (np.sum(fft) + 1e-10)

        # Quantize to create stable-ish speaker ID
        zcr_bin = int(zcr * 100) // 5
        centroid_bin = int(centroid) // 200

        return f"speaker_{zcr_bin}_{centroid_bin}"

    def _assign_voice(self, speaker_id: str):
        """Assign a voice profile from the pool to a new speaker."""
        voice_data = VOICE_POOL[self._next_voice_idx % len(VOICE_POOL)]
        self._next_voice_idx += 1

        profile = VoiceProfile(
            speaker_id=speaker_id,
            pitch_shift=voice_data["pitch"],
            speed_factor=voice_data["speed"],
            voice_name=voice_data["name"]
        )

        self._speaker_profiles[speaker_id] = profile
        utl_speakers_detected_total.inc()
        print(f"[SPEAKER_MAP] New speaker: {speaker_id} -> {voice_data['name']}")

    def get_voice_profile(self, speaker_id: str) -> VoiceProfile:
        """
        Get consistent voice profile for speaker.

        Returns the same profile every time for the same speaker_id
        within a session. Creates a new assignment if unknown speaker.

        Args:
            speaker_id: Unique speaker identifier

        Returns:
            VoiceProfile for this speaker
        """
        if speaker_id not in self._speaker_profiles:
            self._assign_voice(speaker_id)
        return self._speaker_profiles[speaker_id]

    def reset_session(self):
        """Clear speaker mappings for new session (new movie/stream)."""
        self._speaker_profiles.clear()
        self._next_voice_idx = 0
        print("[SPEAKER_MAP] Session reset — all speaker mappings cleared")

    @property
    def active_speakers(self) -> int:
        """Number of unique speakers detected in current session."""
        return len(self._speaker_profiles)

    @property
    def is_available(self) -> bool:
        """Check if full diarization (pyannote) is available."""
        return self._available

    # === DESIGN DOC API ALIASES ===

    def identify_speaker(self, audio_segment: np.ndarray) -> str:
        """
        Identify dominant speaker in an audio segment.

        Convenience method matching the design doc interface.
        Returns the speaker_id of the first detected speaker.

        Args:
            audio_segment: Float32 numpy array of audio samples

        Returns:
            SpeakerID string (or "unknown" if no speech detected)
        """
        segments = self.identify_speakers(audio_segment)
        if segments:
            return segments[0].speaker_id
        return "unknown"

    def get_voice(self, speaker_id: str) -> VoiceProfile:
        """
        Get voice profile for a speaker (design doc API).

        Alias for get_voice_profile() matching design document interface.

        Args:
            speaker_id: Unique speaker identifier

        Returns:
            VoiceProfile for this speaker
        """
        return self.get_voice_profile(speaker_id)


# === ENTRY POINT ===

def main():
    """Test speaker mapper with synthetic audio."""
    print("[SPEAKER_MAP] Testing speaker mapper...")

    mapper = SpeakerMapper(sample_rate=16000)

    # Generate two "speakers" with different characteristics
    sr = 16000
    duration = 0.5
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)

    # Speaker 1: low frequency (simulates male voice)
    speaker1_audio = np.sin(2 * np.pi * 150 * t) * 0.4
    # Speaker 2: high frequency (simulates female voice)
    speaker2_audio = np.sin(2 * np.pi * 350 * t) * 0.4

    # Identify speakers
    segments1 = mapper.identify_speakers(speaker1_audio)
    segments2 = mapper.identify_speakers(speaker2_audio)

    print(f"  Speaker 1 segments: {len(segments1)}")
    if segments1:
        profile1 = mapper.get_voice_profile(segments1[0].speaker_id)
        print(f"    ID: {profile1.speaker_id}")
        print(f"    Voice: {profile1.voice_name}")
        print(f"    Pitch: {profile1.pitch_shift}")

    print(f"  Speaker 2 segments: {len(segments2)}")
    if segments2:
        profile2 = mapper.get_voice_profile(segments2[0].speaker_id)
        print(f"    ID: {profile2.speaker_id}")
        print(f"    Voice: {profile2.voice_name}")
        print(f"    Pitch: {profile2.pitch_shift}")

    # Test design doc API aliases
    print("  --- Design Doc API test ---")
    test_audio = np.sin(2 * np.pi * 200 * t) * 0.3
    sid = mapper.identify_speaker(test_audio)
    voice = mapper.get_voice(sid)
    print(f"    identify_speaker -> {sid}")
    print(f"    get_voice -> {voice.voice_name} (pitch={voice.pitch_shift})")

    print(f"  Active speakers: {mapper.active_speakers}")
    print(f"  Diarization available: {mapper.is_available}")
    print("[SPEAKER_MAP] Test complete")


if __name__ == '__main__':
    main()
