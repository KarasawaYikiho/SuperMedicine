"""Resolve packaged OpenTUI and shared application resources."""

from __future__ import annotations

import sys
from pathlib import Path


def _source_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_resource(relative: str | Path) -> Path:
    relative_path = Path(relative)
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        bundled = Path(bundle_root) / relative_path
        if bundled.exists():
            return bundled
    return _source_root() / relative_path


def resolve_asset(filename: str) -> Path:
    return resolve_resource(Path("assets") / filename)


__all__ = ["resolve_asset", "resolve_resource"]
