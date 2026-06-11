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
from . import style as style_mod
from . import export as export_mod
from . import check as check_mod
from . import layout as layout_mod
from . import qa as qa_mod

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
    "style": ["style", "journal", "nature", "science", "ieee", "字体", "font", "样式", "cjk"],
    "export": ["export", "save", "pdf", "svg", "png", "导出", "保存"],
    "check": ["check", "audit", "compliance", "合规", "检查"],
    "layout": ["layout", "label", "panel", "align", "标签", "对齐", "子图"],
    "qa": ["qa", "preview", "visual", "review", "预览", "自检", "视觉"],
    "plot": ["plot", "chart", "figure", "画图", "图表", "柱状图", "散点图",
             "折线图", "箱线图", "热力图", "直方图", "bar", "scatter",
             "line", "box", "heatmap", "histogram", "violin", "可视化"],
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
    cat_cols = [c for c, m in columns.items()
                if m.get("type") in ("categorical", "boolean", "ordinal")]
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
        suggestions.append(
            f"Scatter + regression (x={cont_cols[0]}, y={cont_cols[1]})"
        )

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
        suggestions = profile_info.get("suggestions", [
            "See references/chart_selection.md for decision framework"
        ])

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
    params = params or {}
    journal: str = params.get("journal", "general")
    lang: str = params.get("lang", "en")
    group_cols: list[str] | None = params.get("group_cols")
    fig = params.get("fig")
    basename: str | None = params.get("basename")
    formats: list[str] | None = params.get("formats")
    dpi: int = params.get("dpi", 300)

    result: dict[str, Any] = {"task": task, "steps": {}}

    # ------------------------------------------------------------------
    # Step 0 — Extract intent
    # ------------------------------------------------------------------
    intents = _extract_intent(task)
    result["intents"] = sorted(intents)
    result["steps"]["step_0_intent"] = {
        "intents": sorted(intents),
        "description": "Parsed task intent to decide workflow emphasis",
    }

    # ------------------------------------------------------------------
    # Step 1 — Data profiling (EDA)
    # ------------------------------------------------------------------
    profile_info: dict | None = None
    if data_path:
        try:
            profile_info = profile_mod.profile_data(
                data_path, group_cols=group_cols
            )
            report_text = profile_mod.render_report(profile_info)
            result["steps"]["step_1_profile"] = {
                "status": "success",
                "source": profile_info.get("source"),
                "shape": f"{profile_info['n_rows']} x {profile_info['n_cols']}",
                "n_warnings": len(profile_info.get("warnings", [])),
                "report": report_text,
            }
        except Exception as exc:
            result["steps"]["step_1_profile"] = {
                "status": "error",
                "error": str(exc),
            }
    else:
        result["steps"]["step_1_profile"] = {
            "status": "skipped",
            "reason": "No data_path provided",
        }

    # ------------------------------------------------------------------
    # Step 2 — Chart type recommendation
    # ------------------------------------------------------------------
    if profile_info:
        chart_suggestions = _recommend_chart(profile_info)
        result["steps"]["step_2_chart_select"] = {
            "recommendations": chart_suggestions,
            "full_reference": "See references/chart_selection.md",
        }
    else:
        result["steps"]["step_2_chart_select"] = {
            "status": "skipped",
            "reason": "No profile data available",
        }

    # ------------------------------------------------------------------
    # Step 3 — Journal specification constraints
    # ------------------------------------------------------------------
    spec = _journal_spec_summary(journal)
    result["steps"]["step_3_journal_spec"] = {
        "journal": journal,
        "constraints": spec,
        "full_reference": _read_reference("journal_specs.md"),
    }

    # ------------------------------------------------------------------
    # Step 4 — Style setup
    # ------------------------------------------------------------------
    try:
        style_info = style_mod.setup_style(journal=journal, lang=lang)
        result["steps"]["step_4_style"] = {
            "status": "success",
            "info": style_info,
        }
    except Exception as exc:
        result["steps"]["step_4_style"] = {
            "status": "error",
            "error": str(exc),
        }

    # ------------------------------------------------------------------
    # Step 5 — Plot recipe guidance
    # ------------------------------------------------------------------
    result["steps"]["step_5_plot_recipe"] = {
        "description": "Plot recipe guidance from references",
        "recipes": _read_reference("plot_recipes.md"),
        "pitfalls": _read_reference("viz_pitfalls.md"),
    }

    # ------------------------------------------------------------------
    # Step 6 — Layout QA (if a figure object is available)
    # ------------------------------------------------------------------
    if fig is not None:
        try:
            qa_issues = qa_mod.audit_layout(fig)
            qa_report = qa_mod.format_audit_report(qa_issues)
            result["steps"]["step_6_qa"] = {
                "status": "success",
                "report": qa_report,
            }
        except Exception as exc:
            result["steps"]["step_6_qa"] = {
                "status": "error",
                "error": str(exc),
            }

        # Also add panel labels if multi-panel
        try:
            placed = layout_mod.add_panel_labels(fig, style=journal)
            result["steps"]["step_6_layout_labels"] = {
                "labels_placed": [t.get_text() for t in placed],
                "count": len(placed),
            }
        except Exception:
            pass  # single-panel figures don't need labels
    else:
        result["steps"]["step_6_qa"] = {
            "status": "skipped",
            "reason": "No figure object provided",
        }

    # ------------------------------------------------------------------
    # Step 7 — Export (if a figure object is available)
    # ------------------------------------------------------------------
    if fig is not None and basename:
        try:
            saved_paths = export_mod.export_figure(
                fig,
                basename=basename,
                formats=formats,
                dpi=dpi,
            )
            result["steps"]["step_7_export"] = {
                "status": "success",
                "paths": saved_paths,
            }
        except Exception as exc:
            result["steps"]["step_7_export"] = {
                "status": "error",
                "error": str(exc),
            }
    else:
        result["steps"]["step_7_export"] = {
            "status": "skipped",
            "reason": "No figure object or basename provided",
        }

    # ------------------------------------------------------------------
    # Final summary
    # ------------------------------------------------------------------
    result["status"] = "success"
    result["output"] = (
        "Workflow complete. Review each step's output above. "
        "If step 6 QA reported FAIL issues, fix them before exporting. "
        "See references/visual_review.md for the AI visual review loop."
    )
    return result


# ---------------------------------------------------------------------------
# Action dispatcher
# ---------------------------------------------------------------------------

# Mapping from action id to (submodule, function name)
_ACTION_MAP: dict[str, tuple[Any, str]] = {
    "figure-profile.profile":     (profile_mod, "execute"),
    "figure-style.setup":         (style_mod,   "execute"),
    "figure-style.list-fonts":    (style_mod,   "execute"),
    "figure-export.export":       (export_mod,  "execute"),
    "figure-check.audit":         (check_mod,   "execute"),
    "figure-layout.labels":       (layout_mod,  "execute"),
    "figure-layout.finalize":     (layout_mod,  "execute"),
    "figure-qa.audit":            (qa_mod,      "execute"),
    "figure-qa.preview":          (qa_mod,      "execute"),
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
