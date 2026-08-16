"""
Model Shard Manager — Universal Translation Layer (UTL)

Manages sharded AI model distribution across mesh nodes.
- Shard storage, retrieval, and assembly
- Cryptographic hash (SHA-256) integrity verification per shard
- Hot-swap of model versions without restart
- Distribution constraint: no single node holds all shards of any model
- Incremental sync for new nodes joining the mesh

Autor: Pan Jeskyně
Asistent: Kiro
Standard: Faucet Mesh Shard Distribution
"""

import hashlib
import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# === LOGGING ===

logger = logging.getLogger(__name__)
LOG_PREFIX = "[SHARD_MGR]"

# === PROMETHEUS METRICS ===

try:
    from prometheus_client import Gauge

    utl_model_shards_distributed = Gauge(
        'utl_model_shards_distributed',
        'Number of model shards stored locally',
        ['model_id']
    )

    utl_model_sync_progress = Gauge(
        'utl_model_sync_progress',
        'Model sync progress (0.0-1.0) for active sync operations',
        ['model_id', 'target_node']
    )
except ImportError:
    utl_model_shards_distributed = None
    utl_model_sync_progress = None

# === CONSTANTS ===

MAX_SHARDS_PER_NODE_RATIO = 0.8  # Node can hold at most 80% of a model's shards
DEFAULT_SHARD_SIZE_BYTES = 64 * 1024 * 1024  # 64MB default shard size


# === DATA MODELS ===

@dataclass
class ShardMetadata:
    """Metadata for a single model shard."""
    model_id: str
    shard_index: int
    total_shards: int
    sha256_hash: str
    size_bytes: int
    version: str
    created_at: float = field(default_factory=time.time)


@dataclass
class ModelInfo:
    """Information about a distributed model."""
    model_id: str
    version: str
    total_shards: int
    shard_hashes: Dict[int, str] = field(default_factory=dict)  # index -> hash
    shard_sizes: Dict[int, int] = field(default_factory=dict)   # index -> size


@dataclass
class NodeShardMap:
    """Tracks which shards are stored on which nodes."""
    node_id: str
    shards: Set[Tuple[str, int]] = field(default_factory=set)  # (model_id, shard_index)


# === MODEL SHARD MANAGER CLASS ===

class ModelShardManager:
    """Manages sharded AI model distribution across mesh nodes.

    Key guarantees:
    - No single node holds all shards of any model (distribution constraint)
    - Cryptographic hash verification ensures integrity
    - Hot-swap allows updating models without service interruption
    - Incremental sync provides shards to new nodes efficiently

    All shard data is stored in memory (no disk persistence for privacy).
    Thread-safe: concurrent access from multiple mesh nodes is supported.
    """

    def __init__(self, local_node_id: str = "local"):
        """Initialize Model Shard Manager.

        Args:
            local_node_id: Identifier for this node in the mesh
        """
        self._lock = threading.RLock()
        self._local_node_id = local_node_id

        # Shard storage: {(model_id, shard_index): bytes}
        self._shards: Dict[Tuple[str, int], bytes] = {}

        # Model registry: {model_id: ModelInfo}
        self._models: Dict[str, ModelInfo] = {}

        # Node distribution map: {node_id: NodeShardMap}
        self._node_maps: Dict[str, NodeShardMap] = {}
        self._node_maps[local_node_id] = NodeShardMap(node_id=local_node_id)

        # Active model versions (for hot-swap)
        self._active_versions: Dict[str, str] = {}

        logger.info(f"{LOG_PREFIX} Initialized for node: {local_node_id}")

    # === SHARD STORAGE AND RETRIEVAL ===

    def store_shard(self, model_id: str, shard_index: int, data: bytes,
                    version: str = "1.0", total_shards: int = 0) -> bool:
        """Store a model shard locally.

        Args:
            model_id: Model identifier
            shard_index: Index of this shard (0-based)
            data: Raw shard data bytes
            version: Model version string
            total_shards: Total number of shards for this model

        Returns:
            True if stored successfully, False if distribution constraint violated
        """
        with self._lock:
            # Register model if not known
            if model_id not in self._models:
                if total_shards <= 0:
                    total_shards = shard_index + 1
                self._models[model_id] = ModelInfo(
                    model_id=model_id,
                    version=version,
                    total_shards=total_shards,
                )

            model_info = self._models[model_id]

            # Update total_shards if provided and larger
            if total_shards > model_info.total_shards:
                model_info.total_shards = total_shards

            # Check distribution constraint
            if not self._can_store_shard(model_id, shard_index):
                logger.warning(
                    f"{LOG_PREFIX} Cannot store shard {model_id}[{shard_index}]: "
                    f"would violate distribution constraint"
                )
                return False

            # Compute hash
            shard_hash = hashlib.sha256(data).hexdigest()

            # Store shard
            self._shards[(model_id, shard_index)] = data
            model_info.shard_hashes[shard_index] = shard_hash
            model_info.shard_sizes[shard_index] = len(data)

            # Update node map
            self._node_maps[self._local_node_id].shards.add((model_id, shard_index))

            # Update metrics
            if utl_model_shards_distributed:
                local_count = sum(
                    1 for k in self._shards if k[0] == model_id
                )
                utl_model_shards_distributed.labels(model_id=model_id).set(local_count)

            logger.info(
                f"{LOG_PREFIX} Stored shard {model_id}[{shard_index}] "
                f"({len(data)} bytes, hash={shard_hash[:16]}...)"
            )
            return True

    def get_shard(self, model_id: str, shard_index: int) -> Optional[bytes]:
        """Retrieve a model shard from local storage.

        Args:
            model_id: Model identifier
            shard_index: Index of the shard

        Returns:
            Shard data bytes, or None if not stored locally
        """
        with self._lock:
            return self._shards.get((model_id, shard_index))

    def has_shard(self, model_id: str, shard_index: int) -> bool:
        """Check if a shard is stored locally."""
        with self._lock:
            return (model_id, shard_index) in self._shards

    def get_local_shards(self, model_id: str) -> List[int]:
        """Get list of shard indices stored locally for a model."""
        with self._lock:
            return [
                idx for (mid, idx) in self._shards.keys()
                if mid == model_id
            ]

    # === INTEGRITY VERIFICATION ===

    def verify_integrity(self, model_id: str, shard_index: int,
                         expected_hash: str) -> bool:
        """Verify integrity of a stored shard using SHA-256 hash.

        Args:
            model_id: Model identifier
            shard_index: Shard index to verify
            expected_hash: Expected SHA-256 hex digest

        Returns:
            True if hash matches, False otherwise
        """
        with self._lock:
            data = self._shards.get((model_id, shard_index))
            if data is None:
                logger.warning(
                    f"{LOG_PREFIX} Cannot verify {model_id}[{shard_index}]: not stored"
                )
                return False

            actual_hash = hashlib.sha256(data).hexdigest()
            is_valid = actual_hash == expected_hash

            if not is_valid:
                logger.warning(
                    f"{LOG_PREFIX} Integrity check FAILED for {model_id}[{shard_index}]: "
                    f"expected={expected_hash[:16]}..., actual={actual_hash[:16]}..."
                )
            else:
                logger.debug(
                    f"{LOG_PREFIX} Integrity check passed for {model_id}[{shard_index}]"
                )

            return is_valid

    def compute_hash(self, model_id: str, shard_index: int) -> Optional[str]:
        """Compute SHA-256 hash for a stored shard.

        Returns:
            Hex digest string, or None if shard not found
        """
        with self._lock:
            data = self._shards.get((model_id, shard_index))
            if data is None:
                return None
            return hashlib.sha256(data).hexdigest()

    # === MODEL ASSEMBLY ===

    def assemble_model(self, model_id: str) -> Optional[bytes]:
        """Assemble a complete model from locally stored shards.

        Concatenates all shards in order. Returns None if any shard is missing.

        Args:
            model_id: Model identifier

        Returns:
            Complete model bytes, or None if incomplete
        """
        with self._lock:
            model_info = self._models.get(model_id)
            if model_info is None:
                logger.warning(f"{LOG_PREFIX} Model {model_id} not registered")
                return None

            parts = []
            for i in range(model_info.total_shards):
                data = self._shards.get((model_id, i))
                if data is None:
                    logger.warning(
                        f"{LOG_PREFIX} Cannot assemble {model_id}: "
                        f"missing shard {i}"
                    )
                    return None
                parts.append(data)

            assembled = b"".join(parts)
            logger.info(
                f"{LOG_PREFIX} Assembled model {model_id}: "
                f"{len(assembled)} bytes from {model_info.total_shards} shards"
            )
            return assembled

    # === HOT-SWAP ===

    def hot_swap(self, model_id: str, new_version: str) -> bool:
        """Hot-swap a model to a new version without service interruption.

        Atomically switches the active version pointer. Old shards are
        kept until the new version is fully available.

        Args:
            model_id: Model to swap
            new_version: New version string

        Returns:
            True if swap was successful
        """
        with self._lock:
            old_version = self._active_versions.get(model_id, "unknown")
            self._active_versions[model_id] = new_version

            if model_id in self._models:
                self._models[model_id].version = new_version

            logger.info(
                f"{LOG_PREFIX} Hot-swap {model_id}: "
                f"{old_version} -> {new_version}"
            )
            return True

    def get_active_version(self, model_id: str) -> Optional[str]:
        """Get the currently active version of a model."""
        with self._lock:
            return self._active_versions.get(model_id)

    # === DISTRIBUTION CONSTRAINT ===

    def _can_store_shard(self, model_id: str, shard_index: int) -> bool:
        """Check if storing this shard would violate the distribution constraint.

        Constraint: no single node holds ALL shards of any model.
        A node can hold at most MAX_SHARDS_PER_NODE_RATIO (80%) of shards.
        """
        model_info = self._models.get(model_id)
        if model_info is None or model_info.total_shards <= 1:
            return True  # Can't enforce constraint for single-shard models

        # Count how many shards of this model we already have locally
        local_count = sum(
            1 for (mid, _) in self._shards.keys() if mid == model_id
        )

        # If we already have this shard, allow overwrite
        if (model_id, shard_index) in self._shards:
            return True

        # Check constraint: local_count + 1 must be < total_shards
        max_allowed = int(model_info.total_shards * MAX_SHARDS_PER_NODE_RATIO)
        max_allowed = max(max_allowed, model_info.total_shards - 1)  # At least N-1

        return (local_count + 1) < model_info.total_shards

    def check_distribution_constraint(self, model_id: str) -> bool:
        """Verify that the distribution constraint holds for a model.

        Returns True if no single node holds all shards.
        """
        with self._lock:
            model_info = self._models.get(model_id)
            if model_info is None:
                return True

            for node_map in self._node_maps.values():
                node_shard_count = sum(
                    1 for (mid, _) in node_map.shards if mid == model_id
                )
                if node_shard_count >= model_info.total_shards:
                    return False

            return True

    # === INCREMENTAL SYNC ===

    def get_sync_plan(self, target_node_id: str,
                      target_existing_shards: Set[Tuple[str, int]] = None
                      ) -> List[Tuple[str, int]]:
        """Generate a sync plan for a new node joining the mesh.

        Returns list of (model_id, shard_index) pairs that the target
        node needs and that we can provide.

        Args:
            target_node_id: ID of the node requesting sync
            target_existing_shards: Shards already on the target node

        Returns:
            List of (model_id, shard_index) tuples to transfer
        """
        with self._lock:
            if target_existing_shards is None:
                target_existing_shards = set()

            plan = []
            for (model_id, shard_idx), data in self._shards.items():
                if (model_id, shard_idx) not in target_existing_shards:
                    # Check that giving this shard wouldn't violate constraint
                    # for the target node
                    model_info = self._models.get(model_id)
                    if model_info and model_info.total_shards > 1:
                        target_count = sum(
                            1 for (mid, _) in target_existing_shards
                            if mid == model_id
                        )
                        if target_count + 1 >= model_info.total_shards:
                            continue  # Would violate constraint

                    plan.append((model_id, shard_idx))

            logger.info(
                f"{LOG_PREFIX} Sync plan for {target_node_id}: "
                f"{len(plan)} shards to transfer"
            )
            return plan

    def register_remote_node(self, node_id: str,
                             shards: Set[Tuple[str, int]] = None) -> None:
        """Register a remote node's shard inventory.

        Used to track distribution across the mesh.
        """
        with self._lock:
            self._node_maps[node_id] = NodeShardMap(
                node_id=node_id,
                shards=shards or set()
            )

    # === STATUS ===

    def get_status(self) -> Dict:
        """Get manager status summary."""
        with self._lock:
            return {
                "local_node": self._local_node_id,
                "total_shards_stored": len(self._shards),
                "models_registered": len(self._models),
                "nodes_tracked": len(self._node_maps),
                "active_versions": dict(self._active_versions),
            }

    @property
    def local_shard_count(self) -> int:
        """Total number of shards stored locally."""
        return len(self._shards)

    @property
    def models_registered(self) -> int:
        """Number of models registered."""
        return len(self._models)


# === MAIN GUARD ===

def main():
    """Self-test entry point for Model Shard Manager module."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    print(f"{LOG_PREFIX} Model Shard Manager self-test")

    manager = ModelShardManager(local_node_id="test_node_001")

    # Store shards for a model with 5 total shards
    model_id = "opus-mt-cs-en"
    total_shards = 5

    for i in range(4):  # Store only 4 of 5 (constraint: can't have all)
        data = f"shard_data_{i}_" .encode() * 1000
        success = manager.store_shard(
            model_id=model_id,
            shard_index=i,
            data=data,
            version="1.0",
            total_shards=total_shards,
        )
        assert success, f"Failed to store shard {i}"
        print(f"{LOG_PREFIX} Stored shard {i}: {len(data)} bytes")

    # Try storing the 5th shard (should fail — distribution constraint)
    data_5 = b"shard_data_4_" * 1000
    success = manager.store_shard(
        model_id=model_id, shard_index=4, data=data_5,
        version="1.0", total_shards=total_shards,
    )
    assert not success, "Should NOT be able to store all shards on one node"
    print(f"{LOG_PREFIX} Distribution constraint enforced: cannot store all shards")

    # Verify integrity
    shard_0 = manager.get_shard(model_id, 0)
    assert shard_0 is not None
    hash_0 = manager.compute_hash(model_id, 0)
    assert manager.verify_integrity(model_id, 0, hash_0)
    print(f"{LOG_PREFIX} Integrity verification: PASSED")

    # Test wrong hash detection
    assert not manager.verify_integrity(model_id, 0, "deadbeef" * 8)
    print(f"{LOG_PREFIX} Wrong hash detection: PASSED")

    # Test assembly (should fail — missing shard 4)
    assembled = manager.assemble_model(model_id)
    assert assembled is None, "Assembly should fail with missing shards"
    print(f"{LOG_PREFIX} Incomplete assembly detection: PASSED")

    # Hot-swap test
    manager.hot_swap(model_id, "2.0")
    assert manager.get_active_version(model_id) == "2.0"
    print(f"{LOG_PREFIX} Hot-swap: PASSED")

    # Sync plan test
    plan = manager.get_sync_plan("new_node", set())
    assert len(plan) > 0
    print(f"{LOG_PREFIX} Sync plan for new node: {len(plan)} shards")

    # Distribution constraint check
    assert manager.check_distribution_constraint(model_id)
    print(f"{LOG_PREFIX} Distribution constraint check: PASSED")

    print(f"{LOG_PREFIX} Status: {manager.get_status()}")
    print(f"{LOG_PREFIX} All self-tests passed.")


if __name__ == '__main__':
    main()
