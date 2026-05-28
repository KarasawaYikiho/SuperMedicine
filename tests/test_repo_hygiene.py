from __future__ import annotations

import importlib
import json
import re
import subprocess
from pathlib import Path

try:
    import tomllib  # type: ignore[import-not-found]
except ModuleNotFoundError:
    tomllib = None  # type: ignore[assignment]


REPO_ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PLATFORM_AGENT_NAMES = {"Brain", "Planner", "Coder", "Tester"}


def _read_pyproject() -> dict:
    """Read pyproject.toml, falling back to regex if tomllib unavailable."""
    path = REPO_ROOT / "pyproject.toml"
    if tomllib is not None:
        with path.open("rb") as f:
            return tomllib.load(f)
    # Fallback: simple regex-based extraction for CI on Python <3.11
    text = path.read_text(encoding="utf-8")
    result: dict = {"project": {}, "tool": {"setuptools": {"package-data": {}}}}
    version_match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if version_match:
        result["project"]["version"] = version_match.group(1)
    optional_dependencies_match = re.search(
        r"^\[project\.optional-dependencies\]\s*$(.*?)(?=^\[|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if optional_dependencies_match:
        dev_match = re.search(
            r"^dev\s*=\s*\[(.*?)\]",
            optional_dependencies_match.group(1),
            re.MULTILINE | re.DOTALL,
        )
        if dev_match:
            result["project"].setdefault("optional-dependencies", {})["dev"] = re.findall(
                r'"([^"]+)"',
                dev_match.group(1),
            )
    # Extract core package-data entries
    in_core_data = False
    for line in text.splitlines():
        if re.match(r'^core\s*=\s*\[', line):
            in_core_data = True
            entries = re.findall(r'"([^"]+)"', line)
            result["tool"]["setuptools"]["package-data"]["core"] = entries
        elif in_core_data and line.strip().startswith("]"):
            in_core_data = False
    return result


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
    assert set(platforms["claude-code"]["ai_provider"]["supported_api_formats"]) == {"openai", "anthropic"}
    assert platforms["claude-code"]["ai_provider"]["custom_base_url"] is True
    assert platforms["claude-code"]["ai_provider"]["secret_redaction_required"] is True
    assert platforms["claude-code"]["ai_provider"]["plaintext_api_keys_in_manifest"] is False
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

    assert install_manifest["version"] == "Beta0.3.0"
    assert package_version is not None
    assert package_version.group(1) == "0.3.0b0"
    assert "Beta0.3.0" in readme
    assert "0.3.0b0" in readme or "Beta0.3.0" in readme
    assert "## [Beta0.3.0]" in changelog
    assert "metadata uses fallback version `0.3.0b0`" in changelog


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
    assert set(plugin["ai_provider"]["supported_api_formats"]) == {"openai", "anthropic"}
    assert plugin["ai_provider"]["supported_api_formats"]["openai"]["custom_base_url"] is True
    assert plugin["ai_provider"]["secret_redaction_required"] is True
    assert plugin["ai_provider"]["plaintext_api_keys_in_manifest"] is False
    assert plugin["uninstall"]["remove_recorded_opencode_artifacts_only"] is True

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


def test_opencode_adapter_docs_do_not_contain_plaintext_api_key_examples():
    opencode_dir = REPO_ROOT / "adapters" / "opencode"
    checked_paths = [opencode_dir / "plugin.json", *sorted((opencode_dir / "agents").glob("*.md")), *sorted((opencode_dir / "skills").glob("*.md"))]
    forbidden_secret_patterns = [
        re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
        re.compile(r"sk-ant-[A-Za-z0-9_-]{12,}"),
        re.compile(r"api[_-]?key\s*[:=]\s*['\"][^'\"<{][^'\"]+['\"]", re.IGNORECASE),
    ]

    offenders = []
    for path in checked_paths:
        content = path.read_text(encoding="utf-8")
        if any(pattern.search(content) for pattern in forbidden_secret_patterns):
            offenders.append(str(path.relative_to(REPO_ROOT)))

    assert offenders == []


def test_claude_code_adapter_docs_do_not_contain_plaintext_api_key_examples():
    claude_code_dir = REPO_ROOT / "adapters" / "claude_code"
    checked_paths = [claude_code_dir / "adapter.py", claude_code_dir / "SKILL.md", REPO_ROOT / "install.json"]
    forbidden_secret_patterns = [
        re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
        re.compile(r"sk-ant-[A-Za-z0-9_-]{12,}"),
        re.compile(r"api[_-]?key\s*[:=]\s*['\"][^'\"<{][^'\"]+['\"]", re.IGNORECASE),
    ]

    offenders = []
    for path in checked_paths:
        content = path.read_text(encoding="utf-8")
        if any(pattern.search(content) for pattern in forbidden_secret_patterns):
            offenders.append(str(path.relative_to(REPO_ROOT)))

    assert offenders == []


def test_repository_docs_and_manifests_do_not_contain_realistic_plaintext_secrets():
    checked_paths = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "CHANGELOG.md",
        REPO_ROOT / "install.json",
        REPO_ROOT / "Install.py",
        REPO_ROOT / "Uninstall.py",
        REPO_ROOT / ".supermedicine" / "config.yaml",
        REPO_ROOT / ".supermedicine" / "policies" / "default.yaml",
    ]
    forbidden_secret_patterns = [
        re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
        re.compile(r"sk-ant-[A-Za-z0-9_-]{12,}"),
        re.compile(r"(?:api[_-]?key|authorization|token)\s*[:=]\s*['\"][^'\"<{][^'\"]{8,}['\"]", re.IGNORECASE),
    ]

    offenders = []
    for path in checked_paths:
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        if any(pattern.search(content) for pattern in forbidden_secret_patterns):
            offenders.append(str(path.relative_to(REPO_ROOT)))

    assert offenders == []


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


def test_opencode_plugin_version_matches_package_version():
    """OpenCode plugin.json version must match pyproject.toml version."""
    plugin_path = REPO_ROOT / "adapters" / "opencode" / "plugin.json"

    pyproject = _read_pyproject()
    package_version = pyproject["project"]["version"]

    with plugin_path.open("r", encoding="utf-8") as f:
        plugin = json.load(f)
    plugin_version = plugin.get("version", "")

    assert plugin_version == package_version, (
        f"OpenCode plugin.json version {plugin_version!r} must match "
        f"pyproject.toml version {package_version!r}"
    )


def test_shebang_lines_are_portable():
    """CLI/install/uninstall entry scripts must use portable shebang."""
    expected = "#!/usr/bin/env python3"
    for filename in ("Cli.py", "Install.py", "Uninstall.py"):
        path = REPO_ROOT / filename
        first_line = path.read_text(encoding="utf-8").split("\n")[0]
        assert first_line == expected, (
            f"{filename} first line must be {expected!r}, got {first_line!r}"
        )


def test_install_manifest_declares_safe_uninstall_entry():
    manifest = json.loads((REPO_ROOT / "install.json").read_text(encoding="utf-8"))
    uninstall = manifest["uninstall"]

    assert uninstall["entry"] == "Uninstall.py"
    assert uninstall["removes_pip_package"] is False
    assert uninstall["log_redaction_required"] is True
    assert "source repository" in uninstall["ownership_rule"]


def test_gitignore_excludes_mypy_cache():
    """.gitignore must exclude .mypy_cache/."""
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".mypy_cache/" in gitignore


def test_package_data_includes_tui_css():
    """pyproject.toml package-data must include core/tui/app.tcss."""
    pyproject = _read_pyproject()
    package_data = pyproject.get("tool", {}).get("setuptools", {}).get("package-data", {})
    core_data = package_data.get("core", [])
    assert "tui/app.tcss" in core_data, (
        f"core package-data must include 'tui/app.tcss', got {core_data!r}"
    )


def test_install_manifest_uses_editable_install():
    """install.json install_deps step must use pip install -e . not pip install -r."""
    install_json_path = REPO_ROOT / "install.json"
    with install_json_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    install_steps = manifest.get("install_steps", [])
    install_deps_steps = [s for s in install_steps if s.get("step") == "install_deps"]
    assert len(install_deps_steps) == 1, "Expected exactly one install_deps step"
    command = install_deps_steps[0].get("command", "")
    assert command == "pip install -e .", (
        f"install_deps command must be 'pip install -e .', got {command!r}"
    )


def test_dev_optional_dependencies_include_pyyaml_type_stubs():
    """CI installs .[dev] before mypy, so PyYAML stubs must be in dev deps."""
    pyproject = _read_pyproject()
    dev_dependencies = pyproject.get("project", {}).get("optional-dependencies", {}).get("dev", [])

    assert any(dep.split(";", maxsplit=1)[0].strip().lower().startswith("types-pyyaml") for dep in dev_dependencies), (
        "project.optional-dependencies.dev must include types-PyYAML so CI mypy has yaml stubs"
    )


def test_ci_workflow_runs_full_quality_gates_without_hardcoded_secrets():
    workflow_paths = sorted((REPO_ROOT / ".github" / "workflows").glob("*.yml")) + sorted((REPO_ROOT / ".github" / "workflows").glob("*.yaml"))
    assert workflow_paths, "Expected at least one CI workflow"

    combined = "\n".join(path.read_text(encoding="utf-8") for path in workflow_paths)

    assert "pytest" in combined
    assert "ruff" in combined
    assert "mypy" in combined
    assert re.search(r"pip\s+install\s+-e\s+(?:['\"])?\.\[dev\](?:['\"])?", combined)
    assert not re.search(r"sk-[A-Za-z0-9_-]{12,}", combined)
    assert not re.search(r"sk-ant-[A-Za-z0-9_-]{12,}", combined)
    assert not re.search(r"(?:api[_-]?key|authorization|token)\s*[:=]\s*['\"][^'\"<{][^'\"]{8,}['\"]", combined, re.IGNORECASE)
