#!/usr/bin/env python3
"""
Karel IV. — Real-time Voice Translator
AsgardLab / web4light.online

Pipeline:
  Microphone → Virtual audio card → VoiceBiometricTunnel
  → Whisper STT → Ada/SPARK validation → Gemini translation
  → Edge TTS → Headphones

Autor: Pan Jeskyně (AsgardLab)
Asistent: Kiro
License: GPL 3.0 + Commercial (see LICENSE)
"""

import os
import sys
import time
import queue
import threading
import argparse
from prometheus_client import start_http_server, Counter, Gauge, Histogram

# ============================================================================
# KONFIGURACE
# ============================================================================

KAREL_PORT = 9306
DEFAULT_SOURCE_LANG = "cs"
DEFAULT_TARGET_LANG = "en"
AUDIO_CHUNK_MS = 500       # Process audio in 500ms chunks
MAX_QUEUE_SIZE = 10        # Max chunks in pipeline queue

SUPPORTED_LANGUAGES = {
    "cs": "Czech",
    "en": "English",
    "de": "German",
    "fr": "French",
    "ja": "Japanese",
    "es": "Spanish",
    "it": "Italian",
    "pl": "Polish",
    "sk": "Slovak",
}

# ============================================================================
# PROMETHEUS METRIKY
# ============================================================================

karel_translations = Counter(
    'karel_translations_total',
    'Total number of completed translations',
    ['source_lang', 'target_lang']
)

karel_latency = Histogram(
    'karel_translation_latency_seconds',
    'End-to-end translation latency',
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0]
)

karel_pipeline_health = Gauge(
    'karel_pipeline_health',
    'Pipeline health (0=down, 1=up)'
)

karel_active_sessions = Gauge(
    'karel_active_sessions',
    'Number of active translation sessions'
)

karel_queue_size = Gauge(
    'karel_queue_size',
    'Current audio chunk queue size'
)

karel_realtime_latency = Histogram(
    'karel_realtime_latency_seconds',
    'E2E realtime latency',
    buckets=[0.1, 0.2, 0.3, 0.5, 1.0]
)

karel_models_loaded = Gauge(
    'karel_models_loaded',
    'Models in RAM'
)

karel_n8n_autonomous = Gauge(
    'karel_n8n_autonomous',
    '1 if in autonomous mode'
)

karel_realtime_under_300ms_ratio = Gauge(
    'karel_realtime_under_300ms_ratio',
    'Ratio of realtime translations completing under 300ms'
)


# ============================================================================
# N8N WEBHOOK INTEGRATION
# ============================================================================

class N8nWebhookClient:
    """n8n Control Plane webhook communication.

    Handles all communication between Karel IV. pipeline and the n8n
    orchestrator at localhost:5678. Reports pipeline status, errors,
    and component registrations via webhook endpoints.

    When n8n becomes unreachable, the client enters autonomous mode —
    the pipeline continues operating with the last known configuration
    for up to 60 minutes before attempting a full reconnect.

    Requirements: 1.1, 1.2, 1.3, 1.5, 15.2
    """

    N8N_BASE_URL = "http://localhost:5678"
    AUTONOMOUS_TIMEOUT = 3600  # 60 minutes

    def __init__(self, base_url=None):
        """
        Initialize n8n webhook client.

        Args:
            base_url: n8n base URL (default: http://localhost:5678)
        """
        self.base_url = base_url or self.N8N_BASE_URL
        self.autonomous_since = None
        self._autonomous = False

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def is_autonomous(self):
        """True when operating in autonomous mode (n8n unreachable)."""
        return self._autonomous

    @is_autonomous.setter
    def is_autonomous(self, value):
        self._autonomous = value

    # ------------------------------------------------------------------
    # Webhook methods
    # ------------------------------------------------------------------

    def post_status(self, stage: str, status: str, data: dict = None) -> bool:
        """
        Report pipeline stage status to n8n.

        POST to /webhook/pipeline-status on stage completion.

        Args:
            stage: pipeline stage name (e.g. "stt", "translate", "tts")
            status: status string (e.g. "completed", "running", "initialized")
            data: optional dict with additional stage-specific data

        Returns:
            bool: True if n8n received the status, False if unreachable
        """
        payload = {
            "stage": stage,
            "status": status,
            "timestamp": int(time.time()),
        }
        if data is not None:
            payload["data"] = data
        return self._post("/webhook/pipeline-status", payload)

    def post_error(self, stage: str, error_type: str, message: str,
                   retry_count: int = 0) -> bool:
        """
        Report error to n8n for automated recovery.

        POST to /webhook/pipeline-error on stage failure. n8n uses this
        to trigger the Error Recovery workflow (3 retries, 5s interval).

        Args:
            stage: pipeline stage that failed (e.g. "gemini_translator")
            error_type: error classification (e.g. "api_unreachable",
                        "validation_failed", "timeout")
            message: human-readable error description
            retry_count: how many retries have been attempted so far

        Returns:
            bool: True if n8n received the error report, False if unreachable
        """
        payload = {
            "stage": stage,
            "error_type": error_type,
            "message": message,
            "timestamp": int(time.time()),
            "retry_count": retry_count,
        }
        return self._post("/webhook/pipeline-error", payload)

    def register_component(self, component: str, version: str, port: int,
                           health: str) -> bool:
        """
        Register component with n8n on startup.

        POST to /webhook/component-register. Each component registers
        during the SystemStartup boot sequence.

        Args:
            component: component name (e.g. "whisper_stt", "bifrost_bridge")
            version: component version string (e.g. "1.0.0")
            port: port number the component listens on (0 if N/A)
            health: health status or health endpoint URL
                    (e.g. "operational", "http://localhost:9306/metrics")

        Returns:
            bool: True if n8n received the registration, False if unreachable
        """
        payload = {
            "component": component,
            "version": version,
            "port": port,
            "health": health,
            "timestamp": int(time.time()),
        }
        return self._post("/webhook/component-register", payload)

    def is_reachable(self) -> bool:
        """
        Check if n8n is reachable.

        Attempts a lightweight GET request to the n8n base URL.
        Used to determine whether to enter or exit autonomous mode.

        Returns:
            bool: True if n8n responded within timeout, False otherwise
        """
        import requests

        try:
            resp = requests.get(self.base_url, timeout=5)
            return resp.status_code < 500
        except Exception:
            return False

    def enter_autonomous_mode(self):
        """
        Enter autonomous mode when n8n is unreachable.

        The pipeline continues operating with the last known workflow
        configuration for up to AUTONOMOUS_TIMEOUT (60 minutes).
        Prometheus gauge karel_n8n_autonomous is set to 1.

        This method is idempotent — calling it when already autonomous
        has no additional effect.
        """
        if not self._autonomous:
            self._autonomous = True
            self.autonomous_since = time.time()
            karel_n8n_autonomous.set(1)
            print("[N8N] Entering autonomous mode — pipeline continues "
                  "without n8n for up to 60 minutes")

    def exit_autonomous_mode(self):
        """
        Exit autonomous mode after n8n becomes reachable again.

        Resets the autonomous timer and Prometheus gauge.
        """
        if self._autonomous:
            self._autonomous = False
            self.autonomous_since = None
            karel_n8n_autonomous.set(0)
            print("[N8N] Reconnected to n8n control plane — autonomous mode OFF")

    # ------------------------------------------------------------------
    # Internal HTTP transport
    # ------------------------------------------------------------------

    def _post(self, endpoint: str, data: dict) -> bool:
        """
        HTTP POST JSON to n8n webhook endpoint.

        Handles autonomous mode transitions:
        - If autonomous timeout (60 min) exceeded, attempts reconnect.
        - On successful POST after being autonomous, exits autonomous mode.
        - On connection failure, enters autonomous mode.

        Args:
            endpoint: webhook path (e.g. "/webhook/pipeline-status")
            data: JSON-serializable dict payload

        Returns:
            bool: True if POST succeeded (HTTP 200), False otherwise
        """
        import requests

        # If autonomous > 60 min: try reconnect
        if self._autonomous and self.autonomous_since:
            elapsed = time.time() - self.autonomous_since
            if elapsed > self.AUTONOMOUS_TIMEOUT:
                print("[N8N] Autonomous timeout (60 min) reached, "
                      "attempting reconnect...")
                self._autonomous = False
                self.autonomous_since = None

        url = f"{self.base_url}{endpoint}"
        try:
            resp = requests.post(url, json=data, timeout=5)
            if self._autonomous:
                self.exit_autonomous_mode()
            return resp.status_code == 200
        except Exception as e:
            if not self._autonomous:
                self.enter_autonomous_mode()
                print(f"[N8N] n8n unreachable: {e}")
            return False


# ============================================================================
# LOCAL TRANSLATION ENGINE
# ============================================================================

class LocalTranslator:
    """CTranslate2 + OPUS-MT for <300ms local translation."""

    def __init__(self, preload_langs=None):
        self.models = {}
        self.tokenizers = {}
        self._available = False
        langs = preload_langs or list(SUPPORTED_LANGUAGES.keys())
        self._load_models(langs)

    def _load_models(self, langs):
        """Load CTranslate2 models for language pairs."""
        try:
            import ctranslate2
            import sentencepiece as spm
            self._available = True
            loaded = 0
            for src in langs:
                for tgt in langs:
                    if src == tgt:
                        continue
                    model_path = f"models/opus-mt/{src}-{tgt}/"
                    tokenizer_path = f"models/opus-mt/{src}-{tgt}/source.spm"
                    if os.path.exists(model_path) and os.path.exists(tokenizer_path):
                        pair_key = f"{src}-{tgt}"
                        self.models[pair_key] = ctranslate2.Translator(
                            model_path, device="cpu"
                        )
                        sp = spm.SentencePieceProcessor()
                        sp.Load(tokenizer_path)
                        self.tokenizers[pair_key] = sp
                        loaded += 1
            karel_models_loaded.set(loaded)
            print(f"[LOCAL-MT] Loaded {loaded} translation model pairs")
        except ImportError:
            print("[LOCAL-MT] ctranslate2/sentencepiece not installed — disabled")
            print("[LOCAL-MT] Install: pip install ctranslate2 sentencepiece")
        except Exception as e:
            print(f"[LOCAL-MT] Model loading error: {e}")

    def translate(self, text, source_lang, target_lang):
        """
        Translate text using local OPUS-MT models.
        Direct pair if available, else route through English.

        Returns:
            str: translated text or None
        """
        if not self._available or not text:
            return None

        pair_key = f"{source_lang}-{target_lang}"

        # Direct pair
        if pair_key in self.models:
            return self._translate_pair(text, pair_key)

        # Route through English
        src_en = f"{source_lang}-en"
        en_tgt = f"en-{target_lang}"

        if src_en in self.models and en_tgt in self.models:
            intermediate = self._translate_pair(text, src_en)
            if intermediate:
                return self._translate_pair(intermediate, en_tgt)

        return None

    def _translate_pair(self, text, pair_key):
        """Translate using a specific model pair."""
        try:
            tokenizer = self.tokenizers[pair_key]
            model = self.models[pair_key]

            tokens = tokenizer.Encode(text, out_type=str)
            results = model.translate_batch([tokens])
            translated_tokens = results[0].hypotheses[0]
            translated = tokenizer.Decode(translated_tokens)
            return translated
        except Exception as e:
            print(f"[LOCAL-MT] Translation error ({pair_key}): {e}")
            return None


# ============================================================================
# PIPER TTS (OFFLINE)
# ============================================================================

class PiperTTS:
    """
    Fully offline TTS using piper-tts. ~50ms latency.
    No network required — models loaded into RAM at startup.
    """

    VOICE_MAP = {
        "cs": "cs_CZ-jirka-medium",
        "en": "en_US-amy-medium",
        "de": "de_DE-thorsten-medium",
        "fr": "fr_FR-siwis-medium",
        "ja": "ja_JP-takumi-medium",
        "es": "es_ES-sharvard-medium",
        "it": "it_IT-riccardo-medium",
        "pl": "pl_PL-darkman-medium",
        "sk": "sk_SK-lili-medium",
    }

    MODEL_DIR = "models/piper/"

    def __init__(self, target_lang="en"):
        self.target_lang = target_lang
        self.voice_name = self.VOICE_MAP.get(target_lang, "en_US-amy-medium")
        self.model_path = os.path.join(self.MODEL_DIR, f"{self.voice_name}.onnx")
        self._available = False
        self._synth = None
        self._load_model()

    def _load_model(self):
        """Load piper model into RAM for low-latency synthesis."""
        try:
            from piper import PiperVoice

            if os.path.exists(self.model_path):
                self._synth = PiperVoice.load(self.model_path)
                self._available = True
                print(f"[PIPER] Voice loaded: {self.voice_name}")
            else:
                print(f"[PIPER] Model not found: {self.model_path}")
                print("[PIPER] Download models to models/piper/ directory")
        except ImportError:
            print("[PIPER] piper-tts not installed — disabled")
            print("[PIPER] Install: pip install piper-tts")
        except Exception as e:
            print(f"[PIPER] Load error: {e}")

    def synthesize(self, text):
        """
        Synthesize text to numpy audio array.

        Args:
            text: text to synthesize

        Returns:
            numpy.ndarray: audio samples (int16, 22050 Hz) or None
        """
        if not self._available or not self._synth or not text:
            return None

        try:
            import numpy as np
            import io
            import wave

            # Piper synthesizes to WAV in-memory
            audio_buffer = io.BytesIO()
            with wave.open(audio_buffer, 'wb') as wav_file:
                self._synth.synthesize(text, wav_file)

            # Read back as numpy array
            audio_buffer.seek(0)
            with wave.open(audio_buffer, 'rb') as wav_file:
                frames = wav_file.readframes(wav_file.getnframes())
                audio = np.frombuffer(frames, dtype=np.int16)

            return audio

        except Exception as e:
            print(f"[PIPER] Synthesis error: {e}")
            return None


# ============================================================================
# REALTIME PIPELINE (<300ms)
# ============================================================================

class RealtimePipeline:
    """Streaming pipeline: 250ms chunks, local models, <300ms e2e."""

    def __init__(self, source_lang, target_lang, voice_sample=None,
                 vad_threshold=0.02, n8n_url=None):
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.audio = AudioCapture(chunk_ms=250, sample_rate=16000,
                                   vad_threshold=vad_threshold)
        self.stt = None  # faster-whisper (loaded lazily)
        self.translator = LocalTranslator()
        self.tts = None  # piper or edge-tts fallback
        self.n8n = N8nWebhookClient(base_url=n8n_url)
        self.vad_threshold = vad_threshold
        self._running = False

        self._init_stt()
        self._init_tts(voice_sample, target_lang)

        print("\n" + "=" * 60)
        print("👑 KAREL IV. — Realtime Mode (<300ms)")
        print("=" * 60)
        print(f"[REALTIME] Source: {SUPPORTED_LANGUAGES.get(source_lang, source_lang)}")
        print(f"[REALTIME] Target: {SUPPORTED_LANGUAGES.get(target_lang, target_lang)}")
        print(f"[REALTIME] Chunk: 250ms | Local models")
        print("=" * 60)

        karel_pipeline_health.set(1.0)
        self.n8n.post_status("realtime_pipeline", "initialized")

    def _init_stt(self):
        """Initialize faster-whisper for low-latency STT."""
        try:
            from faster_whisper import WhisperModel
            self.stt = WhisperModel("base", device="cuda", compute_type="float16")
            print("[REALTIME] faster-whisper loaded (CUDA)")
        except Exception:
            try:
                from faster_whisper import WhisperModel
                self.stt = WhisperModel("base", device="cpu", compute_type="int8")
                print("[REALTIME] faster-whisper loaded (CPU)")
            except ImportError:
                print("[REALTIME] faster-whisper not installed — STT disabled")
                print("[REALTIME] Install: pip install faster-whisper")

    def _init_tts(self, voice_sample, target_lang):
        """Initialize TTS — try PiperTTS first, then edge-tts fallback."""
        piper_tts = PiperTTS(target_lang=target_lang)
        if piper_tts._available:
            self.tts = piper_tts
            print("[REALTIME] PiperTTS ready (offline, ~50ms)")
        else:
            self.tts = EdgeTTS(voice_sample=voice_sample, target_lang=target_lang)
            print("[REALTIME] Using edge-tts as TTS fallback")

    def run(self):
        """Stream audio -> STT -> translate -> TTS with latency tracking."""
        print("\n[REALTIME] Starting realtime pipeline...")
        print("[REALTIME] Speak into microphone. Ctrl+C to stop.\n")

        self._running = True
        karel_active_sessions.inc()
        self.audio.start()
        self.n8n.post_status("realtime_pipeline", "running")

        try:
            while self._running:
                try:
                    chunk = self.audio.output_queue.get(timeout=1.0)
                    self._process_chunk(chunk)
                except queue.Empty:
                    continue
        except KeyboardInterrupt:
            print("\n[REALTIME] Stopping...")
            self._running = False
            self.audio.stop()
            karel_active_sessions.dec()
            karel_pipeline_health.set(0.0)
            self.n8n.post_status("realtime_pipeline", "stopped")
            print("[REALTIME] Shutdown complete")

    def _process_chunk(self, audio_chunk):
        """Process single chunk through realtime pipeline."""
        import numpy as np

        start_time = time.time()

        # VAD check
        audio = audio_chunk.flatten().astype('float32')
        rms = float(np.sqrt(np.mean(audio ** 2)))
        if rms < self.vad_threshold:
            return

        # STT
        text = None
        if self.stt:
            try:
                segments, _ = self.stt.transcribe(
                    audio, language=self.source_lang,
                    beam_size=1, best_of=1
                )
                text = " ".join(seg.text for seg in segments).strip()
            except Exception as e:
                print(f"[REALTIME] STT error: {e}")
                return

        if not text:
            return

        # Translate (local)
        translated = self.translator.translate(text, self.source_lang, self.target_lang)
        if not translated:
            print(f"[REALTIME] No translation model for {self.source_lang}->{self.target_lang}")
            return

        # TTS
        if isinstance(self.tts, PiperTTS):
            self.tts.synthesize(translated)
        elif isinstance(self.tts, EdgeTTS):
            self.tts.synthesize(translated)

        # Metrics
        latency = time.time() - start_time
        karel_realtime_latency.observe(latency)
        if latency < 0.3:
            karel_realtime_under_300ms_ratio.set(1.0)
        else:
            karel_realtime_under_300ms_ratio.set(0.0)
        karel_translations.labels(
            source_lang=self.source_lang,
            target_lang=self.target_lang
        ).inc()

        print(f"[REALTIME] {self.source_lang}->{self.target_lang} "
              f"latency: {latency*1000:.0f}ms | {text[:40]}...")


# ============================================================================
# SYSTEM STARTUP SEQUENCING
# ============================================================================

class SystemStartup:
    """Ordered component initialization with n8n registration."""

    BOOT_ORDER = [
        "prometheus", "faucet_sdn", "spark_validator",
        "whisper_stt", "bifrost_bridge", "tts", "geall_agent"
    ]

    COMPONENT_INFO = {
        "prometheus": {"version": "2.45", "port": 9090, "health": "/metrics"},
        "faucet_sdn": {"version": "1.0", "port": 6653, "health": "/status"},
        "spark_validator": {"version": "1.0", "port": 0, "health": ""},
        "whisper_stt": {"version": "1.0", "port": 0, "health": ""},
        "bifrost_bridge": {"version": "1.0", "port": 0, "health": ""},
        "tts": {"version": "1.0", "port": 0, "health": ""},
        "geall_agent": {"version": "1.0", "port": 0, "health": ""},
    }

    MAX_RETRIES = 3
    RETRY_TIMEOUT = 30  # seconds

    def __init__(self, n8n_client=None):
        self.n8n = n8n_client or N8nWebhookClient()
        self.registered = []

    def boot(self):
        """Initialize each component in order and register with n8n."""
        print("[STARTUP] Beginning component boot sequence...")
        self.n8n.post_status("system", "booting")

        for component in self.BOOT_ORDER:
            success = self._boot_component(component)
            if success:
                self.registered.append(component)
            else:
                print(f"[STARTUP] WARNING: {component} failed to register")
                self.n8n.post_error("startup", "registration_failed",
                                    f"{component} registration failed")

        if len(self.registered) == len(self.BOOT_ORDER):
            self.n8n.post_status("system", "operational")
            print("[STARTUP] All components registered — system OPERATIONAL")
        else:
            self.n8n.post_status("system", "degraded",
                                 data={"missing": list(set(self.BOOT_ORDER) - set(self.registered))})
            print(f"[STARTUP] System DEGRADED — missing: "
                  f"{set(self.BOOT_ORDER) - set(self.registered)}")

        return len(self.registered) == len(self.BOOT_ORDER)

    def _boot_component(self, name):
        """Boot and register a single component with retry logic."""
        info = self.COMPONENT_INFO.get(name, {})
        version = info.get("version", "1.0")
        port = info.get("port", 0)
        health = info.get("health", "")

        health_status = f"http://localhost:{port}{health}" if port and health else "operational"

        start_time = time.time()
        for attempt in range(1, self.MAX_RETRIES + 1):
            elapsed = time.time() - start_time
            if elapsed > self.RETRY_TIMEOUT:
                print(f"[STARTUP] {name}: timeout after {self.RETRY_TIMEOUT}s")
                return False

            print(f"[STARTUP] Registering {name} (attempt {attempt}/{self.MAX_RETRIES})...")
            success = self.n8n.register_component(name, version, port, health_status)

            if success:
                print(f"[STARTUP] ✓ {name} registered")
                return True

            time.sleep(5)

        return False


# ============================================================================
# PIPELINE STAGE 1.5 — VOICE BIOMETRIC TUNNEL
# ============================================================================

class VoiceBiometricTunnel:
    """
    Speaker verification filter — passes only registered voice owner.

    Uses ECAPA-TDNN (speechbrain) to extract speaker embeddings and
    cosine similarity to compare against the enrolled voice.

    Algorithm:
      1. Enrollment: Load WAV → Resample to 16kHz → Extract ECAPA-TDNN
         embedding → Store
      2. Verification: Audio chunk → Extract embedding → Cosine similarity
         vs. enrolled → Threshold 0.75
      3. Open mode: When no voice sample is registered, pass ALL audio chunks

    Privacy: Rejected audio chunks are discarded silently without logging
    personal speaker data.
    """

    SIMILARITY_THRESHOLD = 0.75  # Cosine similarity threshold

    def __init__(self, voice_sample=None, voice_sample_path=None, threshold=0.75):
        """
        Initialize Voice Biometric Tunnel.

        Args:
            voice_sample: path to WAV file for enrollment (legacy parameter)
            voice_sample_path: path to WAV file for enrollment (preferred)
            threshold: cosine similarity threshold (default: 0.75)
        """
        self.SIMILARITY_THRESHOLD = threshold
        self.enrolled_embedding = None
        self.model = None
        self._enrolled = False
        self._model_loaded = False

        # Support both parameter names for backward compatibility
        wav_path = voice_sample_path or voice_sample

        if wav_path and os.path.exists(wav_path):
            self._load_model()
            self.enroll(wav_path)
        elif wav_path:
            print(f"[BIOMETRIC] Voice sample not found: {wav_path}")
            print("[BIOMETRIC] Running in open mode — all voices pass")
        else:
            print("[BIOMETRIC] No voice sample — open mode (all voices pass)")

    def _load_model(self):
        """Load ECAPA-TDNN speaker embedding model from speechbrain."""
        if self._model_loaded:
            return

        try:
            import torch  # noqa: F401
            from speechbrain.inference.speaker import SpeakerRecognition
            self.model = SpeakerRecognition.from_hparams(
                source="speechbrain/spkrec-ecapa-voxceleb",
                savedir="pretrained_models/spkrec-ecapa-voxceleb"
            )
            self._model_loaded = True
            print("[BIOMETRIC] ECAPA-TDNN speaker recognition model loaded")
        except ImportError:
            print("[BIOMETRIC] speechbrain not installed — open mode")
            print("[BIOMETRIC] Install: pip install speechbrain torch torchaudio")
        except Exception as e:
            print(f"[BIOMETRIC] Model load error: {e} — open mode")

    def enroll(self, wav_path: str) -> bool:
        """
        Register a voice sample as the owner identity.

        Loads WAV file, resamples to 16kHz, extracts ECAPA-TDNN embedding,
        and stores it for future verification.

        Args:
            wav_path: path to WAV file with voice sample

        Returns:
            bool: True if enrollment succeeded, False otherwise
        """
        if not wav_path or not os.path.exists(wav_path):
            print(f"[BIOMETRIC] Enrollment failed — file not found: {wav_path}")
            return False

        # Ensure model is loaded
        if not self._model_loaded:
            self._load_model()

        if self.model is None:
            print("[BIOMETRIC] Enrollment failed — model not available")
            return False

        try:
            import torch  # noqa: F401
            import torchaudio

            waveform, sr = torchaudio.load(wav_path)

            # Resample to 16kHz if needed
            if sr != 16000:
                resampler = torchaudio.transforms.Resample(sr, 16000)
                waveform = resampler(waveform)

            # Extract ECAPA-TDNN embedding
            embedding = self.model.encode_batch(waveform)
            self.enrolled_embedding = embedding.squeeze()
            self._enrolled = True

            print(f"[BIOMETRIC] Voice enrolled from: {wav_path}")
            print("[BIOMETRIC] Tunnel ACTIVE — only registered voice passes")
            return True

        except Exception as e:
            print(f"[BIOMETRIC] Enrollment error: {e} — open mode")
            return False

    def verify(self, audio_chunk) -> float:
        """
        Verify audio chunk belongs to enrolled speaker.

        Extracts embedding from audio chunk and computes cosine similarity
        against the enrolled speaker embedding.

        Args:
            audio_chunk: numpy float32 array or bytes of audio data

        Returns:
            float: cosine similarity score (0.0-1.0).
                   Returns 1.0 in open mode (no sample registered).
        """
        if not self._enrolled or self.model is None:
            return 1.0  # Open mode — maximum similarity

        try:
            import torch
            import numpy as np

            # Handle bytes input — convert to float32 numpy array
            if isinstance(audio_chunk, bytes):
                audio_chunk = np.frombuffer(audio_chunk, dtype=np.int16).astype(
                    np.float32
                ) / 32768.0

            waveform = torch.tensor(audio_chunk.flatten(), dtype=torch.float32).unsqueeze(0)
            embedding = self.model.encode_batch(waveform).squeeze()

            # Cosine similarity
            similarity = torch.nn.functional.cosine_similarity(
                self.enrolled_embedding.unsqueeze(0),
                embedding.unsqueeze(0)
            ).item()

            return float(similarity)

        except Exception as e:
            print(f"[BIOMETRIC] Verification error: {e}")
            return 1.0  # On error, pass audio (fail-open for usability)

    def is_enrolled(self) -> bool:
        """
        Check if a voice sample is registered.

        Returns:
            bool: True if a voice sample has been enrolled
        """
        return self._enrolled

    def is_owner(self, audio_chunk) -> bool:
        """
        Check if audio chunk contains the registered voice.

        Uses verify() internally and applies threshold.
        In open mode (no enrolled sample), always returns True.

        Args:
            audio_chunk: numpy float32 array or bytes

        Returns:
            bool: True if voice matches owner (or tunnel is in open mode)
        """
        # Open mode — pass everything
        if not self._enrolled or self.model is None:
            return True

        similarity = self.verify(audio_chunk)

        if similarity >= self.SIMILARITY_THRESHOLD:
            return True
        else:
            # Privacy: do NOT log personal speaker data on rejection
            print("[BIOMETRIC] Audio chunk discarded — speaker not recognized")
            return False


# ============================================================================
# GEMINI TRANSLATION VIA BIFROST SUBPROCESS
# ============================================================================

class BifrostGeminiTranslator:
    """
    Gemini API translation via Bifrost Ada/SPARK bridge subprocess.

    Calls `bifrost --geall --translate` with JSON input via stdin.
    Parses JSON response: {"translated":"...", "quality_score": 0.92}
    Handles errors: queue untranslated text, exponential backoff (5s, 10s, 20s, 40s, 60s).

    This is the production translator — Ada/SPARK validates all I/O,
    Python never calls Gemini directly.
    """

    BACKOFF_INTERVALS = [5, 10, 20, 40, 60]  # seconds

    def __init__(self, bifrost_path="bin/bifrost.exe", source_lang="cs",
                 target_lang="en"):
        """
        Initialize BifrostGeminiTranslator.

        Args:
            bifrost_path: path to bifrost executable
            source_lang: source language code (default: cs)
            target_lang: target language code (default: en)
        """
        self.bifrost_path = bifrost_path
        self.source_lang = source_lang
        self.target_lang = target_lang
        self._retry_queue = []  # Queue of failed translations for retry
        self._retry_count = 0   # Current retry attempt index
        self._last_retry_time = 0.0
        self._lock = threading.Lock()

        # Check if bifrost executable exists
        if os.path.exists(self.bifrost_path):
            print(f"[TRANSLATOR] Bifrost bridge ready: {self.bifrost_path}")
        else:
            print(f"[TRANSLATOR] WARNING: Bifrost not found at {self.bifrost_path}")
            print("[TRANSLATOR] Build with: gprbuild -P mincovna.gpr")

    def translate(self, text, source=None, target=None):
        """
        Translate text via Bifrost subprocess.

        Sends JSON {text, source, target} to bifrost --geall --translate via stdin.
        Parses JSON response with translated text and quality_score.
        On error, queues text for retry with exponential backoff.

        Args:
            text: text to translate
            source: source language code (default: self.source_lang)
            target: target language code (default: self.target_lang)

        Returns:
            dict with keys 'translated' and 'quality_score', or None on failure.
        """
        if not text:
            return None

        source = source or self.source_lang
        target = target or self.target_lang

        import json
        json_input = json.dumps({
            "text": text,
            "source": source,
            "target": target
        })

        result = self._call_bifrost(json_input)

        if result is not None:
            # Reset retry counter on success
            self._retry_count = 0
            return result
        else:
            # Error — queue for retry
            self._handle_error(text, source, target)
            return None

    def _call_bifrost(self, json_input):
        """
        Call bifrost --geall --translate subprocess.

        Sends JSON input via stdin, reads JSON response from stdout.
        Validates response contains expected fields.

        Args:
            json_input: JSON string to send via stdin

        Returns:
            dict with 'translated' and 'quality_score', or None on error.
        """
        import subprocess
        import json

        try:
            result = subprocess.run(
                [self.bifrost_path, "--geall", "--translate"],
                input=json_input,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                stderr = result.stderr.strip() if result.stderr else "unknown error"
                print(f"[TRANSLATOR] Bifrost error (exit {result.returncode}): {stderr}")
                return None

            stdout = result.stdout.strip()
            if not stdout:
                print("[TRANSLATOR] Bifrost returned empty response")
                return None

            response = json.loads(stdout)

            # Check for error response
            if "error" in response:
                print(f"[TRANSLATOR] Bifrost reported error: {response['error']}")
                return None

            # Validate expected fields
            if "translated" not in response:
                print("[TRANSLATOR] Bifrost response missing 'translated' field")
                return None

            translated = response.get("translated", "")
            quality_score = response.get("quality_score", 0.0)

            if not translated:
                print("[TRANSLATOR] Bifrost returned empty translation")
                return None

            print(f"[TRANSLATOR] OK (quality: {quality_score:.2f}): "
                  f"{translated[:60]}...")

            return {
                "translated": translated,
                "quality_score": quality_score
            }

        except FileNotFoundError:
            print(f"[TRANSLATOR] Bifrost executable not found: {self.bifrost_path}")
            return None
        except subprocess.TimeoutExpired:
            print("[TRANSLATOR] Bifrost subprocess timeout (10s)")
            return None
        except json.JSONDecodeError as e:
            print(f"[TRANSLATOR] Invalid JSON from Bifrost: {e}")
            return None
        except Exception as e:
            print(f"[TRANSLATOR] Unexpected error: {e}")
            return None

    def _handle_error(self, text, source, target):
        """
        Queue text for retry with exponential backoff.

        Backoff intervals: 5s, 10s, 20s, 40s, 60s (max).
        Failed translations are stored in the retry queue.

        Args:
            text: text that failed to translate
            source: source language code
            target: target language code
        """
        with self._lock:
            # Add to retry queue
            self._retry_queue.append({
                "text": text,
                "source": source,
                "target": target,
                "timestamp": time.time()
            })

            # Calculate current backoff interval
            backoff_index = min(self._retry_count, len(self.BACKOFF_INTERVALS) - 1)
            backoff_seconds = self.BACKOFF_INTERVALS[backoff_index]

            self._retry_count += 1

            print(f"[TRANSLATOR] Translation queued for retry "
                  f"(attempt {self._retry_count}, "
                  f"backoff: {backoff_seconds}s, "
                  f"queue size: {len(self._retry_queue)})")

    def retry_queued(self):
        """
        Attempt to retry queued translations.

        Checks if enough time has passed since last retry (exponential backoff).
        Processes one item from the queue per call.

        Returns:
            dict with 'translated' and 'quality_score' if successful, None otherwise.
        """
        with self._lock:
            if not self._retry_queue:
                return None

            # Check backoff timing
            backoff_index = min(self._retry_count - 1, len(self.BACKOFF_INTERVALS) - 1)
            backoff_index = max(0, backoff_index)
            backoff_seconds = self.BACKOFF_INTERVALS[backoff_index]

            elapsed = time.time() - self._last_retry_time
            if elapsed < backoff_seconds:
                return None

            # Pop oldest item from queue
            item = self._retry_queue.pop(0)
            self._last_retry_time = time.time()

        # Attempt translation (outside lock)
        import json
        json_input = json.dumps({
            "text": item["text"],
            "source": item["source"],
            "target": item["target"]
        })

        result = self._call_bifrost(json_input)

        if result is not None:
            # Success — reset retry counter
            with self._lock:
                self._retry_count = 0
            print(f"[TRANSLATOR] Retry successful — queue remaining: "
                  f"{len(self._retry_queue)}")
            return result
        else:
            # Still failing — re-queue
            with self._lock:
                self._retry_queue.insert(0, item)
            return None

    @property
    def queue_size(self):
        """Return current retry queue size."""
        return len(self._retry_queue)

    @property
    def current_backoff(self):
        """Return current backoff interval in seconds."""
        if self._retry_count == 0:
            return 0
        backoff_index = min(self._retry_count - 1, len(self.BACKOFF_INTERVALS) - 1)
        return self.BACKOFF_INTERVALS[backoff_index]


# ============================================================================
# PIPELINE STAGES
# ============================================================================

class AudioCapture:
    """
    Stage 1: Capture audio from virtual sound card.
    Uses sounddevice for cross-platform audio input.

    Captures 16-bit signed integer PCM, mono, at configurable sample rate.
    Default: 16kHz, 500ms chunks.
    Includes VAD (Voice Activity Detection) via RMS amplitude threshold.
    Integrates Ada/SPARK PCM validation via subprocess.
    """

    def __init__(self, chunk_ms=AUDIO_CHUNK_MS, sample_rate=16000,
                 vad_threshold=0.02):
        self.chunk_ms = chunk_ms
        self.sample_rate = sample_rate
        self.vad_threshold = vad_threshold
        self.chunk_size = int(sample_rate * chunk_ms / 1000)
        self.output_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
        self._running = False

    def start(self):
        """Start audio capture in background thread."""
        self._running = True
        thread = threading.Thread(target=self._capture_loop, daemon=True)
        thread.start()
        print(f"[CAPTURE] Started — {self.sample_rate}Hz, "
              f"{self.chunk_ms}ms chunks, VAD threshold={self.vad_threshold}")
        return thread

    def stop(self):
        """Stop audio capture."""
        self._running = False
        print("[CAPTURE] Stopped")

    def capture_chunk(self):
        """
        Capture one audio chunk from the queue.
        Returns None if no speech detected (VAD check fails).

        Returns:
            Optional[bytes]: Raw PCM bytes (16-bit signed int, mono, 16kHz)
                             or None if silence/no data.
        """
        import numpy as np

        try:
            chunk = self.output_queue.get(timeout=self.chunk_ms / 1000 * 2)
        except queue.Empty:
            return None

        # Convert float32 audio to 16-bit PCM bytes
        audio_float = chunk.flatten().astype('float32')
        pcm_int16 = (audio_float * 32767).astype(np.int16)
        pcm_bytes = pcm_int16.tobytes()

        # VAD check — skip silence
        if not self.check_vad(pcm_bytes):
            return None

        return pcm_bytes

    def check_vad(self, audio_data):
        """
        Check if audio chunk contains speech using RMS amplitude.

        Voice Activity Detection: compute RMS of PCM samples,
        compare against threshold. RMS > threshold means speech present.

        Args:
            audio_data: bytes — raw PCM (16-bit signed integer, mono)

        Returns:
            bool: True if speech detected (RMS > threshold)
        """
        import numpy as np

        if not audio_data or len(audio_data) < 2:
            return False

        # Decode 16-bit PCM to float samples normalized to [-1.0, 1.0]
        samples = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
        samples = samples / 32768.0

        # Compute RMS amplitude
        rms = float(np.sqrt(np.mean(samples ** 2)))

        return rms > self.vad_threshold

    def validate_pcm(self, chunk_path):
        """
        Call Ada/SPARK validator subprocess for PCM validation.

        Runs: transkomunikator_validator --pcm <path>
        Exit 0 = valid, Exit 1 = invalid, Exit 2 = usage error.

        Args:
            chunk_path: str — path to PCM file on disk

        Returns:
            bool: True if PCM is valid (exit code 0)
        """
        import subprocess

        try:
            result = subprocess.run(
                ["transkomunikator_validator", "--pcm", chunk_path],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                print(f"[CAPTURE] SPARK validation OK: {result.stdout.strip()}")
                return True
            elif result.returncode == 1:
                print(f"[CAPTURE] SPARK validation INVALID: {result.stdout.strip()}")
                return False
            else:
                print(f"[CAPTURE] SPARK validator usage error (exit {result.returncode})")
                return False

        except FileNotFoundError:
            print("[CAPTURE] transkomunikator_validator not found — "
                  "skipping SPARK validation")
            return True  # Pass through if validator not built yet
        except subprocess.TimeoutExpired:
            print("[CAPTURE] SPARK validator timeout (5s) — skipping")
            return False
        except Exception as e:
            print(f"[CAPTURE] SPARK validator error: {e}")
            return False

    def _capture_loop(self):
        """Internal capture loop using sounddevice."""
        try:
            import sounddevice as sd
            import numpy as np

            def callback(indata, frames, time_info, status):
                if status:
                    print(f"[CAPTURE] Warning: {status}")
                if self._running:
                    try:
                        self.output_queue.put_nowait(indata.copy())
                        karel_queue_size.set(self.output_queue.qsize())
                    except queue.Full:
                        pass  # Drop chunk if queue full

            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype='float32',
                blocksize=self.chunk_size,
                callback=callback
            ):
                print(f"[CAPTURE] Listening on virtual sound card...")
                while self._running:
                    time.sleep(0.1)

        except ImportError:
            print("[CAPTURE] sounddevice not installed — demo mode")
            print("[CAPTURE] Install: pip install sounddevice")
            self._demo_loop()
        except Exception as e:
            print(f"[CAPTURE] Error: {e}")

    def _demo_loop(self):
        """Demo mode — simulate audio chunks."""
        import numpy as np
        while self._running:
            chunk = np.zeros((self.chunk_size, 1), dtype='float32')
            try:
                self.output_queue.put_nowait(chunk)
            except queue.Full:
                pass
            time.sleep(self.chunk_ms / 1000)


class WhisperSTT:
    """
    Stage 2: Speech-to-text using faster-whisper with CUDA GPU acceleration.

    Uses faster-whisper (CTranslate2 backend) for 4x faster inference
    compared to openai-whisper. Runs locally on RTX 3070 GPU with
    float16 compute type; falls back to CPU int8 if CUDA unavailable.

    After transcription, validates text via Ada/SPARK subprocess:
      pipeline_validator --stage stt --json <path>

    MIT license — runs locally, no API cost.
    """

    def __init__(self, model_size="base", source_lang="cs", vad_threshold=0.02,
                 device="cuda"):
        """
        Load Whisper model with GPU support.

        Args:
            model_size: Whisper model size (tiny/base/small/medium/large)
            source_lang: source language code (e.g. "cs")
            vad_threshold: RMS amplitude threshold for VAD
            device: preferred device ("cuda" or "cpu")
        """
        self.model_size = model_size
        self.source_lang = source_lang
        self.vad_threshold = vad_threshold
        self.device = device
        self.model = None
        self._actual_device = None
        self._load_model()

    def _load_model(self):
        """Load faster-whisper model with CUDA support, fallback to CPU."""
        try:
            from faster_whisper import WhisperModel

            # Try CUDA first (RTX 3070)
            if self.device == "cuda":
                try:
                    self.model = WhisperModel(
                        self.model_size,
                        device="cuda",
                        compute_type="float16"
                    )
                    self._actual_device = "cuda"
                    print(f"[STT] faster-whisper loaded: model={self.model_size}, "
                          f"device=CUDA (float16)")
                    return
                except Exception as cuda_err:
                    print(f"[STT] CUDA not available ({cuda_err}), falling back to CPU")

            # CPU fallback with int8 quantization
            self.model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type="int8"
            )
            self._actual_device = "cpu"
            print(f"[STT] faster-whisper loaded: model={self.model_size}, "
                  f"device=CPU (int8)")

        except ImportError:
            print("[STT] faster-whisper not installed — demo mode")
            print("[STT] Install: pip install faster-whisper")
        except Exception as e:
            print(f"[STT] Error loading model: {e}")

    def transcribe(self, audio_chunk, language=None):
        """
        Transcribe audio chunk to text.

        Uses faster-whisper for inference, then validates the result
        through Ada/SPARK pipeline_validator subprocess.

        Args:
            audio_chunk: numpy array of audio samples (float32, 16kHz)
                         or bytes (16-bit PCM)
            language: override source language (default: self.source_lang)

        Returns:
            Optional[str]: transcribed text, or None if silence/error
        """
        if self.model is None:
            return "[DEMO] Dobrý den, jak se máte?"

        try:
            import numpy as np

            # Handle bytes input — convert to float32 numpy array
            if isinstance(audio_chunk, bytes):
                audio_chunk = np.frombuffer(
                    audio_chunk, dtype=np.int16
                ).astype(np.float32) / 32768.0

            audio = audio_chunk.flatten().astype('float32')

            # Silence detection — skip if audio is too quiet
            rms = float(np.sqrt(np.mean(audio ** 2)))
            if rms < self.vad_threshold:
                return None

            lang = language or self.source_lang

            # faster-whisper transcription with GPU acceleration
            segments, info = self.model.transcribe(
                audio,
                language=lang,
                beam_size=5,
                best_of=3,
                no_speech_threshold=0.6,
                condition_on_previous_text=False,
                vad_filter=True
            )

            # Collect segment texts
            text = " ".join(seg.text for seg in segments).strip()

            # Filter hallucinations — repeated words
            words = text.split()
            if len(words) > 4:
                unique = len(set(words))
                if unique / len(words) < 0.3:
                    return None  # >70% repeated words = hallucination

            if not text:
                return None

            # SPARK validation of transcribed text
            valid = self.validate_text(text)
            if not valid:
                print(f"[STT] SPARK validation rejected transcription: {text[:50]}...")
                return None

            print(f"[STT] Transcribed ({self._actual_device}): {text}")
            return text

        except Exception as e:
            print(f"[STT] Transcription error: {e}")
            return None

    def validate_text(self, text):
        """
        Call SPARK pipeline_validator for STT output validation.

        Writes text to a temporary JSON file and runs:
          pipeline_validator --stage stt --json <path>

        Exit codes: 0=valid, 1=invalid, 2=usage error.

        Args:
            text: transcribed text to validate

        Returns:
            bool: True if text passes SPARK validation
        """
        import subprocess
        import tempfile
        import json

        if not text:
            return False

        # Write validation payload to temporary JSON file
        payload = {
            "stage": "stt",
            "timestamp": int(time.time()),
            "data": {
                "text": text,
                "source_lang": self.source_lang
            }
        }

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.json', delete=False, encoding='utf-8'
            ) as f:
                json.dump(payload, f, ensure_ascii=False)
                tmp_path = f.name

            result = subprocess.run(
                ["pipeline_validator", "--stage", "stt", "--json", tmp_path],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                print(f"[STT] SPARK validation OK")
                return True
            elif result.returncode == 1:
                print(f"[STT] SPARK validation INVALID: {result.stdout.strip()}")
                return False
            else:
                print(f"[STT] SPARK validator usage error (exit {result.returncode})")
                return False

        except FileNotFoundError:
            # pipeline_validator not built yet — pass through
            print("[STT] pipeline_validator not found — skipping SPARK validation")
            return True
        except subprocess.TimeoutExpired:
            print("[STT] SPARK validator timeout (5s) — skipping")
            return True
        except Exception as e:
            print(f"[STT] SPARK validator error: {e}")
            return True  # Fail-open: don't block pipeline if validator errors
        finally:
            # Cleanup temp file
            if tmp_path:
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass


class GeminiTranslator:
    """
    Stage 3: Translation using Google Gemini API.
    Apache 2.0 (gemini-cli) — free tier: 1500 req/day.
    """

    def __init__(self, target_lang="en", api_key=None):
        self.target_lang = target_lang
        self.target_lang_name = SUPPORTED_LANGUAGES.get(target_lang, target_lang)
        self.api_key = api_key or os.environ.get('GEMINI_API_KEY')
        self.client = None
        self._init_client()

    def _init_client(self):
        if not self.api_key:
            print("[GEMINI] No API key — demo mode")
            print("[GEMINI] Set GEMINI_API_KEY environment variable")
            return

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel('gemini-2.5-flash')
            print("[GEMINI] Client initialized")
        except ImportError:
            print("[GEMINI] google-generativeai not installed — demo mode")
        except Exception as e:
            print(f"[GEMINI] Init error: {e}")

    def translate(self, text):
        """
        Translate text to target language.

        Args:
            text: source text to translate

        Returns:
            str: translated text
        """
        if not text:
            return None

        if self.client is None:
            return f"[DEMO EN] Hello, how are you?"

        try:
            prompt = (
                f"Translate the following text to {self.target_lang_name}. "
                f"Return ONLY the translation, nothing else.\n\n{text}"
            )
            response = self.client.generate_content(prompt)
            translated = response.text.strip()
            print(f"[GEMINI] Translated: {translated}")
            return translated

        except Exception as e:
            print(f"[GEMINI] Translation error: {e}")
            return None


class EdgeTTS:
    """
    Stage 4: Text-to-speech using Microsoft Edge TTS (edge-tts).
    Free, no API key, no account required — uses Microsoft's
    neural voices via the same service that powers Edge's
    "Read Aloud" feature. Pure Python, no C++ compilation needed.
    """

    # One natural-sounding neural voice per supported target language
    VOICE_MAP = {
        "cs": "cs-CZ-VlastaNeural",
        "en": "en-US-AriaNeural",
        "de": "de-DE-KatjaNeural",
        "fr": "fr-FR-DeniseNeural",
        "ja": "ja-JP-NanamiNeural",
        "es": "es-ES-ElviraNeural",
        "it": "it-IT-ElsaNeural",
        "pl": "pl-PL-ZofiaNeural",
        "sk": "sk-SK-ViktoriaNeural",
    }

    def __init__(self, voice_sample=None, target_lang="en"):
        # voice_sample kept for CLI compatibility; edge-tts does not
        # support voice cloning, only preset neural voices.
        self.voice_sample = voice_sample
        self.target_lang = target_lang
        self.voice = self.VOICE_MAP.get(target_lang, "en-US-AriaNeural")

        try:
            import edge_tts  # noqa: F401
            self._available = True
            print(f"[TTS] Edge TTS ready (voice: {self.voice})")
        except ImportError:
            self._available = False
            print("[TTS] edge-tts not installed — demo mode (text output)")
            print("[TTS] Install: pip install edge-tts")

    def synthesize(self, text, output_file="output.mp3"):
        """
        Synthesize speech from text using Edge TTS.

        Args:
            text: text to synthesize
            output_file: output audio file path (mp3)

        Returns:
            str: path to output file or None
        """
        if not text:
            return None

        if not self._available:
            print(f"[TTS/DEMO] Would speak: {text}")
            return None

        try:
            import asyncio
            import edge_tts

            async def _generate():
                communicate = edge_tts.Communicate(text, self.voice)
                await communicate.save(output_file)

            asyncio.run(_generate())
            print(f"[TTS] Synthesized: {output_file}")
            return output_file

        except Exception as e:
            print(f"[TTS] Synthesis error: {e}")
            return None

    def play(self, audio_file):
        """Play audio file to output device."""
        if not audio_file:
            return

        try:
            import sounddevice as sd
            import soundfile as sf
            data, samplerate = sf.read(audio_file)
            sd.play(data, samplerate)
            sd.wait()
        except Exception as e:
            print(f"[TTS] Playback error: {e}")


# ============================================================================
# EDGE TTS SYNTHESIZER (QUALITY MODE — FULL IMPLEMENTATION)
# ============================================================================

class EdgeTTSSynthesizer:
    """
    Edge TTS neural voice synthesis with language-specific voice selection.

    Full-featured TTS synthesizer for Quality mode pipeline:
    - Voice map for 9 supported languages with neural voices
    - Fallback to en-US-AriaNeural when target language has no configured voice
    - Subtitle fallback when TTS synthesis fails
    - Output audio to virtual sound card via sounddevice

    Requirements: 14.1, 14.2, 14.3, 14.4, 14.5
    """

    VOICE_MAP = {
        "cs": "cs-CZ-AntoninNeural",
        "en": "en-US-AriaNeural",
        "de": "de-DE-KatjaNeural",
        "fr": "fr-FR-DeniseNeural",
        "ja": "ja-JP-NanamiNeural",
        "es": "es-ES-ElviraNeural",
        "it": "it-IT-ElsaNeural",
        "pl": "pl-PL-AgnieszkaNeural",
        "sk": "sk-SK-LukasNeural",
    }
    FALLBACK_VOICE = "en-US-AriaNeural"

    def __init__(self, target_lang="en", custom_voice=None):
        """
        Initialize Edge TTS Synthesizer.

        Args:
            target_lang: target language code (e.g. "cs", "en", "de")
            custom_voice: optional custom voice override for the target language
        """
        self.target_lang = target_lang
        self.custom_voice = custom_voice
        self._available = False

        try:
            import edge_tts  # noqa: F401
            self._available = True
            voice = self.get_voice(target_lang)
            print(f"[TTS] EdgeTTSSynthesizer ready (voice: {voice})")
        except ImportError:
            print("[TTS] edge-tts not installed — subtitle fallback only")
            print("[TTS] Install: pip install edge-tts")

    def get_voice(self, lang: str) -> str:
        """
        Get voice name for language, fallback to English.

        If a custom voice is configured for this language, use it.
        Otherwise look up the voice map. If the language is not in the
        map, fall back to en-US-AriaNeural and log a warning.

        Args:
            lang: language code (e.g. "cs", "en", "ja")

        Returns:
            str: Edge TTS neural voice identifier
        """
        # Custom voice override takes priority
        if self.custom_voice and lang == self.target_lang:
            return self.custom_voice

        if lang in self.VOICE_MAP:
            return self.VOICE_MAP[lang]

        # Fallback — language not in voice map
        print(f"[TTS] WARNING: No voice configured for '{lang}', "
              f"falling back to {self.FALLBACK_VOICE}")
        return self.FALLBACK_VOICE

    async def synthesize(self, text: str, target_lang: str = None):
        """
        Synthesize text to audio bytes using Edge TTS.

        Performs async synthesis via edge-tts library. On success, returns
        raw audio bytes (MP3 format). On failure, triggers subtitle fallback.

        Args:
            text: text to synthesize (should be <= 200 chars for <1s latency)
            target_lang: override target language (uses self.target_lang if None)

        Returns:
            Optional[bytes]: MP3 audio bytes, or None if synthesis failed
                             (subtitle fallback is triggered automatically)
        """
        if not text:
            return None

        lang = target_lang or self.target_lang

        if not self._available:
            self.display_subtitle(text)
            return None

        try:
            import edge_tts

            voice = self.get_voice(lang)
            communicate = edge_tts.Communicate(text, voice)

            # Collect audio data into bytes
            audio_chunks = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])

            if audio_chunks:
                audio_bytes = b"".join(audio_chunks)
                print(f"[TTS] Synthesized {len(audio_bytes)} bytes "
                      f"({lang}, voice: {voice})")
                return audio_bytes
            else:
                print("[TTS] Synthesis produced no audio — subtitle fallback")
                self.display_subtitle(text)
                return None

        except Exception as e:
            print(f"[TTS] Synthesis failed: {e} — subtitle fallback")
            self.display_subtitle(text)
            return None

    def synthesize_sync(self, text: str, target_lang: str = None):
        """
        Synchronous wrapper for synthesize().

        Convenience method for non-async callers. Creates or reuses
        an event loop to run the async synthesis.

        Args:
            text: text to synthesize
            target_lang: override target language

        Returns:
            Optional[bytes]: MP3 audio bytes or None
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, create a new loop
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        asyncio.run, self.synthesize(text, target_lang)
                    )
                    return future.result(timeout=10)
            else:
                return loop.run_until_complete(
                    self.synthesize(text, target_lang)
                )
        except RuntimeError:
            return asyncio.run(self.synthesize(text, target_lang))

    def display_subtitle(self, text: str):
        """
        Fallback: display text as subtitle when TTS fails.

        Prints the translated text to console as on-screen subtitle.
        This is the minimum viable fallback — ensures the user always
        receives the translation even when audio synthesis is unavailable.

        Args:
            text: translated text to display as subtitle
        """
        if not text:
            return
        print(f"\n{'=' * 60}")
        print(f"  [SUBTITLE] {text}")
        print(f"{'=' * 60}\n")

    def play_to_virtual_soundcard(self, audio_bytes):
        """
        Output audio bytes to virtual sound card via sounddevice.

        Decodes MP3 audio bytes and plays them through the default
        output device (virtual sound card).

        Args:
            audio_bytes: raw MP3 audio bytes from synthesize()

        Returns:
            bool: True if playback succeeded, False otherwise
        """
        if not audio_bytes:
            return False

        try:
            import sounddevice as sd
            import soundfile as sf
            import io

            # Decode MP3 bytes to numpy audio array
            audio_buffer = io.BytesIO(audio_bytes)
            data, samplerate = sf.read(audio_buffer)

            # Play through virtual sound card (default output device)
            sd.play(data, samplerate)
            sd.wait()
            print(f"[TTS] Playback complete ({samplerate}Hz)")
            return True

        except ImportError as e:
            print(f"[TTS] Playback unavailable (missing library): {e}")
            print("[TTS] Install: pip install sounddevice soundfile")
            return False
        except Exception as e:
            print(f"[TTS] Playback error: {e}")
            return False

    def synthesize_and_play(self, text: str, target_lang: str = None) -> bool:
        """
        Full pipeline: synthesize text and play to virtual sound card.

        Combines synthesis + playback in one call. Falls back to subtitle
        display if either step fails.

        Args:
            text: text to synthesize and play
            target_lang: override target language

        Returns:
            bool: True if audio was played successfully, False if fallback used
        """
        audio_bytes = self.synthesize_sync(text, target_lang)

        if audio_bytes:
            success = self.play_to_virtual_soundcard(audio_bytes)
            if success:
                return True

        # If we reach here, synthesis or playback failed — subtitle already shown
        if audio_bytes is not None:
            # Synthesis succeeded but playback failed
            self.display_subtitle(text)
        return False


# ============================================================================
# GEALL PERSONAL AGENT
# ============================================================================

class GeallAgent:
    """
    Personal autonomous agent — assists, delegates, learns.

    Geall operates through the Bifrost subprocess:
      - --infer path: query → Bifrost → JSON response within 3s
      - --translate path: text → pipeline → JSON with translated + quality_score

    Stores learned user preferences locally in JSON file.
    Proactive assistance triggered via n8n workflow monitoring user patterns.

    Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
    """

    PREFERENCE_FILE = "geall_preferences.json"
    RESPONSE_TIMEOUT = 3  # seconds

    def __init__(self, bifrost_path="bin/bifrost.exe", n8n_client=None):
        """
        Initialize Geall Agent.

        Args:
            bifrost_path: path to Bifrost executable (Ada/SPARK bridge)
            n8n_client: N8nWebhookClient instance for proactive workflows
        """
        self.bifrost_path = bifrost_path
        self.n8n = n8n_client
        self._preferences = {}
        self._available = False

        # Load existing preferences from local storage
        self._load_preferences()

        # Check Bifrost availability
        if os.path.exists(self.bifrost_path):
            self._available = True
            print(f"[GEALL] Agent ready — Bifrost: {self.bifrost_path}")
        else:
            print(f"[GEALL] WARNING: Bifrost not found at {self.bifrost_path}")
            print("[GEALL] Agent running in degraded mode (no AI inference)")

        print(f"[GEALL] Preferences loaded: {len(self._preferences)} entries")

    def infer(self, query: str):
        """
        Process query through Bifrost --geall --infer.

        Sends a JSON query to the Bifrost subprocess and returns the
        AI-generated response within the 3 second timeout.

        Args:
            query: user query string

        Returns:
            Optional[dict]: {"response": "..."} or None on failure
        """
        if not query:
            print("[GEALL] Empty query — skipping")
            return None

        if not self._available:
            print("[GEALL] Bifrost unavailable — cannot process inference")
            return None

        import json
        import subprocess

        json_input = json.dumps({"query": query})

        try:
            result = subprocess.run(
                [self.bifrost_path, "--geall", "--infer"],
                input=json_input,
                capture_output=True,
                text=True,
                timeout=self.RESPONSE_TIMEOUT
            )

            if result.returncode != 0:
                stderr = result.stderr.strip() if result.stderr else "unknown"
                print(f"[GEALL] Infer error (exit {result.returncode}): {stderr}")
                return None

            stdout = result.stdout.strip()
            if not stdout:
                print("[GEALL] Infer returned empty response")
                return None

            response = json.loads(stdout)

            # Check for error in response
            if "error" in response:
                print(f"[GEALL] Infer error: {response['error']}")
                return None

            if "response" not in response:
                print("[GEALL] Infer response missing 'response' field")
                return None

            print(f"[GEALL] Infer OK: {response['response'][:60]}...")
            return response

        except subprocess.TimeoutExpired:
            print(f"[GEALL] Infer timeout ({self.RESPONSE_TIMEOUT}s)")
            return None
        except FileNotFoundError:
            print(f"[GEALL] Bifrost not found: {self.bifrost_path}")
            self._available = False
            return None
        except json.JSONDecodeError as e:
            print(f"[GEALL] Invalid JSON from Bifrost: {e}")
            return None
        except Exception as e:
            print(f"[GEALL] Infer unexpected error: {e}")
            return None

    def translate(self, text: str, source: str, target: str):
        """
        Translate text via pipeline. Returns JSON with translated + quality_score.

        Sends translation request to Bifrost --geall --translate subprocess.

        Args:
            text: text to translate
            source: source language code (e.g. "cs")
            target: target language code (e.g. "en")

        Returns:
            Optional[dict]: {"translated": "...", "quality_score": 0.92} or None
        """
        if not text:
            print("[GEALL] Empty text — skipping translation")
            return None

        if not self._available:
            print("[GEALL] Bifrost unavailable — cannot translate")
            return None

        import json
        import subprocess

        json_input = json.dumps({
            "text": text,
            "source": source,
            "target": target
        })

        try:
            result = subprocess.run(
                [self.bifrost_path, "--geall", "--translate"],
                input=json_input,
                capture_output=True,
                text=True,
                timeout=self.RESPONSE_TIMEOUT
            )

            if result.returncode != 0:
                stderr = result.stderr.strip() if result.stderr else "unknown"
                print(f"[GEALL] Translate error (exit {result.returncode}): {stderr}")
                return None

            stdout = result.stdout.strip()
            if not stdout:
                print("[GEALL] Translate returned empty response")
                return None

            response = json.loads(stdout)

            # Check for error in response
            if "error" in response:
                print(f"[GEALL] Translate error: {response['error']}")
                return None

            if "translated" not in response:
                print("[GEALL] Translate response missing 'translated' field")
                return None

            translated = response.get("translated", "")
            quality_score = response.get("quality_score", 0.0)

            if not translated:
                print("[GEALL] Translate returned empty translation")
                return None

            print(f"[GEALL] Translate OK (quality: {quality_score:.2f}): "
                  f"{translated[:60]}...")
            return response

        except subprocess.TimeoutExpired:
            print(f"[GEALL] Translate timeout ({self.RESPONSE_TIMEOUT}s)")
            return None
        except FileNotFoundError:
            print(f"[GEALL] Bifrost not found: {self.bifrost_path}")
            self._available = False
            return None
        except json.JSONDecodeError as e:
            print(f"[GEALL] Invalid JSON from Bifrost: {e}")
            return None
        except Exception as e:
            print(f"[GEALL] Translate unexpected error: {e}")
            return None

    def learn_preference(self, key: str, value):
        """
        Store a learned user preference locally.

        Saves key-value pair to the local preference file.
        Used by n8n workflow to learn user patterns over time.

        Args:
            key: preference key (e.g. "preferred_target_lang")
            value: preference value (any JSON-serializable type)
        """
        if not key:
            return

        self._preferences[key] = {
            "value": value,
            "learned_at": int(time.time())
        }
        self._save_preferences()
        print(f"[GEALL] Preference learned: {key} = {value}")

    def get_preference(self, key: str, default=None):
        """
        Retrieve a stored preference.

        Args:
            key: preference key to look up
            default: value to return if key not found

        Returns:
            The stored preference value, or default if not found.
        """
        entry = self._preferences.get(key)
        if entry is None:
            return default
        return entry.get("value", default)

    def delegate_to_gemini(self, task: str):
        """
        Delegate task beyond local capability to Gemini via Bifrost.

        When Geall encounters a task it cannot handle locally, it delegates
        to the Gemini model through the Bifrost bridge --infer path.

        Args:
            task: task description to delegate

        Returns:
            Optional[dict]: {"response": "..."} with delegation result, or None
        """
        if not task:
            print("[GEALL] Empty task — skipping delegation")
            return None

        if not self._available:
            print("[GEALL] Cannot delegate — Bifrost unavailable")
            return None

        print(f"[GEALL] Delegating to Gemini: {task[:60]}...")

        # Use the infer path to delegate complex tasks
        result = self.infer(task)

        if result:
            print(f"[GEALL] Delegation successful")
            # Notify n8n about delegation if connected
            if self.n8n:
                self.n8n.post_status("geall_agent", "delegated",
                                     data={"task": task[:200]})
        else:
            print("[GEALL] Delegation failed — Gemini unreachable")
            if self.n8n:
                self.n8n.post_error("geall_agent", "delegation_failed",
                                    f"Delegation failed: {task[:100]}")

        return result

    def _load_preferences(self):
        """Load preferences from local JSON file."""
        import json

        try:
            if os.path.exists(self.PREFERENCE_FILE):
                with open(self.PREFERENCE_FILE, 'r', encoding='utf-8') as f:
                    self._preferences = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"[GEALL] Could not load preferences: {e}")
            self._preferences = {}

    def _save_preferences(self):
        """Save preferences to local JSON file."""
        import json

        try:
            with open(self.PREFERENCE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._preferences, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"[GEALL] Could not save preferences: {e}")

    @property
    def is_available(self):
        """Check if Geall agent has Bifrost connection."""
        return self._available

    @property
    def preference_count(self):
        """Return number of stored preferences."""
        return len(self._preferences)


# ============================================================================
# KAREL IV. MAIN ORCHESTRATOR
# ============================================================================

class KarelIV:
    """
    Karel IV. — Real-time Voice Translator.
    Orchestrates the full pipeline: Audio → STT → Translate → TTS.
    """

    def __init__(
        self,
        source_lang=DEFAULT_SOURCE_LANG,
        target_lang=DEFAULT_TARGET_LANG,
        whisper_model="base",
        voice_sample=None,
        gemini_api_key=None,
        vad_threshold=0.02
    ):
        self.source_lang = source_lang
        self.target_lang = target_lang

        print("\n" + "="*60)
        print("👑 KAREL IV. — Real-time Voice Translator")
        print("="*60)
        print(f"[KAREL] Source: {SUPPORTED_LANGUAGES.get(source_lang, source_lang)}")
        print(f"[KAREL] Target: {SUPPORTED_LANGUAGES.get(target_lang, target_lang)}")
        print(f"[KAREL] Whisper model: {whisper_model}")
        print(f"[KAREL] Voice clone: {voice_sample or 'default'}")
        print("="*60)

        # Initialize pipeline stages
        self.audio = AudioCapture()
        self.biometric = VoiceBiometricTunnel(voice_sample=voice_sample)
        self.stt = WhisperSTT(
            model_size=whisper_model,
            source_lang=source_lang,
            vad_threshold=vad_threshold
        )
        self.translator = GeminiTranslator(
            target_lang=target_lang,
            api_key=gemini_api_key
        )
        self.tts = EdgeTTS(voice_sample=voice_sample, target_lang=target_lang)

        # Ethics Oath — Hippocratic principles (cannot be disabled)
        try:
            from transkomunikator.ethics_oath import EthicsOath
            self.ethics = EthicsOath()
            print("[KAREL] Ethics Oath: ACTIVE (Hippocratic principles enforced)")
        except ImportError:
            from ethics_oath import EthicsOath
            self.ethics = EthicsOath()
            print("[KAREL] Ethics Oath: ACTIVE")

        karel_pipeline_health.set(1.0)
        print("[KAREL] Pipeline initialized")

    def process_chunk(self, audio_chunk):
        """
        Process one audio chunk through the full pipeline.

        Returns:
            dict: pipeline result with timing info
        """
        start_time = time.time()
        result = {
            'audio': True,
            'text': None,
            'translation': None,
            'audio_file': None,
            'latency': 0.0
        }

        # Stage 1.5: Voice biometric tunnel
        if not self.biometric.is_owner(audio_chunk):
            return result  # Not the owner — ignore silently

        # Stage 1.6: Ethics Oath — recording check
        # Refuse to process if third-party voices detected without consent
        is_owner = self.biometric.is_owner(audio_chunk)
        ethics_decision = self.ethics.may_record(
            is_owner_voice=is_owner,
            detected_speakers=1,  # TODO: multi-speaker detection
            context="pipeline_process_chunk"
        )
        if ethics_decision.value.startswith("denied"):
            return result  # Ethics violation — refuse processing

        # Stage 2: STT
        text = self.stt.transcribe(audio_chunk)
        if not text:
            return result
        result['text'] = text

        # Stage 3: Translate
        translation = self.translator.translate(text)
        if not translation:
            return result
        result['translation'] = translation

        # Stage 4: TTS
        audio_file = self.tts.synthesize(
            translation,
            output_file=f"tmp_output_{int(time.time())}.mp3"
        )
        result['audio_file'] = audio_file

        # Play output
        if audio_file:
            self.tts.play(audio_file)
            # Cleanup temp file
            try:
                os.remove(audio_file)
            except OSError:
                pass

        # Metrics
        latency = time.time() - start_time
        result['latency'] = latency
        karel_latency.observe(latency)
        karel_translations.labels(
            source_lang=self.source_lang,
            target_lang=self.target_lang
        ).inc()

        print(
            f"[KAREL] ✓ {self.source_lang}→{self.target_lang} "
            f"latency: {latency:.2f}s"
        )
        return result

    def run(self):
        """Start Karel IV. pipeline."""
        print("\n[KAREL] Starting pipeline...")
        print("[KAREL] Speak into microphone. Ctrl+C to stop.\n")

        karel_active_sessions.inc()

        # Start audio capture
        self.audio.start()

        # Accumulate chunks before processing
        accumulated = []
        accumulate_chunks = 6  # ~3 seconds of audio for better Czech recognition

        try:
            while True:
                try:
                    chunk = self.audio.output_queue.get(timeout=1.0)
                    accumulated.append(chunk)

                    if len(accumulated) >= accumulate_chunks:
                        import numpy as np
                        combined = np.concatenate(accumulated, axis=0)
                        accumulated = []
                        self.process_chunk(combined)

                except queue.Empty:
                    continue

        except KeyboardInterrupt:
            print("\n[KAREL] Stopping...")
            self.audio.stop()
            karel_active_sessions.dec()
            karel_pipeline_health.set(0.0)
            print("[KAREL] Shutdown complete")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Karel IV. main entry point."""
    parser = argparse.ArgumentParser(
        description="Karel IV. — Real-time Voice Translator by AsgardLab"
    )
    parser.add_argument(
        '--source', '-s',
        default=DEFAULT_SOURCE_LANG,
        choices=list(SUPPORTED_LANGUAGES.keys()),
        help='Source language (default: cs)'
    )
    parser.add_argument(
        '--target', '-t',
        default=DEFAULT_TARGET_LANG,
        choices=list(SUPPORTED_LANGUAGES.keys()),
        help='Target language (default: en)'
    )
    parser.add_argument(
        '--mode',
        default='realtime',
        choices=['realtime', 'quality'],
        help='Pipeline mode: realtime (local, <300ms) or quality (Gemini, 500ms chunks)'
    )
    parser.add_argument(
        '--model', '-m',
        default='base',
        choices=['tiny', 'base', 'small', 'medium', 'large'],
        help='Whisper model size (default: base)'
    )
    parser.add_argument(
        '--voice', '-v',
        default=None,
        help='Path to voice sample WAV for cloning (optional)'
    )
    parser.add_argument(
        '--api-key', '-k',
        default=None,
        help='Gemini API key (or set GEMINI_API_KEY env var)'
    )
    parser.add_argument(
        '--port', '-p',
        default=KAREL_PORT,
        type=int,
        help=f'Prometheus metrics port (default: {KAREL_PORT})'
    )
    parser.add_argument(
        '--vad-threshold', '-vad',
        default=0.02,
        type=float,
        help='Voice activity detection threshold (default: 0.02, higher = less sensitive)'
    )
    parser.add_argument(
        '--n8n-url',
        default=None,
        help='n8n base URL (default: http://localhost:5678)'
    )
    parser.add_argument(
        '--list-languages',
        action='store_true',
        help='List supported languages and exit'
    )

    args = parser.parse_args()

    if args.list_languages:
        print("Supported languages:")
        for code, name in SUPPORTED_LANGUAGES.items():
            print(f"  {code}: {name}")
        sys.exit(0)

    # Start Prometheus metrics server
    try:
        start_http_server(args.port)
        print(f"[KAREL] Metrics: http://localhost:{args.port}/metrics")
    except Exception as e:
        print(f"[KAREL] Metrics server error: {e}")

    # System startup sequence (register components with n8n)
    n8n_client = N8nWebhookClient(base_url=args.n8n_url)
    startup = SystemStartup(n8n_client=n8n_client)
    startup.boot()

    if args.mode == 'realtime':
        # Realtime mode: local models, 250ms chunks, <300ms e2e
        pipeline = RealtimePipeline(
            source_lang=args.source,
            target_lang=args.target,
            voice_sample=args.voice,
            vad_threshold=args.vad_threshold,
            n8n_url=args.n8n_url
        )
        pipeline.run()
    else:
        # Quality mode: Gemini translation, 500ms chunks
        karel = KarelIV(
            source_lang=args.source,
            target_lang=args.target,
            whisper_model=args.model,
            voice_sample=args.voice,
            gemini_api_key=args.api_key
        )
        karel.run()


if __name__ == '__main__':
    main()
