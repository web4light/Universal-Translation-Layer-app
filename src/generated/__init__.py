"""
Generated Protocol Buffer bindings for mesh protocol.

This package provides Python message classes for the Faucet Mesh P2P protocol.
Classes can be generated via `python proto/generate.py` or used directly
from the dataclass-based fallback implementation.

Requirements: 6.3 (task routing), 6.5 (model shard distribution)
"""

from src.generated.mesh_protocol_pb2 import (
    TaskType,
    TaskRequest,
    TaskResponse,
    NodeHeartbeat,
)

__all__ = [
    "TaskType",
    "TaskRequest",
    "TaskResponse",
    "NodeHeartbeat",
]
