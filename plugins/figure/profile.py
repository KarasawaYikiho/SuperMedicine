"""Figure data profiler plugin.

Exploratory data analysis for figure planning.
Reads CSV / Excel / DataFrame, outputs profiling report: column types,
missing rate, sample size, distribution shape, outliers, correlations,
and preliminary chart-type suggestions.
"""

from __future__ import annotations

import io
import math
import os
import sys
import warnings
from typing import Any

import numpy as np
import pandas as pd

# Windows GBK terminal: force UTF-8 for unicode arrows/brackets
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    except Exception:
        pass


# Data type constants
TYPE_CONTINUOUS = "continuous"
TYPE_CATEGORICAL = "categorical"
TYPE_ORDINAL = "ordinal"
TYPE_DATETIME = "datetime"
TYPE_BOOLEAN = "boolean"
TYPE_TEXT = "text"
TYPE_UNKNOWN = "unknown"


def _detect_column_type(s: pd.Series) -> str:
    """Identify column data type. Rules ordered by decreasing reliability."""
    if pd.api.types.is_datetime64_any_dtype(s):
        return TYPE_DATETIME
    if pd.api.types.is_bool_dtype(s):
        return TYPE_BOOLEAN
    if pd.api.types.is_numeric_dtype(s):
        non_null = s.dropna()
        if non_null.isin({0, 1}).all() and non_null.nunique() <= 2:
            return TYPE_BOOLEAN
        if non_null.nunique() <= 7 and (non_null % 1 == 0).all():
            return TYPE_ORDINAL
        return TYPE_CONTINUOUS
    if isinstance(s.dtype, pd.CategoricalDtype):
        if s.cat.ordered:
            return TYPE_ORDINAL
        return TYPE_CATEGORICAL
    if pd.api.types.is_object_dtype(s):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                pd.to_datetime(s.dropna().iloc[:10], errors="raise")
            return TYPE_DATETIME
        except Exception:
            pass
        non_null = s.dropna()
        nunique = non_null.nunique()
        if nunique == 0:
            return TYPE_UNKNOWN
        ratio = nunique / max(len(non_null), 1)
        if nunique <= 30 and ratio < 0.5:
            return TYPE_CATEGORICAL
        return TYPE_TEXT
    return TYPE_UNKNOWN


def _iqr_outliers(s: pd.Series) -> tuple[int, float, float]:
    """IQR method: return (outlier count, lower bound, upper bound)."""
    s = s.dropna()
    if len(s) < 4:
        return 0, float("nan"), float("nan")
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return int(((s < lo) | (s > hi)).sum()), float(lo), float(hi)


def _skewness(s: pd.Series) -> float:
    """Fisher-Pearson skewness coefficient; nan for empty or constant."""
    arr = s.dropna().to_numpy(dtype=float)
    if len(arr) < 3:
        return float("nan")
    mean = arr.mean()
    sd = arr.std(ddof=1)
    if sd == 0:
        return 0.0
    return float(np.mean(((arr - mean) / sd) ** 3))


def _profile_continuous(s: pd.Series) -> dict:
    s = s.dropna()
    if len(s) == 0:
        return {"n": 0}
    out_n, out_lo, out_hi = _iqr_outliers(s)
    skew = _skewness(s)
    return {
        "n": int(len(s)),
        "mean": float(s.mean()),
        "median": float(s.median()),
        "sd": float(s.std(ddof=1)) if len(s) > 1 else 0.0,
        "min": float(s.min()),
        "max": float(s.max()),
        "skewness": skew,
        "skew_label": _label_skew(skew),
        "n_outliers_iqr": out_n,
        "outlier_lo": out_lo,
        "outlier_hi": out_hi,
        "needs_log_axis": _suggest_log_axis(s),
    }


def _label_skew(skew: float) -> str:
    if math.isnan(skew):
        return "unknown"
    a = abs(skew)
    if a < 0.5:
        return "approximately symmetric"
    if a < 1.0:
        return "moderately skewed"
    return "highly skewed"


def _suggest_log_axis(s: pd.Series) -> bool:
    """Spans multiple orders of magnitude + all positive => suggest log axis."""
    s = s.dropna()
    if (s <= 0).any() or len(s) < 5:
        return False
    return s.max() / max(s.min(), 1e-300) > 100


def _profile_categorical(s: pd.Series) -> dict:
    counts = s.dropna().value_counts()
    return {
        "n": int(s.dropna().shape[0]),
        "n_unique": int(counts.shape[0]),
        "categories": [(str(k), int(v)) for k, v in counts.items()],
        "min_group_n": int(counts.min()) if len(counts) > 0 else 0,
        "max_group_n": int(counts.max()) if len(counts) > 0 else 0,
        "small_groups_flag": bool(len(counts) > 0 and counts.min() < 10),
    }


def _correlation_matrix(df: pd.DataFrame, cont_cols: list[str]) -> dict | None:
    """Pearson correlation between continuous columns; None if <2 columns."""
    if len(cont_cols) < 2:
        return None
    sub = df[cont_cols].dropna()
    if sub.shape[0] < 5:
        return None
    corr = sub.corr(method="pearson")
    pairs: list[dict] = []
    cols = corr.columns.tolist()
    for i, a in enumerate(cols):
        for b in cols[i + 1 :]:
            r = float(corr.loc[a, b])
            pairs.append({"a": a, "b": b, "r": r, "magnitude": _label_r(r)})
    pairs.sort(key=lambda x: -abs(x["r"]))
    return {"columns": cols, "matrix": corr.round(3).to_dict(), "pairs_sorted": pairs}


def _label_r(r: float) -> str:
    a = abs(r)
    if a < 0.1:
        return "negligible"
    if a < 0.3:
        return "weak"
    if a < 0.5:
        return "moderate"
    if a < 0.7:
        return "strong"
    return "very strong"


def _group_summary(df: pd.DataFrame, group_cols: list[str]) -> dict | None:
    """Compute grouped sample size distribution."""
    if not group_cols:
        return None
    gs = df.groupby(group_cols, dropna=False).size()
    return {
        "by": group_cols,
        "n_groups": int(gs.shape[0]),
        "min_n_per_group": int(gs.min()),
        "max_n_per_group": int(gs.max()),
        "median_n_per_group": int(gs.median()),
        "small_groups_flag": bool(gs.min() < 10),
        "tiny_groups_flag": bool(gs.min() < 3),
        "per_group_counts": [(str(idx), int(n)) for idx, n in gs.items()][:20],
    }


def _suggest_charts(info: dict) -> list[str]:
    """Translate data features into chart-type suggestions."""
    cols = info["columns"]
    cont = [c for c, m in cols.items() if m["type"] == TYPE_CONTINUOUS]
    cats = [
        c
        for c, m in cols.items()
        if m["type"] in (TYPE_CATEGORICAL, TYPE_BOOLEAN, TYPE_ORDINAL)
    ]
    dt = [c for c, m in cols.items() if m["type"] == TYPE_DATETIME]
    group = info.get("group_summary")
    suggestions: list[str] = []

    if dt and cont:
        suggestions.append(
            f"Time series detected: line chart ({dt[0]} as x-axis, "
            f"{cont[0]}{'/' + cont[1] if len(cont) > 1 else ''} as y-axis) + error band"
        )

    if cats and cont:
        if group and group.get("small_groups_flag"):
            suggestions.append(
                "Categorical vs continuous, small sample (n<10 per group) -> "
                "**box/violin + stripplot overlay raw points**; "
                "**avoid** mean-only bar chart (hides distribution)."
            )
        else:
            suggestions.append(
                "Categorical vs continuous, adequate sample -> box / violin, "
                "or bar chart with error bars (annotate SD/SEM/CI)"
            )

    if len(cont) >= 2:
        if len(cont) == 2:
            suggestions.append(
                f"Two continuous variables {cont[0]} vs {cont[1]} -> scatter (with regression fit + r value)"
            )
        else:
            suggestions.append(
                f">=3 continuous variables -> correlation heatmap ({cont[:5]}) or pairplot"
            )

    if len(cont) >= 1 and not cats and not dt:
        suggestions.append(
            f"Single continuous variable {cont[0]} -> histogram / KDE / boxplot for distribution"
        )

    if len(cats) >= 2 and len(cont) >= 1:
        n_combo = 1
        for cat in cats:
            n_combo *= max(cols[cat].get("n_unique", 1), 1)
        if n_combo > 12:
            suggestions.append(
                f"Categorical dimension combinations = {n_combo} ({', '.join(cats)} full cross), "
                "**one figure cannot fit** -- consider splitting by one dimension into multi-panels, or select subset."
            )

    for c in cont:
        m = cols[c]
        if m.get("needs_log_axis"):
            suggestions.append(
                f"{c} spans multiple orders of magnitude ({m['min']:.3g} ~ {m['max']:.3g}) -> use log y-axis"
            )
        elif m.get("skew_label") == "highly skewed":
            suggestions.append(
                f"{c} highly skewed (skew={m['skewness']:.2f}) -> "
                "consider log transform or violin instead of mean bar"
            )

    if not suggestions:
        suggestions.append(
            "Insufficient data features for specific suggestions; see chart_selection.md decision framework."
        )
    return suggestions


def profile_data(source, group_cols: list[str] | None = None) -> dict:
    """
    Main entry. Read data and return structured profiling report (dict).

    Args:
        source: file path (csv/xlsx), pd.DataFrame, or string content.
        group_cols: list of group column names for grouped statistics.
    Returns:
        dict with keys: n_rows / n_cols / columns / correlation /
        group_summary / suggestions / warnings
    """
    if isinstance(source, pd.DataFrame):
        df = source.copy()
        path_label = "<DataFrame>"
    elif isinstance(source, str) and os.path.exists(source):
        ext = os.path.splitext(source)[1].lower()
        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(source)
        elif ext in (".tsv",):
            df = pd.read_csv(source, sep="\t")
        else:
            df = pd.read_csv(source)
        path_label = source
    else:
        raise ValueError(f"Cannot read data from {source!r}")

    group_cols = group_cols or []
    for g in group_cols:
        if g not in df.columns:
            raise ValueError(
                f"group column {g!r} not in data; available: {df.columns.tolist()}"
            )

    cols_info: dict[str, dict] = {}
    warn_list: list[str] = []
    for c in df.columns:
        s = df[c]
        ctype = _detect_column_type(s)
        n_total = len(s)
        n_null = int(s.isnull().sum())
        missing_rate: float = n_null / n_total if n_total else 0.0
        entry: dict[str, Any] = {
            "type": ctype,
            "n_total": n_total,
            "n_null": n_null,
            "missing_rate": missing_rate,
        }
        if missing_rate > 0.20:
            warn_list.append(
                f"Column {c!r} missing rate {entry['missing_rate']:.0%} -- consider imputation, removal, "
                "or reporting in figure legend before plotting."
            )
        if ctype == TYPE_CONTINUOUS:
            entry.update(_profile_continuous(s))
        elif ctype in (TYPE_CATEGORICAL, TYPE_BOOLEAN, TYPE_ORDINAL):
            entry.update(_profile_categorical(s))
            if entry.get("small_groups_flag"):
                warn_list.append(
                    f"Column {c!r} has at least one category with n<10 -- small samples must show raw data points, "
                    "do not use mean-only bar chart."
                )
        elif ctype == TYPE_DATETIME:
            non_null = pd.to_datetime(s, errors="coerce").dropna()
            if len(non_null) > 0:
                entry["min"] = str(non_null.min())
                entry["max"] = str(non_null.max())
        cols_info[c] = entry

    cont_cols = [c for c, m in cols_info.items() if m["type"] == TYPE_CONTINUOUS]
    correlation = _correlation_matrix(df, cont_cols)

    info = {
        "source": path_label,
        "n_rows": int(df.shape[0]),
        "n_cols": int(df.shape[1]),
        "columns": cols_info,
        "correlation": correlation,
        "group_summary": _group_summary(df, group_cols),
        "warnings": warn_list,
    }
    info["suggestions"] = _suggest_charts(info)
    return info


def render_report(info: dict) -> str:
    """Render profile_data() output as a markdown-style human-readable report."""
    lines: list[str] = []
    lines.append(f"# Data profile: {info['source']}")
    lines.append("")
    lines.append(f"**Shape:** {info['n_rows']} rows x {info['n_cols']} cols")
    lines.append("")

    lines.append("## Columns")
    lines.append("")
    lines.append("| Column | Type | n | missing | summary |")
    lines.append("|---|---|---|---|---|")
    for c, m in info["columns"].items():
        summary = ""
        if m["type"] == TYPE_CONTINUOUS:
            summary = (
                f"mean={m.get('mean', 0):.3g}, sd={m.get('sd', 0):.3g}, "
                f"range=[{m.get('min', 0):.3g}, {m.get('max', 0):.3g}], "
                f"skew={m.get('skewness', 0):.2f} ({m.get('skew_label')})"
            )
            if m.get("n_outliers_iqr", 0):
                summary += f"; outliers={m['n_outliers_iqr']} (IQR)"
            if m.get("needs_log_axis"):
                summary += "; -> log axis"
        elif m["type"] in (TYPE_CATEGORICAL, TYPE_BOOLEAN, TYPE_ORDINAL):
            cats_list = m.get("categories", [])[:5]
            cats_str = ", ".join(f"{k}({v})" for k, v in cats_list)
            more = (
                f" +{m['n_unique'] - len(cats_list)} more"
                if m["n_unique"] > len(cats_list)
                else ""
            )
            summary = f"{m['n_unique']} levels: {cats_str}{more}; min_group_n={m['min_group_n']}"
        elif m["type"] == TYPE_DATETIME:
            summary = f"{m.get('min', '?')} -> {m.get('max', '?')}"
        miss = (
            f"{m['n_null']} ({m['missing_rate']:.0%})" if m["missing_rate"] > 0 else "0"
        )
        lines.append(
            f"| `{c}` | {m['type']} | {m['n_total'] - m['n_null']} | {miss} | {summary} |"
        )
    lines.append("")

    if info.get("group_summary"):
        gs = info["group_summary"]
        lines.append("## Group structure")
        lines.append(f"- Grouped by: `{'`, `'.join(gs['by'])}`")
        lines.append(f"- Number of groups: {gs['n_groups']}")
        lines.append(
            f"- Group size: min={gs['min_n_per_group']}, "
            f"median={gs['median_n_per_group']}, max={gs['max_n_per_group']}"
        )
        if gs["tiny_groups_flag"]:
            lines.append(
                "- **WARN**: at least one group has n<3 -- statistics unreliable; "
                "must show all raw points."
            )
        elif gs["small_groups_flag"]:
            lines.append(
                "- **WARN**: at least one group has n<10 -- use box/violin + stripplot "
                "rather than mean-only bar chart."
            )
        lines.append("")

    if info.get("correlation"):
        corr = info["correlation"]
        lines.append("## Correlations (Pearson, sorted by |r|)")
        for p in corr["pairs_sorted"][:10]:
            lines.append(
                f"- `{p['a']}` <-> `{p['b']}` : r = {p['r']:.3f} ({p['magnitude']})"
            )
        if len(corr["pairs_sorted"]) > 10:
            lines.append(f"- ... +{len(corr['pairs_sorted']) - 10} more pairs")
        lines.append("")

    if info["warnings"]:
        lines.append("## Warnings")
        for w in info["warnings"]:
            lines.append(f"- {w}")
        lines.append("")

    lines.append("## Chart suggestions (preliminary)")
    for s in info["suggestions"]:
        lines.append(f"- {s}")
    lines.append("")
    lines.append(
        "> These are **preliminary suggestions** based on data shape. Final chart type must combine "
        "**argumentative intent** (what you want to say) -- see `references/chart_selection.md`."
    )
    return "\n".join(lines)


def _default_json_serializer(o):
    """JSON serializer for numpy/pandas types."""
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.ndarray, pd.Series)):
        return o.tolist()
    return str(o)


def execute(
    action: str,
    params: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute figure profiler action."""
    params = params or {}
    metadata = {
        "resource": "local-figure-profiler",
        "not_for_clinical_decision": True,
        "requires_human_review": True,
    }
    try:
        if action == "figure-profile.profile":
            source = params.get("source")
            if source is None:
                return {
                    "status": "plugin_error",
                    "output": None,
                    "error": "Missing required parameter: source",
                    "metadata": metadata,
                }
            group_cols = params.get("group_cols")
            info = profile_data(source, group_cols=group_cols)
            report = render_report(info)
            return {
                "status": "success",
                "output": {"profile": info, "report": report},
                "metadata": metadata,
            }
        else:
            return {
                "status": "plugin_error",
                "output": None,
                "error": f"Unsupported figure-profile action: {action}",
                "metadata": metadata,
            }
    except Exception as exc:
        return {
            "status": "plugin_error",
            "output": None,
            "error": f"Figure profiler error: {exc}",
            "metadata": metadata,
        }
