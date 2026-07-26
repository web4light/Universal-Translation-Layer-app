"""
Transkomunikátor — Shared Data Models
=======================================

All dataclasses used across multiple Transkomunikátor components.
JSON serialization via dataclass fields (no external ORM).

Bounded field lengths: MAX_FIELD_LENGTH = 4096 characters.

Requirements: 1.1-1.6, 2.1-2.4, 3.1-3.5, 4.1-4.5, 5.1-5.6,
              6.1-6.5, 7.1-7.6, 8.1-8.6, 9.1-9.6, 10.1-10.7,
              11.1-11.5, 12.1-12.5, 13.1-13.5, 14.1-14.5, 15.1-15.5

Standard 700: 12g stříbra = 1 mince
Autor: Pan Jeskyně
Asistent: Kiro
"""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# === CONSTANTS ===

MAX_FIELD_LENGTH: int = 4096
MAX_PROMPT_LENGTH: int = 8192
MAX_RESPONSE_LENGTH: int = 32768


# === ENUMS ===

class PipelineStage(Enum):
    """Discrete processing steps in the translation pipeline."""
    AUDIO_CAPTURE = "audio_capture"
    AUDIO_VALIDATE = "audio_validate"
    SPEECH_TO_TEXT = "speech_to_text"
    TEXT_VALIDATE = "text_validate"
    TRANSLATION = "translation"
    RESPONSE_VALIDATE = "response_validate"
    TEXT_TO_SPEECH = "text_to_speech"
    AUDIO_OUTPUT = "audio_output"


class LanguageCode(Enum):
    """Supported language codes (9 languages)."""
    CS = "cs"
    EN = "en"
    DE = "de"
    FR = "fr"
    JA = "ja"
    ES = "es"
    IT = "it"
    PL = "pl"
    SK = "sk"


class ServiceState(Enum):
    """Lifecycle states for TranskomunikatorService."""
    STARTING = "starting"
    RUNNING = "running"
    SLEEPING = "sleeping"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    STOPPING = "stopping"
    STOPPED = "stopped"


class ErrorSeverity(Enum):
    """Fault classification for ComponentError."""
    TRANSIENT = "transient"      # Retry immediately
    DEGRADED = "degraded"        # Reduce priority, continue
    FAILURE = "failure"          # Isolate + restart (max 3x)
    CRITICAL = "critical"        # After 3 restarts → notify user


# === ABSTRACT BASE — EVICTABLE CACHE ===

class EvictableCache(ABC):
    """Interface for caches that can be purged under memory pressure.

    Components that hold significant memory (translation cache, TTS models,
    audio buffers) implement this so MemoryManager can evict them in priority
    order when approaching the 512 MB hard ceiling.
    """

    @abstractmethod
    def evict(self) -> int:
        """Evict cached data. Returns approximate bytes freed."""
        ...

    @abstractmethod
    def memory_usage_bytes(self) -> int:
        """Current estimated memory usage in bytes."""
        ...

    @property
    @abstractmethod
    def eviction_priority(self) -> int:
        """Lower number = evicted first. Translation cache=1, TTS=2, voice=3, audio=4."""
        ...


# === AUDIO MODELS ===

@dataclass
class AudioFrame:
    """Single audio frame entering/exiting the pipeline.

    Attributes:
        pcm_data: Raw PCM bytes (16-bit signed, little-endian)
        sample_rate: Samples per second (must be >= 16000)
        channels: Number of audio channels (1=mono, 2=stereo)
        timestamp_ms: Capture timestamp in milliseconds (monotonic)
        duration_ms: Frame duration in milliseconds
    """
    pcm_data: bytes
    sample_rate: int = 16000
    channels: int = 1
    timestamp_ms: int = 0
    duration_ms: int = 0

    def __post_init__(self):
        if self.sample_rate < 16000:
            raise ValueError(f"sample_rate must be >= 16000, got {self.sample_rate}")
        if self.channels < 1:
            raise ValueError(f"channels must be >= 1, got {self.channels}")


# === TRANSCRIPTION / TRANSLATION MODELS ===

@dataclass
class TranscriptionResult:
    """Result from Whisper STT."""
    text: str
    language: str
    confidence: float = 0.0
    timestamp_ms: int = 0
    duration_ms: int = 0

    def __post_init__(self):
        if len(self.text) > MAX_FIELD_LENGTH:
            self.text = self.text[:MAX_FIELD_LENGTH]


@dataclass
class TranslationResult:
    """Result from translation engine (Geall or Gemini)."""
    translated_text: str
    source_lang: str
    target_lang: str
    quality_score: float = 0.0
    engine: str = "geall"
    latency_ms: float = 0.0

    def __post_init__(self):
        if len(self.translated_text) > MAX_FIELD_LENGTH:
            self.translated_text = self.translated_text[:MAX_FIELD_LENGTH]


@dataclass
class ConversationContext:
    """Context for Karel IV. assistant sessions."""
    session_id: str
    turns: List[Dict[str, str]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    language_preference: str = "cs"

    def add_turn(self, query: str, response: str) -> None:
        """Add a query/response turn to the context."""
        self.turns.append({
            "query": query[:MAX_FIELD_LENGTH],
            "response": response[:MAX_FIELD_LENGTH],
            "timestamp": time.time(),
        })

    def clear(self) -> None:
        """Purge all turns (called by PrivacyPurge423 on session end)."""
        self.turns.clear()

    @property
    def turn_count(self) -> int:
        return len(self.turns)


# === PRIVACY MODELS ===

@dataclass
class MetadataRecord:
    """A single metadata record subject to privacy purge.

    Contains ONLY hashed/numeric data — never raw text or audio.
    """
    content_hash: str
    created_at_unix: float
    category: str

    def __post_init__(self):
        if self.created_at_unix <= 0:
            raise ValueError("created_at_unix must be > 0")

    @property
    def age_seconds(self) -> float:
        """Age of this record in seconds."""
        return time.time() - self.created_at_unix


@dataclass
class PurgeReport:
    """Result of a privacy sweep — numeric only, no sensitive content."""
    records_scanned: int = 0
    records_purged: int = 0
    records_retained: int = 0
    sweep_duration_seconds: float = 0.0
    verify_clean: bool = False


# === PAYMENT MODELS ===

@dataclass
class Transaction:
    """Financial transaction record (asterisk coins via VR_Network)."""
    tx_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    wallet_id: str = ""
    amount: int = 0
    confirmed: bool = False
    timestamp: float = field(default_factory=time.time)
    description: str = ""

    def __post_init__(self):
        if len(self.description) > MAX_FIELD_LENGTH:
            self.description = self.description[:MAX_FIELD_LENGTH]


# === LICENSE MODELS ===

@dataclass
class LicenseStatus:
    """Status returned by geall_license.exe Ada binary."""
    active: bool = False
    plan: str = "unknown"
    expires_unix: float = 0.0
    device_count: int = 0

    @property
    def is_household(self) -> bool:
        return self.plan == "household"

    @property
    def days_remaining(self) -> float:
        remaining = self.expires_unix - time.time()
        return max(0.0, remaining / 86400.0)


# === MESH / P2P MODELS ===

@dataclass
class Peer:
    """A peer node in the P2P mesh network."""
    peer_id: str
    ip_address: str
    port: int = 8080
    cpu_usage: float = 0.0
    available: bool = True
    last_seen: float = field(default_factory=time.time)
    capabilities: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MeshTask:
    """A task offloaded to a peer in the mesh."""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_type: str = "translation"
    payload: Dict[str, Any] = field(default_factory=dict)
    assigned_peer: Optional[str] = None
    submitted_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    result: Optional[Dict[str, Any]] = None


# === WORKFLOW MODELS ===

@dataclass
class WorkflowStatus:
    """Status of an n8n workflow execution."""
    workflow_id: str
    succeeded: bool = False
    steps_completed: int = 0
    steps_total: int = 0
    error_message: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


# === SERVICE STATUS ===

@dataclass
class ServiceStatus:
    """Overall Transkomunikátor service status."""
    state: ServiceState = ServiceState.STOPPED
    uptime_seconds: float = 0.0
    memory_usage_mb: float = 0.0
    active_peers: int = 0
    pipeline_latency_ms: float = 0.0
    license_active: bool = False
    last_error: Optional[str] = None


# === ERROR MODELS ===

@dataclass
class ComponentError:
    """Error from a specific component, classified by severity."""
    component: str
    severity: ErrorSeverity
    message: str
    timestamp: float = field(default_factory=time.time)
    exception_type: Optional[str] = None
    retry_count: int = 0

    def __post_init__(self):
        if len(self.message) > MAX_FIELD_LENGTH:
            self.message = self.message[:MAX_FIELD_LENGTH]


# === GEALL REQUEST / FUTURE ===

@dataclass
class GeallRequest:
    """Request to the Geall/Gemini engine (translate or infer)."""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    mode: str = "translate"  # "translate" or "infer"
    text: str = ""
    source_lang: str = "cs"
    target_lang: str = "en"
    query: str = ""  # For infer mode
    submitted_at: float = field(default_factory=time.time)

    def __post_init__(self):
        if len(self.text) > MAX_PROMPT_LENGTH:
            self.text = self.text[:MAX_PROMPT_LENGTH]
        if len(self.query) > MAX_PROMPT_LENGTH:
            self.query = self.query[:MAX_PROMPT_LENGTH]


@dataclass
class Future:
    """Represents a pending async result from Geall engine."""
    request_id: str
    completed: bool = False
    result: Optional[Any] = None
    error: Optional[str] = None
    submitted_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def resolve(self, result: Any) -> None:
        """Mark future as completed with result."""
        self.completed = True
        self.result = result
        self.completed_at = time.time()

    def reject(self, error: str) -> None:
        """Mark future as failed with error."""
        self.completed = True
        self.error = error
        self.completed_at = time.time()

    @property
    def elapsed_seconds(self) -> float:
        end = self.completed_at or time.time()
        return end - self.submitted_at
