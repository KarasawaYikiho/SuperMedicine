"""Build the installer payload directory for packaging.

Extracts the inline Python script from the CI workflow's
"Build standalone installer Exe artifact" step into a standalone
script that can be run from the repository root:

    python scripts/ci/build_installer_payload.py

This script creates ``.installer-payload-stage/release_payload/``
and populates it with the files and directories needed by the
installer.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

# Ensure repo root is on sys.path so that "scripts.ci" resolves when
# invoked as ``python scripts/ci/build_installer_payload.py``.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.ci._packaging_common import (
    copy_include_dirs,
    copy_include_files,
)

STAGE_DIR = ".installer-payload-stage"
PAYLOAD_SUBDIR = "release_payload"


def main() -> None:
    root = Path.cwd()
    stage = root / STAGE_DIR
    payload = stage / PAYLOAD_SUBDIR

    # Clean any previous staging area
    if stage.exists():
        shutil.rmtree(stage)

    # Create fresh payload directory
    payload.mkdir(parents=True)

    # Copy include files (cli_entry.py, pyproject.toml, etc.)
    copy_include_files(root, payload)

    # Copy the built release executable
    release_exe = root / "dist" / "SuperMedicine.exe"
    if not release_exe.is_file():
        print("Missing CI release executable: dist/SuperMedicine.exe", file=sys.stderr)
        raise SystemExit(1)
    exe_target = payload / "dist" / "SuperMedicine.exe"
    exe_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(release_exe, exe_target)

    # Copy include directories (core, permission, agents, etc.)
    copy_include_dirs(root, payload)

    print(f"Installer payload staged at: {payload}")


if __name__ == "__main__":
    main()
