"""
Mesh Protocol — Python Bindings (protobuf-compatible interface)

Purpose: Provide Python classes mirroring protoc-generated code for mesh protocol
         messages. Uses dataclasses with SerializeToString/ParseFromString API.
         Allows the project to work without protoc installed while maintaining
         the same interface as generated protobuf bindings.

Author: Pan Jeskyne (Jakub Panocha) — AsgardLab
Requirements: 6.3 (task routing), 6.5 (model shard distribution)
"""

import json
import struct
from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Optional


# === TASK TYPE ENUMERATION ===

class TaskType(IntEnum):
    """Types of tasks that can be routed through the mesh network."""
    TRANSLATE_TEXT = 0
    TRANSLATE_AUDIO = 1
    VOICE_SEPARATE = 2
    OCR_EXTRACT = 3
    INFERENCE = 4
    MODEL_SHARD_SYNC = 5


# === BASE MESSAGE CLASS ===

class _MessageBase:
    """Base class providing protobuf-compatible serialization interface."""

    def SerializeToString(self) -> bytes:
        """Serialize this message to a binary string (JSON-encoded UTF-8).

        Returns a deterministic byte representation suitable for network
        transmission and storage. Uses JSON encoding for portability.
        """
        return json.dumps(self._to_dict(), sort_keys=True).encode("utf-8")

    def ParseFromString(self, data: bytes) -> None:
        """Parse a binary string and populate this message's fields.

        Args:
            data: Bytes previously produced by SerializeToString().

        Raises:
            ValueError: If data cannot be parsed or contains invalid fields.
        """
        try:
            obj = json.loads(data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise ValueError(f"Failed to parse message: {e}")
        self._from_dict(obj)

    def _to_dict(self) -> dict:
        raise NotImplementedError

    def _from_dict(self, obj: dict) -> None:
        raise NotImplementedError

    def __eq__(self, other) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self._to_dict() == other._to_dict()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._to_dict()})"


# === TASK REQUEST ===

@dataclass
class TaskRequest(_MessageBase):
    """Request sent by a node that needs computation from the mesh.

    The encrypted_payload contains the actual task data, encrypted with
    XChaCha20-Poly1305. Only the requester and the assigned processing
    node can decrypt it.
    """
    task_id: str = ""
    task_type: TaskType = TaskType.TRANSLATE_TEXT
    encrypted_payload: bytes = b""
    max_latency_ms: int = 0
    requester_node_id: str = ""
    requester_signature: bytes = b""

    def _to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "task_type": int(self.task_type),
            "encrypted_payload": self.encrypted_payload.hex(),
            "max_latency_ms": self.max_latency_ms,
            "requester_node_id": self.requester_node_id,
            "requester_signature": self.requester_signature.hex(),
        }

    def _from_dict(self, obj: dict) -> None:
        self.task_id = str(obj.get("task_id", ""))
        self.task_type = TaskType(int(obj.get("task_type", 0)))
        self.encrypted_payload = bytes.fromhex(obj.get("encrypted_payload", ""))
        self.max_latency_ms = int(obj.get("max_latency_ms", 0))
        self.requester_node_id = str(obj.get("requester_node_id", ""))
        self.requester_signature = bytes.fromhex(obj.get("requester_signature", ""))


# === TASK RESPONSE ===

@dataclass
class TaskResponse(_MessageBase):
    """Response returned by the node that processed a task.

    The encrypted_result is decryptable only by the original requester
    (end-to-end encryption via Privacy Protocol).
    """
    task_id: str = ""
    success: bool = False
    encrypted_result: bytes = b""
    processing_time_ms: int = 0
    responder_node_id: str = ""

    def _to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "success": self.success,
            "encrypted_result": self.encrypted_result.hex(),
            "processing_time_ms": self.processing_time_ms,
            "responder_node_id": self.responder_node_id,
        }

    def _from_dict(self, obj: dict) -> None:
        self.task_id = str(obj.get("task_id", ""))
        self.success = bool(obj.get("success", False))
        self.encrypted_result = bytes.fromhex(obj.get("encrypted_result", ""))
        self.processing_time_ms = int(obj.get("processing_time_ms", 0))
        self.responder_node_id = str(obj.get("responder_node_id", ""))


# === NODE HEARTBEAT ===

@dataclass
class NodeHeartbeat(_MessageBase):
    """Periodically broadcast by each mesh node to report availability.

    Contains hardware utilization metrics and list of available AI models,
    used by Mesh_Orchestrator for task routing decisions.
    """
    node_id: str = ""
    cpu_usage: float = 0.0
    gpu_usage: float = 0.0
    ram_available_mb: float = 0.0
    available_models: List[str] = field(default_factory=list)
    timestamp: int = 0

    def _to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "cpu_usage": self.cpu_usage,
            "gpu_usage": self.gpu_usage,
            "ram_available_mb": self.ram_available_mb,
            "available_models": list(self.available_models),
            "timestamp": self.timestamp,
        }

    def _from_dict(self, obj: dict) -> None:
        self.node_id = str(obj.get("node_id", ""))
        self.cpu_usage = float(obj.get("cpu_usage", 0.0))
        self.gpu_usage = float(obj.get("gpu_usage", 0.0))
        self.ram_available_mb = float(obj.get("ram_available_mb", 0.0))
        self.available_models = [str(m) for m in obj.get("available_models", [])]
        self.timestamp = int(obj.get("timestamp", 0))
