"""Python launcher for the real OpenTUI runtime bridge."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from core.tui.resources import resolve_resource


@dataclass(frozen=True, slots=True)
class OpenTUIRuntimeInfo:
    """Runtime metadata exposed to smoke checks and dry-run callers."""

    package: str = "@opentui/core"
    version: str = "0.4.3"
    bridge: str = "core/tui/opentui_runtime.mjs"


class OpenTUIRuntimeError(RuntimeError):
    """Raised when the OpenTUI runtime bridge cannot be launched."""


def _configure_output_errors() -> None:
    """Keep Unicode bridge output printable on legacy Windows consoles."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(errors="replace")


def runtime_info() -> OpenTUIRuntimeInfo:
    """Return the approved OpenTUI runtime package metadata."""

    return OpenTUIRuntimeInfo()


def _project_bridge_path(project_root: Path) -> Path | None:
    bridge = project_root / "core" / "tui" / "opentui_runtime.mjs"
    opentui_package = project_root / "node_modules" / "@opentui" / "core"
    if bridge.is_file() and opentui_package.exists():
        return bridge
    return None


def _bridge_path(project_root: Path | None = None) -> Path:
    if project_root is not None:
        project_bridge = _project_bridge_path(project_root)
        if project_bridge is not None:
            return project_bridge
    return resolve_resource(Path("core") / "tui" / "opentui_runtime.mjs")


def _preferred_js_runtime() -> str:
    """Return the JS runtime used for OpenTUI.

    OpenTUI 0.4.3's native FFI is not available under Node on Windows.  Require
    Bun (or an explicitly configured Bun-compatible executable) so smoke checks
    exercise the real runtime instead of falling through to an unsupported host.
    """

    configured = os.environ.get("SUPERMEDICINE_OPENTUI_JS_RUNTIME")
    if configured:
        executable_name = Path(configured).name.lower()
        if executable_name in {"node", "node.exe"}:
            raise OpenTUIRuntimeError(
                "OpenTUI runtime requires Bun; Node.js is not a supported host "
                "for @opentui/core native FFI in this environment. Install Bun "
                "from https://bun.sh/ or set SUPERMEDICINE_OPENTUI_JS_RUNTIME "
                "to a Bun-compatible executable."
            )
        return configured
    bun = shutil.which("bun")
    if bun:
        return bun
    raise OpenTUIRuntimeError(
        "OpenTUI runtime requires Bun to execute @opentui/core native FFI. "
        "Install Bun from https://bun.sh/ and rerun `npm run opentui:smoke`. "
        "Node.js fallback is intentionally disabled because it cannot load the "
        "OpenTUI native runtime here."
    )


def opentui_command(
    *,
    project_root: Path | str | None = None,
    smoke: bool = False,
    automated_nav: bool = False,
    full_page_interactions: bool = False,
    interaction_matrix: bool = False,
) -> list[str]:
    """Build the command that starts the OpenTUI bridge."""

    root = Path(project_root) if project_root is not None else Path.cwd()
    bridge = _bridge_path(root)
    command = [_preferred_js_runtime(), str(bridge), "--project-root", str(root)]
    command.extend(["--python-executable", sys.executable])
    if smoke:
        command.append("--smoke")
    if automated_nav:
        command.append("--automated-nav")
    if full_page_interactions:
        command.append("--full-page-interactions")
    if interaction_matrix:
        command.append("--interaction-matrix")
    return command


def launch_opentui_runtime(*, project_root: Path | str | None = None) -> int:
    """Launch the interactive OpenTUI runtime and return its process code."""

    command = opentui_command(project_root=project_root)
    try:
        completed = subprocess.run(command, cwd=Path(project_root or Path.cwd()))
    except FileNotFoundError as exc:
        raise OpenTUIRuntimeError(
            "OpenTUI runtime requires Bun to execute @opentui/core native FFI. "
            "Install Bun from https://bun.sh/ and rerun the TUI."
        ) from exc
    return int(completed.returncode or 0)


def smoke_opentui_runtime(
    *, project_root: Path | str | None = None
) -> subprocess.CompletedProcess[str]:
    """Start the OpenTUI bridge in smoke mode for external verification."""

    command = opentui_command(project_root=project_root, smoke=True)
    try:
        return subprocess.run(
            command,
            cwd=Path(project_root or Path.cwd()),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
    except FileNotFoundError as exc:
        raise OpenTUIRuntimeError(
            "OpenTUI runtime requires Bun to execute @opentui/core native FFI. "
            "Install Bun from https://bun.sh/ and rerun `npm run opentui:smoke`."
        ) from exc


def automated_nav_opentui_runtime(
    *, project_root: Path | str | None = None
) -> subprocess.CompletedProcess[str]:
    """Start the OpenTUI bridge in scripted navigation mode for verification."""

    command = opentui_command(project_root=project_root, automated_nav=True)
    try:
        return subprocess.run(
            command,
            cwd=Path(project_root or Path.cwd()),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
    except FileNotFoundError as exc:
        raise OpenTUIRuntimeError(
            "OpenTUI runtime requires Bun to execute @opentui/core native FFI. "
            "Install Bun from https://bun.sh/ and rerun automated navigation checks."
        ) from exc


def full_page_interactions_opentui_runtime(
    *, project_root: Path | str | None = None
) -> subprocess.CompletedProcess[str]:
    """Start the OpenTUI bridge in scripted all-page interaction mode."""

    command = opentui_command(project_root=project_root, full_page_interactions=True)
    try:
        return subprocess.run(
            command,
            cwd=Path(project_root or Path.cwd()),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
        )
    except FileNotFoundError as exc:
        raise OpenTUIRuntimeError(
            "OpenTUI runtime requires Bun to execute @opentui/core native FFI. "
            "Install Bun from https://bun.sh/ and rerun full-page interaction checks."
        ) from exc


def interaction_matrix_opentui_runtime(
    *, project_root: Path | str | None = None
) -> subprocess.CompletedProcess[str]:
    """Exercise real mouse, resize, Unicode, cancellation, and recovery paths."""

    command = opentui_command(project_root=project_root, interaction_matrix=True)
    try:
        return subprocess.run(
            command,
            cwd=Path(project_root or Path.cwd()),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
        )
    except FileNotFoundError as exc:
        raise OpenTUIRuntimeError(
            "OpenTUI runtime requires Bun for the interaction matrix."
        ) from exc


def main(argv: list[str] | None = None) -> int:
    """Standalone smoke/launch helper for packaging diagnostics."""

    _configure_output_errors()
    argv = list(sys.argv[1:] if argv is None else argv)
    smoke = "--smoke" in argv
    automated_nav = "--automated-nav" in argv
    full_page_interactions = "--full-page-interactions" in argv
    interaction_matrix = "--interaction-matrix" in argv
    if interaction_matrix:
        result = interaction_matrix_opentui_runtime()
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        return int(result.returncode or 0)
    if full_page_interactions:
        result = full_page_interactions_opentui_runtime()
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        return int(result.returncode or 0)
    if automated_nav:
        result = automated_nav_opentui_runtime()
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        return int(result.returncode or 0)
    if smoke:
        result = smoke_opentui_runtime()
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        return int(result.returncode or 0)
    return launch_opentui_runtime()


if __name__ == "__main__":  # pragma: no cover - exercised by external smoke checks
    raise SystemExit(main())
