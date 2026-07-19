"""Shared PyInstaller build engine for preserved desktop executable targets."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PyInstallerTarget:
    """Declarative inputs for one standalone executable."""

    entry_script: str
    output_name: str
    data_items: tuple[str, ...]
    hidden_imports: tuple[str, ...]
    icon: Path
    build_extras: str | None = None
    required_modules: tuple[str, ...] = ()


def _separator() -> str:
    return ";" if sys.platform == "win32" else ":"


def _add_data_args(root: Path, items: tuple[str, ...]) -> list[str]:
    separator = _separator()
    args: list[str] = []
    for item in items:
        source = root / item
        if source.exists():
            destination = str(Path(item).parent) if source.is_file() else item
            args.append(f"--add-data={source}{separator}{destination}")
        else:
            print(f"Warning: skipping missing data item: {item}")
    return args


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

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        f"--name={target.output_name}",
        f"--distpath={dist}",
        f"--workpath={build_dir}",
        f"--specpath={root}",
        f"--icon={target.icon}",
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
