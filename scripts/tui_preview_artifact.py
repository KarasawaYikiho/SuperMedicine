"""Generate a lightweight SuperMedicine TUI preview artifact.

This workflow writes a text preview to the user's Downloads directory by
default.  It intentionally does not claim image rendering or user approval; it
records the current dry-run TUI shell state and the commands a maintainer can
use before asking for visual feedback.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from core.tui.app import SuperMedicineTUI, launch_tui


def default_downloads_dir() -> Path:
    """Return the default Windows-style Downloads directory for artifacts."""

    return Path.home() / "Downloads"


def build_preview_text(project_root: Path) -> str:
    """Build a deterministic text preview from dry-run TUI metadata."""

    status = launch_tui(dry_run=True, project_root=project_root)
    refresh_surfaces = SuperMedicineTUI.dynamic_refresh_surfaces()
    refresh_lines = "\n".join(
        f"- {surface.view_id}: {surface.refresh_hook} via {surface.manual_control} ({surface.policy})"
        for surface in refresh_surfaces
    )
    return "\n".join(
        [
            "SuperMedicine TUI Preview Artifact",
            f"Generated: {datetime.now(timezone.utc).isoformat()}",
            f"Project root: {project_root}",
            "",
            "Dry-run shell:",
            f"- Title: {status.title}",
            f"- Message: {status.message}",
            f"- Current view: {status.view_title}",
            f"- Shortcuts: {status.shortcut_hint}",
            f"- Status left: {status.status_left}",
            f"- Status center: {status.status_center}",
            f"- Status right: {status.status_right}",
            "",
            "Menu affordance:",
            "- Upper-left clickable label: ≡ 菜单 (M)",
            "- Keyboard fallback: uppercase M",
            "",
            "Targeted refresh boundary:",
            refresh_lines,
            "",
            "Approval status:",
            "- User approval has NOT been recorded by this artifact.",
            "- If image rendering is required, capture a terminal screenshot after running `python -m supermedicine tui` or `python Cli.py tui`.",
        ]
    )


def write_preview_artifact(
    *, project_root: Path, output_dir: Path | None = None, filename: str | None = None
) -> Path:
    """Write the TUI preview text artifact and return its path."""

    target_dir = output_dir or default_downloads_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    target_name = filename or "SuperMedicine_TUI_preview.txt"
    target_path = target_dir / target_name
    target_path.write_text(build_preview_text(project_root), encoding="utf-8")
    return target_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a TUI preview artifact.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--filename", default=None)
    return parser


def main(argv: list[str] | None = None) -> Path:
    args = build_parser().parse_args(argv)
    path = write_preview_artifact(
        project_root=args.project_root,
        output_dir=args.output_dir,
        filename=args.filename,
    )
    print(path)
    return path


if __name__ == "__main__":
    main()
