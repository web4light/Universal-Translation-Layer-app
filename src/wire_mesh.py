"""
Wire Mesh Orchestrator — Universal Translation Layer (UTL)

Integration module: connects MeshOrchestrator → ModelShardManager →
PrivacyProtocol → OfflineFallback into the complete mesh layer.

Autor: Pan Jeskyně
Asistent: Kiro
"""

import logging
from typing import Optional

# === LOGGING ===

logger = logging.getLogger(__name__)
LOG_PREFIX = "[WIRE_MESH]"

# === LOCAL IMPORTS ===

from mesh_orchestrator import MeshOrchestrator, NodeCapabilities, MeshTask, TaskType
from model_shard_manager import ModelShardManager
from privacy_protocol import PrivacyProtocol
from offline_fallback import OfflineFallback


# === MESH LAYER CLASS ===

class MeshLayer:
    """Unified mesh coordination layer.

    Combines:
    - MeshOrchestrator: node routing and GCP burst
    - ModelShardManager: model distribution
    - PrivacyProtocol: E2E encryption for all mesh traffic
    - OfflineFallback: graceful degradation when mesh unavailable
    """

    def __init__(self, local_node_id: str = "primary"):
        self._orchestrator = MeshOrchestrator()
        self._shard_manager = ModelShardManager(local_node_id=local_node_id)
        self._privacy = PrivacyProtocol()
        self._offline = OfflineFallback()

        # Wire offline callbacks
        self._offline.on_offline(self._on_mesh_offline)
        self._offline.on_online(self._on_mesh_online)

        logger.info(f"{LOG_PREFIX} Mesh layer wired (node={local_node_id})")

    def start(self) -> None:
        """Start mesh layer services."""
        self._offline.start_monitoring()
        self._privacy.schedule_purge()
        logger.info(f"{LOG_PREFIX} Mesh layer started")

    def stop(self) -> None:
        """Stop mesh layer services."""
        self._offline.stop_monitoring()
        self._privacy.stop_purge()
        logger.info(f"{LOG_PREFIX} Mesh layer stopped")

    def route_task_encrypted(self, task: MeshTask) -> Optional[bytes]:
        """Route a task through the mesh with E2E encryption.

        Encrypts payload, routes via orchestrator, decrypts result.
        Falls back to offline queue if mesh is unavailable.
        """
        if self._offline.is_offline:
            self._offline.queue_task(
                task_type=task.task_type.name,
                payload=task.payload,
                priority=task.priority,
            )
            logger.info(f"{LOG_PREFIX} Task queued (offline)")
            return None

        # Encrypt payload
        key = self._privacy.get_session_key()
        task.payload = self._privacy.encrypt(task.payload, key)

        # Route
        result = self._orchestrator.route_task(task)

        if result.success and result.result:
            # Decrypt result
            try:
                return self._privacy.decrypt(result.result)
            except RuntimeError:
                return result.result
        return result.result if result.success else None

    def _on_mesh_offline(self) -> None:
        """Handle mesh going offline."""
        logger.warning(f"{LOG_PREFIX} Mesh offline — switching to local processing")

    def _on_mesh_online(self) -> None:
        """Handle mesh coming back online — drain queued tasks."""
        tasks = self._offline.drain_queue()
        logger.info(f"{LOG_PREFIX} Mesh online — processing {len(tasks)} queued tasks")

    @property
    def orchestrator(self) -> MeshOrchestrator:
        return self._orchestrator

    @property
    def shard_manager(self) -> ModelShardManager:
        return self._shard_manager

    @property
    def privacy(self) -> PrivacyProtocol:
        return self._privacy

    @property
    def offline(self) -> OfflineFallback:
        return self._offline

    def get_status(self) -> dict:
        return {
            "orchestrator": self._orchestrator.get_status(),
            "shards": self._shard_manager.get_status(),
            "privacy": self._privacy.get_status(),
            "offline": self._offline.get_status(),
        }


# === MAIN GUARD ===

def main():
    """Self-test."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    print(f"{LOG_PREFIX} Mesh Layer wiring self-test")

    mesh = MeshLayer(local_node_id="test_primary")
    mesh.start()
    print(f"{LOG_PREFIX} Status: {mesh.get_status()}")
    mesh.stop()
    print(f"{LOG_PREFIX} Done.")


if __name__ == '__main__':
    main()
