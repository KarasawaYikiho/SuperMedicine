"""Build ``dist/SuperMedicineGUI.exe`` from the preserved desktop entrypoint."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.ci._pyinstaller_builder import PyInstallerTarget, build_executable  # noqa: E402

ENTRY_SCRIPT = "gui_standalone.py"
OUTPUT_NAME = "SuperMedicineGUI"
DIST_DIR = "dist"
BUILD_EXTRAS = ".[desktop,web]"


def main() -> None:
    root = Path.cwd()
    target = PyInstallerTarget(
        entry_script=ENTRY_SCRIPT,
        output_name=OUTPUT_NAME,
        data_items=("core", "assets"),
        hidden_imports=(
            "webview",
            "uvicorn",
            "websockets",
            "fastapi",
            "core",
            "core.web",
            "core.web.server",
        ),
        icon=root / 'assets' / 'logo.ico',
        build_extras=BUILD_EXTRAS,
        required_modules=("webview", "uvicorn", "websockets", "fastapi"),
    )
    build_executable(root, target)


if __name__ == "__main__":
    main()
