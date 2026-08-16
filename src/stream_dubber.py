"""
Stream Dubber — Universal Translation Layer (UTL)

Real-time audio capture, voice separation, translation and synthesis orchestrator.
Wires pipeline: AudioCapture -> VoiceSeparator -> SpeakerMapper -> STT -> Translation -> TTS -> AudioMixer

Modes:
- DUB: Full voice dubbing (replace dialog with translated TTS)
- SUBTITLE: Translated subtitles only (no audio replacement)

Target: <2s end-to-end dubbing latency
Mix: dubbed dialog with original music + SFX, preserving spatial audio

Autor: Pan Jeskyne
Asistent: Kiro
"""

import time
import logging
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, List

import numpy as np

# === LOGGING ===

logger = logging.getLogger(__name__)
LOG_PREFIX = "[DUBBER]"

# === PROMETHEUS METRICS ===

try:
    from prometheus_client import Histogram, Counter

    utl_dubbing_latency_seconds = Histogram(
        'utl_dubbing_latency_seconds',
        'End-to-end dubbing latency in seconds',
        buckets=[0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0]
    )

    utl_dubbing_segments_total = Counter(
        'utl_dubbing_segments_total',
        'Total number of dubbed audio segments processed',
        ['mode', 'status']  # mode: dub/subtitle, status: success/error/fallback
    )
except ImportError:
    utl_dubbing_latency_seconds = None
    utl_dubbing_segments_total = None

# === OPTIONAL DEPENDENCIES ===

try:
    import whisper
    _WHISPER_AVAILABLE = True
except ImportError:
    _WHISPER_AVAILABLE = False
    whisper = None

try:
    from TTS.api import TTS as CoquiTTS
    _TTS_AVAILABLE = True
except ImportError:
    _TTS_AVAILABLE = False
    CoquiTTS = None

# === LOCAL IMPORTS ===

from audio_capture import AudioCapture, AudioChunk
from voice_separator import VoiceSeparator, SeparatedAudio
from speaker_mapper import SpeakerMapper, VoiceProfile
from translation_engine import TranslationEngine, TranslationResult

# === CONSTANTS ===

LATENCY_TARGET_S = 2.0            # <2s end-to-end target
WHISPER_MODEL_SIZE = "base"       # Whisper model for STT
DEFAULT_SAMPLE_RATE = 48000       # Pipeline sample rate
DEFAULT_CHANNELS = 2              # Stereo for spatial audio
STT_SAMPLE_RATE = 16000           # Whisper expects 16kHz mono


# === ENUMS ===

class DubbingMode(Enum):
    """Dubbing operation mode."""
    DUB = "dub"            # Full voice dubbing (replace dialog with TTS)
    SUBTITLE = "subtitle"  # Translated subtitles only (no audio replacement)


# === DATA MODELS ===

@dataclass
class SubtitleEvent:
    """A subtitle event produced in SUBTITLE mode.

    Attributes:
        text: Original transcribed text
        translated_text: Translated text in target language
        speaker_id: Speaker identifier
        timestamp: Time when subtitle was generated (epoch seconds)
        duration_ms: Approximate duration of the speech segment
    """
    text: str
    translated_text: str
    speaker_id: str
    timestamp: float
    duration_ms: int


@dataclass
class DubbingSegment:
    """A processed dubbing segment with all pipeline outputs.

    Attributes:
        original_audio: Original audio chunk from capture
        separated: Voice-separated audio tracks
        speaker_id: Identified speaker
        voice_profile: Voice profile for the speaker
        transcription: STT result text
        translation: Translated text
        dubbed_audio: Synthesized TTS audio (or None in subtitle mode)
        mixed_audio: Final mixed output (dubbed + music + sfx)
        latency_s: End-to-end processing latency in seconds
    """
    original_audio: AudioChunk
    separated: Optional[SeparatedAudio] = None
    speaker_id: Optional[str] = None
    voice_profile: Optional[VoiceProfile] = None
    transcription: Optional[str] = None
    translation: Optional[str] = None
    dubbed_audio: Optional[np.ndarray] = None
    mixed_audio: Optional[np.ndarray] = None
    latency_s: float = 0.0


# === AUDIO MIXER ===

class AudioMixer:
    """Mixes dubbed dialog with original music and SFX tracks.

    Preserves spatial audio characteristics by maintaining channel layout
    from the original separated tracks.
    """

    def __init__(self, sample_rate: int = DEFAULT_SAMPLE_RATE):
        self._sample_rate = sample_rate

    def mix(self, dubbed_vocals: np.ndarray, music: np.ndarray,
            sfx: np.ndarray, original_vocals: np.ndarray) -> np.ndarray:
        """Mix dubbed dialog with music and SFX tracks.

        Args:
            dubbed_vocals: Synthesized TTS audio (target language)
            music: Original music track from voice separation
            sfx: Original SFX track from voice separation
            original_vocals: Original vocals (used for timing/energy reference)

        Returns:
            Mixed audio numpy array combining all tracks.
        """
        # Ensure all tracks have compatible shapes
        target_length = max(len(music), len(sfx))

        # Pad or trim dubbed vocals to match original timing
        dubbed = self._match_length(dubbed_vocals, target_length)
        music_track = self._match_length(music, target_length)
        sfx_track = self._match_length(sfx, target_length)

        # Mix: dubbed vocals + music + sfx with balanced levels
        # Vocals at full volume, music at 0.7, sfx at 0.9
        mixed = (
            dubbed * 1.0
            + music_track * 0.7
            + sfx_track * 0.9
        )

        # Prevent clipping
        peak = np.max(np.abs(mixed))
        if peak > 1.0:
            mixed = mixed / peak

        return mixed.astype(np.float32)

    def _match_length(self, audio: np.ndarray, target_length: int) -> np.ndarray:
        """Pad or trim audio to target length."""
        if len(audio) == 0:
            return np.zeros(target_length, dtype=np.float32)
        if len(audio) >= target_length:
            return audio[:target_length]
        # Pad with zeros
        padded = np.zeros(target_length, dtype=np.float32)
        padded[:len(audio)] = audio
        return padded


# === STREAM DUBBER CLASS ===

class StreamDubber:
    """Real-time audio capture, voice separation, translation, synthesis.

    Orchestrates the full dubbing pipeline:
    AudioCapture -> VoiceSeparator -> SpeakerMapper -> STT (Whisper)
    -> Translation -> TTS -> AudioMixer

    Modes:
    - DUB: Full voice dubbing with TTS synthesis and audio mixing
    - SUBTITLE: Transcribe + translate only, emit subtitle events

    Target latency: <2s end-to-end from speech to dubbed output.
    """

    def __init__(self, target_lang: str = "cs",
                 sample_rate: int = DEFAULT_SAMPLE_RATE,
                 channels: int = DEFAULT_CHANNELS):
        """Initialize the Stream Dubber orchestrator.

        Args:
            target_lang: Target language code for translation (ISO 639-1)
            sample_rate: Audio pipeline sample rate in Hz
            channels: Number of audio channels (2 = stereo)
        """
        self._target_lang = target_lang
        self._sample_rate = sample_rate
        self._channels = channels
        self._mode = DubbingMode.DUB
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._last_latency: float = 0.0
        self._segments_processed: int = 0

        # Pipeline components
        self._capture = AudioCapture(
            sample_rate=sample_rate, channels=channels
        )
        self._separator = VoiceSeparator(sample_rate=sample_rate)
        self._speaker_mapper = SpeakerMapper(sample_rate=STT_SAMPLE_RATE)
        self._translator = TranslationEngine()
        self._mixer = AudioMixer(sample_rate=sample_rate)

        # STT (Whisper) — loaded lazily
        self._whisper_model = None

        # TTS — loaded lazily
        self._tts_engine = None

        # Callbacks
        self._on_subtitle: Optional[Callable[[SubtitleEvent], None]] = None
        self._on_dubbed_audio: Optional[Callable[[np.ndarray], None]] = None

        logger.info(
            f"{LOG_PREFIX} Initialized: target_lang={target_lang}, "
            f"mode={self._mode.value}, sample_rate={sample_rate}, "
            f"whisper={'available' if _WHISPER_AVAILABLE else 'unavailable'}, "
            f"tts={'available' if _TTS_AVAILABLE else 'unavailable'}"
        )

    # === PUBLIC API ===

    def start(self, target_lang: str = None) -> None:
        """Start the dubbing pipeline.

        Begins capturing system audio and processing through the full
        pipeline in a background thread.

        Args:
            target_lang: Override target language (optional).
                         If None, uses the language set at init.

        Raises:
            RuntimeError: If the pipeline is already running.
        """
        with self._lock:
            if self._running:
                raise RuntimeError(f"{LOG_PREFIX} Pipeline is already running")

            if target_lang is not None:
                self._target_lang = target_lang

            self._running = True

        # Load STT model if needed
        self._ensure_whisper_loaded()

        # Load TTS engine if in DUB mode
        if self._mode == DubbingMode.DUB:
            self._ensure_tts_loaded()

        # Start audio capture
        self._capture.start()

        # Start processing thread
        self._thread = threading.Thread(
            target=self._processing_loop,
            name="StreamDubberThread",
            daemon=True
        )
        self._thread.start()

        logger.info(
            f"{LOG_PREFIX} Started pipeline: mode={self._mode.value}, "
            f"target_lang={self._target_lang}"
        )

    def stop(self) -> None:
        """Stop the dubbing pipeline and release resources."""
        with self._lock:
            if not self._running:
                return
            self._running = False

        # Stop audio capture
        self._capture.stop()

        # Wait for processing thread
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None

        # Reset speaker mapper session
        self._speaker_mapper.reset_session()

        logger.info(
            f"{LOG_PREFIX} Stopped pipeline. "
            f"Segments processed: {self._segments_processed}"
        )

    def set_mode(self, mode: DubbingMode) -> None:
        """Set the dubbing mode.

        Args:
            mode: DubbingMode.DUB for full voice dubbing,
                  DubbingMode.SUBTITLE for subtitles only.
        """
        old_mode = self._mode
        self._mode = mode
        logger.info(
            f"{LOG_PREFIX} Mode changed: {old_mode.value} -> {mode.value}"
        )

        # Load TTS if switching to DUB mode while running
        if mode == DubbingMode.DUB and self._running:
            self._ensure_tts_loaded()

    def get_latency(self) -> float:
        """Get the last measured end-to-end dubbing latency in seconds.

        Returns:
            Last measured latency in seconds, or 0.0 if no segments processed.
        """
        return self._last_latency

    # === CALLBACK REGISTRATION ===

    def on_subtitle(self, callback: Callable[[SubtitleEvent], None]) -> None:
        """Register a callback for subtitle events (SUBTITLE mode).

        Args:
            callback: Function called with SubtitleEvent when subtitles are ready.
        """
        self._on_subtitle = callback

    def on_dubbed_audio(self, callback: Callable[[np.ndarray], None]) -> None:
        """Register a callback for dubbed audio output (DUB mode).

        Args:
            callback: Function called with mixed audio numpy array.
        """
        self._on_dubbed_audio = callback

    # === PROPERTIES ===

    @property
    def is_running(self) -> bool:
        """Whether the dubbing pipeline is currently active."""
        return self._running

    @property
    def mode(self) -> DubbingMode:
        """Current dubbing mode."""
        return self._mode

    @property
    def target_lang(self) -> str:
        """Current target language code."""
        return self._target_lang

    @property
    def segments_processed(self) -> int:
        """Total number of segments processed in this session."""
        return self._segments_processed

    @property
    def pipeline_status(self) -> dict:
        """Status of all pipeline components."""
        return {
            "running": self._running,
            "mode": self._mode.value,
            "target_lang": self._target_lang,
            "whisper_available": _WHISPER_AVAILABLE,
            "whisper_loaded": self._whisper_model is not None,
            "tts_available": _TTS_AVAILABLE,
            "tts_loaded": self._tts_engine is not None,
            "separator_available": self._separator.is_available,
            "segments_processed": self._segments_processed,
            "last_latency_s": self._last_latency,
        }

    # === PROCESSING LOOP ===

    def _processing_loop(self) -> None:
        """Main processing loop: capture -> separate -> identify -> STT -> translate -> TTS -> mix."""
        logger.info(f"{LOG_PREFIX} Processing loop started")

        while self._running:
            try:
                # 1. Capture audio chunk (blocks up to 1s)
                chunk = self._capture.get_chunk(timeout=1.0)
                if chunk is None:
                    continue

                start_time = time.perf_counter()

                # 2. Process the chunk through the pipeline
                segment = self._process_chunk(chunk, start_time)

                # 3. Record latency
                elapsed = time.perf_counter() - start_time
                self._last_latency = elapsed
                self._segments_processed += 1

                # 4. Record Prometheus metrics
                self._record_metrics(elapsed, "success")

                # 5. Latency warning
                if elapsed > LATENCY_TARGET_S:
                    logger.warning(
                        f"{LOG_PREFIX} Segment latency {elapsed:.3f}s "
                        f"exceeds target {LATENCY_TARGET_S}s"
                    )

            except Exception as e:
                logger.error(f"{LOG_PREFIX} Processing error: {e}")
                self._record_metrics(0.0, "error")

        logger.info(f"{LOG_PREFIX} Processing loop ended")

    def _process_chunk(self, chunk: AudioChunk, start_time: float) -> DubbingSegment:
        """Process a single audio chunk through the full pipeline.

        Pipeline stages:
        1. Voice separation (Demucs) — isolate vocals, music, SFX
        2. Speaker identification (pyannote / energy fallback)
        3. STT (Whisper) — transcribe vocals
        4. Translation — translate transcription to target language
        5. TTS — synthesize translated text (DUB mode only)
        6. Audio mixing — combine dubbed vocals + music + SFX

        Args:
            chunk: Captured audio chunk from AudioCapture
            start_time: Timestamp when processing started (for latency calc)

        Returns:
            DubbingSegment with all pipeline outputs.
        """
        segment = DubbingSegment(original_audio=chunk)

        # === STAGE 1: Voice Separation ===
        # Convert chunk samples to mono for separation if needed
        audio_for_separation = self._prepare_for_separation(chunk)
        separated = self._separator.separate(audio_for_separation)
        segment.separated = separated

        # === STAGE 2: Speaker Identification ===
        # Use vocals at 16kHz mono for speaker identification
        vocals_16k = self._resample_to_16k(separated.vocals)
        speaker_id = self._speaker_mapper.identify_speaker(vocals_16k)
        segment.speaker_id = speaker_id

        # Skip silent segments
        if speaker_id == "silence":
            return segment

        # Get voice profile for this speaker
        voice_profile = self._speaker_mapper.get_voice(speaker_id)
        segment.voice_profile = voice_profile

        # === STAGE 3: STT (Whisper) ===
        transcription = self._transcribe(vocals_16k)
        segment.transcription = transcription

        if not transcription or not transcription.strip():
            return segment

        # === STAGE 4: Translation ===
        translation_result = self._translate(transcription)
        segment.translation = translation_result.translated_text

        # === STAGE 5 & 6: TTS + Mixing (DUB mode) or Subtitle ===
        if self._mode == DubbingMode.DUB:
            # Synthesize translated text
            dubbed_audio = self._synthesize(
                translation_result.translated_text, voice_profile
            )
            segment.dubbed_audio = dubbed_audio

            # Mix dubbed audio with music + SFX
            mixed = self._mixer.mix(
                dubbed_vocals=dubbed_audio,
                music=separated.music,
                sfx=separated.sfx,
                original_vocals=separated.vocals
            )
            segment.mixed_audio = mixed

            # Emit dubbed audio via callback
            if self._on_dubbed_audio is not None:
                self._on_dubbed_audio(mixed)

        elif self._mode == DubbingMode.SUBTITLE:
            # Emit subtitle event
            if self._on_subtitle is not None:
                event = SubtitleEvent(
                    text=transcription,
                    translated_text=translation_result.translated_text,
                    speaker_id=speaker_id,
                    timestamp=time.time(),
                    duration_ms=chunk.duration_ms
                )
                self._on_subtitle(event)

        segment.latency_s = time.perf_counter() - start_time
        return segment

    # === PIPELINE STAGE HELPERS ===

    def _prepare_for_separation(self, chunk: AudioChunk) -> np.ndarray:
        """Prepare audio chunk for voice separation.

        VoiceSeparator expects mono (samples,) or stereo (channels, samples).
        AudioChunk.samples shape is (samples, channels).

        Returns:
            Audio in shape (channels, samples) for stereo or (samples,) for mono.
        """
        samples = chunk.samples
        if samples.ndim == 2 and samples.shape[1] <= 4:
            # Shape is (samples, channels) -> transpose to (channels, samples)
            return samples.T.astype(np.float32)
        return samples.astype(np.float32)

    def _resample_to_16k(self, audio: np.ndarray) -> np.ndarray:
        """Resample audio to 16kHz mono for STT and speaker identification.

        Args:
            audio: Input audio, can be mono (samples,) or multi-channel.

        Returns:
            Mono 16kHz audio as 1D numpy array.
        """
        # Convert to mono if needed
        if audio.ndim == 2:
            mono = np.mean(audio, axis=0)
        else:
            mono = audio

        # Resample from pipeline sample rate to 16kHz
        if self._sample_rate == STT_SAMPLE_RATE:
            return mono.astype(np.float32)

        # Simple resampling via linear interpolation
        ratio = STT_SAMPLE_RATE / self._sample_rate
        output_length = int(len(mono) * ratio)
        if output_length == 0:
            return np.zeros(1, dtype=np.float32)

        indices = np.linspace(0, len(mono) - 1, output_length)
        resampled = np.interp(indices, np.arange(len(mono)), mono)
        return resampled.astype(np.float32)

    def _transcribe(self, audio_16k: np.ndarray) -> str:
        """Transcribe audio using Whisper STT.

        Args:
            audio_16k: Mono 16kHz audio numpy array.

        Returns:
            Transcribed text, or empty string if STT unavailable or fails.
        """
        if self._whisper_model is None:
            # Fallback: return empty (no transcription available)
            logger.debug(f"{LOG_PREFIX} Whisper not loaded, skipping STT")
            return ""

        try:
            result = self._whisper_model.transcribe(
                audio_16k,
                fp16=False,
                language=None  # Auto-detect source language
            )
            text = result.get("text", "").strip()
            return text
        except Exception as e:
            logger.error(f"{LOG_PREFIX} STT error: {e}")
            return ""

    def _translate(self, text: str) -> TranslationResult:
        """Translate text to target language via TranslationEngine.

        Uses the configured TranslationEngine with its full fallback chain
        (mesh -> local model -> degraded).

        Args:
            text: Source text to translate.

        Returns:
            TranslationResult from the translation engine.
        """
        # Auto-detect source language (use "auto" and let engine handle it)
        # In practice, Whisper already detected the language
        return self._translator.translate(
            text=text,
            source_lang="auto",
            target_lang=self._target_lang
        )

    def _synthesize(self, text: str,
                    voice_profile: VoiceProfile) -> np.ndarray:
        """Synthesize translated text using TTS with voice profile.

        Applies pitch shift and speed factor from the voice profile to
        maintain speaker-specific voice characteristics.

        Args:
            text: Translated text to synthesize.
            voice_profile: Voice profile for the target speaker.

        Returns:
            Synthesized audio as numpy array (mono, pipeline sample rate).
            Returns zeros if TTS is unavailable.
        """
        if self._tts_engine is None:
            # Fallback: generate silence of approximate duration
            # Estimate ~150ms per word
            word_count = max(1, len(text.split()))
            duration_samples = int(
                word_count * 0.15 * self._sample_rate
            )
            logger.debug(
                f"{LOG_PREFIX} TTS unavailable, generating silence "
                f"({duration_samples} samples)"
            )
            return np.zeros(duration_samples, dtype=np.float32)

        try:
            # Use Coqui TTS for synthesis
            wav = self._tts_engine.tts(text=text)
            audio = np.array(wav, dtype=np.float32)

            # Apply voice profile adjustments
            audio = self._apply_voice_profile(audio, voice_profile)

            return audio

        except Exception as e:
            logger.error(f"{LOG_PREFIX} TTS synthesis error: {e}")
            # Fallback silence
            return np.zeros(
                int(0.5 * self._sample_rate), dtype=np.float32
            )

    def _apply_voice_profile(self, audio: np.ndarray,
                             voice_profile: VoiceProfile) -> np.ndarray:
        """Apply voice profile (pitch shift + speed) to synthesized audio.

        Args:
            audio: Raw TTS output audio.
            voice_profile: Target speaker's voice profile.

        Returns:
            Audio with pitch and speed adjustments applied.
        """
        # Apply speed factor via resampling
        speed = voice_profile.speed_factor
        if abs(speed - 1.0) > 0.01:
            output_length = int(len(audio) / speed)
            if output_length > 0:
                indices = np.linspace(0, len(audio) - 1, output_length)
                audio = np.interp(
                    indices, np.arange(len(audio)), audio
                ).astype(np.float32)

        # Apply pitch shift via simple frequency scaling
        # (basic implementation — production would use librosa or rubberband)
        pitch_semitones = voice_profile.pitch_shift
        if abs(pitch_semitones) > 0.1:
            pitch_factor = 2.0 ** (pitch_semitones / 12.0)
            output_length = int(len(audio) / pitch_factor)
            if output_length > 0:
                indices = np.linspace(0, len(audio) - 1, output_length)
                audio = np.interp(
                    indices, np.arange(len(audio)), audio
                ).astype(np.float32)

        return audio

    # === MODEL LOADING ===

    def _ensure_whisper_loaded(self) -> None:
        """Load Whisper STT model if available and not already loaded."""
        if self._whisper_model is not None:
            return

        if not _WHISPER_AVAILABLE:
            logger.warning(
                f"{LOG_PREFIX} Whisper not available. "
                "STT will be disabled. Install with: pip install openai-whisper"
            )
            return

        try:
            logger.info(
                f"{LOG_PREFIX} Loading Whisper model '{WHISPER_MODEL_SIZE}'..."
            )
            self._whisper_model = whisper.load_model(WHISPER_MODEL_SIZE)
            logger.info(f"{LOG_PREFIX} Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"{LOG_PREFIX} Failed to load Whisper: {e}")
            self._whisper_model = None

    def _ensure_tts_loaded(self) -> None:
        """Load TTS engine if available and not already loaded."""
        if self._tts_engine is not None:
            return

        if not _TTS_AVAILABLE:
            logger.warning(
                f"{LOG_PREFIX} Coqui TTS not available. "
                "Voice synthesis will be disabled. Install with: pip install TTS"
            )
            return

        try:
            logger.info(f"{LOG_PREFIX} Loading TTS engine...")
            self._tts_engine = CoquiTTS(
                model_name="tts_models/multilingual/multi-dataset/xtts_v2",
                progress_bar=False
            )
            logger.info(f"{LOG_PREFIX} TTS engine loaded successfully")
        except Exception as e:
            logger.error(f"{LOG_PREFIX} Failed to load TTS: {e}")
            self._tts_engine = None

    # === METRICS ===

    def _record_metrics(self, latency: float, status: str) -> None:
        """Record Prometheus metrics for a processed segment.

        Args:
            latency: Processing latency in seconds.
            status: Status label ('success', 'error', 'fallback').
        """
        if utl_dubbing_latency_seconds is not None and latency > 0:
            utl_dubbing_latency_seconds.observe(latency)

        if utl_dubbing_segments_total is not None:
            utl_dubbing_segments_total.labels(
                mode=self._mode.value,
                status=status
            ).inc()


# === MAIN GUARD ===

def main():
    """Self-test entry point for Stream Dubber module."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    print(f"{LOG_PREFIX} Stream Dubber self-test")
    print(f"{LOG_PREFIX} Whisper available: {_WHISPER_AVAILABLE}")
    print(f"{LOG_PREFIX} TTS available: {_TTS_AVAILABLE}")

    # Create dubber instance
    dubber = StreamDubber(target_lang="cs")
    print(f"{LOG_PREFIX} Pipeline status: {dubber.pipeline_status}")

    # Test mode switching
    dubber.set_mode(DubbingMode.SUBTITLE)
    assert dubber.mode == DubbingMode.SUBTITLE
    dubber.set_mode(DubbingMode.DUB)
    assert dubber.mode == DubbingMode.DUB
    print(f"{LOG_PREFIX} Mode switching: OK")

    # Test latency getter
    assert dubber.get_latency() == 0.0
    print(f"{LOG_PREFIX} Initial latency: {dubber.get_latency()}")

    # Test subtitle callback
    subtitles_received: List[SubtitleEvent] = []

    def on_sub(event: SubtitleEvent):
        subtitles_received.append(event)
        print(
            f"{LOG_PREFIX} Subtitle: [{event.speaker_id}] "
            f"{event.text} -> {event.translated_text}"
        )

    dubber.on_subtitle(on_sub)

    # Test dubbed audio callback
    audio_chunks_received: List[np.ndarray] = []

    def on_audio(audio: np.ndarray):
        audio_chunks_received.append(audio)

    dubber.on_dubbed_audio(on_audio)

    # Test AudioMixer independently
    mixer = AudioMixer()
    vocals = np.random.randn(8000).astype(np.float32) * 0.5
    music = np.random.randn(8000).astype(np.float32) * 0.3
    sfx = np.random.randn(8000).astype(np.float32) * 0.2
    mixed = mixer.mix(vocals, music, sfx, vocals)
    assert mixed.shape == (8000,), f"Mixed shape: {mixed.shape}"
    assert np.max(np.abs(mixed)) <= 1.0, "Mixed audio exceeds [-1, 1]"
    print(f"{LOG_PREFIX} AudioMixer test: OK (shape={mixed.shape})")

    # Test pipeline briefly (2 chunks in stub mode)
    dubber.set_mode(DubbingMode.SUBTITLE)
    print(f"{LOG_PREFIX} Starting pipeline for 2 seconds (stub mode)...")
    dubber.start()
    time.sleep(2.0)
    dubber.stop()

    print(f"{LOG_PREFIX} Segments processed: {dubber.segments_processed}")
    print(f"{LOG_PREFIX} Last latency: {dubber.get_latency():.4f}s")
    print(f"{LOG_PREFIX} Subtitles received: {len(subtitles_received)}")

    print(f"{LOG_PREFIX} All self-tests passed.")


if __name__ == '__main__':
    main()
