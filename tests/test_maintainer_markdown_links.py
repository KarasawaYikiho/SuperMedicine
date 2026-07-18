from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "maintainers" / "check_markdown_links.py"


def _load_checker():
    spec = importlib.util.spec_from_file_location("check_markdown_links", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_markdown_link_checker_reports_missing_relative_markdown_link(tmp_path):
    module = _load_checker()
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.md").write_text("[missing](missing.md)\n", encoding="utf-8")

    errors = module.check_markdown_links(docs)

    assert errors == ["index.md: missing relative Markdown link: missing.md"]


def test_markdown_link_checker_accepts_existing_relative_markdown_link(tmp_path):
    module = _load_checker()
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.md").write_text("[guide](guide.md)\n", encoding="utf-8")
    (docs / "guide.md").write_text("# Guide\n", encoding="utf-8")

    assert module.check_markdown_links(docs) == []


def test_maintainer_readme_links_feature_parity_guide():
    readme = (REPO_ROOT / "docs" / "maintainers" / "README.md").read_text(
        encoding="utf-8"
    )
    assert "[feature-parity.md](feature-parity.md)" in readme
