import importlib
import json
import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PLATFORM_AGENT_NAMES = {"Brain", "Planner", "Coder", "Tester"}


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


def test_tracked_supermedicine_config_is_limited_to_core_bootstrap_files():
    tracked_supermedicine = sorted(
        path for path in _tracked_files() if path == ".supermedicine" or path.startswith(".supermedicine/")
    )

    assert tracked_supermedicine == [
        ".supermedicine/config.yaml",
        ".supermedicine/policies/default.yaml",
    ]


def test_gitignore_excludes_runtime_and_external_platform_config_artifacts():
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    required_patterns = {
        ".pytest_cache/",
        ".pytest-tmp/",
        ".ruff_cache/",
        ".supermedicine/policies/audit.jsonl",
        ".supermedicine/checkpoints/",
        ".claude/",
        ".opencode/",
        "superpowers/",
    }

    for pattern in required_patterns:
        assert pattern in gitignore


def test_install_manifest_keeps_external_platform_config_out_of_core_product_paths():
    manifest = json.loads((REPO_ROOT / "install.json").read_text(encoding="utf-8"))

    for platform_name, platform in manifest["platforms"].items():
        entry = Path(platform["entry"])
        entry_parts = entry.parts

        assert entry_parts[0] == "adapters", f"{platform_name} should be packaged as an optional adapter"
        assert ".claude" not in entry_parts
        assert ".opencode" not in entry_parts
        assert "superpowers" not in entry_parts


def test_install_manifest_platform_entries_point_to_existing_adapter_files():
    manifest = json.loads((REPO_ROOT / "install.json").read_text(encoding="utf-8"))
    from adapters.claude_code.adapter import ClaudeCodeAdapter
    from adapters.opencode.adapter import OpenCodeAdapter

    platforms = manifest["platforms"]
    claude_entry = REPO_ROOT / platforms["claude-code"]["entry"]
    opencode_entry = REPO_ROOT / platforms["opencode"]["entry"]

    assert claude_entry == REPO_ROOT / "adapters" / "claude_code" / "SKILL.md"
    assert claude_entry.is_file()
    assert opencode_entry == REPO_ROOT / "adapters" / "opencode" / "plugin.json"
    assert opencode_entry.is_file()
    assert (REPO_ROOT / platforms["claude-code"]["adapter_module"]).is_file()
    assert (REPO_ROOT / platforms["opencode"]["adapter_module"]).is_file()
    assert set(platforms["claude-code"]["supported_tools"]) == ClaudeCodeAdapter.SUPPORTED_TOOLS
    assert set(platforms["opencode"]["supported_tools"]) == OpenCodeAdapter.SUPPORTED_TOOLS
    assert platforms["claude-code"]["native_skill_loading"] is False
    assert platforms["claude-code"]["native_subagent_runtime"] is False
    assert platforms["opencode"]["native_subagent_runtime"] is False


def test_install_manifest_declares_single_user_facing_platform_agent():
    manifest = json.loads((REPO_ROOT / "install.json").read_text(encoding="utf-8"))

    for platform_name, platform in manifest["platforms"].items():
        assert platform["user_facing_agents"] == ["SuperMedicine"], platform_name
        assert len(platform["user_facing_agents"]) == 1, platform_name
        assert FORBIDDEN_PLATFORM_AGENT_NAMES.isdisjoint(platform["user_facing_agents"]), platform_name
        assert platform["internal_role_contexts"] == ["alpha", "beta", "gamma", "delta"], platform_name
        assert platform["optional_add_on"] is True, platform_name
        assert platform["core_runtime_required"] is False, platform_name
    assert manifest["install_completeness_model"]["single_user_facing_agent"] == "SuperMedicine"


def test_release_label_and_package_version_stay_in_sync():
    install_manifest = json.loads((REPO_ROOT / "install.json").read_text(encoding="utf-8"))
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    package_version = re.search(r'^version\s*=\s*["\']([^"\']+)["\']\s*$', pyproject, re.MULTILINE)

    assert install_manifest["version"] == "Beta0.2.1"
    assert package_version is not None
    assert package_version.group(1) == "0.2.1b0"
    assert "Release-ready label: `Beta0.2.1`" in readme
    assert "Python package metadata uses `0.2.1b0`" in readme
    assert "## [Beta0.2.1]" in changelog
    assert "metadata uses fallback version `0.2.1b0`" in changelog


def test_opencode_plugin_declared_entry_skills_and_agents_exist():
    plugin_dir = REPO_ROOT / "adapters" / "opencode"
    plugin = json.loads((plugin_dir / "plugin.json").read_text(encoding="utf-8"))
    from adapters.opencode.adapter import OpenCodeAdapter

    assert (plugin_dir / plugin["entry"]).is_file()
    assert (plugin_dir / plugin["install_entry_files"]["plugin_manifest"]).is_file()
    assert (plugin_dir / plugin["install_entry_files"]["adapter_module"]).is_file()
    assert (plugin_dir / plugin["install_entry_files"]["single_user_facing_agent"]).is_file()
    assert (plugin_dir / plugin["install_entry_files"]["skill_documents_dir"]).is_dir()
    assert (plugin_dir / plugin["install_entry_files"]["internal_role_context_dir"]).is_dir()
    assert plugin["optional_add_on"] is True
    assert plugin["core_runtime_required"] is False
    assert plugin["native_opencode_subagent_runtime"] is False
    assert "orchestrator_backed_dispatch" in plugin["capabilities"]
    assert "multi_agent_orchestration" not in plugin["capabilities"]
    assert set(plugin["permissions"]["tools"]) == OpenCodeAdapter.SUPPORTED_TOOLS
    assert "opencode.capabilities" in plugin["permissions"]["tools"]
    assert plugin["agents"] == ["agents/supermedicine.md"]
    user_facing_names = [agent["name"] for agent in plugin["user_facing_agents"]]
    assert user_facing_names == ["SuperMedicine"]
    assert len(plugin["user_facing_agents"]) == 1
    assert FORBIDDEN_PLATFORM_AGENT_NAMES.isdisjoint(user_facing_names)
    assert plugin["install_entry_files"]["single_user_facing_agent"] == "agents/supermedicine.md"
    assert plugin["install_completeness_model"]["single_user_facing_agent"] == "SuperMedicine"

    for relative_path in plugin["skills"]:
        declared_path = plugin_dir / relative_path
        assert declared_path.is_file(), f"Missing OpenCode skill: {relative_path}"
        assert declared_path.read_text(encoding="utf-8").strip()

    for relative_path in plugin["agents"]:
        declared_path = plugin_dir / relative_path
        assert declared_path.is_file(), f"Missing OpenCode agent: {relative_path}"
        assert declared_path.read_text(encoding="utf-8").strip()

    for relative_path in plugin["internal_role_contexts"]:
        declared_path = plugin_dir / relative_path
        assert declared_path.is_file(), f"Missing OpenCode internal role context: {relative_path}"
        content = declared_path.read_text(encoding="utf-8")
        assert "user_facing: false" in content
        assert "internal_role_context: true" in content


def test_platform_adapter_docs_do_not_use_legacy_platform_agent_names():
    """Platform adapter surfaces should use SuperMedicine role positioning names."""
    forbidden_agent_names = re.compile(r"\b(?:Brain|Planner|Coder|Tester)\b")
    opencode_dir = REPO_ROOT / "adapters" / "opencode"
    checked_paths = [
        REPO_ROOT / "install.json",
        REPO_ROOT / "permission" / "prompt_generator.py",
        REPO_ROOT / "adapters" / "claude_code" / "adapter.py",
        REPO_ROOT / "adapters" / "claude_code" / "SKILL.md",
        opencode_dir / "adapter.py",
        opencode_dir / "plugin.json",
        *sorted((opencode_dir / "agents").glob("*.md")),
    ]

    offenders = []
    for path in checked_paths:
        content = path.read_text(encoding="utf-8")
        if forbidden_agent_names.search(content):
            offenders.append(str(path.relative_to(REPO_ROOT)))

    assert offenders == []


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
