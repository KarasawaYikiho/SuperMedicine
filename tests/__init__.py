"""SuperMedicine test suite."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from permission.policy import PermissionResult, ensure_default_policy


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def copy_default_policy(project_dir: Path) -> None:
    """Install the repository's canonical policy in a temporary project."""

    ensure_default_policy(project_dir, source_root=REPOSITORY_ROOT)


class RecordingPermissionEngine:
    """Return a fixed decision while recording each permission check."""

    def __init__(self, result: PermissionResult):
        self.result = result
        self.calls: list[dict[str, Any]] = []

    def check(self, agent_id, action, resource, context=None):
        self.calls.append(
            {
                "agent_id": agent_id,
                "action": action,
                "resource": resource,
                "context": context,
            }
        )
        return self.result


class EmptyPluginRegistry:
    """Minimal plugin registry used by CLI Kernel doubles."""

    def discover(self):
        return []


class FakeCheckpointManager:
    """Minimal checkpoint manager used by CLI Kernel doubles."""

    base_dir = "checkpoints"


class KernelDouble:
    """Initialize the common Kernel attributes required by CLI tests."""

    def __init__(self, *args, **kwargs):
        self._config_path = kwargs["config_path"]
        self._plugins_dir = kwargs["plugins_dir"]
        self._policies_dir = kwargs["policies_dir"]
        self.plugin_registry = EmptyPluginRegistry()
        self.checkpoint_manager = FakeCheckpointManager()
