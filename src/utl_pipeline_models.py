"""
UTL Pipeline Data Models — Karel IV.

Datové modely pro Universal Translation Layer pipeline:
- TextInterceptionMessage: zprávy z textové intercepce
- DubbingSegment: segmenty dabovaného audia
- MeshNodeRegistration: registrace uzlů v P2P mesh síti
- SubscriptionState: stav předplatného uživatele
- NodeCapabilities: HW schopnosti mesh uzlu

Round-trip serialize/deserialize (JSON). Bounded field lengths (MAX_FIELD_LENGTH = 4096).
Methods: to_json() / from_json(data) for all models.

Autor: Pan Jeskyně
Asistent: Kiro
"""

import json
import time
import base64
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple

# === CONSTANTS ===

MAX_FIELD_LENGTH = 4096

# === LOGGING ===

logger = logging.getLogger(__name__)
LOG_PREFIX = "[UTL]"

# === PROMETHEUS METRICS ===

try:
    from prometheus_client import Counter
    utl_serialization_errors_total = Counter(
        'utl_serialization_errors_total',
        'Total UTL model serialization/deserialization errors'
    )
    utl_messages_serialized_total = Counter(
        'utl_messages_serialized_total',
        'Total UTL messages serialized'
    )
except ImportError:
    utl_serialization_errors_total = None
    utl_messages_serialized_total = None


# === SUBSCRIPTION TIER ===

class SubscriptionTier(Enum):
    """Cenové plány Karel IV. — hodnota = cena v CZK/měsíc."""
    GEALL_111 = 111       # Geall AI assistant, 1 device
    KAREL_222 = 222       # Voice translation + clone
    DUBBING_333 = 333     # Stream dubbing
    FAMILY_423 = 423      # All features, unlimited devices


# === NODE CAPABILITIES ===

@dataclass
class NodeCapabilities:
    """Hardware capabilities of a mesh node.

    Reported during node registration so the Mesh_Orchestrator
    can route tasks to nodes with sufficient resources.
    """

    cpu_cores: int
    gpu_vram_mb: int
    ram_mb: int
    bandwidth_mbps: float
    available_models: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.cpu_cores < 0:
            raise ValueError("cpu_cores must be >= 0")
        if self.gpu_vram_mb < 0:
            raise ValueError("gpu_vram_mb must be >= 0")
        if self.ram_mb < 0:
            raise ValueError("ram_mb must be >= 0")
        if self.bandwidth_mbps < 0.0:
            raise ValueError("bandwidth_mbps must be >= 0.0")
        if not isinstance(self.available_models, list):
            self.available_models = list(self.available_models)

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self._to_dict())

    def _to_dict(self) -> dict:
        """Convert to dict for embedding in parent messages."""
        return {
            "cpu_cores": self.cpu_cores,
            "gpu_vram_mb": self.gpu_vram_mb,
            "ram_mb": self.ram_mb,
            "bandwidth_mbps": self.bandwidth_mbps,
            "available_models": self.available_models
        }

    @classmethod
    def from_json(cls, data) -> "NodeCapabilities":
        """Deserialize from JSON string or dict."""
        obj = json.loads(data) if isinstance(data, str) else data
        return cls(
            cpu_cores=obj["cpu_cores"],
            gpu_vram_mb=obj["gpu_vram_mb"],
            ram_mb=obj["ram_mb"],
            bandwidth_mbps=obj["bandwidth_mbps"],
            available_models=obj.get("available_models", [])
        )

    @classmethod
    def from_dict(cls, data: dict) -> "NodeCapabilities":
        """Alias for from_json accepting a dict."""
        return cls.from_json(data)

    def __eq__(self, other):
        if not isinstance(other, NodeCapabilities):
            return False
        return (self.cpu_cores == other.cpu_cores and
                self.gpu_vram_mb == other.gpu_vram_mb and
                self.ram_mb == other.ram_mb and
                self.bandwidth_mbps == other.bandwidth_mbps and
                self.available_models == other.available_models)


# === TEXT INTERCEPTION MESSAGE ===

@dataclass
class TextInterceptionMessage:
    """Message flowing through text interception pipeline.

    Represents intercepted text from OS accessibility APIs,
    with detected language, translation, and screen position.
    """

    source_app: str
    element_id: str
    original_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    confidence: float
    position: Tuple[int, int, int, int]
    timestamp: int = 0

    def __post_init__(self):
        self.original_text = self.original_text[:MAX_FIELD_LENGTH] if self.original_text else ""
        self.translated_text = self.translated_text[:MAX_FIELD_LENGTH] if self.translated_text else ""
        self.source_app = self.source_app[:MAX_FIELD_LENGTH] if self.source_app else ""
        self.element_id = self.element_id[:MAX_FIELD_LENGTH] if self.element_id else ""
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")
        if self.timestamp == 0:
            self.timestamp = int(time.time())
        if not isinstance(self.position, tuple):
            self.position = tuple(self.position)
        if len(self.position) != 4:
            raise ValueError("position must be a 4-tuple (x, y, width, height)")

    def to_json(self) -> str:
        """Serialize to JSON string."""
        if utl_messages_serialized_total:
            utl_messages_serialized_total.inc()
        return json.dumps({
            "source_app": self.source_app,
            "element_id": self.element_id,
            "original_text": self.original_text,
            "translated_text": self.translated_text,
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "confidence": self.confidence,
            "position": list(self.position),
            "timestamp": self.timestamp
        })

    # Legacy alias
    serialize = to_json

    @classmethod
    def from_json(cls, data) -> "TextInterceptionMessage":
        """Deserialize from JSON string or dict."""
        obj = json.loads(data) if isinstance(data, str) else data
        return cls(
            source_app=obj["source_app"],
            element_id=obj["element_id"],
            original_text=obj["original_text"],
            translated_text=obj["translated_text"],
            source_lang=obj["source_lang"],
            target_lang=obj["target_lang"],
            confidence=obj["confidence"],
            position=tuple(obj["position"]),
            timestamp=obj["timestamp"]
        )

    # Legacy alias
    deserialize = from_json

    def __eq__(self, other):
        if not isinstance(other, TextInterceptionMessage):
            return False
        return (self.source_app == other.source_app and
                self.element_id == other.element_id and
                self.original_text == other.original_text and
                self.translated_text == other.translated_text and
                self.source_lang == other.source_lang and
                self.target_lang == other.target_lang and
                self.confidence == other.confidence and
                self.position == other.position and
                self.timestamp == other.timestamp)


# === DUBBING SEGMENT ===

@dataclass
class DubbingSegment:
    """A segment of dubbed audio with metadata.

    Represents a single speaker segment from the stream dubbing pipeline.
    """

    speaker_id: str
    original_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    start_time_ms: int
    duration_ms: int
    voice_profile_id: str

    def __post_init__(self):
        self.original_text = self.original_text[:MAX_FIELD_LENGTH] if self.original_text else ""
        self.translated_text = self.translated_text[:MAX_FIELD_LENGTH] if self.translated_text else ""
        self.speaker_id = self.speaker_id[:MAX_FIELD_LENGTH] if self.speaker_id else ""
        self.voice_profile_id = self.voice_profile_id[:MAX_FIELD_LENGTH] if self.voice_profile_id else ""
        if self.start_time_ms < 0:
            raise ValueError("start_time_ms must be >= 0")
        if self.duration_ms < 0:
            raise ValueError("duration_ms must be >= 0")

    def to_json(self) -> str:
        """Serialize to JSON string."""
        if utl_messages_serialized_total:
            utl_messages_serialized_total.inc()
        return json.dumps({
            "speaker_id": self.speaker_id,
            "original_text": self.original_text,
            "translated_text": self.translated_text,
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "start_time_ms": self.start_time_ms,
            "duration_ms": self.duration_ms,
            "voice_profile_id": self.voice_profile_id
        })

    # Legacy alias
    serialize = to_json

    @classmethod
    def from_json(cls, data) -> "DubbingSegment":
        """Deserialize from JSON string or dict."""
        obj = json.loads(data) if isinstance(data, str) else data
        return cls(
            speaker_id=obj["speaker_id"],
            original_text=obj["original_text"],
            translated_text=obj["translated_text"],
            source_lang=obj["source_lang"],
            target_lang=obj["target_lang"],
            start_time_ms=obj["start_time_ms"],
            duration_ms=obj["duration_ms"],
            voice_profile_id=obj["voice_profile_id"]
        )

    # Legacy alias
    deserialize = from_json

    def __eq__(self, other):
        if not isinstance(other, DubbingSegment):
            return False
        return (self.speaker_id == other.speaker_id and
                self.original_text == other.original_text and
                self.translated_text == other.translated_text and
                self.source_lang == other.source_lang and
                self.target_lang == other.target_lang and
                self.start_time_ms == other.start_time_ms and
                self.duration_ms == other.duration_ms and
                self.voice_profile_id == other.voice_profile_id)


# === MESH NODE REGISTRATION ===

@dataclass
class MeshNodeRegistration:
    """Node registration message for Faucet Mesh.

    Each user device registers as a mesh node with its hardware
    capabilities and currently held model shards.
    """

    node_id: str
    ip_address: str
    port: int
    capabilities: NodeCapabilities
    model_shards: List[str]
    timestamp: int = 0
    signature: bytes = b""

    def __post_init__(self):
        self.node_id = self.node_id[:MAX_FIELD_LENGTH] if self.node_id else ""
        self.ip_address = self.ip_address[:MAX_FIELD_LENGTH] if self.ip_address else ""
        if self.port < 0 or self.port > 65535:
            raise ValueError("port must be between 0 and 65535")
        if self.timestamp == 0:
            self.timestamp = int(time.time())
        if not isinstance(self.model_shards, list):
            self.model_shards = list(self.model_shards)
        if not isinstance(self.signature, bytes):
            self.signature = bytes(self.signature)
        # Accept dict for capabilities and convert to NodeCapabilities
        if isinstance(self.capabilities, dict):
            self.capabilities = NodeCapabilities.from_dict(self.capabilities)

    def to_json(self) -> str:
        """Serialize to JSON string. Signature is base64-encoded."""
        if utl_messages_serialized_total:
            utl_messages_serialized_total.inc()
        return json.dumps({
            "node_id": self.node_id,
            "ip_address": self.ip_address,
            "port": self.port,
            "capabilities": self.capabilities._to_dict(),
            "model_shards": self.model_shards,
            "timestamp": self.timestamp,
            "signature": base64.b64encode(self.signature).decode("ascii")
        })

    # Legacy alias
    serialize = to_json

    @classmethod
    def from_json(cls, data) -> "MeshNodeRegistration":
        """Deserialize from JSON string or dict."""
        obj = json.loads(data) if isinstance(data, str) else data
        return cls(
            node_id=obj["node_id"],
            ip_address=obj["ip_address"],
            port=obj["port"],
            capabilities=NodeCapabilities.from_json(obj["capabilities"]),
            model_shards=obj["model_shards"],
            timestamp=obj["timestamp"],
            signature=base64.b64decode(obj["signature"])
        )

    # Legacy alias
    deserialize = from_json

    def __eq__(self, other):
        if not isinstance(other, MeshNodeRegistration):
            return False
        return (self.node_id == other.node_id and
                self.ip_address == other.ip_address and
                self.port == other.port and
                self.capabilities == other.capabilities and
                self.model_shards == other.model_shards and
                self.timestamp == other.timestamp and
                self.signature == other.signature)


# === SUBSCRIPTION STATE ===

@dataclass
class SubscriptionState:
    """User subscription managed via Soulbound NFT wallet.

    Tracks the user's active plan, expiration, and registered devices.
    """

    wallet_address: str
    tier: SubscriptionTier
    active: bool
    expires_at: int
    devices: List[str]
    payment_token: str

    def __post_init__(self):
        self.wallet_address = self.wallet_address[:MAX_FIELD_LENGTH] if self.wallet_address else ""
        self.payment_token = self.payment_token[:MAX_FIELD_LENGTH] if self.payment_token else ""
        if not isinstance(self.devices, list):
            self.devices = list(self.devices)
        if isinstance(self.tier, int):
            self.tier = SubscriptionTier(self.tier)
        if self.expires_at < 0:
            raise ValueError("expires_at must be >= 0")

    def to_json(self) -> str:
        """Serialize to JSON string."""
        if utl_messages_serialized_total:
            utl_messages_serialized_total.inc()
        return json.dumps({
            "wallet_address": self.wallet_address,
            "tier": self.tier.value,
            "active": self.active,
            "expires_at": self.expires_at,
            "devices": self.devices,
            "payment_token": self.payment_token
        })

    # Legacy alias
    serialize = to_json

    @classmethod
    def from_json(cls, data) -> "SubscriptionState":
        """Deserialize from JSON string or dict."""
        obj = json.loads(data) if isinstance(data, str) else data
        return cls(
            wallet_address=obj["wallet_address"],
            tier=SubscriptionTier(obj["tier"]),
            active=obj["active"],
            expires_at=obj["expires_at"],
            devices=obj["devices"],
            payment_token=obj["payment_token"]
        )

    # Legacy alias
    deserialize = from_json

    def __eq__(self, other):
        if not isinstance(other, SubscriptionState):
            return False
        return (self.wallet_address == other.wallet_address and
                self.tier == other.tier and
                self.active == other.active and
                self.expires_at == other.expires_at and
                self.devices == other.devices and
                self.payment_token == other.payment_token)


# === MAIN GUARD ===

if __name__ == '__main__':
    # Quick sanity check — serialize/deserialize round-trip
    logging.basicConfig(level=logging.INFO)
    logger.info(f"{LOG_PREFIX} Running self-test...")

    msg = TextInterceptionMessage(
        source_app="Firefox",
        element_id="txt_001",
        original_text="Hello world",
        translated_text="Ahoj svete",
        source_lang="en",
        target_lang="cs",
        confidence=0.98,
        position=(100, 200, 300, 50),
        timestamp=1700000000
    )
    assert TextInterceptionMessage.from_json(msg.to_json()) == msg

    seg = DubbingSegment(
        speaker_id="spk_01",
        original_text="How are you?",
        translated_text="Jak se mas?",
        source_lang="en",
        target_lang="cs",
        start_time_ms=5000,
        duration_ms=1500,
        voice_profile_id="voice_cz_male_01"
    )
    assert DubbingSegment.from_json(seg.to_json()) == seg

    caps = NodeCapabilities(
        cpu_cores=8,
        gpu_vram_mb=8192,
        ram_mb=32768,
        bandwidth_mbps=100.0,
        available_models=["opus-mt-en-cs"]
    )
    assert NodeCapabilities.from_json(caps.to_json()) == caps

    node = MeshNodeRegistration(
        node_id="node_abc123",
        ip_address="192.168.1.42",
        port=9302,
        capabilities=NodeCapabilities(
            cpu_cores=8, gpu_vram_mb=8192, ram_mb=32768,
            bandwidth_mbps=100.0, available_models=["opus-mt-en-cs"]
        ),
        model_shards=["shard_001", "shard_002"],
        timestamp=1700000000,
        signature=b"\x01\x02\x03\x04"
    )
    assert MeshNodeRegistration.from_json(node.to_json()) == node

    sub = SubscriptionState(
        wallet_address="0x1234567890abcdef1234567890abcdef12345678",
        tier=SubscriptionTier.FAMILY_423,
        active=True,
        expires_at=1703000000,
        devices=["device_a", "device_b", "smart_tv_1"],
        payment_token="0xMiniMeContractAddress"
    )
    assert SubscriptionState.from_json(sub.to_json()) == sub

    # Test legacy aliases still work
    assert TextInterceptionMessage.deserialize(msg.serialize()) == msg
    assert DubbingSegment.deserialize(seg.serialize()) == seg
    assert MeshNodeRegistration.deserialize(node.serialize()) == node
    assert SubscriptionState.deserialize(sub.serialize()) == sub

    # Test dict-based capabilities (backward compatibility)
    node_dict = MeshNodeRegistration(
        node_id="node_compat",
        ip_address="10.0.0.1",
        port=9302,
        capabilities={"cpu_cores": 4, "gpu_vram_mb": 4096, "ram_mb": 16384,
                      "bandwidth_mbps": 50.0, "available_models": []},
        model_shards=[],
        timestamp=1700000000,
        signature=b""
    )
    assert isinstance(node_dict.capabilities, NodeCapabilities)

    print(f"{LOG_PREFIX} All self-tests passed.")
