"""Build ``dist/SuperMedicineGUI.exe`` from the preserved desktop entrypoint."""

from __future__ import annotations

import sys
import json
import subprocess
import tempfile
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
    root = _REPO_ROOT
    target = PyInstallerTarget(
        entry_script=ENTRY_SCRIPT,
        output_name=OUTPUT_NAME,
        data_items=("core", "permission", "plugins", "agents", "adapters", "assets"),
        hidden_imports=(
            "webview",
            "uvicorn",
            "uvicorn.logging",
            "uvicorn.loops.auto",
            "uvicorn.protocols.http.auto",
            "uvicorn.protocols.websockets.auto",
            "uvicorn.lifespan.on",
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
    output = build_executable(root, target)
    if output is None:
        raise SystemExit("GUI build did not produce SuperMedicineGUI.exe")
    with tempfile.TemporaryDirectory(prefix="supermedicine-gui-self-test-") as temp_dir:
        report_path = Path(temp_dir) / "report.json"
        result = subprocess.run(
            [
                str(output),
                "--self-test",
                "--self-test-report",
                str(report_path),
            ],
            cwd=root,
            check=False,
        )
        if not report_path.is_file():
            raise SystemExit("GUI self-test did not write its JSON report")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if result.returncode or not report.get("ok"):
            raise SystemExit(f"GUI self-test failed: {report}")


if __name__ == "__main__":
    main()
