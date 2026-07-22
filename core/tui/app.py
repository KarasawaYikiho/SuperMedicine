"""OpenTUI launcher compatibility surface."""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

from core.tui.i18n import LABELS, t
from core.tui.opentui_runtime import (
    OpenTUIRuntimeError,
    launch_opentui_runtime,
    runtime_info,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TUIStatus:
    """Machine-readable status for dry-run and launcher callers."""

    title: str
    message: str
    labels: dict[str, str]
    interactive: bool
    runtime_name: str = "@opentui/core"
    runtime_version: str = "0.4.3"


def _project_root(project_root: Path | str | None) -> Path:
    if project_root is not None:
        return Path(project_root).expanduser().resolve()
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd().resolve()


def launch_tui(
    *, dry_run: bool = False, project_root: Path | str | None = None
) -> TUIStatus:
    """Describe or launch the sole production TUI, OpenTUI."""

    root = _project_root(project_root)
    runtime = runtime_info()
    status = TUIStatus(
        title=t("app_title"),
        message=t("dry_run_status") if dry_run else t("welcome"),
        labels=dict(LABELS),
        interactive=not dry_run,
        runtime_name=runtime.package,
        runtime_version=runtime.version,
    )
    if dry_run:
        print(status.title)
        print(status.message)
        return status

    from core.log_report_handler import configure_tui_log_storage

    configure_tui_log_storage(root)
    try:
        return_code = launch_opentui_runtime(project_root=root)
    except OpenTUIRuntimeError as exc:
        logger.error("OpenTUI launch failed for %s: %s", root, exc)
        return TUIStatus(
            title=status.title,
            message=str(exc),
            labels=status.labels,
            interactive=False,
            runtime_name=runtime.package,
            runtime_version=runtime.version,
        )
    if return_code:
        logger.error("OpenTUI exited with code %s for %s", return_code, root)
    return status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="supermedicine tui", description=t("app_title")
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="report OpenTUI readiness without launching"
    )
    return parser


def main(argv: list[str] | None = None) -> TUIStatus:
    args = build_parser().parse_args(argv)
    return launch_tui(dry_run=args.dry_run)


__all__ = ["TUIStatus", "build_parser", "launch_tui", "main"]
