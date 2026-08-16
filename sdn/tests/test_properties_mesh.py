"""Property-based tests for Faucet Mesh network correctness.

Properties tested:
- Property 11: Model shard distribution — no complete model on single node
- Property 12: Mesh fault tolerance at 30% node loss
- Property 13: Mesh node authentication — NFT + attestation gate
- Property 16: GCP burst threshold control
- Property 19: Model shard integrity verification

Validates: Requirements 6.5, 6.7, 17.1, 17.4, 18.1, 18.3, 16.2
"""

import hashlib
from dataclasses import dataclass, field

from hypothesis import given, settings, assume
from hypothesis import strategies as st


# ---------------------------------------------------------------------------
# Domain models for mesh property testing
# ---------------------------------------------------------------------------


@dataclass
class ShardAssignment:
    """Tracks which shards of a model are assigned to which nodes."""

    model_id: str
    total_shards: int
    # Mapping: node_id -> set of shard indices assigned to that node
    node_shards: dict[str, set[int]] = field(default_factory=dict)


@dataclass
class MeshNode:
    """A node in the Faucet Mesh network."""

    node_id: str
    neighbors: set[str] = field(default_factory=set)
    is_active: bool = True


@dataclass
class MeshTopology:
    """A mesh network topology with routing capability."""

    nodes: dict[str, MeshNode] = field(default_factory=dict)

    def can_route(self, source: str, target: str) -> bool:
        """BFS routing check between source and target using active nodes."""
        if source == target:
            return True
        if source not in self.nodes or target not in self.nodes:
            return False
        if not self.nodes[source].is_active or not self.nodes[target].is_active:
            return False

        visited = {source}
        queue = [source]
        while queue:
            current = queue.pop(0)
            for neighbor in self.nodes[current].neighbors:
                if neighbor == target and self.nodes[neighbor].is_active:
                    return True
                if neighbor not in visited and neighbor in self.nodes and self.nodes[neighbor].is_active:
                    visited.add(neighbor)
                    queue.append(neighbor)
        return False

    def all_pairs_routable(self) -> bool:
        """Check if all active nodes can route to each other."""
        active_nodes = [nid for nid, node in self.nodes.items() if node.is_active]
        for i, src in enumerate(active_nodes):
            for dst in active_nodes[i + 1 :]:
                if not self.can_route(src, dst):
                    return False
        return True


def distribute_shards(model_id: str, total_shards: int, node_ids: list[str]) -> ShardAssignment:
    """Distribute model shards across nodes ensuring no node gets all shards.

    Uses round-robin distribution. When replication would cause a node to hold
    all shards, the replica is placed on a different node to maintain the invariant.
    The key constraint: no single node holds ALL shards of a model.
    """
    assignment = ShardAssignment(model_id=model_id, total_shards=total_shards)
    if not node_ids or total_shards <= 0:
        return assignment

    num_nodes = len(node_ids)

    # Primary assignment: round-robin
    for shard_idx in range(total_shards):
        primary_node = node_ids[shard_idx % num_nodes]
        if primary_node not in assignment.node_shards:
            assignment.node_shards[primary_node] = set()
        assignment.node_shards[primary_node].add(shard_idx)

    # Replication: add replicas only if the replica node would NOT end up
    # with all shards. Skip replica if it would violate the invariant.
    if num_nodes > 1:
        for shard_idx in range(total_shards):
            replica_node = node_ids[(shard_idx + 1) % num_nodes]
            if replica_node not in assignment.node_shards:
                assignment.node_shards[replica_node] = set()

            # Check if adding this shard would give the replica node ALL shards
            candidate_set = assignment.node_shards[replica_node] | {shard_idx}
            if len(candidate_set) < total_shards:
                assignment.node_shards[replica_node].add(shard_idx)
            else:
                # Try next node in ring that won't violate invariant
                for offset in range(2, num_nodes):
                    alt_node = node_ids[(shard_idx + offset) % num_nodes]
                    if alt_node not in assignment.node_shards:
                        assignment.node_shards[alt_node] = set()
                    alt_set = assignment.node_shards[alt_node] | {shard_idx}
                    if len(alt_set) < total_shards:
                        assignment.node_shards[alt_node].add(shard_idx)
                        break

    return assignment


def authenticate_node(has_valid_nft: bool, has_valid_attestation: bool) -> bool:
    """Mesh node authentication: access granted iff valid NFT AND valid attestation.

    Both conditions must be true for mesh access to be granted.
    """
    return has_valid_nft and has_valid_attestation


def check_burst_activation(latency_readings: list[float]) -> bool:
    """Check if GCP burst should be activated.

    Burst activates when average latency exceeds 3 seconds.
    """
    if not latency_readings:
        return False
    avg_latency = sum(latency_readings) / len(latency_readings)
    return avg_latency > 3.0


def check_burst_deactivation(latency_readings: list[float], duration_minutes: float) -> bool:
    """Check if GCP burst should be deactivated.

    Burst deactivates when average latency is below 1.5s for at least 5 minutes.
    """
    if not latency_readings:
        return False
    avg_latency = sum(latency_readings) / len(latency_readings)
    return avg_latency < 1.5 and duration_minutes >= 5.0


def verify_shard_integrity(shard_data: bytes, expected_hash: str) -> bool:
    """Verify integrity of a model shard using SHA-256 hash comparison."""
    actual_hash = hashlib.sha256(shard_data).hexdigest()
    return actual_hash == expected_hash


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

node_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
    min_size=1,
    max_size=16,
)

# Strategy for generating a list of unique node IDs (at least 2 nodes for distribution)
node_list_strategy = st.lists(node_id_strategy, min_size=2, max_size=20, unique=True)

# Strategy for total shard count (at least 2 shards to make distribution meaningful)
shard_count_strategy = st.integers(min_value=2, max_value=64)

# Strategy for model IDs
model_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
    min_size=1,
    max_size=32,
)

# Strategy for latency readings (positive floats representing seconds)
latency_strategy = st.floats(min_value=0.01, max_value=30.0, allow_nan=False, allow_infinity=False)

# Strategy for shard data (random binary)
shard_data_strategy = st.binary(min_size=1, max_size=4096)


# ---------------------------------------------------------------------------
# Property 11: Model shard distribution — no complete model on single node
# **Validates: Requirements 6.5**
# ---------------------------------------------------------------------------


class TestProperty11ShardDistribution:
    """Property 11: For any model M distributed across the mesh,
    for any node N: shards_on_N(M) < total_shards(M).

    No single node shall hold a complete model.
    """

    @given(
        model_id=model_id_strategy,
        total_shards=shard_count_strategy,
        node_ids=node_list_strategy,
    )
    @settings(max_examples=100)
    def test_no_single_node_holds_complete_model(self, model_id: str, total_shards: int, node_ids: list[str]):
        """**Validates: Requirements 6.5**

        For any model M, for any node N: shards_on_N(M) < total_shards(M).
        """
        assignment = distribute_shards(model_id, total_shards, node_ids)

        # The core invariant: no single node has all shards
        for node_id, shards in assignment.node_shards.items():
            assert len(shards) < assignment.total_shards, (
                f"Node {node_id} holds {len(shards)} shards out of "
                f"{assignment.total_shards} total — complete model on single node!"
            )

    @given(
        model_id=model_id_strategy,
        total_shards=shard_count_strategy,
        node_ids=node_list_strategy,
    )
    @settings(max_examples=100)
    def test_all_shards_are_distributed(self, model_id: str, total_shards: int, node_ids: list[str]):
        """All shards must be assigned to at least one node (completeness)."""
        assignment = distribute_shards(model_id, total_shards, node_ids)

        all_assigned_shards = set()
        for shards in assignment.node_shards.values():
            all_assigned_shards.update(shards)

        expected_shards = set(range(total_shards))
        assert all_assigned_shards == expected_shards, (
            f"Not all shards distributed: missing {expected_shards - all_assigned_shards}"
        )


# ---------------------------------------------------------------------------
# Property 12: Mesh fault tolerance at 30% node loss
# **Validates: Requirements 6.7**
# ---------------------------------------------------------------------------


def build_connected_topology(node_ids: list[str]) -> MeshTopology:
    """Build a fully connected mesh topology (complete graph) from node IDs.

    A complete graph guarantees that removing up to (n-2) nodes still leaves
    the remaining nodes connected. For 30% removal with n>=4, this holds.
    """
    topology = MeshTopology()
    for nid in node_ids:
        topology.nodes[nid] = MeshNode(node_id=nid)

    # Create complete graph — every node connected to every other
    for i, nid in enumerate(node_ids):
        for j, other in enumerate(node_ids):
            if i != j:
                topology.nodes[nid].neighbors.add(other)

    return topology


class TestProperty12FaultTolerance:
    """Property 12: Remove any 30% of nodes, verify remaining nodes can still route tasks.

    The mesh must maintain full connectivity after losing 30% of nodes.
    """

    @given(
        node_ids=st.lists(node_id_strategy, min_size=4, max_size=20, unique=True),
        removal_seed=st.integers(min_value=0, max_value=2**32 - 1),
    )
    @settings(max_examples=100)
    def test_routing_survives_30_percent_node_loss(self, node_ids: list[str], removal_seed: int):
        """**Validates: Requirements 6.7**

        After removing 30% of nodes from a connected topology,
        all remaining active nodes can still route to each other.
        """
        topology = build_connected_topology(node_ids)

        # Determine 30% of nodes to remove
        num_to_remove = max(1, int(len(node_ids) * 0.3))

        # Use deterministic selection based on seed
        import random

        rng = random.Random(removal_seed)
        nodes_to_remove = rng.sample(node_ids, num_to_remove)

        # Deactivate removed nodes
        for nid in nodes_to_remove:
            topology.nodes[nid].is_active = False

        # Verify remaining nodes can still route to each other
        assert topology.all_pairs_routable(), (
            f"Routing failed after removing {num_to_remove}/{len(node_ids)} nodes: "
            f"removed={nodes_to_remove}"
        )


# ---------------------------------------------------------------------------
# Property 13: Mesh node authentication — NFT + attestation gate
# **Validates: Requirements 17.1, 17.4**
# ---------------------------------------------------------------------------


class TestProperty13Authentication:
    """Property 13: Access granted iff valid NFT AND valid attestation; else denied.

    Both Soulbound NFT verification and hardware attestation must pass
    for a node to be granted mesh access.
    """

    @given(
        has_valid_nft=st.booleans(),
        has_valid_attestation=st.booleans(),
    )
    @settings(max_examples=100)
    def test_authentication_gate_logic(self, has_valid_nft: bool, has_valid_attestation: bool):
        """**Validates: Requirements 17.1, 17.4**

        Access granted iff (valid_nft AND valid_attestation).
        """
        result = authenticate_node(has_valid_nft, has_valid_attestation)
        expected = has_valid_nft and has_valid_attestation

        assert result == expected, (
            f"Authentication mismatch: NFT={has_valid_nft}, "
            f"attestation={has_valid_attestation}, got={result}, expected={expected}"
        )

    @given(has_valid_attestation=st.booleans())
    @settings(max_examples=100)
    def test_invalid_nft_always_denied(self, has_valid_attestation: bool):
        """Without valid NFT, access is always denied regardless of attestation."""
        result = authenticate_node(has_valid_nft=False, has_valid_attestation=has_valid_attestation)
        assert result is False, "Access granted without valid NFT"

    @given(has_valid_nft=st.booleans())
    @settings(max_examples=100)
    def test_invalid_attestation_always_denied(self, has_valid_nft: bool):
        """Without valid attestation, access is always denied regardless of NFT."""
        result = authenticate_node(has_valid_nft=has_valid_nft, has_valid_attestation=False)
        assert result is False, "Access granted without valid attestation"


# ---------------------------------------------------------------------------
# Property 16: GCP burst threshold control
# **Validates: Requirements 18.1, 18.3**
# ---------------------------------------------------------------------------


class TestProperty16GCPBurst:
    """Property 16: GCP burst activation and deactivation thresholds.

    - avg_latency > 3s → burst activates
    - avg_latency < 1.5s for 5 min → burst deactivates
    """

    @given(
        latency_readings=st.lists(
            st.floats(min_value=3.01, max_value=30.0, allow_nan=False, allow_infinity=False),
            min_size=1,
            max_size=50,
        )
    )
    @settings(max_examples=100)
    def test_burst_activates_when_latency_exceeds_threshold(self, latency_readings: list[float]):
        """**Validates: Requirements 18.1**

        When average latency exceeds 3 seconds, GCP burst must activate.
        """
        result = check_burst_activation(latency_readings)
        assert result is True, (
            f"Burst should activate: avg={sum(latency_readings)/len(latency_readings):.2f}s > 3s"
        )

    @given(
        latency_readings=st.lists(
            st.floats(min_value=0.01, max_value=2.99, allow_nan=False, allow_infinity=False),
            min_size=1,
            max_size=50,
        )
    )
    @settings(max_examples=100)
    def test_burst_does_not_activate_below_threshold(self, latency_readings: list[float]):
        """When average latency is below 3 seconds, burst must NOT activate."""
        result = check_burst_activation(latency_readings)
        assert result is False, (
            f"Burst should NOT activate: avg={sum(latency_readings)/len(latency_readings):.2f}s < 3s"
        )

    @given(
        latency_readings=st.lists(
            st.floats(min_value=0.01, max_value=1.49, allow_nan=False, allow_infinity=False),
            min_size=1,
            max_size=50,
        ),
        duration_minutes=st.floats(min_value=5.0, max_value=60.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_burst_deactivates_when_latency_low_for_5_min(
        self, latency_readings: list[float], duration_minutes: float
    ):
        """**Validates: Requirements 18.3**

        When avg latency < 1.5s for >= 5 minutes, burst deactivates.
        """
        result = check_burst_deactivation(latency_readings, duration_minutes)
        assert result is True, (
            f"Burst should deactivate: avg={sum(latency_readings)/len(latency_readings):.2f}s "
            f"< 1.5s for {duration_minutes:.1f} min"
        )

    @given(
        latency_readings=st.lists(
            st.floats(min_value=0.01, max_value=1.49, allow_nan=False, allow_infinity=False),
            min_size=1,
            max_size=50,
        ),
        duration_minutes=st.floats(min_value=0.01, max_value=4.99, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_burst_does_not_deactivate_before_5_min(
        self, latency_readings: list[float], duration_minutes: float
    ):
        """Burst must NOT deactivate if low latency has not been sustained for 5 minutes."""
        result = check_burst_deactivation(latency_readings, duration_minutes)
        assert result is False, (
            f"Burst should NOT deactivate yet: only {duration_minutes:.1f} min < 5 min"
        )


# ---------------------------------------------------------------------------
# Property 19: Model shard integrity verification
# **Validates: Requirements 16.2**
# ---------------------------------------------------------------------------


class TestProperty19ShardIntegrity:
    """Property 19: Model shard integrity verification.

    - Unmodified shard + correct hash → integrity passes
    - Modified shard → integrity fails
    """

    @given(shard_data=shard_data_strategy)
    @settings(max_examples=100)
    def test_unmodified_shard_passes_integrity(self, shard_data: bytes):
        """**Validates: Requirements 16.2**

        Unmodified shard with correct hash must pass integrity verification.
        """
        correct_hash = hashlib.sha256(shard_data).hexdigest()
        assert verify_shard_integrity(shard_data, correct_hash) is True, (
            "Integrity check failed for unmodified shard with correct hash"
        )

    @given(
        shard_data=shard_data_strategy,
        modification_pos=st.integers(min_value=0),
        modification_byte=st.integers(min_value=0, max_value=255),
    )
    @settings(max_examples=100)
    def test_modified_shard_fails_integrity(
        self, shard_data: bytes, modification_pos: int, modification_byte: int
    ):
        """Modified shard must fail integrity verification."""
        # Compute hash of original data
        correct_hash = hashlib.sha256(shard_data).hexdigest()

        # Modify the shard at a valid position
        pos = modification_pos % len(shard_data)
        original_byte = shard_data[pos]

        # Ensure we actually modify (different byte value)
        assume(modification_byte != original_byte)

        modified_data = bytearray(shard_data)
        modified_data[pos] = modification_byte
        modified_shard = bytes(modified_data)

        assert verify_shard_integrity(modified_shard, correct_hash) is False, (
            "Integrity check passed for MODIFIED shard — should have failed"
        )

    @given(
        shard_data=shard_data_strategy,
        wrong_hash=st.text(
            alphabet="0123456789abcdef",
            min_size=64,
            max_size=64,
        ),
    )
    @settings(max_examples=100)
    def test_wrong_hash_fails_integrity(self, shard_data: bytes, wrong_hash: str):
        """Shard with incorrect expected hash must fail integrity verification."""
        correct_hash = hashlib.sha256(shard_data).hexdigest()
        assume(wrong_hash != correct_hash)

        assert verify_shard_integrity(shard_data, wrong_hash) is False, (
            "Integrity check passed with wrong hash — should have failed"
        )
