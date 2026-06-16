"""Tests for R/Python workspace tool scanning and import (DBG-BUG-003).

Validates that ``WorkspaceToolService`` correctly scans ``plugins/tools`` for
Python and R tool candidates, handles metadata fallbacks, and imports candidates
into workspace directories without data loss or path-escape issues.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from core.workspace_tools import WorkspaceToolService
from core.workspace_tool_models import (
    InvalidToolId,
    InvalidToolLanguage,
    ToolCandidateError,
    validate_language,
    validate_tool_id,
)


# ═══ Language / Tool ID Validation ═══


class TestValidation:
    """Sanity checks on language and tool-id validators exposed by the models."""

    @pytest.mark.parametrize("language", ["python", "r"])
    def test_validate_language_accepts_supported(self, language: str):
        assert validate_language(language) == language

    @pytest.mark.parametrize(
        "language", ["", "Python", "R", "julia", "javascript", "python/../r"]
    )
    def test_validate_language_rejects_unsupported(self, language: str):
        with pytest.raises(InvalidToolLanguage):
            validate_language(language)

    @pytest.mark.parametrize("tool_id", ["heatmap", "umap-2", "a", "my-tool-1"])
    def test_validate_tool_id_accepts_safe_slugs(self, tool_id: str):
        assert validate_tool_id(tool_id) == tool_id

    @pytest.mark.parametrize(
        "tool_id",
        ["", "Heatmap", "heat_map", "heat map", "-heatmap", "heatmap-",
         "../heatmap", "heatmap/one", "..", ".", "UPPER"],
    )
    def test_validate_tool_id_rejects_unsafe(self, tool_id: str):
        with pytest.raises(InvalidToolId):
            validate_tool_id(tool_id)


# ═══ Tool Source Root ═══


class TestToolSourceRoot:
    """Verify the project directory scanned for importable tools."""

    def test_tool_source_root_points_to_plugins_tools(self, tmp_path: Path):
        service = WorkspaceToolService(tmp_path)
        expected = (tmp_path / "plugins" / "tools").resolve()
        assert service.tool_source_root() == expected


# ═══ Scan Import Candidates ═══


class TestScanImportCandidates:
    """Exercises ``scan_import_candidates`` against synthetic tool directories."""

    @staticmethod
    def _make_python_tool(
        source_root: Path,
        dir_name: str,
        plugin_meta: dict | None = None,
        entrypoint_name: str = "main.py",
    ) -> Path:
        tool_dir = source_root / dir_name
        tool_dir.mkdir(parents=True, exist_ok=True)
        if plugin_meta is not None:
            (tool_dir / "plugin.yaml").write_text(
                yaml.safe_dump(plugin_meta, sort_keys=False), encoding="utf-8"
            )
        (tool_dir / entrypoint_name).write_text("print('ok')\n", encoding="utf-8")
        return tool_dir

    @staticmethod
    def _make_r_tool(
        source_root: Path,
        dir_name: str,
        plugin_meta: dict | None = None,
        entrypoint_name: str = "runner.R",
    ) -> Path:
        tool_dir = source_root / dir_name
        tool_dir.mkdir(parents=True, exist_ok=True)
        if plugin_meta is not None:
            (tool_dir / "plugin.yaml").write_text(
                yaml.safe_dump(plugin_meta, sort_keys=False), encoding="utf-8"
            )
        (tool_dir / entrypoint_name).write_text("cat('ok')\n", encoding="utf-8")
        return tool_dir

    def test_scan_empty_source_root_returns_empty_groups(self, tmp_path: Path):
        grouped = WorkspaceToolService(tmp_path).scan_import_candidates()
        assert grouped["python"] == []
        assert grouped["r"] == []

    def test_scan_discovers_python_tool_with_plugin_yaml(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        self._make_python_tool(source_root, "py_stats", {
            "name": "py-stats",
            "version": "0.1.0",
            "type": "tool",
            "language": "python",
            "description": "Python stats tool",
            "entry": "main.py",
        })

        grouped = WorkspaceToolService(tmp_path).scan_import_candidates()

        assert len(grouped["python"]) == 1
        candidate = grouped["python"][0]
        assert candidate["id"] == "py-stats"
        assert candidate["language"] == "python"
        assert candidate["importable"] is True

    def test_scan_discovers_r_tool_with_r_prefix_inference(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        self._make_r_tool(source_root, "r_survival", {
            "name": "r-survival",
            "version": "0.1.0",
            "type": "tool",
            "description": "R survival analysis",
        })

        grouped = WorkspaceToolService(tmp_path).scan_import_candidates()

        assert len(grouped["r"]) == 1
        candidate = grouped["r"][0]
        assert candidate["id"] == "r-survival"
        assert candidate["language"] == "r"
        assert candidate["importable"] is True

    def test_scan_infers_python_when_language_metadata_missing(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        self._make_python_tool(source_root, "mystery_tool", {
            "name": "mystery-tool",
            "version": "0.1.0",
            "type": "tool",
            # no language field
            "entry": "main.py",
        })

        grouped = WorkspaceToolService(tmp_path).scan_import_candidates()

        assert len(grouped["python"]) == 1
        assert grouped["python"][0]["language"] == "python"
        assert any("inferred" in w for w in grouped["python"][0]["warnings"])

    def test_scan_infers_r_from_directory_prefix_when_language_missing(
        self, tmp_path: Path
    ):
        source_root = tmp_path / "plugins" / "tools"
        self._make_r_tool(source_root, "r_kaplan", {
            "name": "r-kaplan",
            "version": "0.1.0",
            "type": "tool",
            # no language field
        })

        grouped = WorkspaceToolService(tmp_path).scan_import_candidates()

        assert len(grouped["r"]) == 1
        assert grouped["r"][0]["language"] == "r"
        assert any("inferred" in w for w in grouped["r"][0]["warnings"])

    def test_scan_falls_back_to_directory_name_when_no_metadata(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        self._make_python_tool(source_root, "plain_tool")

        grouped = WorkspaceToolService(tmp_path).scan_import_candidates()

        assert len(grouped["python"]) == 1
        candidate = grouped["python"][0]
        assert candidate["name"] == "plain_tool"
        assert any("metadata missing" in w for w in candidate["warnings"])

    def test_scan_skips_non_directories(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        source_root.mkdir(parents=True)
        (source_root / "readme.txt").write_text("not a tool", encoding="utf-8")

        grouped = WorkspaceToolService(tmp_path).scan_import_candidates()
        assert grouped["python"] == []
        assert grouped["r"] == []

    def test_scan_skips_pycache(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        source_root.mkdir(parents=True)
        pycache = source_root / "__pycache__"
        pycache.mkdir()
        (pycache / "main.py").write_text("print('ok')\n", encoding="utf-8")

        grouped = WorkspaceToolService(tmp_path).scan_import_candidates()
        assert grouped["python"] == []
        assert grouped["r"] == []

    def test_scan_filters_by_language(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        self._make_python_tool(source_root, "py_tool", {
            "name": "py-tool", "version": "0.1.0", "type": "tool",
            "language": "python", "entry": "main.py",
        })
        self._make_r_tool(source_root, "r_tool", {
            "name": "r-tool", "version": "0.1.0", "type": "tool",
            "language": "r",
        })

        python_only = WorkspaceToolService(tmp_path).scan_import_candidates("python")
        assert len(python_only["python"]) == 1
        assert "r" not in python_only

    def test_scan_assigns_sequential_indices(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        self._make_python_tool(source_root, "alpha", {
            "name": "alpha", "version": "0.1.0", "type": "tool",
            "language": "python", "entry": "main.py",
        })
        self._make_python_tool(source_root, "beta", {
            "name": "beta", "version": "0.1.0", "type": "tool",
            "language": "python", "entry": "main.py",
        })

        grouped = WorkspaceToolService(tmp_path).scan_import_candidates()
        indices = [c["index"] for c in grouped["python"]]
        assert indices == [1, 2]

    def test_scan_marks_missing_entrypoint_as_invalid(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        tool_dir = source_root / "bad_entry"
        tool_dir.mkdir(parents=True)
        (tool_dir / "plugin.yaml").write_text(
            yaml.safe_dump({
                "name": "bad-entry",
                "version": "0.1.0",
                "type": "tool",
                "language": "python",
                "entry": "nonexistent.py",
            }, sort_keys=False),
            encoding="utf-8",
        )
        # no actual .py file created

        grouped = WorkspaceToolService(tmp_path).scan_import_candidates()
        assert len(grouped["python"]) == 1
        assert grouped["python"][0]["status"] == "invalid"
        assert grouped["python"][0]["importable"] is False

    def test_scan_accepts_tool_yaml_over_plugin_yaml(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        tool_dir = source_root / "dual_meta"
        tool_dir.mkdir(parents=True)
        (tool_dir / "tool.yaml").write_text(
            yaml.safe_dump({
                "id": "dual-meta",
                "language": "python",
                "name": "Dual Meta Tool",
                "description": "Has tool.yaml",
                "entrypoint": "main.py",
                "dependencies": [],
                "inputs": [],
                "outputs": [],
                "version": "1.0.0",
            }, sort_keys=False),
            encoding="utf-8",
        )
        (tool_dir / "plugin.yaml").write_text(
            yaml.safe_dump({
                "name": "different-name",
                "version": "9.9.9",
                "type": "tool",
                "language": "python",
            }, sort_keys=False),
            encoding="utf-8",
        )
        (tool_dir / "main.py").write_text("print('ok')\n", encoding="utf-8")

        grouped = WorkspaceToolService(tmp_path).scan_import_candidates()
        assert len(grouped["python"]) == 1
        candidate = grouped["python"][0]
        assert candidate["id"] == "dual-meta"
        assert candidate["name"] == "Dual Meta Tool"
        # Should NOT have the plugin.yaml fallback warning
        assert not any("workspace tool.yaml missing" in w for w in candidate["warnings"])


# ═══ Import Scanned Tools ═══


class TestImportScannedTools:
    """Exercises ``import_scanned_tools`` with synthetic candidates."""

    @staticmethod
    def _setup_source_tools(source_root: Path):
        """Create two importable source tools (one Python, one R)."""
        py_dir = source_root / "py_heatmap"
        py_dir.mkdir(parents=True)
        (py_dir / "plugin.yaml").write_text(
            yaml.safe_dump({
                "name": "py-heatmap",
                "version": "1.0.0",
                "type": "tool",
                "language": "python",
                "description": "Heatmap generator",
                "entry": "main.py",
            }, sort_keys=False),
            encoding="utf-8",
        )
        (py_dir / "main.py").write_text("print('heatmap')\n", encoding="utf-8")

        r_dir = source_root / "r_umap"
        r_dir.mkdir()
        (r_dir / "plugin.yaml").write_text(
            yaml.safe_dump({
                "name": "r-umap",
                "version": "1.0.0",
                "type": "tool",
                "language": "r",
                "description": "UMAP in R",
                "entry": "runner.R",
            }, sort_keys=False),
            encoding="utf-8",
        )
        (r_dir / "runner.R").write_text("cat('umap')\n", encoding="utf-8")

    def test_import_by_index(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        self._setup_source_tools(source_root)

        service = WorkspaceToolService(tmp_path)
        result = service.import_scanned_tools("trial-1", ["1"])

        assert result["status"] == "imported"
        assert len(result["imported"]) == 1
        assert result["imported"][0]["tool"]["id"] == "py-heatmap"

    def test_import_by_slug(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        self._setup_source_tools(source_root)

        service = WorkspaceToolService(tmp_path)
        result = service.import_scanned_tools("trial-1", ["r-umap"])

        assert result["status"] == "imported"
        assert result["imported"][0]["tool"]["language"] == "r"

    def test_import_by_language_prefixed_slug(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        self._setup_source_tools(source_root)

        service = WorkspaceToolService(tmp_path)
        result = service.import_scanned_tools("trial-1", ["python/py-heatmap"])

        assert result["status"] == "imported"
        assert result["imported"][0]["tool"]["id"] == "py-heatmap"

    def test_import_both_languages(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        self._setup_source_tools(source_root)

        service = WorkspaceToolService(tmp_path)
        result = service.import_scanned_tools("trial-1", ["1", "2"])

        assert result["status"] == "imported"
        assert len(result["imported"]) == 2
        imported_ids = {item["tool"]["id"] for item in result["imported"]}
        assert imported_ids == {"py-heatmap", "r-umap"}

    def test_import_no_candidates_returns_no_candidates(self, tmp_path: Path):
        service = WorkspaceToolService(tmp_path)
        result = service.import_scanned_tools("trial-1", ["1"])

        assert result["status"] == "no_candidates"
        assert result["imported"] == []
        assert result["errors"] == []

    def test_import_invalid_selection_raises(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        self._setup_source_tools(source_root)

        service = WorkspaceToolService(tmp_path)
        with pytest.raises(ToolCandidateError, match="Unknown scanned tool selection"):
            service.import_scanned_tools("trial-1", ["999"])

    def test_import_empty_selection_raises(self, tmp_path: Path):
        service = WorkspaceToolService(tmp_path)
        with pytest.raises(ToolCandidateError, match="Select one or more"):
            service.import_scanned_tools("trial-1", [])

    def test_import_creates_manifest_in_workspace(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        py_dir = source_root / "my_tool"
        py_dir.mkdir(parents=True)
        (py_dir / "plugin.yaml").write_text(
            yaml.safe_dump({
                "name": "my-tool",
                "version": "2.0.0",
                "type": "tool",
                "language": "python",
                "description": "My tool",
                "entry": "main.py",
            }, sort_keys=False),
            encoding="utf-8",
        )
        (py_dir / "main.py").write_text("print('ok')\n", encoding="utf-8")

        service = WorkspaceToolService(tmp_path)
        result = service.import_scanned_tools("trial-1", ["1"])

        assert result["status"] == "imported"
        workspace_tool_dir = (
            tmp_path / "workspaces" / "trial-1" / "tools" / "python" / "my-tool"
        )
        assert workspace_tool_dir.is_dir()
        assert (workspace_tool_dir / "tool.yaml").is_file()
        assert (workspace_tool_dir / "main.py").is_file()

    def test_import_writes_normalized_manifest(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        py_dir = source_root / "norm_tool"
        py_dir.mkdir(parents=True)
        (py_dir / "plugin.yaml").write_text(
            yaml.safe_dump({
                "name": "norm-tool",
                "version": "3.0.0",
                "type": "tool",
                "language": "python",
                "description": "Normalization test",
                "entry": "main.py",
            }, sort_keys=False),
            encoding="utf-8",
        )
        (py_dir / "main.py").write_text("print('ok')\n", encoding="utf-8")

        service = WorkspaceToolService(tmp_path)
        service.import_scanned_tools("trial-1", ["1"])

        manifest_path = (
            tmp_path / "workspaces" / "trial-1" / "tools" / "python"
            / "norm-tool" / "tool.yaml"
        )
        manifest_data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        assert manifest_data["id"] == "norm-tool"
        assert manifest_data["language"] == "python"
        assert manifest_data["version"] == "3.0.0"
        assert isinstance(manifest_data["dependencies"], list)
        assert isinstance(manifest_data["inputs"], list)
        assert isinstance(manifest_data["outputs"], list)

    def test_import_existing_tool_without_overwrite_returns_exists(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        self._setup_source_tools(source_root)

        service = WorkspaceToolService(tmp_path)
        first = service.import_scanned_tools("trial-1", ["1"])
        second = service.import_scanned_tools("trial-1", ["1"])

        assert first["status"] == "imported"
        assert second["status"] == "imported"
        assert second["imported"][0]["status"] == "exists"

    def test_import_overwrite_replaces_existing(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        self._setup_source_tools(source_root)

        service = WorkspaceToolService(tmp_path)
        service.import_scanned_tools("trial-1", ["1"])
        result = service.import_scanned_tools("trial-1", ["1"], overwrite=True)

        assert result["status"] == "imported"
        assert result["imported"][0]["status"] == "imported"

    def test_import_partial_when_one_candidate_invalid(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        # Valid Python tool
        py_dir = source_root / "py_good"
        py_dir.mkdir(parents=True)
        (py_dir / "plugin.yaml").write_text(
            yaml.safe_dump({
                "name": "py-good",
                "version": "0.1.0",
                "type": "tool",
                "language": "python",
                "entry": "main.py",
            }, sort_keys=False),
            encoding="utf-8",
        )
        (py_dir / "main.py").write_text("print('ok')\n", encoding="utf-8")
        # Invalid R tool (entrypoint missing on disk)
        r_dir = source_root / "r_bad"
        r_dir.mkdir()
        (r_dir / "plugin.yaml").write_text(
            yaml.safe_dump({
                "name": "r-bad",
                "version": "0.1.0",
                "type": "tool",
                "language": "r",
                "description": "Bad R tool",
                "entry": "missing.R",
            }, sort_keys=False),
            encoding="utf-8",
        )
        # No runner.R created

        service = WorkspaceToolService(tmp_path)
        result = service.import_scanned_tools("trial-1", ["1", "2"])

        assert result["status"] == "partial"
        assert len(result["imported"]) == 1
        assert result["imported"][0]["tool"]["id"] == "py-good"
        assert len(result["errors"]) == 1
        assert result["errors"][0]["language"] == "r"

    def test_import_deduplicates_selections(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        self._setup_source_tools(source_root)

        service = WorkspaceToolService(tmp_path)
        result = service.import_scanned_tools("trial-1", ["1", "1", "1"])

        assert result["status"] == "imported"
        assert len(result["imported"]) == 1

    def test_import_r_tool_creates_correct_directory_structure(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        r_dir = source_root / "r_kaplan"
        r_dir.mkdir(parents=True)
        (r_dir / "plugin.yaml").write_text(
            yaml.safe_dump({
                "name": "r-kaplan",
                "version": "0.1.0",
                "type": "tool",
                "language": "r",
                "description": "Kaplan-Meier",
                "entry": "runner.R",
            }, sort_keys=False),
            encoding="utf-8",
        )
        (r_dir / "runner.R").write_text("cat('km')\n", encoding="utf-8")

        service = WorkspaceToolService(tmp_path)
        result = service.import_scanned_tools("trial-1", ["1"])

        assert result["status"] == "imported"
        r_tool_dir = (
            tmp_path / "workspaces" / "trial-1" / "tools" / "r" / "r-kaplan"
        )
        assert r_tool_dir.is_dir()
        assert (r_tool_dir / "runner.R").is_file()
        assert (r_tool_dir / "tool.yaml").is_file()
        manifest_data = yaml.safe_load(
            (r_tool_dir / "tool.yaml").read_text(encoding="utf-8")
        )
        assert manifest_data["language"] == "r"


# ═══ List / Show Tools ═══


class TestListShowTools:
    """Tests for ``list_tools`` and ``show_tool`` after import."""

    def test_list_returns_imported_tools_grouped_by_language(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        py_dir = source_root / "py_tool"
        py_dir.mkdir(parents=True)
        (py_dir / "plugin.yaml").write_text(
            yaml.safe_dump({
                "name": "py-tool", "version": "0.1.0", "type": "tool",
                "language": "python", "entry": "main.py",
            }, sort_keys=False),
            encoding="utf-8",
        )
        (py_dir / "main.py").write_text("print('ok')\n", encoding="utf-8")
        r_dir = source_root / "r_tool"
        r_dir.mkdir()
        (r_dir / "plugin.yaml").write_text(
            yaml.safe_dump({
                "name": "r-tool", "version": "0.1.0", "type": "tool",
                "language": "r", "entry": "runner.R",
            }, sort_keys=False),
            encoding="utf-8",
        )
        (r_dir / "runner.R").write_text("cat('ok')\n", encoding="utf-8")

        service = WorkspaceToolService(tmp_path)
        service.import_scanned_tools("trial-1", ["1", "2"])

        grouped = service.list_tools("trial-1")
        assert [t["id"] for t in grouped["python"]] == ["py-tool"]
        assert [t["id"] for t in grouped["r"]] == ["r-tool"]

    def test_show_tool_returns_full_details(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        py_dir = source_root / "detail_tool"
        py_dir.mkdir(parents=True)
        (py_dir / "plugin.yaml").write_text(
            yaml.safe_dump({
                "name": "detail-tool",
                "version": "2.0.0",
                "type": "tool",
                "language": "python",
                "description": "Detailed tool",
                "entry": "main.py",
            }, sort_keys=False),
            encoding="utf-8",
        )
        (py_dir / "main.py").write_text("print('ok')\n", encoding="utf-8")

        service = WorkspaceToolService(tmp_path)
        service.import_scanned_tools("trial-1", ["1"])

        shown = service.show_tool("trial-1", "python", "detail-tool")
        assert shown["id"] == "detail-tool"
        assert shown["language"] == "python"
        assert shown["version"] == "2.0.0"
        assert shown["description"] == "Detailed tool"
        assert shown["entrypoint"] == "main.py"
        assert "path" in shown
        assert "entrypoint_path" in shown
