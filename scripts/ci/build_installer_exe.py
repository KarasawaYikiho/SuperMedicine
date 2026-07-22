"""Build ``dist/SuperMedicineInstaller.exe`` from the preserved GUI installer."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.ci._pyinstaller_builder import PyInstallerTarget, build_executable  # noqa: E402
from scripts.ci.build_installer_payload import main as build_installer_payload  # noqa: E402

ENTRY_SCRIPT = "installer/gui_installer.py"
OUTPUT_NAME = "SuperMedicineInstaller"
DIST_DIR = "dist"


def main() -> None:
    root = _REPO_ROOT
    build_installer_payload()
    target = PyInstallerTarget(
        entry_script=ENTRY_SCRIPT,
        output_name=OUTPUT_NAME,
        data_items=(
            (".installer-payload-stage/release_payload", "release_payload"),
            "install.json", "installer", "core", "permission", "agents",
            "plugins", "adapters", "assets",
        ),
        hidden_imports=(
            "installer", "installer.gui_installer", "installer.component_installer",
            "core", "permission", "tkinter", "tkinter.ttk", "tkinter.filedialog",
            "tkinter.messagebox",
        ),
        icon=root / 'assets' / 'logo.ico',
    )
    build_executable(root, target)


if __name__ == "__main__":
    main()
