from __future__ import annotations

import ast
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
CANONICAL_SUPERMEDICINE_POLICY = ".supermedicine/policies/default.yaml"
FORBIDDEN_FRONTEND_STREAMING_HINTS = (
    "".join(["模型正在", "返回内容，会", "增量", "显示"]),
    "".join(["模型正在", "返回内容"]),
    "".join(["界面会", "增量", "显示"]),
    "".join(["增量", "显示"]),
    "".join(["助手正在", "生成回复"]),
)
FRONTEND_STREAMING_HINT_SCAN_PATHS = (
    "core/web/frontend/app.js",
    "core/web/frontend/index.html",
    "core/web/frontend/style.css",
    "core/tui/screens/chat_view.py",
    "core/tui/i18n.py",
    "core/tui/app.py",
    "core/kernel_llm_chat.py",
)
TEMPORARY_TEST_FILE_PATTERNS = (
    "test_tmp_*.py",
    "test_temp_*.py",
    "test_scratch_*.py",
    "test_debug_*.py",
)
LOCAL_ONLY_MARKERS = (
    ".agents",
    ".claude",
    ".codex",
    ".continue",
    ".cursor",
    ".opencode",
    ".windsurf",
    ".roo",
    ".cline",
    "codextem",
    "codex-tem",
    "codex_tmp",
    "superpower",
    "superpowers",
)
LOCAL_ONLY_DOCUMENT_PATTERNS = (
    "*_audit_dump*.md",
    "*_audit_log*.md",
    "*_codex_cache*.md",
    "*_codex_notes*.md",
    "*_gap-analysis*.md",
    "*_gap_analysis*.md",
    "*_machine_notes*.md",
    "*_plan_draft*.md",
    "*_planning_draft*.md",
    "*_private_analysis*.md",
    "*_scratch*.md",
    "*_scratch_notes*.md",
    "*_transient_checklist*.md",
    "*_uncurated_engineering*.md",
    "*_validation_notes*.md",
    "local_plan*.md",
    "LOCAL_PLAN*.md",
    "Superpower*.md",
    "SUPERPOWER*.md",
    "superpower*.md",
)
LOCAL_ONLY_ARCHIVE_DOCUMENTS = {
    "docs/archive/DebugReviewManualValidation.md",
    "docs/archive/PushCleanupClassification.md",
    "docs/archive/TestMergeInventory.md",
}

INTENTIONAL_GENERATED_ARTIFACT_REFERENCES = {
    "build/": "ignored build output pattern; not a required repository directory",
    "dist/": "ignored distribution output pattern; not a required repository directory",
    "supermedicine.egg-info/": "editable/build metadata output; not repository content",
    ".mypy_cache/": "ignored type-check cache pattern; not repository content",
    ".ruff_cache/": "ignored lint cache pattern; not repository content",
    ".supermedicine/checkpoints/": "ignored runtime checkpoint state; not repository content",
    ".supermedicine/policies/audit.jsonl": "ignored runtime audit log; not repository content",
    "plugins/tools/r_template/plugin.yaml": (
        "stale distribution member cleanup target; setup.py removes this formerly "
        "packaged manifest name when old build artifacts are rewritten"
    ),
}


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
            result["project"].setdefault("optional-dependencies", {})["dev"] = (
                re.findall(
                    r'"([^"]+)"',
                    dev_match.group(1),
                )
            )
    # Extract core package-data entries
    current_package_data_key = None
    for line in text.splitlines():
        package_data_match = re.match(r"^(core|installer)\s*=\s*\[", line)
        if package_data_match:
            current_package_data_key = package_data_match.group(1)
            entries = re.findall(r'"([^"]+)"', line)
            result["tool"]["setuptools"]["package-data"][current_package_data_key] = (
                entries
            )
        elif current_package_data_key and line.strip().startswith("]"):
            current_package_data_key = None
    return result


def _tracked_files() -> list[str]:
    """Return paths currently present in the Git index.

    Hygiene checks intentionally inspect the index rather than the working tree:
    staged additions/modifications of local-only artifacts are visible here and
    must fail, while staged deletions/de-indexing of previously tracked
    local-only artifacts are absent and must be allowed so the repository can be
    cleaned up.
    """
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _active_gitignore_patterns() -> set[str]:
    """Return only active .gitignore patterns, excluding comments/blank lines."""
    patterns: set[str] = set()
    for line in (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        patterns.add(stripped)
    return patterns


def _git_check_ignore(path: str) -> str:
    result = subprocess.run(
        ["git", "check-ignore", "-v", "--", path],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, f"{path} is not ignored by active .gitignore"
    assert result.stdout.strip(), f"{path} did not report an active ignore rule"
    return result.stdout.strip()


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


def _tracked_python_files() -> list[Path]:
    return [
        REPO_ROOT / path
        for path in _tracked_files()
        if path.endswith(".py") and (REPO_ROOT / path).is_file()
    ]


def _is_temporary_test_file(path: str) -> bool:
    path_obj = Path(path)
    parts = path_obj.parts
    if not parts or parts[0] != "tests":
        return False
    return any(path_obj.match(pattern) for pattern in TEMPORARY_TEST_FILE_PATTERNS)


def _matches_local_only_document(path: str) -> bool:
    path_obj = Path(path)
    return any(path_obj.match(pattern) for pattern in LOCAL_ONLY_DOCUMENT_PATTERNS)


def test_python_sources_do_not_import_legacy_uppercase_install_module_outside_compatibility_tests():
    """Regression baseline: mypy must not depend on resolving top-level ``Install``.

    Windows and case-only sibling checkouts cannot consistently expose the
    uppercase top-level module to mypy while also supporting the documented
    lowercase ``install.py`` entrypoint.  Runtime entrypoints and tests should
    import the stable lowercase installer surface instead of ``from Install`` or
    ``import Install``.
    """

    allowed_legacy_compatibility_imports: set[tuple[str, int]] = set()
    offenders: list[str] = []
    for path in _tracked_python_files():
        relative_path = path.relative_to(REPO_ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "Install":
                if (
                    relative_path,
                    node.lineno,
                ) not in allowed_legacy_compatibility_imports:
                    offenders.append(
                        f"{relative_path}:{node.lineno}: legacy uppercase Install import-from"
                    )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "Install":
                        if (
                            relative_path,
                            node.lineno,
                        ) not in allowed_legacy_compatibility_imports:
                            offenders.append(
                                f"{relative_path}:{node.lineno}: legacy uppercase Install direct import"
                            )

    assert offenders == [], (
        "Do not import the legacy uppercase top-level Install module; use the "
        "lowercase installer entrypoint/module so mypy and case-only sibling "
        "checkouts are stable. Only narrowly scoped runtime compatibility tests "
        f"may be allowlisted here. Offenders: {offenders}"
    )


def test_tracked_files_do_not_include_forbidden_or_generated_artifacts():
    forbidden_matches = []

    for tracked_path in _tracked_files():
        if tracked_path == CANONICAL_SUPERMEDICINE_POLICY:
            continue
        if tracked_path == "docs/archive/REQUIREMENTS_TRACEABILITY.md":
            forbidden_matches.append(tracked_path)
        parts = _normalized_parts(tracked_path)
        name = parts[-1]
        lower_parts = tuple(part.lower() for part in parts)

        if parts and parts[0] == "Docs":
            forbidden_matches.append(tracked_path)
        if any(part in LOCAL_ONLY_MARKERS for part in lower_parts):
            forbidden_matches.append(tracked_path)
        if "node_modules" in lower_parts or ".cache" in lower_parts:
            forbidden_matches.append(tracked_path)
        if name.endswith(".pyc"):
            forbidden_matches.append(tracked_path)
        if name.lower().endswith(".exe"):
            forbidden_matches.append(tracked_path)
        if any(
            part
            in {
                "__pycache__",
                ".pytest_cache",
                ".pytest-tmp",
                ".ruff_cache",
                "build",
                "dist",
            }
            for part in parts
        ):
            forbidden_matches.append(tracked_path)
        if any(part in {".release-zip-stage", "release-artifacts"} for part in parts):
            forbidden_matches.append(tracked_path)
        if any(part.endswith(".egg-info") for part in parts):
            forbidden_matches.append(tracked_path)
        if any(
            part
            in {
                ".installer-payload-stage",
                ".pyinstaller-build",
                ".pyinstaller-installer-build",
                "build-pyinstaller",
            }
            for part in parts
        ):
            forbidden_matches.append(tracked_path)
        if _matches_local_only_document(tracked_path):
            forbidden_matches.append(tracked_path)
        if tracked_path in LOCAL_ONLY_ARCHIVE_DOCUMENTS:
            forbidden_matches.append(tracked_path)
        if tracked_path == ".supermedicine/policies/audit.jsonl":
            forbidden_matches.append(tracked_path)
        if tracked_path == ".supermedicine/checkpoints" or tracked_path.startswith(
            ".supermedicine/checkpoints/"
        ):
            forbidden_matches.append(tracked_path)
        if _is_temporary_test_file(tracked_path):
            forbidden_matches.append(tracked_path)

    assert sorted(set(forbidden_matches)) == []


def test_frontend_streaming_incremental_hint_copy_is_not_reintroduced():
    offenders: list[str] = []

    for relative_path in FRONTEND_STREAMING_HINT_SCAN_PATHS:
        text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        for phrase in FORBIDDEN_FRONTEND_STREAMING_HINTS:
            if phrase in text:
                offenders.append(f"{relative_path}: {phrase}")

    assert offenders == []


def test_intentional_generated_artifact_references_are_documented_non_repository_paths():
    """Generated/cache/stale-cleanup path strings must be explicit exceptions.

    These strings are not repository files and should not be "fixed" to existing
    paths: they document ignore rules or cleanup targets for artifacts that may
    appear outside a clean source checkout.
    """

    tracked_files = set(_tracked_files())

    for path, rationale in INTENTIONAL_GENERATED_ARTIFACT_REFERENCES.items():
        assert rationale.strip(), path
        normalized_path = path.rstrip("/")
        assert normalized_path not in tracked_files, (
            f"{path} is documented as a generated/cache/stale-artifact reference "
            "but is currently tracked repository content"
        )


def test_supermedicine_runtime_bootstrap_copies_are_local_only():
    """Only the canonical default policy may remain tracked under .supermedicine.

    All other .supermedicine runtime/bootstrap files are local-only artifacts,
    not repository content. Adding or modifying them in the index must fail this
    check; staging their deletion/de-indexing is permitted because it removes
    them from the indexed file list returned by ``git ls-files``.
    """
    tracked_supermedicine = sorted(
        path
        for path in _tracked_files()
        if path == ".supermedicine" or path.startswith(".supermedicine/")
    )

    assert tracked_supermedicine == [CANONICAL_SUPERMEDICINE_POLICY], (
        ".supermedicine runtime files must stay local-only; only the canonical "
        "default policy may be tracked. Stage deletion or de-indexing for any "
        "other existing remote-tracked copies; do not stage additions or "
        "modifications under .supermedicine/."
    )
    assert (REPO_ROOT / CANONICAL_SUPERMEDICINE_POLICY).is_file()


def test_canonical_supermedicine_default_policy_is_tracked_and_not_ignored():
    path = CANONICAL_SUPERMEDICINE_POLICY

    assert path in _tracked_files()

    result = subprocess.run(
        ["git", "check-ignore", "-v", "--", path],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1, f"{path} must not be ignored by .gitignore"
    assert result.stdout.strip() == ""


def test_gitignore_excludes_runtime_and_external_platform_config_artifacts():
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    required_patterns = {
        ".supermedicine/",
        ".pytest_cache/",
        ".pytest-tmp/",
        ".pytest_tmp/",
        ".ruff_cache/",
        ".mypy_cache/",
        "build/",
        "dist/",
        ".pyinstaller-build/",
        ".pyinstaller-installer-build/",
        "build-pyinstaller/",
        ".installer-payload-stage/",
        ".release-zip-stage/",
        "release-artifacts/",
        "*.exe",
        "*.py[cod]",
        ".supermedicine/config.yaml",
        ".supermedicine/policies/default.yaml",
        ".supermedicine/install-record.json",
        ".supermedicine/policies/audit.jsonl",
        ".supermedicine/checkpoints/",
        ".supermedicine/cache/",
        ".supermedicine/tmp/",
        ".claude/",
        ".agents/",
        ".opencode/",
        ".codex/",
        ".cursor/",
        ".continue/",
        ".aider*",
        ".windsurf/",
        ".roo/",
        ".cline/",
        "CodexTem/",
        "codex-tem/",
        "codex_tmp/",
        "superpowers/",
        "Superpower/",
        "Superpowers/",
        "superpower/",
        "EXTERNAL_PROJECT_ANALYSIS.md",
        "failure_inventory.md",
        "docs/superpowers/",
        "docs/Superpower/",
        "docs/Superpowers/",
        "docs/superpower/",
        "tests/**/test_tmp_*.py",
        "tests/**/test_temp_*.py",
        "tests/**/test_scratch_*.py",
        "tests/**/test_debug_*.py",
        "*_audit_dump*.md",
        "*_audit_dump*.json",
        "*_audit_log*.md",
        "*_audit_log*.jsonl",
        "*_plan_draft*.md",
        "*_planning_draft*.md",
        "*_scratch*.md",
        "*_scratch_notes*.md",
        "*_machine_notes*.md",
        "*_codex_notes*.md",
        "*_codex_cache*.md",
        "*_gap-analysis*.md",
        "*_gap_analysis*.md",
        "*_private_analysis*.md",
        "*_transient_checklist*.md",
        "*_uncurated_engineering*.md",
        "*_validation_notes*.md",
        "/Planning/",
        "node_modules/",
        "/docs/**/*gap-analysis*.md",
        "/docs/**/*gap_analysis*.md",
        "/docs/**/*validation_notes*.md",
        "/docs/archive/DebugReviewManualValidation.md",
        "/docs/archive/PushCleanupClassification.md",
        "/docs/archive/REQUIREMENTS_TRACEABILITY.md",
        "/docs/archive/TestMergeInventory.md",
    }

    for pattern in required_patterns:
        assert pattern in gitignore

    # Also verify that key local-only files are actively ignored (merged from
    # the former test_local_only_files_are_ignored_by_active_gitignore_rules).
    for path in [
        ".supermedicine/config.yaml",
        "EXTERNAL_PROJECT_ANALYSIS.md",
        "failure_inventory.md",
        "docs/archive/REQUIREMENTS_TRACEABILITY.md",
        "tests/test_tmp_example.py",
        ".codex/session.json",
        ".agents/session.json",
        ".cursor/session.json",
        ".continue/config.json",
        ".aider.chat.history.md",
        ".windsurf/state.json",
        ".roo/state.json",
        ".cline/state.json",
        "Superpowers/local.md",
        "docs/Superpowers/local.md",
        "docs/tui-opentui-gap-analysis.md",
        "docs/archive/release_validation_notes.md",
        "docs/archive/DebugReviewManualValidation.md",
        "docs/archive/PushCleanupClassification.md",
        "docs/archive/TestMergeInventory.md",
        "local_plan_next.md",
        "analysis_codex_notes.md",
    ]:
        rule = _git_check_ignore(path)
        assert path in rule, rule


def test_gitattributes_normalizes_text_and_marks_binary_assets():
    gitattributes = (REPO_ROOT / ".gitattributes").read_text(encoding="utf-8")

    assert "* text=auto eol=lf" in gitattributes
    for pattern in {"*.png binary", "*.jpg binary", "*.jpeg binary", "*.ico binary"}:
        assert pattern in gitattributes


def test_gitignore_allows_curated_maintainer_repository_docs():
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    active_patterns = _active_gitignore_patterns()

    assert "Maintainer-facing repository docs are commit/upload eligible" in gitignore
    for pattern in {
        "Architecture/ExecutionRoadmap.md",
        "Architecture/ExecutionRoadMap.md",
        "docs/architecture/FUNCTION_MAP.md",
    }:
        assert pattern not in active_patterns


def test_install_manifest_keeps_external_platform_config_out_of_core_product_paths():
    manifest = json.loads((REPO_ROOT / "install.json").read_text(encoding="utf-8"))

    for platform_name, platform in manifest["platforms"].items():
        entry = Path(platform["entry"])
        entry_parts = entry.parts

        assert entry_parts[0] == "adapters", (
            f"{platform_name} should be packaged as an optional adapter"
        )
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
    assert (
        set(platforms["claude-code"]["supported_tools"])
        == ClaudeCodeAdapter.SUPPORTED_TOOLS
    )
    assert (
        set(platforms["opencode"]["supported_tools"]) == OpenCodeAdapter.SUPPORTED_TOOLS
    )
    assert platforms["claude-code"]["native_skill_loading"] is False
    assert platforms["claude-code"]["native_subagent_runtime"] is False
    assert set(platforms["claude-code"]["ai_provider"]["supported_api_formats"]) == {
        "openai",
        "anthropic",
        "openrouter",
    }
    assert platforms["claude-code"]["ai_provider"]["custom_base_url"] is True
    assert platforms["claude-code"]["ai_provider"]["secret_redaction_required"] is True
    assert (
        platforms["claude-code"]["ai_provider"]["plaintext_api_keys_in_manifest"]
        is False
    )
    assert platforms["opencode"]["native_subagent_runtime"] is False


def test_install_manifest_declares_single_user_facing_platform_agent():
    manifest = json.loads((REPO_ROOT / "install.json").read_text(encoding="utf-8"))

    for platform_name, platform in manifest["platforms"].items():
        assert platform["user_facing_agents"] == ["SuperMedicine"], platform_name
        assert len(platform["user_facing_agents"]) == 1, platform_name
        assert FORBIDDEN_PLATFORM_AGENT_NAMES.isdisjoint(
            platform["user_facing_agents"]
        ), platform_name
        assert platform["internal_role_contexts"] == [
            "alpha",
            "beta",
            "gamma",
            "delta",
        ], platform_name
        assert platform["optional_add_on"] is True, platform_name
        assert platform["core_runtime_required"] is False, platform_name
    assert (
        manifest["install_completeness_model"]["single_user_facing_agent"]
        == "SuperMedicine"
    )


def test_release_label_and_package_version_stay_in_sync():
    install_manifest = json.loads(
        (REPO_ROOT / "install.json").read_text(encoding="utf-8")
    )
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    package_version = re.search(
        r'^version\s*=\s*["\']([^"\']+)["\']\s*$', pyproject, re.MULTILINE
    )

    assert install_manifest["version"] == "Beta0.4.2"
    assert package_version is not None
    assert package_version.group(1) == "0.4.2b0"
    assert "Beta0.4.2" in readme
    assert "## [Beta0.4.2]" in changelog
    assert "metadata uses fallback version `0.4.2b0`" in changelog


def test_release_zip_archive_name_uses_display_format_without_source_suffix():
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    build_release_zip = (REPO_ROOT / "scripts" / "ci" / "build_release_zip.py").read_text(
        encoding="utf-8"
    )
    package_version = _read_pyproject()["project"]["version"]
    beta_match = re.fullmatch(r"(\d+\.\d+\.\d+)b\d+", package_version)
    assert beta_match is not None

    expected_archive_name = f"SuperMedicine Beta{beta_match.group(1)}.zip"
    archive_body = expected_archive_name.removesuffix(".zip")

    assert expected_archive_name == "SuperMedicine Beta0.4.2.zip"
    assert "source" not in archive_body.lower()
    assert "_" not in archive_body
    assert 'archive_name = f"SuperMedicine {release_label}.zip"' in build_release_zip
    assert (
        'stage = root / ".release-zip-stage" / f"SuperMedicine {release_label}"'
        in build_release_zip
    )
    assert "SuperMedicine-{release_label}-source" not in workflow
    assert ".source-zip-stage" not in workflow
    assert "${{ steps.source_zip.outputs.release_label }}-source" not in workflow
    assert "${{ needs.packaging-smoke.outputs.release_label }}-source" not in workflow
    assert 'output.write(f"archive_name={archive_name}\\n")' in build_release_zip
    assert "ARCHIVE_NAME: ${{ needs.packaging-smoke.outputs.archive_name }}" in workflow
    assert 'asset_path="release-artifacts/${ARCHIVE_NAME}"' in workflow
    assert 'gh release upload "$RELEASE_TAG" "$asset_path"' in workflow


def test_release_zip_layout_includes_installer_package_for_install_entrypoint():
    packaging_common = (REPO_ROOT / "scripts" / "ci" / "_packaging_common.py").read_text(
        encoding="utf-8"
    )

    assert '"install_entry.py"' in packaging_common
    assert (
        'INCLUDE_DIRS = ["core", "permission", "agents", "plugins", "adapters", "installer"]'
        in packaging_common
    )
    assert "installer/__init__.py" in _tracked_files()
    assert "installer/exe_release.py" in _tracked_files()


def test_release_asset_cleanup_does_not_delete_graphql_node_ids_with_rest_endpoint():
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    extracts_release_asset_node_ids = re.search(
        r"gh\s+release\s+view\b(?:(?!\n\s*(?:if|else|fi|while|done)\b).)*"
        r"--json\s+assets\b(?:(?!\n\s*(?:if|else|fi|while|done)\b).)*"
        r"--jq\s+[\"'][^\"']*\.id\b",
        workflow,
        re.DOTALL,
    )
    deletes_release_asset_with_rest_endpoint = re.search(
        r"gh\s+api\s+--method\s+DELETE\s+repos/[^\s\"']+/releases/assets/\$\{?asset_id\}?\b",
        workflow,
    )

    assert not (
        extracts_release_asset_node_ids and deletes_release_asset_with_rest_endpoint
    ), (
        "Release asset cleanup must not pass GraphQL asset node IDs from "
        "`gh release view --json assets --jq ... .id` to the REST release asset delete endpoint."
    )
    assert "gh release delete-asset" in workflow


def test_opencode_plugin_declared_entry_skills_and_agents_exist():
    plugin_dir = REPO_ROOT / "adapters" / "opencode"
    plugin = json.loads((plugin_dir / "plugin.json").read_text(encoding="utf-8"))
    from adapters.opencode.adapter import OpenCodeAdapter

    assert (plugin_dir / plugin["entry"]).is_file()
    assert (plugin_dir / plugin["install_entry_files"]["plugin_manifest"]).is_file()
    assert (plugin_dir / plugin["install_entry_files"]["adapter_module"]).is_file()
    assert (
        plugin_dir / plugin["install_entry_files"]["single_user_facing_agent"]
    ).is_file()
    assert (plugin_dir / plugin["install_entry_files"]["skill_documents_dir"]).is_dir()
    assert (
        plugin_dir / plugin["install_entry_files"]["internal_role_context_dir"]
    ).is_dir()
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
    assert (
        plugin["install_entry_files"]["single_user_facing_agent"]
        == "agents/supermedicine.md"
    )
    assert (
        plugin["install_completeness_model"]["single_user_facing_agent"]
        == "SuperMedicine"
    )
    assert set(plugin["ai_provider"]["supported_api_formats"]) == {
        "openai",
        "anthropic",
        "openrouter",
    }
    assert (
        plugin["ai_provider"]["supported_api_formats"]["openai"]["custom_base_url"]
        is True
    )
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
        assert declared_path.is_file(), (
            f"Missing OpenCode internal role context: {relative_path}"
        )
        content = declared_path.read_text(encoding="utf-8")
        assert "user_facing: false" in content
        assert "internal_role_context: true" in content


def test_no_plaintext_secrets_in_docs_and_manifests():
    """Consolidated scan: no docs or manifests may contain plaintext secret patterns."""
    opencode_dir = REPO_ROOT / "adapters" / "opencode"
    claude_code_dir = REPO_ROOT / "adapters" / "claude_code"

    checked_paths = [
        # OpenCode adapter docs
        opencode_dir / "plugin.json",
        *sorted((opencode_dir / "agents").glob("*.md")),
        *sorted((opencode_dir / "skills").glob("*.md")),
        # Claude Code adapter docs
        claude_code_dir / "adapter.py",
        claude_code_dir / "SKILL.md",
        # Repository-level docs and manifests
        REPO_ROOT / "install.json",
        REPO_ROOT / "README.md",
        REPO_ROOT / "CHANGELOG.md",
        REPO_ROOT / "Install.py",
        REPO_ROOT / "Uninstall.py",
        REPO_ROOT / ".supermedicine" / "config.yaml",
        REPO_ROOT / ".supermedicine" / "policies" / "default.yaml",
        # Root-level markdown docs
        *sorted(REPO_ROOT.glob("*.md")),
    ]
    # Deduplicate while preserving order
    seen: set[Path] = set()
    unique_paths: list[Path] = []
    for p in checked_paths:
        if p not in seen:
            seen.add(p)
            unique_paths.append(p)

    forbidden_secret_patterns = [
        re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
        re.compile(r"sk-ant-[A-Za-z0-9_-]{12,}"),
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(
            r"(?:api[_-]?key|authorization|token|secret)\s*[:=]\s*['\"][^'\"<{][^'\"]{8,}['\"]",
            re.IGNORECASE,
        ),
    ]

    offenders = []
    for path in unique_paths:
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
            missing_entries.append(
                f"{manifest_path.relative_to(REPO_ROOT)}: missing entry"
            )
            continue
        entry_path = manifest_path.parent / entry
        if not entry_path.is_file():
            missing_entries.append(f"{manifest_path.relative_to(REPO_ROOT)} -> {entry}")

    assert missing_entries == []


def test_pyproject_console_script_target_is_importable():
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(
        r'^supermedicine\s*=\s*["\']([^"\']+)["\']\s*$', pyproject, re.MULTILINE
    )
    assert match, "Missing supermedicine console script"

    module_name, attribute_name = match.group(1).split(":", maxsplit=1)
    module = importlib.import_module(module_name)

    assert callable(getattr(module, attribute_name))


def test_pyproject_console_script_top_level_module_is_packaged():
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(
        r'^supermedicine\s*=\s*["\']([^"\']+)["\']\s*$', pyproject, re.MULTILINE
    )
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
    for filename in ("cli_entry.py", "install_entry.py", "uninstall_entry.py"):
        path = REPO_ROOT / filename
        first_line = path.read_text(encoding="utf-8").split("\n")[0]
        assert first_line == expected, (
            f"{filename} first line must be {expected!r}, got {first_line!r}"
        )


def test_distribution_build_forces_exact_lowercase_install_entry():
    """Packaging must not rely on Windows materializing install.py and Install.py."""

    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    setup_py = (REPO_ROOT / "setup.py").read_text(encoding="utf-8")

    py_modules = _setuptools_py_modules(pyproject)
    assert "cli_entry" in py_modules
    assert "uninstall_entry" in py_modules
    assert "install" not in py_modules
    assert "Install" not in py_modules
    assert '["git", "show", ":install.py"]' in setup_py
    assert '["git", "show", ":install_entry.py"]' in setup_py
    assert 'LOWERCASE_INSTALL_NAME = "install.py"' in setup_py
    assert 'UPPERCASE_INSTALL_NAME = "install_entry.py"' in setup_py
    assert "class build_py" in setup_py
    assert "class sdist" in setup_py
    assert "class bdist_wheel" in setup_py
    assert 'Path(self.dist_dir).glob("*.whl")' in setup_py
    assert "get_outputs()" not in setup_py
    assert "archive.writestr(name, data)" in setup_py


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
    package_data = (
        pyproject.get("tool", {}).get("setuptools", {}).get("package-data", {})
    )
    core_data = package_data.get("core", [])
    assert "tui/app.tcss" in core_data, (
        f"core package-data must include 'tui/app.tcss', got {core_data!r}"
    )


def test_packaging_declares_installer_resource_strategy_without_tracked_exe():
    pyproject = _read_pyproject()
    package_data = (
        pyproject.get("tool", {}).get("setuptools", {}).get("package-data", {})
    )
    installer_data = package_data.get("installer", [])
    manifest = json.loads((REPO_ROOT / "install.json").read_text(encoding="utf-8"))
    resource_policy = manifest["packaging_resources"]

    assert "resources/*.json" in installer_data
    assert "resources/*.md" in installer_data
    assert "resources/*.txt" in installer_data
    assert resource_policy["installer_package"] == "installer"
    assert "Install.py --release-exe" in resource_policy["exe_resource_strategy"]
    assert "not committed" in resource_policy["exe_resource_strategy"]
    assert "*.exe" in resource_policy["generated_artifacts_excluded"]
    assert not any(path.lower().endswith(".exe") for path in _tracked_files())


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
    dev_dependencies = (
        pyproject.get("project", {}).get("optional-dependencies", {}).get("dev", [])
    )

    assert any(
        dep.split(";", maxsplit=1)[0].strip().lower().startswith("types-pyyaml")
        for dep in dev_dependencies
    ), (
        "project.optional-dependencies.dev must include types-PyYAML so CI mypy has yaml stubs"
    )


def test_ci_workflow_runs_full_quality_gates_without_hardcoded_secrets():
    workflow_paths = sorted(
        (REPO_ROOT / ".github" / "workflows").glob("*.yml")
    ) + sorted((REPO_ROOT / ".github" / "workflows").glob("*.yaml"))
    assert workflow_paths, "Expected at least one CI workflow"

    combined = "\n".join(path.read_text(encoding="utf-8") for path in workflow_paths)

    assert "pytest" in combined
    assert "ruff" in combined
    assert "mypy" in combined
    assert re.search(r"pip\s+install\s+-e\s+(?:['\"])?\.\[dev\](?:['\"])?", combined)
    assert not re.search(r"sk-[A-Za-z0-9_-]{12,}", combined)
    assert not re.search(r"sk-ant-[A-Za-z0-9_-]{12,}", combined)
    assert not re.search(
        r"(?:api[_-]?key|authorization|token)\s*[:=]\s*['\"][^'\"<{][^'\"]{8,}['\"]",
        combined,
        re.IGNORECASE,
    )
