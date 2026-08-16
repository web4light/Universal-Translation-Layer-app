"""
Translation Engine — Universal Translation Layer (UTL)

Překladový modul Karel IV. se třemi úrovněmi fallbacku:
1. Mesh (P2P síť) — nejlepší kvalita, vyžaduje síť
2. Lokální model (CTranslate2 + OPUS-MT) — offline překlad
3. Degradovaný režim — echo originálu s nízkou spolehlivostí

Komunikace s Ada/SPARK validátorem přes subprocess (JSON stdin/stdout).
Detekce síťové konektivity a přepnutí do offline režimu do 1 sekundy.

Autor: Pan Jeskyně
Asistent: Kiro
"""

import json
import time
import logging
import subprocess
import os
import platform
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict

# === LOGGING ===

logger = logging.getLogger(__name__)
LOG_PREFIX = "[TRANSLATION]"

# === PROMETHEUS METRICS ===

try:
    from prometheus_client import Counter, Histogram

    utl_translation_requests_total = Counter(
        'utl_translation_requests_total',
        'Total translation requests processed',
        ['method', 'source_lang', 'target_lang']
    )

    utl_translation_latency_seconds = Histogram(
        'utl_translation_latency_seconds',
        'Translation request latency in seconds',
        ['method'],
        buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0]
    )
except ImportError:
    utl_translation_requests_total = None
    utl_translation_latency_seconds = None

# === CTRANSLATE2 IMPORT (GRACEFUL FALLBACK) ===

try:
    import ctranslate2
    _CTRANSLATE2_AVAILABLE = True
except ImportError:
    _CTRANSLATE2_AVAILABLE = False

try:
    import sentencepiece
    _SENTENCEPIECE_AVAILABLE = True
except ImportError:
    _SENTENCEPIECE_AVAILABLE = False

# === CONSTANTS ===

# Ada validator binary path (Windows / Linux)
if platform.system() == "Windows":
    _VALIDATOR_BINARY = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "bin", "translation_validator.exe"
    )
else:
    _VALIDATOR_BINARY = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "bin", "translation_validator"
    )

# Supported language codes matching Ada Language_Code type
SUPPORTED_LANG_CODES = ["CS", "EN", "DE", "FR", "JA", "ES", "IT", "PL", "SK"]

# Default local model directory
_DEFAULT_MODEL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "models"
)

# Network connectivity check timeout
_CONNECTIVITY_TIMEOUT = 1.0  # 1 second (Requirement 7.2)

# Offline switch threshold — seamless switch within 1 second
_OFFLINE_SWITCH_TIMEOUT = 1.0


# === ENUMS ===

class TranslationMethod(Enum):
    """Method used for translation in the fallback chain."""
    MESH = "mesh"
    LOCAL = "local"
    DEGRADED = "degraded"


# === DATA MODELS ===

@dataclass
class TranslationResult:
    """Result of a translation operation.

    Attributes:
        translated_text: The translated output text
        source_lang: Detected or specified source language code
        target_lang: Target language code
        confidence: Translation confidence 0.0 - 1.0
        method: Which method was used (mesh/local/degraded)
        validation_result: Ada validator output (dict or None)
    """
    translated_text: str
    source_lang: str
    target_lang: str
    confidence: float
    method: TranslationMethod
    validation_result: Optional[Dict] = field(default_factory=lambda: None)

    def __post_init__(self):
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")


@dataclass
class ValidationResult:
    """Result from Ada translation_validator subprocess.

    Attributes:
        valid: Whether the translation ratio is within bounds
        reason: Human-readable reason string
        stage: Pipeline stage name (e.g. 'Text_Translate')
    """
    valid: bool
    reason: str
    stage: str


# === TRANSLATION ENGINE CLASS ===

class TranslationEngine:
    """Translation engine with fallback chain: mesh -> local -> degraded.

    Provides:
    - translate(text, source_lang, target_lang) -> TranslationResult
    - Ada/SPARK validation of translation ratios via subprocess
    - Network connectivity detection for seamless offline switch
    - Prometheus metrics for monitoring

    The fallback chain ensures translation is always available:
    1. Mesh network — best quality, distributed across P2P nodes
    2. Local model (CTranslate2 + OPUS-MT) — offline, good quality
    3. Degraded — echo original text with low confidence (last resort)
    """

    def __init__(self, model_dir: Optional[str] = None,
                 validator_binary: Optional[str] = None):
        """Initialize the Translation Engine.

        Args:
            model_dir: Path to local OPUS-MT model directory.
                       Defaults to <project_root>/models/
            validator_binary: Path to Ada translation_validator binary.
                             Defaults to bin/translation_validator.exe (Windows)
                             or bin/translation_validator (Linux)
        """
        self._model_dir = model_dir or _DEFAULT_MODEL_DIR
        self._validator_binary = validator_binary or _VALIDATOR_BINARY
        self._is_online = True
        self._last_connectivity_check = 0.0
        self._connectivity_check_interval = 5.0  # Re-check every 5 seconds
        self._mesh_endpoint: Optional[str] = None
        self._local_models: Dict[str, object] = {}
        self._tokenizers: Dict[str, object] = {}

        # Log initialization state
        logger.info(f"{LOG_PREFIX} CTranslate2 available: {_CTRANSLATE2_AVAILABLE}")
        logger.info(f"{LOG_PREFIX} SentencePiece available: {_SENTENCEPIECE_AVAILABLE}")
        logger.info(f"{LOG_PREFIX} Validator binary: {self._validator_binary}")
        logger.info(f"{LOG_PREFIX} Model directory: {self._model_dir}")

    # === PUBLIC API ===

    def translate(self, text: str, source_lang: str,
                  target_lang: str) -> TranslationResult:
        """Translate text with automatic fallback chain.

        Fallback order:
        1. Mesh network (if online and mesh endpoint configured)
        2. Local CTranslate2 model (if available)
        3. Degraded mode (echo original with low confidence)

        After translation, optionally validates via Ada subprocess.

        Args:
            text: Input text to translate
            source_lang: Source language code (ISO 639-1, e.g. 'en', 'cs')
            target_lang: Target language code (ISO 639-1, e.g. 'cs', 'en')

        Returns:
            TranslationResult with translated text, method used, and confidence.
        """
        start_time = time.perf_counter()

        if not text or not text.strip():
            return TranslationResult(
                translated_text="",
                source_lang=source_lang,
                target_lang=target_lang,
                confidence=1.0,
                method=TranslationMethod.DEGRADED,
                validation_result=None
            )

        # Same language — identity pass-through
        if source_lang.lower() == target_lang.lower():
            return TranslationResult(
                translated_text=text,
                source_lang=source_lang,
                target_lang=target_lang,
                confidence=1.0,
                method=TranslationMethod.LOCAL,
                validation_result=None
            )

        result = None

        # === FALLBACK CHAIN ===

        # 1. Try mesh translation
        if self._is_mesh_available():
            result = self._translate_via_mesh(text, source_lang, target_lang)

        # 2. Try local model
        if result is None:
            result = self._translate_via_local(text, source_lang, target_lang)

        # 3. Degraded mode (last resort)
        if result is None:
            result = self._translate_degraded(text, source_lang, target_lang)

        # === ADA VALIDATION ===
        validation = self._validate_with_ada(
            input_length=len(text),
            output_length=len(result.translated_text),
            source_lang=source_lang,
            target_lang=target_lang
        )
        result.validation_result = validation

        # === METRICS ===
        elapsed = time.perf_counter() - start_time
        self._record_metrics(result.method, source_lang, target_lang, elapsed)

        logger.info(
            f"{LOG_PREFIX} Translated {len(text)} chars "
            f"({source_lang}->{target_lang}) via {result.method.value} "
            f"in {elapsed:.3f}s, confidence={result.confidence:.2f}"
        )

        return result

    def set_mesh_endpoint(self, endpoint: str) -> None:
        """Configure mesh translation endpoint URL.

        Args:
            endpoint: HTTP endpoint for mesh translation service.
        """
        self._mesh_endpoint = endpoint
        logger.info(f"{LOG_PREFIX} Mesh endpoint set: {endpoint}")

    def check_connectivity(self) -> bool:
        """Check network connectivity and update online status.

        Implements seamless offline switch within 1 second (Req 7.2).
        Caches result to avoid excessive checks.

        Returns:
            True if network is available, False otherwise.
        """
        now = time.time()
        if now - self._last_connectivity_check < self._connectivity_check_interval:
            return self._is_online

        self._last_connectivity_check = now
        was_online = self._is_online

        try:
            import socket
            sock = socket.create_connection(
                ("8.8.8.8", 53), timeout=_CONNECTIVITY_TIMEOUT
            )
            sock.close()
            self._is_online = True
        except (socket.timeout, socket.error, OSError):
            self._is_online = False

        # Log state transition
        if was_online and not self._is_online:
            logger.warning(f"{LOG_PREFIX} Network lost — switching to offline mode")
        elif not was_online and self._is_online:
            logger.info(f"{LOG_PREFIX} Network restored — resuming mesh operation")

        return self._is_online

    @property
    def is_online(self) -> bool:
        """Current network connectivity state."""
        return self._is_online

    @property
    def has_local_model(self) -> bool:
        """Whether CTranslate2 local translation is available."""
        return _CTRANSLATE2_AVAILABLE and _SENTENCEPIECE_AVAILABLE

    @property
    def has_validator(self) -> bool:
        """Whether Ada translation_validator binary exists."""
        return os.path.isfile(self._validator_binary)

    # === MESH TRANSLATION ===

    def _is_mesh_available(self) -> bool:
        """Check if mesh translation is currently available."""
        if self._mesh_endpoint is None:
            return False
        return self.check_connectivity()

    def _translate_via_mesh(self, text: str, source_lang: str,
                            target_lang: str) -> Optional[TranslationResult]:
        """Attempt translation via mesh network.

        Args:
            text: Input text
            source_lang: Source language code
            target_lang: Target language code

        Returns:
            TranslationResult if successful, None if mesh unavailable.
        """
        try:
            import requests

            payload = {
                "text": text,
                "source_lang": source_lang,
                "target_lang": target_lang
            }

            response = requests.post(
                f"{self._mesh_endpoint}/translate",
                json=payload,
                timeout=_OFFLINE_SWITCH_TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                return TranslationResult(
                    translated_text=data.get("translated_text", text),
                    source_lang=source_lang,
                    target_lang=target_lang,
                    confidence=data.get("confidence", 0.9),
                    method=TranslationMethod.MESH
                )
            else:
                logger.warning(
                    f"{LOG_PREFIX} Mesh returned status {response.status_code}"
                )
                return None

        except Exception as e:
            logger.warning(f"{LOG_PREFIX} Mesh translation failed: {e}")
            # Mark offline for fast fallback next time
            self._is_online = False
            return None

    # === LOCAL TRANSLATION (CTranslate2 + OPUS-MT) ===

    def _translate_via_local(self, text: str, source_lang: str,
                             target_lang: str) -> Optional[TranslationResult]:
        """Attempt translation using local CTranslate2 model.

        Uses OPUS-MT models for offline translation. Falls back to None
        if ctranslate2 or sentencepiece are not installed, or if the
        required model is not available locally.

        Args:
            text: Input text
            source_lang: Source language code
            target_lang: Target language code

        Returns:
            TranslationResult if successful, None otherwise.
        """
        if not _CTRANSLATE2_AVAILABLE or not _SENTENCEPIECE_AVAILABLE:
            logger.debug(
                f"{LOG_PREFIX} Local translation unavailable "
                f"(ctranslate2={_CTRANSLATE2_AVAILABLE}, "
                f"sentencepiece={_SENTENCEPIECE_AVAILABLE})"
            )
            return None

        model_name = f"opus-mt-{source_lang.lower()}-{target_lang.lower()}"
        model_path = os.path.join(self._model_dir, model_name)

        if not os.path.isdir(model_path):
            logger.debug(f"{LOG_PREFIX} Model not found: {model_path}")
            return None

        try:
            # Load or get cached translator
            translator = self._get_local_translator(model_path)
            tokenizer = self._get_tokenizer(model_path)

            # Tokenize input
            tokens = tokenizer.encode(text, out_type=str)
            tokens = [tokens]  # Batch of 1

            # Translate
            results = translator.translate_batch(tokens)
            translated_tokens = results[0].hypotheses[0]

            # Detokenize
            translated_text = tokenizer.decode(translated_tokens)

            return TranslationResult(
                translated_text=translated_text,
                source_lang=source_lang,
                target_lang=target_lang,
                confidence=0.85,
                method=TranslationMethod.LOCAL
            )

        except Exception as e:
            logger.error(f"{LOG_PREFIX} Local translation error: {e}")
            return None

    def _get_local_translator(self, model_path: str):
        """Get or create a cached CTranslate2 translator instance."""
        if model_path not in self._local_models:
            self._local_models[model_path] = ctranslate2.Translator(
                model_path, device="cpu"
            )
        return self._local_models[model_path]

    def _get_tokenizer(self, model_path: str):
        """Get or create a cached SentencePiece tokenizer instance."""
        if model_path not in self._tokenizers:
            sp_model = os.path.join(model_path, "source.spm")
            sp = sentencepiece.SentencePieceProcessor()
            sp.load(sp_model)
            self._tokenizers[model_path] = sp
        return self._tokenizers[model_path]

    # === DEGRADED TRANSLATION ===

    def _translate_degraded(self, text: str, source_lang: str,
                            target_lang: str) -> TranslationResult:
        """Degraded mode: echo original text with low confidence.

        This is the last resort when neither mesh nor local models
        are available. Returns the original text unchanged with a
        confidence of 0.1 to signal degraded quality.

        Args:
            text: Original input text (returned unchanged)
            source_lang: Source language code
            target_lang: Target language code

        Returns:
            TranslationResult with original text and low confidence.
        """
        logger.warning(
            f"{LOG_PREFIX} Using degraded mode (echo) for "
            f"{source_lang}->{target_lang}"
        )
        return TranslationResult(
            translated_text=text,
            source_lang=source_lang,
            target_lang=target_lang,
            confidence=0.1,
            method=TranslationMethod.DEGRADED
        )

    # === ADA VALIDATION ===

    def _validate_with_ada(self, input_length: int, output_length: int,
                           source_lang: str,
                           target_lang: str) -> Optional[Dict]:
        """Validate translation output via Ada/SPARK subprocess.

        Calls the translation_validator binary with JSON on stdin,
        reads JSON result from stdout.

        Input format:
            {"input_length": N, "output_length": M,
             "source_lang": "XX", "target_lang": "YY"}

        Output format:
            {"valid": true/false, "reason": "...", "stage": "Text_Translate"}

        Args:
            input_length: Length of original text
            output_length: Length of translated text
            source_lang: Source language code (2-letter)
            target_lang: Target language code (2-letter)

        Returns:
            Dict with validation result, or None if validator unavailable.
        """
        if not os.path.isfile(self._validator_binary):
            logger.debug(
                f"{LOG_PREFIX} Ada validator not found at "
                f"{self._validator_binary} — skipping validation"
            )
            return None

        # Normalize language codes to uppercase for Ada
        src = source_lang.upper()[:2]
        tgt = target_lang.upper()[:2]

        # Verify language codes are supported by Ada
        if src not in SUPPORTED_LANG_CODES or tgt not in SUPPORTED_LANG_CODES:
            logger.debug(
                f"{LOG_PREFIX} Language pair {src}->{tgt} not supported "
                f"by Ada validator"
            )
            return None

        input_json = json.dumps({
            "input_length": input_length,
            "output_length": output_length,
            "source_lang": src,
            "target_lang": tgt
        })

        try:
            proc = subprocess.run(
                [self._validator_binary],
                input=input_json,
                capture_output=True,
                text=True,
                timeout=5.0
            )

            if proc.returncode != 0:
                logger.warning(
                    f"{LOG_PREFIX} Ada validator returned code "
                    f"{proc.returncode}: {proc.stderr}"
                )
                return None

            result = json.loads(proc.stdout.strip())
            logger.debug(f"{LOG_PREFIX} Ada validation: {result}")
            return result

        except FileNotFoundError:
            logger.debug(f"{LOG_PREFIX} Ada validator binary not found")
            return None
        except subprocess.TimeoutExpired:
            logger.warning(f"{LOG_PREFIX} Ada validator timed out")
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"{LOG_PREFIX} Ada validator output parse error: {e}")
            return None
        except Exception as e:
            logger.error(f"{LOG_PREFIX} Ada validator error: {e}")
            return None

    # === METRICS ===

    def _record_metrics(self, method: TranslationMethod, source_lang: str,
                        target_lang: str, elapsed: float) -> None:
        """Record Prometheus metrics for a translation request."""
        if utl_translation_requests_total is not None:
            utl_translation_requests_total.labels(
                method=method.value,
                source_lang=source_lang,
                target_lang=target_lang
            ).inc()

        if utl_translation_latency_seconds is not None:
            utl_translation_latency_seconds.labels(
                method=method.value
            ).observe(elapsed)


# === MAIN GUARD ===

def main():
    """Self-test entry point for Translation Engine module."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    engine = TranslationEngine()

    print(f"{LOG_PREFIX} Translation Engine self-test")
    print(f"{LOG_PREFIX} CTranslate2 available: {_CTRANSLATE2_AVAILABLE}")
    print(f"{LOG_PREFIX} SentencePiece available: {_SENTENCEPIECE_AVAILABLE}")
    print(f"{LOG_PREFIX} Ada validator present: {engine.has_validator}")
    print(f"{LOG_PREFIX} Local model available: {engine.has_local_model}")

    # Test empty text
    result = engine.translate("", "en", "cs")
    assert result.translated_text == ""
    assert result.method == TranslationMethod.DEGRADED
    print(f"{LOG_PREFIX} Empty text: OK")

    # Test same language (identity)
    result = engine.translate("Hello world", "en", "en")
    assert result.translated_text == "Hello world"
    assert result.confidence == 1.0
    print(f"{LOG_PREFIX} Same language pass-through: OK")

    # Test degraded fallback (no mesh, no local model expected in test)
    result = engine.translate("Hello world", "en", "cs")
    assert result.translated_text is not None
    assert result.method in (TranslationMethod.LOCAL, TranslationMethod.DEGRADED)
    print(f"{LOG_PREFIX} Fallback translation: method={result.method.value}, "
          f"confidence={result.confidence}")

    # Test connectivity check
    is_online = engine.check_connectivity()
    print(f"{LOG_PREFIX} Network online: {is_online}")

    # Test Ada validation (may return None if binary not compiled)
    val_result = engine._validate_with_ada(
        input_length=11, output_length=9,
        source_lang="en", target_lang="cs"
    )
    if val_result:
        print(f"{LOG_PREFIX} Ada validation: {val_result}")
    else:
        print(f"{LOG_PREFIX} Ada validator not available (binary not compiled)")

    print(f"{LOG_PREFIX} All self-tests passed.")


if __name__ == '__main__':
    main()
