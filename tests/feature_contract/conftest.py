from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture
def manifest(repository_root: Path) -> dict[str, object]:
    return json.loads((repository_root / "feature_manifest.json").read_text(encoding="utf-8"))
