"""Build the standalone GUI EXE using PyInstaller.

Packages ``gui_standalone.py`` into a single-file executable
``dist/SuperMedicineGUI.exe`` that, when double-clicked, displays
a native desktop window via pywebview with the embedded web server.

The ``core/web/`` directory (containing the frontend HTML/JS/CSS) is
embedded into the executable so it is fully self-contained.

Usage from the repository root::

    python scripts/ci/build_gui_exe.py

Prerequisites:
    - PyInstaller must be installed (``pip install pyinstaller``).
    - pywebview must be installed (``pip install pywebview``).
    - The script must be run from the repository root directory.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

# Ensure repo root is on sys.path so that "scripts.ci" resolves when
# invoked as ``python scripts/ci/build_gui_exe.py``.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ENTRY_SCRIPT = "gui_standalone.py"
OUTPUT_NAME = "SuperMedicineGUI"
DIST_DIR = "dist"
BUILD_EXTRAS = ".[desktop,web]"

# Data files / directories to embed inside the frozen executable.
# These are relative to the repository root.
_DATA_ITEMS: list[str] = [
    "core",
    "assets",
]

# PyInstaller hidden imports that may not be auto-detected.
_HIDDEN_IMPORTS: list[str] = [
    "webview",
    "uvicorn",
    "websockets",
    "fastapi",
    "core",
    "core.web",
    "core.web.server",
]


def _separator() -> str:
    """Return the platform-specific path separator for --add-data."""
    return ";" if sys.platform == "win32" else ":"


def _build_add_data_args(root: Path) -> list[str]:
    """Build ``--add-data`` arguments for all data items."""
    sep = _separator()
    args: list[str] = []
    for item in _DATA_ITEMS:
        source = root / item
        if not source.exists():
            print(f"Warning: skipping missing data item: {item}")
            continue
        # Embed under the same relative path so that runtime lookups work.
        args.append(f"--add-data={source}{sep}{item}")
    return args


def _build_hidden_import_args() -> list[str]:
    """Build ``--hidden-import`` arguments."""
    return [f"--hidden-import={mod}" for mod in _HIDDEN_IMPORTS]


def main() -> None:
    root = Path.cwd()
    entry = root / ENTRY_SCRIPT

    if not entry.is_file():
        print(
            f"Error: entry script not found: {entry}",
            file=sys.stderr,
        )
        raise SystemExit(1)

    dependency_result = subprocess.run(
        [sys.executable, "-m", "pip", "install", BUILD_EXTRAS], cwd=root
    )
    if dependency_result.returncode != 0:
        raise SystemExit(dependency_result.returncode)

    # Ensure dist directory exists
    dist = root / DIST_DIR
    dist.mkdir(parents=True, exist_ok=True)

    # Clean previous build artifacts
    build_dir = root / "build"
    spec_file = root / f"{OUTPUT_NAME}.spec"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    if spec_file.exists():
        spec_file.unlink()

    # Construct PyInstaller command
    cmd: list[str] = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        f"--name={OUTPUT_NAME}",
        f"--distpath={dist}",
        f"--workpath={build_dir}",
        f"--specpath={root}",
        f"--icon={root / 'assets' / 'logo.ico'}",
        *_build_add_data_args(root),
        *_build_hidden_import_args(),
        str(entry),
    ]

    print(f"Running PyInstaller to build {OUTPUT_NAME}.exe ...")
    print(f"Command: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, cwd=root)

    if result.returncode != 0:
        print(
            f"\nError: PyInstaller exited with code {result.returncode}",
            file=sys.stderr,
        )
        raise SystemExit(result.returncode)

    # Verify output
    exe_path = dist / f"{OUTPUT_NAME}.exe"
    if not exe_path.is_file():
        # On Linux/macOS the .exe suffix is absent
        exe_path = dist / OUTPUT_NAME
    if exe_path.is_file():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"\nSuccessfully built: {exe_path}  ({size_mb:.1f} MB)")
    else:
        print(
            f"\nWarning: expected output not found at {dist / OUTPUT_NAME}",
            file=sys.stderr,
        )

    # Clean up build directory and spec file
    if build_dir.exists():
        shutil.rmtree(build_dir)
    if spec_file.exists():
        spec_file.unlink()


if __name__ == "__main__":
    main()
