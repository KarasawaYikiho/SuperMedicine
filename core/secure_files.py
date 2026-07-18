"""Operating-system permission helpers for files that can contain secrets."""

from __future__ import annotations

import os
from pathlib import Path

IS_POSIX = os.name == "posix"


def secure_config_permissions(config_path: Path) -> None:
    """Restrict a persisted config and its directory to its POSIX owner."""
    if not IS_POSIX:
        return
    path = Path(config_path)
    os.chmod(path.parent, 0o700)
    os.chmod(path, 0o600)
