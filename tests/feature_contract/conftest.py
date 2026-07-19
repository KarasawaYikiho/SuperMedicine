from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture
def manifest(repository_root: Path) -> dict[str, Any]:
    return json.loads((repository_root / "feature_manifest.json").read_text(encoding="utf-8"))
