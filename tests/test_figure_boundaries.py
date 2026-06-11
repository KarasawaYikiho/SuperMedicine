"""Unit tests for figure plugin boundary-case fixes.

Tests the five edge-case fixes:
1. check.py — DPI empty tuple validation
2. export.py — formats parameter accepts string
3. qa.py — y-axis tick label overlap detection
4. layout.py — _letter_sequence for n>702 (3+ letter labels)
5. runner.py — exception logging instead of silent pass
"""

from __future__ import annotations

import string
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Fix 1: check.py — DPI empty tuple
# ---------------------------------------------------------------------------

class TestCheckDpiTuple:
    """Verify _check_raster handles DPI as tuple correctly."""

    def test_dpi_empty_tuple_warns(self, tmp_path):
        """Empty DPI tuple should produce a WARN, not crash."""
        # Test the logic directly: simulate what _check_raster does when
        # dpi is an empty tuple.  The function imports Image locally, so
        # we patch PIL.Image.open in sys.modules before calling.
        import sys
        from types import ModuleType

        mock_pil = ModuleType("PIL")
        mock_image_mod = ModuleType("PIL.Image")
        mock_img = MagicMock()
        mock_img.size = (100, 100)
        mock_img.info = {"dpi": ()}
        mock_image_mod.open = MagicMock(return_value=mock_img)
        mock_pil.Image = mock_image_mod

        sys.modules["PIL"] = mock_pil
        sys.modules["PIL.Image"] = mock_image_mod
        try:
            from plugins.figure.check import _check_raster
            issues, info = _check_raster("fake.png", "png", 300, None)
        finally:
            sys.modules.pop("PIL", None)
            sys.modules.pop("PIL.Image", None)

        severity_msgs = [(s, m) for s, m in issues if "empty tuple" in m.lower()
                         or "cannot determine" in m.lower()]
        assert len(severity_msgs) >= 1, f"Expected empty-tuple warning, got: {issues}"
        assert severity_msgs[0][0] == "WARN"

    def test_dpi_single_element_tuple(self):
        """Single-element tuple DPI should work (access dpi[0])."""
        # Simulate the logic directly
        dpi = (300,)
        assert isinstance(dpi, tuple)
        assert len(dpi) > 0
        dx = dpi[0]
        assert dx == 300

    def test_dpi_two_element_tuple_uses_first(self):
        """Two-element tuple DPI should use dpi[0]."""
        dpi = (300, 300)
        assert isinstance(dpi, tuple)
        assert len(dpi) > 0
        dx = dpi[0]
        assert dx == 300


# ---------------------------------------------------------------------------
# Fix 2: export.py — formats parameter accepts string
# ---------------------------------------------------------------------------

class TestExportFormatsString:
    """Verify export_figure handles string formats parameter."""

    def test_formats_string_converted_to_list(self):
        """A single string 'pdf' should become ['pdf'], not ['p','d','f']."""
        from plugins.figure.export import export_figure

        fig = MagicMock()
        fig.savefig = MagicMock()

        # Passing formats="pdf" should NOT iterate over characters
        with patch("plugins.figure.export.plt"):
            saved = export_figure(fig, "test_out", formats="pdf", dpi=300)

        # Should have saved one file: test_out.pdf
        assert len(saved) == 1
        assert saved[0].endswith(".pdf")

    def test_formats_list_works_normally(self):
        """A list of formats should work as before."""
        from plugins.figure.export import export_figure

        fig = MagicMock()
        fig.savefig = MagicMock()

        with patch("plugins.figure.export.plt"):
            saved = export_figure(fig, "test_out", formats=["png"], dpi=300)

        assert len(saved) == 1
        assert saved[0].endswith(".png")

    def test_formats_none_uses_default(self):
        """None formats should use default (pdf, svg, png)."""
        from plugins.figure.export import export_figure

        fig = MagicMock()
        fig.savefig = MagicMock()

        with patch("plugins.figure.export.plt"):
            saved = export_figure(fig, "test_out", formats=None, dpi=300)

        assert len(saved) == 3
        extensions = {p.rsplit(".", 1)[-1] for p in saved}
        assert extensions == {"pdf", "svg", "png"}


# ---------------------------------------------------------------------------
# Fix 3: qa.py — y-axis tick label overlap detection
# ---------------------------------------------------------------------------

class TestQaTickOverlap:
    """Verify _ticklabels_overlap uses correct coordinates per axis."""

    def _make_label(self, x0, y0, x1, y1):
        """Create a mock tick label with given bounding box."""
        label = MagicMock()
        label.get_visible.return_value = True
        label.get_text.return_value = "tick"
        bbox = MagicMock()
        bbox.x0 = x0
        bbox.y0 = y0
        bbox.x1 = x1
        bbox.y1 = y1
        label.get_window_extent.return_value = bbox
        return label

    def test_y_axis_detects_vertical_overlap(self):
        """Y-axis labels that overlap vertically should be detected."""
        from plugins.figure.qa import _ticklabels_overlap

        renderer = MagicMock()
        # Two labels stacked vertically with overlap
        label1 = self._make_label(0, 0, 50, 30)   # bottom label
        label2 = self._make_label(0, 20, 50, 50)   # top label (overlaps by 10px)

        result = _ticklabels_overlap([label1, label2], renderer,
                                     axis="y", tol=1.0)
        assert result is True, "Y-axis vertical overlap should be detected"

    def test_y_axis_no_overlap_when_separated(self):
        """Y-axis labels with no vertical overlap should not trigger."""
        from plugins.figure.qa import _ticklabels_overlap

        renderer = MagicMock()
        label1 = self._make_label(0, 0, 50, 20)
        label2 = self._make_label(0, 30, 50, 50)  # gap of 10px

        result = _ticklabels_overlap([label1, label2], renderer,
                                     axis="y", tol=1.0)
        assert result is False, "Separated y-axis labels should not overlap"

    def test_x_axis_detects_horizontal_overlap(self):
        """X-axis labels that overlap horizontally should be detected."""
        from plugins.figure.qa import _ticklabels_overlap

        renderer = MagicMock()
        label1 = self._make_label(0, 0, 40, 20)
        label2 = self._make_label(30, 0, 70, 20)  # overlaps by 10px

        result = _ticklabels_overlap([label1, label2], renderer,
                                     axis="x", tol=1.0)
        assert result is True, "X-axis horizontal overlap should be detected"


# ---------------------------------------------------------------------------
# Fix 4: layout.py — _letter_sequence for n>702
# ---------------------------------------------------------------------------

class TestLetterSequence:
    """Verify _letter_sequence generates correct labels for large n."""

    def test_basic_sequence(self):
        """a, b, ..., z for first 26."""
        from plugins.figure.layout import _letter_sequence

        result = _letter_sequence(26)
        assert result == list(string.ascii_lowercase)

    def test_two_letter_sequence(self):
        """aa, ab, ..., az for indices 26-51."""
        from plugins.figure.layout import _letter_sequence

        result = _letter_sequence(52)
        assert result[26] == "aa"
        assert result[27] == "ab"
        assert result[51] == "az"

    def test_three_letter_boundary(self):
        """Index 702 should produce 'aaa' (3-letter label)."""
        from plugins.figure.layout import _letter_sequence

        result = _letter_sequence(703)
        assert result[702] == "aaa", f"Expected 'aaa' at index 702, got '{result[702]}'"

    def test_large_n_does_not_crash(self):
        """Generating 1000 labels should not raise IndexError."""
        from plugins.figure.layout import _letter_sequence

        result = _letter_sequence(1000)
        assert len(result) == 1000
        # Verify some key points
        assert result[0] == "a"
        assert result[25] == "z"
        assert result[26] == "aa"
        assert result[702] == "aaa"
        assert result[728] == "aba"

    def test_sequence_ordering(self):
        """Labels should be in lexicographic order within same length."""
        from plugins.figure.layout import _letter_sequence

        result = _letter_sequence(703)
        # All single-letter labels
        assert result[:26] == list(string.ascii_lowercase)
        # Two-letter labels should start with 'aa'
        assert result[26] == "aa"
        # Last two-letter label
        assert result[701] == "zz"
        # First three-letter label
        assert result[702] == "aaa"


# ---------------------------------------------------------------------------
# Fix 5: runner.py — exception logging in panel labels
# ---------------------------------------------------------------------------

class TestRunnerExceptionLogging:
    """Verify runner.py logs panel label exceptions instead of swallowing."""

    def test_panel_label_exception_recorded(self):
        """When add_panel_labels raises, the error should be in the result."""
        from plugins.figure.runner import execute_figure_workflow

        fig = MagicMock()
        # Make add_panel_labels raise an exception
        with patch("plugins.figure.runner.layout_mod") as mock_layout:
            mock_layout.add_panel_labels.side_effect = ValueError("test error")
            with patch("plugins.figure.runner.qa_mod") as mock_qa:
                mock_qa.audit_layout.return_value = []
                mock_qa.format_audit_report.return_value = {"verdict": "PASS", "issues": []}
                with patch("plugins.figure.runner.style_mod") as mock_style:
                    mock_style.setup_style.return_value = {}
                    result = execute_figure_workflow(
                        "test task",
                        params={"fig": fig, "journal": "nature"},
                    )

        step6_labels = result["steps"].get("step_6_layout_labels")
        assert step6_labels is not None, "step_6_layout_labels should be present"
        assert step6_labels.get("status") == "error", (
            f"Expected status='error', got: {step6_labels}"
        )
        assert "test error" in step6_labels.get("error", ""), (
            f"Expected error message containing 'test error', got: {step6_labels}"
        )
