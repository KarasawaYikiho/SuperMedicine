from __future__ import annotations

import re
import subprocess
from pathlib import Path, PurePosixPath


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {
    ".cfg",
    ".css",
    ".html",
    ".in",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".mjs",
    ".ps1",
    ".py",
    ".pyi",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
FORBIDDEN_PARTS = {
    "__pycache__",
    ".agents",
    ".claude",
    ".codex",
    ".continue",
    ".cursor",
    ".mypy_cache",
    ".opencode",
    ".pytest_cache",
    ".ruff_cache",
    ".supermedicine",
    ".windsurf",
    "build",
    "dist",
    "node_modules",
}
FORBIDDEN_TEST_PATTERNS = (
    "tests/test_tmp_*.py",
    "tests/test_temp_*.py",
    "tests/test_debug_*.py",
    "tests/test_scratch_*.py",
)
FORBIDDEN_DOCUMENT_PATTERNS = (
    "*_audit_dump*.md",
    "*_audit_log*.md",
    "*_codex_notes*.md",
    "*_machine_notes*.md",
    "*_plan_draft*.md",
    "*_private_analysis*.md",
    "*_scratch*.md",
    "*_validation_notes*.md",
    "local_plan*.md",
)
SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bsk-ant-[A-Za-z0-9_-]{12,}\b"),
    re.compile(
        r"(?:api[_-]?key|authorization|token)\s*[:=]\s*"
        r"""['"][^'"<{][^'"]{8,}['"]""",
        re.IGNORECASE,
    ),
)


def _tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines()]


def _tracked_text() -> list[tuple[str, str]]:
    files: list[tuple[str, str]] = []
    for relative in _tracked_files():
        path = REPOSITORY_ROOT / relative
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        files.append((relative, path.read_bytes().decode("utf-8-sig")))
    return files


def test_tracked_text_is_valid_utf8_without_known_mojibake() -> None:
    offenders: list[str] = []
    for relative in _tracked_files():
        path = REPOSITORY_ROOT / relative
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_bytes().decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            offenders.append(f"{relative}: invalid UTF-8 at byte {exc.start}")
            continue
        if "\ufffd" in text or ("鏁板" + "瓧閿") in text:
            offenders.append(f"{relative}: known encoding corruption")
    assert offenders == []


def test_git_index_excludes_generated_local_and_temporary_artifacts() -> None:
    offenders: list[str] = []
    for relative in _tracked_files():
        if relative == ".supermedicine/policies/default.yaml":
            continue
        path = PurePosixPath(relative)
        parts = set(path.parts)
        if parts & FORBIDDEN_PARTS:
            offenders.append(relative)
        if path.suffix.lower() == ".exe" or path.name.endswith(".egg-info"):
            offenders.append(relative)
        if any(path.match(pattern) for pattern in FORBIDDEN_TEST_PATTERNS):
            offenders.append(relative)
        if any(path.match(pattern) for pattern in FORBIDDEN_DOCUMENT_PATTERNS):
            offenders.append(relative)
        if relative.startswith("docs/archive/"):
            offenders.append(relative)
    assert sorted(set(offenders)) == []


def test_tracked_docs_and_manifests_do_not_contain_plaintext_secrets() -> None:
    offenders: list[str] = []
    scanned_suffixes = {".json", ".md", ".toml", ".yaml", ".yml"}
    for relative, text in _tracked_text():
        if Path(relative).suffix.lower() not in scanned_suffixes:
            continue
        if any(pattern.search(text) for pattern in SECRET_PATTERNS):
            offenders.append(relative)
    assert offenders == []
