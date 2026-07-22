"""Shared PyInstaller build engine for preserved desktop executable targets."""

from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

DataItem = str | tuple[str, str]


@dataclass(frozen=True)
class PyInstallerTarget:
    """Declarative inputs for one standalone executable."""

    entry_script: str
    output_name: str
    data_items: tuple[DataItem, ...]
    hidden_imports: tuple[str, ...]
    icon: Path
    build_extras: str | None = None
    required_modules: tuple[str, ...] = ()
    windowed: bool = True
    include_version_info: bool = True


def _separator() -> str:
    return ";" if sys.platform == "win32" else ":"


def _add_data_args(root: Path, items: tuple[DataItem, ...]) -> list[str]:
    separator = _separator()
    args: list[str] = []
    for item in items:
        source_item, explicit_destination = (
            item if isinstance(item, tuple) else (item, None)
        )
        source = root / source_item
        if source.exists():
            destination = explicit_destination or (
                str(Path(source_item).parent) if source.is_file() else source_item
            )
            args.append(f"--add-data={source}{separator}{destination}")
        else:
            print(f"Warning: skipping missing data item: {source_item}")
    return args


def _write_version_info(root: Path, build_dir: Path, target: PyInstallerTarget) -> Path:
    project_text = (root / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', project_text, re.MULTILINE)
    version = match.group(1) if match else "0.0.0"
    numbers = [int(value) for value in re.findall(r"\d+", version)[:4]]
    version_tuple = tuple((numbers + [0, 0, 0, 0])[:4])
    version_file = build_dir / f"{target.output_name}-version.txt"
    build_dir.mkdir(parents=True, exist_ok=True)
    version_file.write_text(
        "VSVersionInfo(ffi=FixedFileInfo("
        f"filevers={version_tuple}, prodvers={version_tuple}, mask=0x3f, flags=0x0, "
        "OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)), kids=["
        "StringFileInfo([StringTable('040904B0', ["
        f"StringStruct('FileDescription', '{target.output_name}'), "
        f"StringStruct('FileVersion', '{version}'), "
        "StringStruct('ProductName', 'SuperMedicine'), "
        f"StringStruct('ProductVersion', '{version}')])]), "
        "VarFileInfo([VarStruct('Translation', [1033, 1200])])])\n",
        encoding="utf-8",
    )
    return version_file


def build_executable(root: Path, target: PyInstallerTarget) -> Path | None:
    """Build *target* from *root* and return the produced executable if present."""

    entry = root / target.entry_script
    if not entry.is_file():
        print(f"Error: entry script not found: {entry}", file=sys.stderr)
        raise SystemExit(1)
    required_modules = ("PyInstaller", *target.required_modules)
    missing_modules = [
        module
        for module in required_modules
        if importlib.util.find_spec(module) is None
    ]
    if target.build_extras and missing_modules:
        print(f"Installing missing build modules: {', '.join(missing_modules)}")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", target.build_extras], cwd=root
        )
        if result.returncode != 0:
            raise SystemExit(result.returncode)
    elif missing_modules:
        print(
            f"Error: missing build modules: {', '.join(missing_modules)}",
            file=sys.stderr,
        )
        raise SystemExit(1)

    dist = root / "dist"
    build_dir = root / "build"
    spec_file = root / f"{target.output_name}.spec"
    dist.mkdir(parents=True, exist_ok=True)
    if build_dir.exists():
        shutil.rmtree(build_dir)
    if spec_file.exists():
        spec_file.unlink()
    version_args: list[str] = []
    if target.include_version_info and sys.platform == "win32":
        version_file = _write_version_info(root, build_dir, target)
        version_args.append(f"--version-file={version_file}")

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        *(["--windowed"] if target.windowed else []),
        f"--name={target.output_name}",
        f"--distpath={dist}",
        f"--workpath={build_dir}",
        f"--specpath={root}",
        f"--icon={target.icon}",
        *version_args,
        *_add_data_args(root, target.data_items),
        *(f"--hidden-import={module}" for module in target.hidden_imports),
        str(entry),
    ]
    print(f"Running PyInstaller to build {target.output_name}.exe ...")
    print(f"Command: {' '.join(command)}\n")
    result = subprocess.run(command, cwd=root)
    if result.returncode != 0:
        print(
            f"\nError: PyInstaller exited with code {result.returncode}",
            file=sys.stderr,
        )
        raise SystemExit(result.returncode)

    candidate = dist / f"{target.output_name}.exe"
    if not candidate.is_file():
        candidate = dist / target.output_name
    output: Path | None = candidate if candidate.is_file() else None
    if output is not None:
        size_mb = output.stat().st_size / (1024 * 1024)
        print(f"\nSuccessfully built: {output}  ({size_mb:.1f} MB)")
    else:
        print(f"\nWarning: expected output not found at {candidate}", file=sys.stderr)
    if build_dir.exists():
        shutil.rmtree(build_dir)
    if spec_file.exists():
        spec_file.unlink()
    return output


def build_application(root: Path) -> Path | None:
    """Build the standalone CLI application with all dynamic runtime resources."""

    return build_executable(
        root,
        PyInstallerTarget(
            entry_script="cli_entry.py",
            output_name="SuperMedicine",
            data_items=(
                "core",
                "permission",
                "plugins",
                "agents",
                "adapters",
                "assets",
            ),
            hidden_imports=("core", "permission", "plugins", "agents", "adapters"),
            icon=root / "assets" / "logo.ico",
            windowed=False,
        ),
    )


if __name__ == "__main__":
    if sys.argv[1:] != ["application"]:
        raise SystemExit("usage: _pyinstaller_builder.py application")
    build_application(Path.cwd())
