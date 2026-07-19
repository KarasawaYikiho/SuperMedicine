"""Scientific Figure Advisor — workflow orchestrator + action dispatcher.

Unified entry-point for the ``figure`` plugin.  Provides:

* ``execute(action, params, context)`` — dispatcher that routes individual
  actions (profile, style, export, check, layout, qa) to their respective
  sub-modules.
* ``execute_figure_workflow(task, data_path, params)`` — full 8-step pipeline
  that walks through understand → profile → select → spec → style → plot →
  check → export.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Sub-module imports
# ---------------------------------------------------------------------------
from . import profile as profile_mod
from . import export as export_mod
from . import audit as check_mod
from . import audit as qa_mod
from . import presentation as layout_mod
from . import presentation as style_mod

# ---------------------------------------------------------------------------
# Path to reference documents bundled with the plugin
# ---------------------------------------------------------------------------
_REFERENCES_DIR = Path(__file__).resolve().parent / "references"


def _read_reference(filename: str) -> str:
    """Return the text content of a bundled reference markdown file."""
    path = _REFERENCES_DIR / filename
    if not path.exists():
        return f"[reference file not found: {filename}]"
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Intent extraction helpers
# ---------------------------------------------------------------------------

# Maps lightweight keywords to a canonical "intent" label used by the
# workflow to decide which steps need emphasis.
_INTENT_KEYWORDS: dict[str, list[str]] = {
    "profile": ["profile", "eda", "explore", "profiling", "数据探索", "数据概况"],
    "style": [
        "style",
        "journal",
        "nature",
        "science",
        "ieee",
        "字体",
        "font",
        "样式",
        "cjk",
    ],
    "export": ["export", "save", "pdf", "svg", "png", "导出", "保存"],
    "check": ["check", "audit", "compliance", "合规", "检查"],
    "layout": ["layout", "label", "panel", "align", "标签", "对齐", "子图"],
    "qa": ["qa", "preview", "visual", "review", "预览", "自检", "视觉"],
    "plot": [
        "plot",
        "chart",
        "figure",
        "画图",
        "图表",
        "柱状图",
        "散点图",
        "折线图",
        "箱线图",
        "热力图",
        "直方图",
        "bar",
        "scatter",
        "line",
        "box",
        "heatmap",
        "histogram",
        "violin",
        "可视化",
    ],
}


def _extract_intent(task: str) -> set[str]:
    """Return a set of intent labels inferred from the free-text *task*."""
    lowered = task.lower()
    intents: set[str] = set()
    for label, keywords in _INTENT_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            intents.add(label)
    # If nothing matched, assume the user wants the full workflow.
    if not intents:
        intents = {"full_workflow"}
    return intents


# ---------------------------------------------------------------------------
# Chart-type recommendation (Step 2)
# ---------------------------------------------------------------------------


def _recommend_chart(profile_info: dict) -> list[str]:
    """Translate data profile into concrete chart-type recommendations.

    Uses the column-type distribution and the preliminary suggestions from
    the profiler, augmented with scale-aware heuristics.
    """
    suggestions: list[str] = []

    columns = profile_info.get("columns", {})
    cont_cols = [c for c, m in columns.items() if m.get("type") == "continuous"]
    cat_cols = [
        c
        for c, m in columns.items()
        if m.get("type") in ("categorical", "boolean", "ordinal")
    ]
    dt_cols = [c for c, m in columns.items() if m.get("type") == "datetime"]

    # Time-series
    if dt_cols and cont_cols:
        suggestions.append(
            f"Time-series: line chart with error band "
            f"(x={dt_cols[0]}, y={cont_cols[0]})"
        )

    # Categorical vs continuous
    if cat_cols and cont_cols:
        group_summary = profile_info.get("group_summary")
        if group_summary and group_summary.get("small_groups_flag"):
            suggestions.append(
                "Small groups (n<10): box/violin + stripplot overlay; "
                "avoid mean-only bar chart"
            )
        else:
            suggestions.append(
                "Categorical vs continuous: box/violin or bar with error bars"
            )

    # Two continuous → scatter
    if len(cont_cols) >= 2:
        suggestions.append(f"Scatter + regression (x={cont_cols[0]}, y={cont_cols[1]})")

    # Many continuous → heatmap / pairplot
    if len(cont_cols) >= 3:
        suggestions.append(
            f"Correlation heatmap or pairplot ({', '.join(cont_cols[:5])})"
        )

    # Single continuous → distribution
    if len(cont_cols) == 1 and not cat_cols and not dt_cols:
        suggestions.append(f"Histogram / KDE for {cont_cols[0]}")

    # Fall back to profiler suggestions
    if not suggestions:
        suggestions = profile_info.get(
            "suggestions", ["See references/chart_selection.md for decision framework"]
        )

    return suggestions


# ---------------------------------------------------------------------------
# Journal specification summary (Step 3)
# ---------------------------------------------------------------------------

_JOURNAL_SPECS: dict[str, dict[str, str]] = {
    "nature": {
        "single_col": "3.5 in (89 mm)",
        "double_col": "7.2 in (183 mm)",
        "font": "Helvetica / Arial, 5-7 pt",
        "dpi": ">= 300",
        "vector": "EPS / PDF",
        "panel_labels": "a, b, c (lowercase bold)",
    },
    "science": {
        "single_col": "2.2 in (55 mm)",
        "double_col": "7.2 in (183 mm)",
        "font": "Helvetica / Arial, 5-7 pt",
        "dpi": ">= 300",
        "vector": "PDF / EPS",
        "panel_labels": "A, B, C (uppercase bold)",
    },
    "ieee": {
        "single_col": "3.5 in (88.9 mm)",
        "double_col": "7.16 in (181.9 mm)",
        "font": "Times New Roman, 8-10 pt",
        "dpi": "600 (line art)",
        "vector": "PDF / EPS",
        "panel_labels": "(a), (b), (c)",
    },
    "general": {
        "single_col": "5.0 in",
        "double_col": "7.0 in",
        "font": "Arial, 9 pt",
        "dpi": ">= 300",
        "vector": "PDF / SVG",
        "panel_labels": "a, b, c",
    },
}


def _journal_spec_summary(journal: str) -> dict[str, str]:
    """Return a dict of key requirements for *journal*."""
    return _JOURNAL_SPECS.get(journal, _JOURNAL_SPECS["general"])


# ---------------------------------------------------------------------------
# Full 8-step workflow
# ---------------------------------------------------------------------------


class _FigureWorkflow:
    """Stateful orchestration of the documented eight figure workflow steps."""

    def __init__(self, task: str, data_path: str | None, params: dict[str, Any]):
        self.task = task
        self.data_path = data_path
        self.params = params
        self.journal: str = params.get("journal", "general")
        self.lang: str = params.get("lang", "en")
        self.fig = params.get("fig")
        self.result: dict[str, Any] = {"task": task, "steps": {}}

    @property
    def steps(self) -> dict[str, Any]:
        return self.result["steps"]

    def run(self) -> dict[str, Any]:
        intents = sorted(_extract_intent(self.task))
        self.result["intents"] = intents
        self.steps["step_0_intent"] = {
            "intents": intents,
            "description": "Parsed task intent to decide workflow emphasis",
        }
        profile_info = self._profile_data()
        self._add_guidance(profile_info)
        self._audit_layout()
        self._export_figure()
        self.result["status"] = "success"
        self.result["output"] = (
            "Workflow complete. Review each step's output above. "
            "If step 6 QA reported FAIL issues, fix them before exporting. "
            "See references/visual_review.md for the AI visual review loop."
        )
        return self.result

    def _profile_data(self) -> dict[str, Any] | None:
        if not self.data_path:
            self.steps["step_1_profile"] = {
                "status": "skipped",
                "reason": "No data_path provided",
            }
            return None
        try:
            profile_info = profile_mod.profile_data(
                self.data_path, group_cols=self.params.get("group_cols")
            )
            self.steps["step_1_profile"] = {
                "status": "success",
                "source": profile_info.get("source"),
                "shape": f"{profile_info['n_rows']} x {profile_info['n_cols']}",
                "n_warnings": len(profile_info.get("warnings", [])),
                "report": profile_mod.render_report(profile_info),
            }
            return profile_info
        except Exception as exc:
            self.steps["step_1_profile"] = {"status": "error", "error": str(exc)}
            return None

    def _add_guidance(self, profile_info: dict[str, Any] | None) -> None:
        self.steps["step_2_chart_select"] = (
            {
                "recommendations": _recommend_chart(profile_info),
                "full_reference": "See references/chart_selection.md",
            }
            if profile_info
            else {"status": "skipped", "reason": "No profile data available"}
        )
        self.steps["step_3_journal_spec"] = {
            "journal": self.journal,
            "constraints": _journal_spec_summary(self.journal),
            "full_reference": _read_reference("journal_specs.md"),
        }
        try:
            self.steps["step_4_style"] = {
                "status": "success",
                "info": style_mod.setup_style(journal=self.journal, lang=self.lang),
            }
        except Exception as exc:
            self.steps["step_4_style"] = {"status": "error", "error": str(exc)}
        self.steps["step_5_plot_recipe"] = {
            "description": "Plot recipe guidance from references",
            "recipes": _read_reference("plot_recipes.md"),
            "pitfalls": _read_reference("viz_pitfalls.md"),
        }

    def _audit_layout(self) -> None:
        if self.fig is None:
            self.steps["step_6_qa"] = {
                "status": "skipped",
                "reason": "No figure object provided",
            }
            return
        try:
            issues = qa_mod.audit_layout(self.fig)
            self.steps["step_6_qa"] = {
                "status": "success",
                "report": qa_mod.format_audit_report(issues),
            }
        except Exception as exc:
            self.steps["step_6_qa"] = {"status": "error", "error": str(exc)}
        try:
            placed = layout_mod.add_panel_labels(self.fig, style=self.journal)
            self.steps["step_6_layout_labels"] = {
                "labels_placed": [label.get_text() for label in placed],
                "count": len(placed),
            }
        except Exception as exc:
            self.steps["step_6_layout_labels"] = {
                "status": "error",
                "error": str(exc),
            }

    def _export_figure(self) -> None:
        basename = self.params.get("basename")
        if self.fig is None or not basename:
            self.steps["step_7_export"] = {
                "status": "skipped",
                "reason": "No figure object or basename provided",
            }
            return
        try:
            paths = export_mod.export_figure(
                self.fig,
                basename=basename,
                formats=self.params.get("formats"),
                dpi=self.params.get("dpi", 300),
            )
            self.steps["step_7_export"] = {"status": "success", "paths": paths}
        except Exception as exc:
            self.steps["step_7_export"] = {"status": "error", "error": str(exc)}


def execute_figure_workflow(
    task: str,
    data_path: str | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute the full 8-step figure workflow.

    Parameters
    ----------
    task : str
        Free-text description of the figure task.
    data_path : str | None
        Path to a CSV / Excel data file.  May be ``None`` when the user is
        only asking for style / export / QA help.
    params : dict | None
        Extra keyword arguments.  Recognised keys:
        - ``journal``: target journal preset (default ``"general"``).
        - ``lang``: ``"en"`` or ``"zh"`` (default ``"en"``).
        - ``group_cols``: list of column names for grouped profiling.
        - ``fig``: an existing matplotlib ``Figure`` object for steps 6-7.
        - ``basename``: output path prefix for export.
        - ``formats``: list of export format extensions.
        - ``dpi``: raster DPI (default 300).
    """
    return _FigureWorkflow(task, data_path, params or {}).run()


# ---------------------------------------------------------------------------
# Action dispatcher
# ---------------------------------------------------------------------------

# Mapping from action id to (submodule, function name)
_ACTION_MAP: dict[str, tuple[Any, str]] = {
    "figure-profile.profile": (profile_mod, "execute"),
    "figure-style.setup": (style_mod, "execute_style"),
    "figure-style.list-fonts": (style_mod, "execute_style"),
    "figure-export.export": (export_mod, "execute"),
    "figure-check.audit": (check_mod, "execute_check"),
    "figure-layout.labels": (layout_mod, "execute_layout"),
    "figure-layout.finalize": (layout_mod, "execute_layout"),
    "figure-qa.audit": (qa_mod, "execute_qa"),
    "figure-qa.preview": (qa_mod, "execute_qa"),
}


def execute(
    action: str,
    params: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute a figure plugin action.

    Parameters
    ----------
    action : str
        One of the action ids declared in ``plugin.yaml``.
    params : dict | None
        Action-specific parameters.
    context : dict | None
        Runtime context (agent_id, permission info, etc.).

    Returns
    -------
    dict
        Standard result dict with ``status``, ``output``, ``error``,
        ``metadata`` keys.
    """
    params = params or {}
    metadata: dict[str, Any] = {
        "resource": "local-figure",
        "not_for_clinical_decision": True,
        "requires_human_review": True,
    }

    try:
        # ---- Full workflow ----
        if action == "figure.workflow":
            task = params.get("task", "")
            data_path = params.get("data_path")
            result = execute_figure_workflow(task, data_path=data_path, params=params)
            return {
                "status": "success",
                "output": result,
                "metadata": metadata,
            }

        # ---- Individual sub-module actions ----
        if action in _ACTION_MAP:
            mod, func_name = _ACTION_MAP[action]
            func = getattr(mod, func_name)
            return func(action=action, params=params, context=context)

        # ---- Unknown action ----
        return {
            "status": "plugin_error",
            "output": None,
            "error": f"Unsupported figure action: {action}",
            "metadata": metadata,
        }

    except Exception as exc:
        return {
            "status": "plugin_error",
            "output": None,
            "error": f"Figure plugin error: {exc}",
            "metadata": metadata,
        }
