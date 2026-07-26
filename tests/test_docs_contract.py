from __future__ import annotations

import importlib.util
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str):
    path = REPOSITORY_ROOT / relative
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_repository_documentation_contract_is_valid() -> None:
    checker = _load("scripts/maintainers/check_docs.py")
    assert checker.check_docs() == []


def test_release_metadata_mirrors_are_current() -> None:
    metadata = _load("scripts/maintainers/sync_release_metadata.py")
    stale = [
        path.relative_to(REPOSITORY_ROOT).as_posix()
        for path, desired in metadata.desired_files().items()
        if path.read_text(encoding="utf-8") != desired
    ]
    assert stale == []
