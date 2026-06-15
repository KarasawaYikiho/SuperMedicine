"""Tests for installer.component_installer – component-based installation logic.

Covers:
  - load_components parsing install.json
  - validate_selection rejecting invalid selections
  - install_components file copy correctness
  - default selection logic
  - empty / full selection scenarios
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from installer.component_installer import (
    ComponentDef,
    ComponentError,
    get_component_files,
    get_default_selection,
    install_components,
    load_components,
    validate_selection,
)


# ── Helpers ─────────────────────────────────────────────────────────────────


def _write_install_json(tmp_path: Path, data: dict) -> Path:
    """Write an install.json helper and return its path."""
    path = tmp_path / "install.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def _minimal_components_json() -> dict:
    """Return a minimal but valid components dict for install.json."""
    return {
        "components": {
            "core": {
                "name": "core",
                "description": "Core runtime files",
                "required": True,
                "default": True,
                "files": ["core/"],
                "dependencies": [],
            },
            "cli": {
                "name": "cli",
                "description": "CLI interface",
                "required": False,
                "default": True,
                "files": ["cli/"],
                "dependencies": ["core"],
            },
            "web": {
                "name": "web",
                "description": "Web interface",
                "required": False,
                "default": False,
                "files": ["web/"],
                "dependencies": ["core"],
            },
            "tui": {
                "name": "tui",
                "description": "Terminal UI",
                "required": False,
                "default": False,
                "files": ["tui/"],
                "dependencies": ["core"],
            },
        }
    }


def _make_source_tree(root: Path) -> None:
    """Create a minimal source tree with files for each component."""
    root.mkdir(parents=True, exist_ok=True)
    for subdir in ("core", "cli", "web", "tui"):
        d = root / subdir
        d.mkdir()
        (d / "main.py").write_text(f"# {subdir} main\n", encoding="utf-8")
        (d / "__init__.py").write_text("", encoding="utf-8")


# ═══ load_components ═══════════════════════════════════════════════════════


class TestLoadComponents:
    """Test that load_components correctly parses install.json."""

    def test_loads_valid_config(self, tmp_path):
        data = _minimal_components_json()
        path = _write_install_json(tmp_path, data)

        result = load_components(path)

        assert set(result.keys()) == {"core", "cli", "web", "tui"}
        assert all(isinstance(c, ComponentDef) for c in result.values())

    def test_component_fields_are_parsed(self, tmp_path):
        data = _minimal_components_json()
        path = _write_install_json(tmp_path, data)

        result = load_components(path)

        core = result["core"]
        assert core.name == "core"
        assert core.description == "Core runtime files"
        assert core.required is True
        assert core.default is True
        assert core.files == ("core/",)
        assert core.dependencies == ()

    def test_optional_component_has_correct_flags(self, tmp_path):
        data = _minimal_components_json()
        path = _write_install_json(tmp_path, data)

        result = load_components(path)

        web = result["web"]
        assert web.required is False
        assert web.default is False
        assert web.dependencies == ("core",)

    def test_raises_file_not_found_for_missing_path(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="配置文件不存在"):
            load_components(tmp_path / "nonexistent.json")

    def test_raises_key_error_when_components_key_missing(self, tmp_path):
        path = _write_install_json(tmp_path, {"name": "test"})

        with pytest.raises(KeyError, match="缺少 'components' 字段"):
            load_components(path)

    def test_raises_component_error_for_malformed_entry(self, tmp_path):
        data = {"components": {"bad": "not-a-dict"}}
        path = _write_install_json(tmp_path, data)

        with pytest.raises(ComponentError, match="必须是字典"):
            load_components(path)

    def test_raises_component_error_for_name_mismatch(self, tmp_path):
        data = {
            "components": {
                "key_name": {
                    "name": "different_name",
                    "description": "mismatch",
                }
            }
        }
        path = _write_install_json(tmp_path, data)

        with pytest.raises(ComponentError, match="不一致"):
            load_components(path)

    def test_raises_component_error_for_non_list_files(self, tmp_path):
        data = {
            "components": {
                "bad": {
                    "name": "bad",
                    "description": "bad files",
                    "files": "not-a-list",
                }
            }
        }
        path = _write_install_json(tmp_path, data)

        with pytest.raises(ComponentError, match="files 必须是列表"):
            load_components(path)

    def test_raises_component_error_for_non_list_dependencies(self, tmp_path):
        data = {
            "components": {
                "bad": {
                    "name": "bad",
                    "description": "bad deps",
                    "dependencies": "not-a-list",
                }
            }
        }
        path = _write_install_json(tmp_path, data)

        with pytest.raises(ComponentError, match="dependencies 必须是列表"):
            load_components(path)

    def test_defaults_when_optional_fields_missing(self, tmp_path):
        data = {
            "components": {
                "minimal": {
                    "name": "minimal",
                    "description": "Minimal component",
                }
            }
        }
        path = _write_install_json(tmp_path, data)

        result = load_components(path)

        comp = result["minimal"]
        assert comp.required is False
        assert comp.default is False
        assert comp.files == ()
        assert comp.dependencies == ()


# ═══ get_default_selection ══════════════════════════════════════════════════


class TestDefaultSelection:
    """Test default selection logic."""

    def test_default_includes_default_true_components(self, tmp_path):
        data = _minimal_components_json()
        path = _write_install_json(tmp_path, data)
        components = load_components(path)

        default = get_default_selection(components)

        # core (required+default) and cli (default) should be selected
        assert "core" in default
        assert "cli" in default

    def test_default_excludes_non_default_components(self, tmp_path):
        data = _minimal_components_json()
        path = _write_install_json(tmp_path, data)
        components = load_components(path)

        default = get_default_selection(components)

        # web and tui are not required and not default
        assert "web" not in default
        assert "tui" not in default

    def test_required_components_always_in_default(self):
        components = {
            "forced": ComponentDef(
                name="forced",
                description="Required but default=False",
                required=True,
                default=False,
            ),
            "optional": ComponentDef(
                name="optional",
                description="Optional, default=False",
                required=False,
                default=False,
            ),
        }

        default = get_default_selection(components)

        assert "forced" in default
        assert "optional" not in default

    def test_default_list_is_sorted(self):
        components = {
            "z_comp": ComponentDef(name="z_comp", description="z", default=True),
            "a_comp": ComponentDef(name="a_comp", description="a", default=True),
            "m_comp": ComponentDef(name="m_comp", description="m", default=True),
        }

        default = get_default_selection(components)

        assert default == ["a_comp", "m_comp", "z_comp"]

    def test_empty_components_returns_empty_default(self):
        assert get_default_selection({}) == []


# ═══ validate_selection ════════════════════════════════════════════════════


class TestValidateSelection:
    """Test that validate_selection enforces selection rules."""

    def test_valid_selection_passes(self, tmp_path):
        data = _minimal_components_json()
        path = _write_install_json(tmp_path, data)
        components = load_components(path)

        # Should not raise
        validate_selection(components, ["core", "cli", "web"])

    def test_raises_on_unknown_component(self, tmp_path):
        data = _minimal_components_json()
        path = _write_install_json(tmp_path, data)
        components = load_components(path)

        with pytest.raises(ComponentError, match="未知组件"):
            validate_selection(components, ["core", "nonexistent"])

    def test_raises_on_missing_required_component(self, tmp_path):
        data = _minimal_components_json()
        path = _write_install_json(tmp_path, data)
        components = load_components(path)

        # core is required — omitting it must fail
        with pytest.raises(ComponentError, match="必选组件不可取消"):
            validate_selection(components, ["cli"])

    def test_raises_on_unsatisfied_dependency(self, tmp_path):
        data = _minimal_components_json()
        path = _write_install_json(tmp_path, data)
        components = load_components(path)

        # web depends on core — selecting web without core must fail
        with pytest.raises(ComponentError, match="必选组件不可取消"):
            validate_selection(components, ["web"])

    def test_empty_selection_fails_if_required_exists(self, tmp_path):
        data = _minimal_components_json()
        path = _write_install_json(tmp_path, data)
        components = load_components(path)

        with pytest.raises(ComponentError, match="必选组件不可取消"):
            validate_selection(components, [])

    def test_empty_selection_passes_when_no_required(self):
        components = {
            "opt": ComponentDef(name="opt", description="Optional", required=False),
        }

        # Should not raise
        validate_selection(components, [])

    def test_only_required_component_passes(self, tmp_path):
        data = _minimal_components_json()
        path = _write_install_json(tmp_path, data)
        components = load_components(path)

        # core is required and has no deps — valid minimal selection
        validate_selection(components, ["core"])


# ═══ install_components ════════════════════════════════════════════════════


class TestInstallComponents:
    """Test that install_components correctly deploys selected files."""

    def test_copies_selected_component_files(self, tmp_path):
        data = _minimal_components_json()
        config_path = _write_install_json(tmp_path, data)
        components = load_components(config_path)

        source_root = tmp_path / "source"
        _make_source_tree(source_root)
        install_dir = tmp_path / "install"

        result = install_components(
            components,
            ["core"],
            install_path=install_dir,
            source_root=source_root,
        )

        assert result["status"] == "copied"
        assert (install_dir / "core" / "main.py").exists()
        assert (install_dir / "core" / "__init__.py").exists()

    def test_only_copies_selected_components(self, tmp_path):
        data = _minimal_components_json()
        config_path = _write_install_json(tmp_path, data)
        components = load_components(config_path)

        source_root = tmp_path / "source"
        _make_source_tree(source_root)
        install_dir = tmp_path / "install"

        install_components(
            components,
            ["core"],
            install_path=install_dir,
            source_root=source_root,
        )

        # core should exist, cli/web/tui should not
        assert (install_dir / "core" / "main.py").exists()
        assert not (install_dir / "cli").exists()
        assert not (install_dir / "web").exists()
        assert not (install_dir / "tui").exists()

    def test_copies_multiple_selected_components(self, tmp_path):
        data = _minimal_components_json()
        config_path = _write_install_json(tmp_path, data)
        components = load_components(config_path)

        source_root = tmp_path / "source"
        _make_source_tree(source_root)
        install_dir = tmp_path / "install"

        result = install_components(
            components,
            ["core", "cli"],
            install_path=install_dir,
            source_root=source_root,
        )

        assert result["status"] == "copied"
        assert (install_dir / "core" / "main.py").exists()
        assert (install_dir / "cli" / "main.py").exists()
        assert not (install_dir / "web").exists()

    def test_dry_run_does_not_copy_files(self, tmp_path):
        data = _minimal_components_json()
        config_path = _write_install_json(tmp_path, data)
        components = load_components(config_path)

        source_root = tmp_path / "source"
        _make_source_tree(source_root)
        install_dir = tmp_path / "install"

        result = install_components(
            components,
            ["core"],
            install_path=install_dir,
            source_root=source_root,
            dry_run=True,
        )

        assert result["status"] == "dry-run"
        assert not install_dir.exists()

    def test_skips_when_no_files_in_selection(self, tmp_path):
        components = {
            "empty": ComponentDef(
                name="empty",
                description="No files",
                files=(),
            ),
        }
        install_dir = tmp_path / "install"

        result = install_components(
            components,
            ["empty"],
            install_path=install_dir,
            source_root=tmp_path,
        )

        assert result["status"] == "skipped"
        assert result["reason"] == "no-files"

    def test_raises_on_validation_failure(self, tmp_path):
        components = {
            "required": ComponentDef(
                name="required",
                description="Must be selected",
                required=True,
            ),
        }

        with pytest.raises(ComponentError, match="必选组件不可取消"):
            install_components(components, [], install_path=tmp_path / "out")

    def test_result_contains_expected_keys(self, tmp_path):
        data = _minimal_components_json()
        config_path = _write_install_json(tmp_path, data)
        components = load_components(config_path)

        source_root = tmp_path / "source"
        _make_source_tree(source_root)
        install_dir = tmp_path / "install"

        result = install_components(
            components,
            ["core"],
            install_path=install_dir,
            source_root=source_root,
        )

        assert "status" in result
        assert "target_dir" in result
        assert "file_count" in result
        assert "components" in result
        assert result["components"] == ["core"]

    def test_preserves_file_content_during_copy(self, tmp_path):
        data = _minimal_components_json()
        config_path = _write_install_json(tmp_path, data)
        components = load_components(config_path)

        source_root = tmp_path / "source"
        source_root.mkdir()
        core_dir = source_root / "core"
        core_dir.mkdir()
        content = "# specific content for testing\n"
        (core_dir / "main.py").write_text(content, encoding="utf-8")

        install_dir = tmp_path / "install"

        install_components(
            components,
            ["core"],
            install_path=install_dir,
            source_root=source_root,
        )

        installed_content = (install_dir / "core" / "main.py").read_text(encoding="utf-8")
        assert installed_content == content

    def test_skips_existing_target_when_overwrite_false(self, tmp_path):
        data = _minimal_components_json()
        config_path = _write_install_json(tmp_path, data)
        components = load_components(config_path)

        source_root = tmp_path / "source"
        source_root.mkdir()
        core_dir = source_root / "core"
        core_dir.mkdir()
        (core_dir / "main.py").write_text("new content", encoding="utf-8")

        install_dir = tmp_path / "install"
        install_dir.mkdir()
        (install_dir / "core").mkdir()
        (install_dir / "core" / "main.py").write_text("old content", encoding="utf-8")

        result = install_components(
            components,
            ["core"],
            install_path=install_dir,
            source_root=source_root,
            overwrite=False,
        )

        assert result["status"] == "skipped"
        assert result["reason"] == "target-exists"
        # Original content preserved
        assert (install_dir / "core" / "main.py").read_text(encoding="utf-8") == "old content"

    def test_overwrites_existing_target_when_requested(self, tmp_path):
        data = _minimal_components_json()
        config_path = _write_install_json(tmp_path, data)
        components = load_components(config_path)

        source_root = tmp_path / "source"
        source_root.mkdir()
        core_dir = source_root / "core"
        core_dir.mkdir()
        (core_dir / "main.py").write_text("new content", encoding="utf-8")

        install_dir = tmp_path / "install"
        install_dir.mkdir()
        (install_dir / "core").mkdir()
        (install_dir / "core" / "main.py").write_text("old content", encoding="utf-8")

        result = install_components(
            components,
            ["core"],
            install_path=install_dir,
            source_root=source_root,
            overwrite=True,
        )

        assert result["status"] == "copied"
        assert (install_dir / "core" / "main.py").read_text(encoding="utf-8") == "new content"


# ═══ get_component_files ═══════════════════════════════════════════════════


class TestGetComponentFiles:
    """Test file enumeration for selected components."""

    def test_returns_source_relative_pairs(self, tmp_path):
        data = _minimal_components_json()
        config_path = _write_install_json(tmp_path, data)
        components = load_components(config_path)

        source_root = tmp_path / "source"
        _make_source_tree(source_root)

        files = get_component_files(components, ["core"], source_root=source_root)

        assert len(files) >= 1
        for source, relative in files:
            assert source.is_absolute()
            assert not relative.is_absolute()

    def test_deduplicates_shared_files(self, tmp_path):
        components = {
            "a": ComponentDef(
                name="a",
                description="A",
                files=("shared/file.txt",),
            ),
            "b": ComponentDef(
                name="b",
                description="B",
                files=("shared/file.txt",),
            ),
        }
        source_root = tmp_path
        (source_root / "shared").mkdir(parents=True, exist_ok=True)
        (source_root / "shared" / "file.txt").write_text("shared content", encoding="utf-8")

        files = get_component_files(components, ["a", "b"], source_root=source_root)

        # Even though both components reference the same file, it should appear once
        relative_paths = [rel for _, rel in files]
        shared_count = sum(1 for p in relative_paths if p.as_posix() == "shared/file.txt")
        assert shared_count == 1

    def test_handles_missing_source_gracefully(self, tmp_path):
        components = {
            "ghost": ComponentDef(
                name="ghost",
                description="Missing files",
                files=("nonexistent/path.py",),
            ),
        }

        files = get_component_files(components, ["ghost"], source_root=tmp_path)

        assert files == []

    def test_empty_selected_returns_empty(self, tmp_path):
        components = {
            "a": ComponentDef(name="a", description="A", files=("a/",)),
        }

        files = get_component_files(components, [], source_root=tmp_path)

        assert files == []


# ═══ Empty / Full Selection Scenarios ══════════════════════════════════════


class TestEdgeCaseSelections:
    """Test edge-case selection scenarios."""

    def test_full_selection_installs_all_components(self, tmp_path):
        data = _minimal_components_json()
        config_path = _write_install_json(tmp_path, data)
        components = load_components(config_path)

        source_root = tmp_path / "source"
        _make_source_tree(source_root)
        install_dir = tmp_path / "install"

        all_names = list(components.keys())
        result = install_components(
            components,
            all_names,
            install_path=install_dir,
            source_root=source_root,
        )

        assert result["status"] == "copied"
        for name in ("core", "cli", "web", "tui"):
            assert (install_dir / name / "main.py").exists()

    def test_only_required_with_no_optional(self, tmp_path):
        data = _minimal_components_json()
        config_path = _write_install_json(tmp_path, data)
        components = load_components(config_path)

        source_root = tmp_path / "source"
        _make_source_tree(source_root)
        install_dir = tmp_path / "install"

        result = install_components(
            components,
            ["core"],
            install_path=install_dir,
            source_root=source_root,
        )

        assert result["status"] == "copied"
        assert result["components"] == ["core"]

    def test_full_selection_with_dependencies_satisfied(self, tmp_path):
        data = _minimal_components_json()
        config_path = _write_install_json(tmp_path, data)
        components = load_components(config_path)

        # All selected — all dependencies satisfied
        validate_selection(components, list(components.keys()))

    def test_component_with_single_file_entry(self, tmp_path):
        components = {
            "readme": ComponentDef(
                name="readme",
                description="A single file",
                files=("README.md",),
            ),
        }

        source_root = tmp_path / "source"
        source_root.mkdir()
        (source_root / "README.md").write_text("# Hello\n", encoding="utf-8")
        install_dir = tmp_path / "install"

        result = install_components(
            components,
            ["readme"],
            install_path=install_dir,
            source_root=source_root,
        )

        assert result["status"] == "copied"
        assert result["file_count"] == 1
        assert (install_dir / "README.md").exists()
        assert (install_dir / "README.md").read_text(encoding="utf-8") == "# Hello\n"
