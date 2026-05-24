import importlib
import json
import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _normalized_parts(path: str) -> tuple[str, ...]:
    return Path(path).parts


def _top_level_entry_from_yaml(path: Path, key: str) -> str | None:
    pattern = re.compile(rf"^{re.escape(key)}:\s*[\"']?([^\"'#]+?)[\"']?\s*(?:#.*)?$")
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith((" ", "\t")):
            continue
        match = pattern.match(line)
        if match:
            return match.group(1).strip()
    return None


def _setuptools_py_modules(pyproject: str) -> set[str]:
    section_match = re.search(
        r"^\[tool\.setuptools\]\s*$(.*?)(?=^\[|\Z)",
        pyproject,
        re.MULTILINE | re.DOTALL,
    )
    if not section_match:
        return set()

    modules_match = re.search(
        r"^py-modules\s*=\s*\[(.*?)\]\s*$",
        section_match.group(1),
        re.MULTILINE | re.DOTALL,
    )
    if not modules_match:
        return set()

    return set(re.findall(r'["\']([^"\']+)["\']', modules_match.group(1)))


def test_tracked_files_do_not_include_forbidden_or_generated_artifacts():
    forbidden_matches = []

    for tracked_path in _tracked_files():
        parts = _normalized_parts(tracked_path)
        name = parts[-1]
        lower_parts = tuple(part.lower() for part in parts)

        if parts and parts[0] in {"Docs", "Superpower", "superpower"}:
            forbidden_matches.append(tracked_path)
        if parts and parts[0] in {".claude", ".opencode", "superpowers"}:
            forbidden_matches.append(tracked_path)
        if "node_modules" in lower_parts or ".cache" in lower_parts:
            forbidden_matches.append(tracked_path)
        if name.endswith(".pyc"):
            forbidden_matches.append(tracked_path)
        if any(part in {"__pycache__", ".pytest_cache", ".pytest-tmp", ".ruff_cache", "build", "dist"} for part in parts):
            forbidden_matches.append(tracked_path)
        if any(part.endswith(".egg-info") for part in parts):
            forbidden_matches.append(tracked_path)
        if tracked_path == ".supermedicine/policies/audit.jsonl":
            forbidden_matches.append(tracked_path)
        if tracked_path == ".supermedicine/checkpoints" or tracked_path.startswith(".supermedicine/checkpoints/"):
            forbidden_matches.append(tracked_path)

    assert sorted(set(forbidden_matches)) == []


def test_install_manifest_platform_entries_point_to_existing_adapter_files():
    manifest = json.loads((REPO_ROOT / "install.json").read_text(encoding="utf-8"))

    platforms = manifest["platforms"]
    claude_entry = REPO_ROOT / platforms["claude-code"]["entry"]
    opencode_entry = REPO_ROOT / platforms["opencode"]["entry"]

    assert claude_entry == REPO_ROOT / "adapters" / "claude_code" / "SKILL.md"
    assert claude_entry.is_file()
    assert opencode_entry == REPO_ROOT / "adapters" / "opencode" / "plugin.json"
    assert opencode_entry.is_file()


def test_opencode_plugin_declared_entry_skills_and_agents_exist():
    plugin_dir = REPO_ROOT / "adapters" / "opencode"
    plugin = json.loads((plugin_dir / "plugin.json").read_text(encoding="utf-8"))

    assert (plugin_dir / plugin["entry"]).is_file()

    for relative_path in plugin["skills"]:
        declared_path = plugin_dir / relative_path
        assert declared_path.is_file(), f"Missing OpenCode skill: {relative_path}"
        assert declared_path.read_text(encoding="utf-8").strip()

    for relative_path in plugin["agents"]:
        declared_path = plugin_dir / relative_path
        assert declared_path.is_file(), f"Missing OpenCode agent: {relative_path}"
        assert declared_path.read_text(encoding="utf-8").strip()


def test_plugin_manifest_entry_paths_exist():
    plugin_manifests = sorted((REPO_ROOT / "plugins").glob("**/plugin.yaml"))
    assert plugin_manifests

    missing_entries = []
    for manifest_path in plugin_manifests:
        entry = _top_level_entry_from_yaml(manifest_path, "entry")
        if not entry:
            missing_entries.append(f"{manifest_path.relative_to(REPO_ROOT)}: missing entry")
            continue
        entry_path = manifest_path.parent / entry
        if not entry_path.is_file():
            missing_entries.append(f"{manifest_path.relative_to(REPO_ROOT)} -> {entry}")

    assert missing_entries == []


def test_pyproject_console_script_target_is_importable():
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^supermedicine\s*=\s*["\']([^"\']+)["\']\s*$', pyproject, re.MULTILINE)
    assert match, "Missing supermedicine console script"

    module_name, attribute_name = match.group(1).split(":", maxsplit=1)
    module = importlib.import_module(module_name)

    assert callable(getattr(module, attribute_name))


def test_pyproject_console_script_top_level_module_is_packaged():
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^supermedicine\s*=\s*["\']([^"\']+)["\']\s*$', pyproject, re.MULTILINE)
    assert match, "Missing supermedicine console script"

    module_name, _attribute_name = match.group(1).split(":", maxsplit=1)
    if "." in module_name:
        return

    assert module_name in _setuptools_py_modules(pyproject)
