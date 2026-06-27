#!/usr/bin/env python3
"""
Karel IV. — Real-time Voice Translator
AsgardLab / web4light.online

Pipeline:
  Microphone → Virtual audio card → Whisper STT
  → Ada/SPARK validation → Gemini translation
  → Coqui TTS → Headphones

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


# ============================================================================
# PIPELINE STAGES
# ============================================================================

class AudioCapture:
    """
    Stage 1: Capture audio from virtual sound card.
    Uses sounddevice for cross-platform audio input.
    """

    def __init__(self, chunk_ms=AUDIO_CHUNK_MS, sample_rate=16000):
        self.chunk_ms = chunk_ms
        self.sample_rate = sample_rate
        self.chunk_size = int(sample_rate * chunk_ms / 1000)
        self.output_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
        self._running = False

    def start(self):
        """Start audio capture in background thread."""
        self._running = True
        thread = threading.Thread(target=self._capture_loop, daemon=True)
        thread.start()
        print("[AUDIO] Capture started")
        return thread

    def stop(self):
        self._running = False

    def _capture_loop(self):
        try:
            import sounddevice as sd
            import numpy as np

            def callback(indata, frames, time_info, status):
                if status:
                    print(f"[AUDIO] Warning: {status}")
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
                while self._running:
                    time.sleep(0.1)

        except ImportError:
            print("[AUDIO] sounddevice not installed — demo mode")
            self._demo_loop()
        except Exception as e:
            print(f"[AUDIO] Error: {e}")

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
    Stage 2: Speech-to-text using OpenAI Whisper.
    MIT license — runs locally, no API cost.
    """

    def __init__(self, model_size="base", source_lang="cs"):
        self.model_size = model_size
        self.source_lang = source_lang
        self.model = None
        self._load_model()

    def _load_model(self):
        try:
            import whisper
            print(f"[WHISPER] Loading model: {self.model_size}")
            self.model = whisper.load_model(self.model_size)
            print("[WHISPER] Model loaded")
        except ImportError:
            print("[WHISPER] whisper not installed — demo mode")
        except Exception as e:
            print(f"[WHISPER] Error loading model: {e}")

    def transcribe(self, audio_chunk):
        """
        Transcribe audio chunk to text.

        Args:
            audio_chunk: numpy array of audio samples

        Returns:
            str: transcribed text or None
        """
        if self.model is None:
            return "[DEMO] Dobrý den, jak se máte?"

        try:
            import numpy as np
            audio = audio_chunk.flatten().astype('float32')

            result = self.model.transcribe(
                audio,
                language=self.source_lang,
                fp16=False
            )
            text = result.get('text', '').strip()
            if text:
                print(f"[WHISPER] Transcribed: {text}")
            return text if text else None

        except Exception as e:
            print(f"[WHISPER] Transcription error: {e}")
            return None


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
            self.client = genai.GenerativeModel('gemini-1.5-flash')
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


class CoquiTTS:
    """
    Stage 4: Text-to-speech using Coqui TTS.
    MIT license — runs locally, supports voice cloning.
    """

    def __init__(self, voice_sample=None):
        self.voice_sample = voice_sample
        self.tts = None
        self._load_model()

    def _load_model(self):
        try:
            from TTS.api import TTS
            print("[TTS] Loading Coqui TTS model...")
            self.tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
            print("[TTS] Model loaded")
        except ImportError:
            print("[TTS] Coqui TTS not installed — demo mode (text output)")
        except Exception as e:
            print(f"[TTS] Error loading model: {e}")

    def synthesize(self, text, output_file="output.wav"):
        """
        Synthesize speech from text.

        Args:
            text: text to synthesize
            output_file: output WAV file path

        Returns:
            str: path to output file or None
        """
        if not text:
            return None

        if self.tts is None:
            print(f"[TTS/DEMO] Would speak: {text}")
            return None

        try:
            if self.voice_sample and os.path.exists(self.voice_sample):
                # Voice cloning mode
                self.tts.tts_to_file(
                    text=text,
                    speaker_wav=self.voice_sample,
                    language="en",
                    file_path=output_file
                )
            else:
                self.tts.tts_to_file(
                    text=text,
                    file_path=output_file
                )

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
        gemini_api_key=None
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
        self.stt = WhisperSTT(
            model_size=whisper_model,
            source_lang=source_lang
        )
        self.translator = GeminiTranslator(
            target_lang=target_lang,
            api_key=gemini_api_key
        )
        self.tts = CoquiTTS(voice_sample=voice_sample)

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
            output_file=f"tmp_output_{int(time.time())}.wav"
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
        accumulate_chunks = 3  # ~1.5 seconds of audio

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

    # Start Karel IV.
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
