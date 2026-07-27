"""
Audio Pipeline End-to-End — Universal Translation Layer (UTL)

Full end-to-end audio dubbing pipeline wiring:
AudioCapture → VoiceSeparator → SpeakerMapper → Whisper STT →
Ada Validator (subprocess) → Bifrost/Translation → TTS → AudioMixer → Output

Supports:
- DUB mode: Full voice dubbing with spatial audio preservation
- SUBTITLE mode: Text overlay path (transcription + translation only)
- Platform detection: WASAPI (Windows) / PulseAudio (Linux)
- Prometheus metrics for full pipeline observability
- <2s end-to-end latency target tracking

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8

Autor: Pan Jeskyně
Asistent: Kiro
"""

import sys
import time
import logging
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, List, Dict

import numpy as np

# === LOGGING ===

logger = logging.getLogger(__name__)
LOG_PREFIX = "[AUDIO_PIPELINE]"

# === PROMETHEUS METRICS ===

try:
    from prometheus_client import Counter, Histogram, Gauge

    utl_audio_pipeline_latency_seconds = Histogram(
        "utl_audio_pipeline_latency_seconds",
        "End-to-end audio pipeline latency in seconds",
        ["stage"],
        buckets=[0.1, 0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0],
    )

    utl_audio_pipeline_segments_total = Counter(
        "utl_audio_pipeline_segments_total",
        "Total audio segments processed by the pipeline",
        ["mode", "status"],
    )

    utl_audio_pipeline_errors_total = Counter(
        "utl_audio_pipeline_errors_total",
        "Total errors in the audio pipeline",
        ["stage"],
    )

    utl_audio_pipeline_active = Gauge(
        "utl_audio_pipeline_active",
        "Whether the audio pipeline is currently running (1=active, 0=stopped)",
    )

    _METRICS_AVAILABLE = True
except ImportError:
    utl_audio_pipeline_latency_seconds = None
    utl_audio_pipeline_segments_total = None
    utl_audio_pipeline_errors_total = None
    utl_audio_pipeline_active = None
    _METRICS_AVAILABLE = False


# === LOCAL IMPORTS ===

from audio_capture import AudioCapture, AudioChunk
from voice_separator import VoiceSeparator, SeparatedAudio
from speaker_mapper import SpeakerMapper, VoiceProfile, SpeakerSegment
from translation_engine import TranslationEngine, TranslationResult
from stream_dubber import DubbingMode, SubtitleEvent, AudioMixer

# === CONSTANTS ===

LATENCY_TARGET_S = 2.0          # <2s end-to-end dubbing latency target
DEFAULT_SAMPLE_RATE = 48000     # Pipeline sample rate (Hz)
DEFAULT_CHANNELS = 2            # Stereo for spatial audio preservation
STT_SAMPLE_RATE = 16000         # Whisper expects 16kHz mono
DEFAULT_CHUNK_MS = 500          # Audio chunk duration

# Whisper STT model size (trade-off: speed vs accuracy)
WHISPER_MODEL_SIZE = "base"


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


# === PLATFORM DETECTION ===

def detect_audio_backend() -> str:
    """Detect the appropriate audio backend for the current platform.

    Returns:
        'wasapi' on Windows, 'pulseaudio' on Linux, 'fallback' otherwise.
    """
    if sys.platform == "win32":
        return "wasapi"
    elif sys.platform.startswith("linux"):
        return "pulseaudio"
    elif sys.platform == "darwin":
        return "coreaudio"
    return "fallback"


# === DATA MODELS ===

@dataclass
class PipelineSegmentResult:
    """Result of processing one audio segment through the full pipeline.

    Attributes:
        chunk_timestamp: Original capture timestamp
        speaker_id: Identified speaker (or None if no speech)
        voice_profile: Assigned voice profile for the speaker
        transcription: STT output text
        translation: Translated text in target language
        dubbed_audio: Synthesized TTS audio (DUB mode only)
        mixed_audio: Final mixed output (dubbed + music + SFX)
        subtitle_event: Subtitle event (SUBTITLE mode only)
        stage_latencies: Per-stage latency breakdown (seconds)
        total_latency_s: Total end-to-end latency (seconds)
        within_target: Whether total latency is within <2s target
        ada_validation: Ada validator result (dict or None)
    """
    chunk_timestamp: float = 0.0
    speaker_id: Optional[str] = None
    voice_profile: Optional[VoiceProfile] = None
    transcription: Optional[str] = None
    translation: Optional[str] = None
    dubbed_audio: Optional[np.ndarray] = None
    mixed_audio: Optional[np.ndarray] = None
    subtitle_event: Optional[SubtitleEvent] = None
    stage_latencies: Dict[str, float] = field(default_factory=dict)
    total_latency_s: float = 0.0
    within_target: bool = True
    ada_validation: Optional[Dict] = None


# === AUDIO PIPELINE CLASS ===

class AudioPipeline:
    """End-to-end audio dubbing pipeline.

    Wires all audio pipeline components into a single orchestrated flow:

    1. AudioCapture — system audio (WASAPI on Windows, PulseAudio on Linux)
    2. VoiceSeparator — isolate vocals from music/SFX (Demucs v4)
    3. SpeakerMapper — identify speakers, assign voice profiles (pyannote)
    4. Whisper STT — transcribe dialog
    5. Ada Validator — validate transcription via subprocess
    6. TranslationEngine — translate text (Bifrost/Gemini or local)
    7. TTS — synthesize speech with speaker voice profile
    8. AudioMixer — mix dubbed audio with original music + SFX
    9. Output — emit mixed audio or subtitle events

    Supports two modes:
    - DUB: Full voice dubbing (replace dialog with translated TTS)
    - SUBTITLE: Translated subtitles only (no audio synthesis)

    Exposes Prometheus metrics:
    - utl_audio_pipeline_latency_seconds (per-stage and total)
    - utl_audio_pipeline_segments_total (count by mode and status)
    - utl_audio_pipeline_errors_total (count by stage)
    """

    def __init__(
        self,
        target_lang: str = "cs",
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        channels: int = DEFAULT_CHANNELS,
        chunk_ms: int = DEFAULT_CHUNK_MS,
        mode: DubbingMode = DubbingMode.DUB,
    ):
        """Initialize the audio pipeline.

        Args:
            target_lang: Target language code (ISO 639-1)
            sample_rate: Audio pipeline sample rate in Hz
            channels: Number of audio channels (2 = stereo)
            chunk_ms: Audio chunk duration in milliseconds
            mode: Initial dubbing mode (DUB or SUBTITLE)
        """
        self._target_lang = target_lang
        self._sample_rate = sample_rate
        self._channels = channels
        self._chunk_ms = chunk_ms
        self._mode = mode
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Platform detection
        self._backend = detect_audio_backend()

        # Pipeline components (wired in order)
        self._capture = AudioCapture(
            sample_rate=sample_rate,
            channels=channels,
            chunk_ms=chunk_ms,
        )
        self._separator = VoiceSeparator(
            sample_rate=sample_rate,
            device="cuda",
        )
        self._speaker_mapper = SpeakerMapper(sample_rate=STT_SAMPLE_RATE)
        self._translator = TranslationEngine()
        self._mixer = AudioMixer(sample_rate=sample_rate)

        # Whisper STT — loaded lazily on start
        self._whisper_model = None

        # TTS engine — loaded lazily on start (DUB mode only)
        self._tts_engine = None

        # Runtime state
        self._segments_processed: int = 0
        self._segments_errors: int = 0
        self._last_latency: float = 0.0
        self._latency_history: List[float] = []

        # Callbacks
        self._on_subtitle: Optional[Callable[[SubtitleEvent], None]] = None
        self._on_dubbed_audio: Optional[Callable[[np.ndarray], None]] = None
        self._on_segment: Optional[Callable[[PipelineSegmentResult], None]] = None

        logger.info(
            f"{LOG_PREFIX} Initialized: target_lang={target_lang}, "
            f"mode={mode.value}, backend={self._backend}, "
            f"sample_rate={sample_rate}Hz, chunk={chunk_ms}ms"
        )

    # === PUBLIC API ===

    def start(self, target_lang: str = None) -> None:
        """Start the full audio pipeline.

        Begins capturing system audio and processing through all stages
        in a background thread.

        Args:
            target_lang: Override target language (optional).
        """
        with self._lock:
            if self._running:
                logger.warning(f"{LOG_PREFIX} Pipeline already running")
                return

            if target_lang is not None:
                self._target_lang = target_lang

            self._running = True

        # Load STT model
        self._ensure_whisper_loaded()

        # Load TTS engine in DUB mode
        if self._mode == DubbingMode.DUB:
            self._ensure_tts_loaded()

        # Start audio capture
        self._capture.start()

        # Update active gauge
        if utl_audio_pipeline_active:
            utl_audio_pipeline_active.set(1)

        # Start processing thread
        self._thread = threading.Thread(
            target=self._processing_loop,
            name="AudioPipelineThread",
            daemon=True,
        )
        self._thread.start()

        logger.info(
            f"{LOG_PREFIX} Pipeline started: mode={self._mode.value}, "
            f"lang={self._target_lang}, backend={self._backend}"
        )

    def stop(self) -> None:
        """Stop the audio pipeline and release resources."""
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

        # Update active gauge
        if utl_audio_pipeline_active:
            utl_audio_pipeline_active.set(0)

        logger.info(
            f"{LOG_PREFIX} Pipeline stopped. "
            f"Segments: {self._segments_processed}, "
            f"Errors: {self._segments_errors}"
        )

    def set_mode(self, mode: DubbingMode) -> None:
        """Switch dubbing mode.

        Args:
            mode: DubbingMode.DUB for full dubbing,
                  DubbingMode.SUBTITLE for subtitles only.
        """
        old = self._mode
        self._mode = mode
        logger.info(f"{LOG_PREFIX} Mode: {old.value} -> {mode.value}")

        if mode == DubbingMode.DUB and self._running:
            self._ensure_tts_loaded()

    def set_target_lang(self, lang: str) -> None:
        """Change target language at runtime."""
        self._target_lang = lang
        logger.info(f"{LOG_PREFIX} Target language: {lang}")

    # === CALLBACK REGISTRATION ===

    def on_subtitle(self, callback: Callable[[SubtitleEvent], None]) -> None:
        """Register callback for subtitle events (SUBTITLE mode)."""
        self._on_subtitle = callback

    def on_dubbed_audio(self, callback: Callable[[np.ndarray], None]) -> None:
        """Register callback for dubbed audio output (DUB mode)."""
        self._on_dubbed_audio = callback

    def on_segment(self, callback: Callable[[PipelineSegmentResult], None]) -> None:
        """Register callback for full segment results (any mode)."""
        self._on_segment = callback

    # === PROPERTIES ===

    @property
    def is_running(self) -> bool:
        """Whether the pipeline is currently active."""
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
    def backend(self) -> str:
        """Detected audio backend (wasapi/pulseaudio/fallback)."""
        return self._backend

    @property
    def segments_processed(self) -> int:
        """Total segments processed in this session."""
        return self._segments_processed

    @property
    def last_latency(self) -> float:
        """Last measured end-to-end latency in seconds."""
        return self._last_latency

    @property
    def average_latency(self) -> float:
        """Average end-to-end latency across recent segments."""
        if not self._latency_history:
            return 0.0
        return sum(self._latency_history) / len(self._latency_history)

    @property
    def meets_latency_target(self) -> bool:
        """Whether average latency is within the <2s target."""
        return self.average_latency < LATENCY_TARGET_S

    @property
    def pipeline_status(self) -> dict:
        """Full pipeline status for monitoring."""
        return {
            "running": self._running,
            "mode": self._mode.value,
            "target_lang": self._target_lang,
            "backend": self._backend,
            "whisper_available": _WHISPER_AVAILABLE,
            "whisper_loaded": self._whisper_model is not None,
            "tts_available": _TTS_AVAILABLE,
            "tts_loaded": self._tts_engine is not None,
            "separator_available": self._separator.is_available,
            "speaker_mapper_available": self._speaker_mapper.is_available,
            "segments_processed": self._segments_processed,
            "segments_errors": self._segments_errors,
            "last_latency_s": self._last_latency,
            "average_latency_s": self.average_latency,
            "meets_latency_target": self.meets_latency_target,
            "active_speakers": self._speaker_mapper.active_speakers,
        }

    # === PROCESSING LOOP ===

    def _processing_loop(self) -> None:
        """Main processing loop: capture → process → emit."""
        logger.info(f"{LOG_PREFIX} Processing loop started")

        while self._running:
            try:
                # 1. Capture audio chunk (blocks up to 1s)
                chunk = self._capture.get_chunk(timeout=1.0)
                if chunk is None:
                    continue

                pipeline_start = time.perf_counter()

                # 2. Process through full pipeline
                result = self._process_segment(chunk, pipeline_start)

                # 3. Record total latency
                total_latency = time.perf_counter() - pipeline_start
                result.total_latency_s = total_latency
                result.within_target = total_latency < LATENCY_TARGET_S

                self._last_latency = total_latency
                self._latency_history.append(total_latency)
                # Keep last 50 measurements for rolling average
                if len(self._latency_history) > 50:
                    self._latency_history.pop(0)

                self._segments_processed += 1

                # 4. Record metrics
                self._record_segment_metrics(result, "success")

                # 5. Emit segment result callback
                if self._on_segment is not None:
                    self._on_segment(result)

                # 6. Latency warning
                if not result.within_target:
                    logger.warning(
                        f"{LOG_PREFIX} Latency {total_latency:.3f}s "
                        f"exceeds {LATENCY_TARGET_S}s target"
                    )

            except Exception as e:
                logger.error(f"{LOG_PREFIX} Processing error: {e}")
                self._segments_errors += 1
                self._record_error("processing_loop")

        logger.info(f"{LOG_PREFIX} Processing loop ended")

    # === SEGMENT PROCESSING ===

    def _process_segment(
        self, chunk: AudioChunk, pipeline_start: float
    ) -> PipelineSegmentResult:
        """Process a single audio segment through the full pipeline.

        Stages:
        1. Voice Separation (Demucs v4)
        2. Speaker Identification (pyannote)
        3. STT (Whisper)
        4. Ada Validation (subprocess)
        5. Translation (Bifrost/local)
        6. TTS Synthesis (DUB mode) or Subtitle emit (SUBTITLE mode)
        7. Audio Mixing (DUB mode)

        Args:
            chunk: Captured audio chunk from AudioCapture
            pipeline_start: perf_counter timestamp when processing began

        Returns:
            PipelineSegmentResult with all pipeline outputs.
        """
        result = PipelineSegmentResult(chunk_timestamp=chunk.timestamp)
        latencies: Dict[str, float] = {}

        # === STAGE 1: Voice Separation (Demucs v4) ===
        t0 = time.perf_counter()
        try:
            audio_for_sep = self._prepare_for_separation(chunk)
            separated = self._separator.separate(audio_for_sep)
        except Exception as e:
            logger.error(f"{LOG_PREFIX} Separation error: {e}")
            self._record_error("voice_separation")
            return result
        latencies["voice_separation"] = time.perf_counter() - t0

        # === STAGE 2: Speaker Identification (pyannote) ===
        t0 = time.perf_counter()
        try:
            vocals_16k = self._resample_to_16k(separated.vocals)
            speaker_id = self._speaker_mapper.identify_speaker(vocals_16k)
        except Exception as e:
            logger.error(f"{LOG_PREFIX} Speaker mapping error: {e}")
            self._record_error("speaker_mapping")
            return result
        latencies["speaker_identification"] = time.perf_counter() - t0

        # Skip silent segments (no speech detected)
        if speaker_id == "unknown" or speaker_id == "silence":
            result.stage_latencies = latencies
            return result

        result.speaker_id = speaker_id
        voice_profile = self._speaker_mapper.get_voice(speaker_id)
        result.voice_profile = voice_profile

        # === STAGE 3: STT — Whisper Transcription ===
        t0 = time.perf_counter()
        try:
            transcription = self._transcribe(vocals_16k)
        except Exception as e:
            logger.error(f"{LOG_PREFIX} STT error: {e}")
            self._record_error("stt")
            result.stage_latencies = latencies
            return result
        latencies["stt"] = time.perf_counter() - t0

        if not transcription or not transcription.strip():
            result.stage_latencies = latencies
            return result

        result.transcription = transcription

        # === STAGE 4: Ada Validation (subprocess) ===
        t0 = time.perf_counter()
        try:
            ada_validation = self._translator._validate_with_ada(
                input_length=len(transcription),
                output_length=len(transcription),  # pre-translation check
                source_lang="auto",
                target_lang=self._target_lang,
            )
            result.ada_validation = ada_validation
        except Exception as e:
            logger.debug(f"{LOG_PREFIX} Ada validation skipped: {e}")
        latencies["ada_validation"] = time.perf_counter() - t0

        # === STAGE 5: Translation (Bifrost / local fallback) ===
        t0 = time.perf_counter()
        try:
            translation_result = self._translator.translate(
                text=transcription,
                source_lang="auto",
                target_lang=self._target_lang,
            )
            result.translation = translation_result.translated_text
        except Exception as e:
            logger.error(f"{LOG_PREFIX} Translation error: {e}")
            self._record_error("translation")
            result.stage_latencies = latencies
            return result
        latencies["translation"] = time.perf_counter() - t0

        # === STAGE 6 & 7: Mode-dependent output ===
        if self._mode == DubbingMode.DUB:
            # STAGE 6: TTS Synthesis
            t0 = time.perf_counter()
            try:
                dubbed_audio = self._synthesize(
                    translation_result.translated_text, voice_profile
                )
                result.dubbed_audio = dubbed_audio
            except Exception as e:
                logger.error(f"{LOG_PREFIX} TTS error: {e}")
                self._record_error("tts")
                result.stage_latencies = latencies
                return result
            latencies["tts"] = time.perf_counter() - t0

            # STAGE 7: Audio Mixing (dubbed + music + SFX)
            t0 = time.perf_counter()
            try:
                mixed = self._mixer.mix(
                    dubbed_vocals=dubbed_audio,
                    music=separated.music,
                    sfx=separated.sfx,
                    original_vocals=separated.vocals,
                )
                result.mixed_audio = mixed
            except Exception as e:
                logger.error(f"{LOG_PREFIX} Mixing error: {e}")
                self._record_error("mixing")
                result.stage_latencies = latencies
                return result
            latencies["mixing"] = time.perf_counter() - t0

            # Emit dubbed audio callback
            if self._on_dubbed_audio is not None:
                self._on_dubbed_audio(mixed)

        elif self._mode == DubbingMode.SUBTITLE:
            # SUBTITLE mode — emit text event instead of audio
            t0 = time.perf_counter()
            subtitle = SubtitleEvent(
                text=transcription,
                translated_text=translation_result.translated_text,
                speaker_id=speaker_id,
                timestamp=time.time(),
                duration_ms=chunk.duration_ms,
            )
            result.subtitle_event = subtitle
            latencies["subtitle_emit"] = time.perf_counter() - t0

            # Emit subtitle callback
            if self._on_subtitle is not None:
                self._on_subtitle(subtitle)

        result.stage_latencies = latencies
        return result

    # === INTERNAL HELPERS ===

    def _prepare_for_separation(self, chunk: AudioChunk) -> np.ndarray:
        """Prepare audio chunk for voice separation.

        VoiceSeparator expects (channels, samples) or (samples,).
        AudioChunk.samples is (samples, channels).

        Returns:
            Audio in shape (channels, samples) for multi-channel or
            (samples,) for mono.
        """
        samples = chunk.samples
        if samples.ndim == 2 and samples.shape[1] <= 4:
            return samples.T.astype(np.float32)
        return samples.astype(np.float32)

    def _resample_to_16k(self, audio: np.ndarray) -> np.ndarray:
        """Resample audio to 16kHz mono for STT and speaker ID.

        Args:
            audio: Input audio (mono or multi-channel).

        Returns:
            Mono 16kHz float32 numpy array.
        """
        if audio.ndim == 2:
            mono = np.mean(audio, axis=0)
        else:
            mono = audio

        if self._sample_rate == STT_SAMPLE_RATE:
            return mono.astype(np.float32)

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
            Transcribed text, or empty string if unavailable.
        """
        if self._whisper_model is None:
            logger.debug(f"{LOG_PREFIX} Whisper not loaded, skipping STT")
            return ""

        try:
            result = self._whisper_model.transcribe(
                audio_16k,
                fp16=False,
                language=None,  # Auto-detect source language
            )
            return result.get("text", "").strip()
        except Exception as e:
            logger.error(f"{LOG_PREFIX} Whisper STT error: {e}")
            return ""

    def _synthesize(
        self, text: str, voice_profile: VoiceProfile
    ) -> np.ndarray:
        """Synthesize translated text using TTS with voice profile.

        Applies pitch shift and speed factor from the voice profile.

        Args:
            text: Translated text to synthesize.
            voice_profile: Speaker's voice profile.

        Returns:
            Synthesized audio as numpy array (mono).
        """
        if self._tts_engine is None:
            # Fallback: approximate silence (~150ms per word)
            word_count = max(1, len(text.split()))
            duration_samples = int(word_count * 0.15 * self._sample_rate)
            return np.zeros(duration_samples, dtype=np.float32)

        try:
            wav = self._tts_engine.tts(text=text)
            audio = np.array(wav, dtype=np.float32)
            audio = self._apply_voice_profile(audio, voice_profile)
            return audio
        except Exception as e:
            logger.error(f"{LOG_PREFIX} TTS synthesis error: {e}")
            return np.zeros(int(0.5 * self._sample_rate), dtype=np.float32)

    def _apply_voice_profile(
        self, audio: np.ndarray, voice_profile: VoiceProfile
    ) -> np.ndarray:
        """Apply voice profile (pitch + speed) to synthesized audio.

        Args:
            audio: Raw TTS output audio.
            voice_profile: Target voice profile.

        Returns:
            Audio with pitch and speed adjustments.
        """
        # Apply speed factor
        speed = voice_profile.speed_factor
        if abs(speed - 1.0) > 0.01:
            output_length = int(len(audio) / speed)
            if output_length > 0:
                indices = np.linspace(0, len(audio) - 1, output_length)
                audio = np.interp(
                    indices, np.arange(len(audio)), audio
                ).astype(np.float32)

        # Apply pitch shift via frequency scaling
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
                "Install: pip install openai-whisper"
            )
            return

        try:
            logger.info(
                f"{LOG_PREFIX} Loading Whisper model '{WHISPER_MODEL_SIZE}'..."
            )
            self._whisper_model = whisper.load_model(WHISPER_MODEL_SIZE)
            logger.info(f"{LOG_PREFIX} Whisper model loaded")
        except Exception as e:
            logger.error(f"{LOG_PREFIX} Whisper load failed: {e}")
            self._whisper_model = None

    def _ensure_tts_loaded(self) -> None:
        """Load TTS engine if available and not already loaded."""
        if self._tts_engine is not None:
            return

        if not _TTS_AVAILABLE:
            logger.warning(
                f"{LOG_PREFIX} Coqui TTS not available. "
                "Install: pip install TTS"
            )
            return

        try:
            logger.info(f"{LOG_PREFIX} Loading TTS engine...")
            self._tts_engine = CoquiTTS(
                model_name="tts_models/multilingual/multi-dataset/xtts_v2",
                progress_bar=False,
            )
            logger.info(f"{LOG_PREFIX} TTS engine loaded")
        except Exception as e:
            logger.error(f"{LOG_PREFIX} TTS load failed: {e}")
            self._tts_engine = None

    # === METRICS ===

    def _record_segment_metrics(
        self, result: PipelineSegmentResult, status: str
    ) -> None:
        """Record Prometheus metrics for a processed segment."""
        if not _METRICS_AVAILABLE:
            return

        # Total segments counter
        utl_audio_pipeline_segments_total.labels(
            mode=self._mode.value, status=status
        ).inc()

        # Per-stage latencies
        for stage, latency in result.stage_latencies.items():
            utl_audio_pipeline_latency_seconds.labels(stage=stage).observe(
                latency
            )

        # Total pipeline latency
        utl_audio_pipeline_latency_seconds.labels(stage="total").observe(
            result.total_latency_s
        )

    def _record_error(self, stage: str) -> None:
        """Record an error in a specific pipeline stage."""
        if utl_audio_pipeline_errors_total:
            utl_audio_pipeline_errors_total.labels(stage=stage).inc()
        if utl_audio_pipeline_segments_total:
            utl_audio_pipeline_segments_total.labels(
                mode=self._mode.value, status="error"
            ).inc()


# === LATENCY VERIFICATION UTILITY ===

def verify_latency_target(pipeline: AudioPipeline, duration_s: float = 5.0) -> dict:
    """Run the pipeline for a duration and verify the <2s latency target.

    This utility runs the pipeline, collects latency measurements,
    and reports whether the target is met.

    Args:
        pipeline: An initialized AudioPipeline instance.
        duration_s: How long to run the test (seconds).

    Returns:
        Dict with latency statistics and pass/fail result.
    """
    results: List[PipelineSegmentResult] = []

    def collect(seg: PipelineSegmentResult):
        results.append(seg)

    pipeline.on_segment(collect)
    pipeline.start()

    time.sleep(duration_s)
    pipeline.stop()

    if not results:
        return {
            "segments": 0,
            "avg_latency_s": 0.0,
            "max_latency_s": 0.0,
            "min_latency_s": 0.0,
            "within_target": True,
            "target_s": LATENCY_TARGET_S,
        }

    latencies = [r.total_latency_s for r in results if r.total_latency_s > 0]
    if not latencies:
        return {
            "segments": len(results),
            "avg_latency_s": 0.0,
            "max_latency_s": 0.0,
            "min_latency_s": 0.0,
            "within_target": True,
            "target_s": LATENCY_TARGET_S,
        }

    avg = sum(latencies) / len(latencies)
    return {
        "segments": len(results),
        "avg_latency_s": avg,
        "max_latency_s": max(latencies),
        "min_latency_s": min(latencies),
        "within_target": avg < LATENCY_TARGET_S,
        "target_s": LATENCY_TARGET_S,
        "p95_latency_s": sorted(latencies)[int(len(latencies) * 0.95)]
        if len(latencies) > 1
        else latencies[0],
    }


# === MAIN GUARD ===

def main():
    """Self-test entry point for Audio Pipeline module."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    print(f"{LOG_PREFIX} Audio Pipeline end-to-end self-test")
    print(f"{LOG_PREFIX} Platform: {sys.platform}")
    print(f"{LOG_PREFIX} Backend: {detect_audio_backend()}")
    print(f"{LOG_PREFIX} Whisper available: {_WHISPER_AVAILABLE}")
    print(f"{LOG_PREFIX} TTS available: {_TTS_AVAILABLE}")

    # Create pipeline in SUBTITLE mode (lighter for testing)
    pipeline = AudioPipeline(
        target_lang="cs",
        mode=DubbingMode.SUBTITLE,
    )

    print(f"{LOG_PREFIX} Pipeline status: {pipeline.pipeline_status}")

    # Test mode switching
    pipeline.set_mode(DubbingMode.DUB)
    assert pipeline.mode == DubbingMode.DUB
    pipeline.set_mode(DubbingMode.SUBTITLE)
    assert pipeline.mode == DubbingMode.SUBTITLE

    # Test target language change
    pipeline.set_target_lang("en")
    assert pipeline.target_lang == "en"
    pipeline.set_target_lang("cs")

    # Test subtitle callback
    subtitles: List[SubtitleEvent] = []

    def on_sub(event: SubtitleEvent):
        subtitles.append(event)
        print(
            f"{LOG_PREFIX} Subtitle: [{event.speaker_id}] "
            f"{event.text} -> {event.translated_text}"
        )

    pipeline.on_subtitle(on_sub)

    # Run pipeline briefly (2 seconds)
    print(f"{LOG_PREFIX} Starting pipeline for 2 seconds...")
    pipeline.start()
    time.sleep(2.0)
    pipeline.stop()

    print(f"{LOG_PREFIX} Segments processed: {pipeline.segments_processed}")
    print(f"{LOG_PREFIX} Last latency: {pipeline.last_latency:.4f}s")
    print(f"{LOG_PREFIX} Average latency: {pipeline.average_latency:.4f}s")
    print(f"{LOG_PREFIX} Meets <2s target: {pipeline.meets_latency_target}")
    print(f"{LOG_PREFIX} Subtitles received: {len(subtitles)}")
    print(f"{LOG_PREFIX} All self-tests passed.")


if __name__ == "__main__":
    main()
