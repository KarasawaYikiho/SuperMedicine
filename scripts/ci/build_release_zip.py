"""Build the release zip archive for distribution.

Extracts the inline Python script from the CI workflow's
"Build release Zip" step into a standalone script that can be run
from the repository root:

    python scripts/ci/build_release_zip.py

This script creates ``.release-zip-stage/`` as a staging area,
populates it with release files and executables, then compresses
everything into a zip archive at the repository root.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

# Ensure repo root is on sys.path so that "scripts.ci" resolves when
# invoked as ``python scripts/ci/build_release_zip.py``.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.ci._packaging_common import (  # noqa: E402
    copy_include_dirs,
    copy_include_files,
)


def main() -> None:
    root = _REPO_ROOT

    # --- Determine version and release metadata ---
    version = tomllib.loads(
        (root / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]["version"]
    release_label = f"v{version}"
    release_title = f"SuperMedicine {version}"
    archive_name = f"SuperMedicine {release_label}.zip"

    # --- Prepare staging directory ---
    stage = root / ".release-zip-stage" / f"SuperMedicine {release_label}"
    if stage.parent.exists():
        shutil.rmtree(stage.parent)
    stage.mkdir(parents=True)

    # --- Copy include files ---
    copy_include_files(root, stage)

    # --- Copy release executables ---
    release_exe = root / "dist" / "SuperMedicine.exe"
    if not release_exe.is_file():
        raise SystemExit(
            "Missing CI release executable: dist/SuperMedicine.exe. "
            "Re-run the Build release application Exe artifact step."
        )
    exe_target = stage / "dist" / "SuperMedicine.exe"
    exe_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(release_exe, exe_target)

    installer_exe = root / "dist" / "SuperMedicineInstaller.exe"
    if not installer_exe.is_file():
        raise SystemExit(
            "Missing CI installer executable: dist/SuperMedicineInstaller.exe. "
            "Re-run the Build standalone installer Exe artifact step."
        )
    shutil.copy2(installer_exe, stage / "SuperMedicineInstaller.exe")

    gui_exe = root / "dist" / "SuperMedicineGUI.exe"
    if not gui_exe.is_file():
        raise SystemExit(
            "Missing CI GUI executable: dist/SuperMedicineGUI.exe. "
            "Re-run the Build GUI standalone Exe artifact step."
        )
    shutil.copy2(gui_exe, stage / "SuperMedicineGUI.exe")

    # --- Copy include directories ---
    copy_include_dirs(root, stage)

    # --- Create zip archive ---
    archive_path = root / archive_name
    if archive_path.exists():
        archive_path.unlink()
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source in sorted(stage.rglob("*")):
            if source.is_file():
                archive.write(source, source.relative_to(stage.parent).as_posix())
        # Windows runners cannot always materialize case-only sibling files
        # in the staging directory, but release archives must keep the
        # canonical lowercase entry alongside the legacy uppercase entry
        # for case-sensitive extraction targets.
        lowercase_entry = f"SuperMedicine {release_label}/install.py"
        if lowercase_entry not in archive.namelist():
            lowercase_source = subprocess.check_output(
                ["git", "show", ":install.py"], cwd=root, text=True
            )
            archive.writestr(lowercase_entry, lowercase_source)

    # --- Cleanup staging directory ---
    shutil.rmtree(stage.parent)
    print(f"Created {archive_name}")

    # --- Write GitHub Actions outputs if running in CI ---
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as output:
            output.write(f"release_label={release_label}\n")
            output.write(f"release_title={release_title}\n")
            output.write(f"archive_name={archive_name}\n")


if __name__ == "__main__":
    main()
