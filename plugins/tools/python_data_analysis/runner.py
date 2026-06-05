#!/usr/bin/env python3
"""Lightweight Python mainstream data-analysis workspace tool."""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any


MISSING = {"", "na", "n/a", "nan", "null", "none", "."}
OPTIONAL_PACKAGES = {
    "random-forest": ["sklearn"],
    "gradient-boosting": ["sklearn", "xgboost", "lightgbm"],
}


def _sample_rows() -> list[dict[str, str]]:
    return [
        {"x1": "1", "x2": "2", "group": "A", "target": "0", "date": "2024-01-01"},
        {"x1": "2", "x2": "3", "group": "A", "target": "0", "date": "2024-01-02"},
        {"x1": "3", "x2": "5", "group": "B", "target": "1", "date": "2024-01-03"},
        {"x1": "4", "x2": "8", "group": "B", "target": "1", "date": "2024-01-04"},
        {"x1": "5", "x2": "13", "group": "B", "target": "1", "date": "2024-01-05"},
    ]


def _read_rows(path: str | None) -> list[dict[str, str]]:
    if not path:
        return _sample_rows()
    input_path = Path(path)
    if not input_path.is_file():
        raise ValueError(f"input file not found: {path}")
    sample = input_path.read_text(encoding="utf-8-sig", errors="replace")[:4096]
    dialect = csv.Sniffer().sniff(sample, delimiters=",\t;") if sample.strip() else csv.excel
    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle, dialect=dialect)]


def _is_missing(value: Any) -> bool:
    return value is None or str(value).strip().lower() in MISSING


def _float(value: Any) -> float | None:
    if _is_missing(value):
        return None
    try:
        result = float(str(value).strip())
    except ValueError:
        return None
    return result if math.isfinite(result) else None


def _numeric_columns(rows: list[dict[str, str]], requested: str | None) -> dict[str, list[float]]:
    names = [name.strip() for name in requested.split(",") if name.strip()] if requested else list(rows[0])
    cols: dict[str, list[float]] = {}
    for name in names:
        values = [_float(row.get(name)) for row in rows]
        numeric = [value for value in values if value is not None]
        if numeric:
            cols[name] = numeric
    if not cols:
        raise ValueError("no numeric columns found for analysis")
    return cols


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _variance(values: list[float]) -> float:
    return statistics.variance(values) if len(values) > 1 else 0.0


def _normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def descriptive(cols: dict[str, list[float]]) -> dict[str, Any]:
    return {
        name: {
            "count": len(values),
            "mean": _mean(values),
            "std": math.sqrt(_variance(values)),
            "min": min(values),
            "median": statistics.median(values),
            "max": max(values),
        }
        for name, values in cols.items()
    }


def missing(rows: list[dict[str, str]]) -> dict[str, Any]:
    total = len(rows)
    names = list(rows[0]) if rows else []
    return {
        name: {
            "missing": sum(1 for row in rows if _is_missing(row.get(name))),
            "missing_rate": (sum(1 for row in rows if _is_missing(row.get(name))) / total) if total else 0,
        }
        for name in names
    }


def scale(cols: dict[str, list[float]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, values in cols.items():
        mean = _mean(values)
        std = math.sqrt(_variance(values)) or 1.0
        low, high = min(values), max(values)
        span = (high - low) or 1.0
        result[name] = {
            "z_score": [(value - mean) / std for value in values],
            "min_max": [(value - low) / span for value in values],
        }
    return result


def _pearson(a: list[float], b: list[float]) -> float:
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    ma, mb = _mean(a), _mean(b)
    da = math.sqrt(sum((x - ma) ** 2 for x in a))
    db = math.sqrt(sum((y - mb) ** 2 for y in b))
    return 0.0 if da == 0 or db == 0 else sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (da * db)


def _ranks(values: list[float]) -> list[float]:
    order = sorted((value, idx) for idx, value in enumerate(values))
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and order[j + 1][0] == order[i][0]:
            j += 1
        rank = (i + j + 2) / 2
        for _, idx in order[i : j + 1]:
            ranks[idx] = rank
        i = j + 1
    return ranks


def correlation(cols: dict[str, list[float]]) -> dict[str, Any]:
    names = list(cols)
    return {
        f"{a}:{b}": {"pearson": _pearson(cols[a], cols[b]), "spearman": _pearson(_ranks(cols[a]), _ranks(cols[b]))}
        for i, a in enumerate(names)
        for b in names[i + 1 :]
    }


def linear_regression(cols: dict[str, list[float]]) -> dict[str, Any]:
    names = list(cols)
    if len(names) < 2:
        raise ValueError("linear-regression requires at least two numeric columns")
    x, y = cols[names[0]], cols[names[1]]
    n = min(len(x), len(y))
    x, y = x[:n], y[:n]
    mx, my = _mean(x), _mean(y)
    ssx = sum((v - mx) ** 2 for v in x)
    if ssx == 0:
        raise ValueError("predictor variance is zero")
    slope = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y)) / ssx
    intercept = my - slope * mx
    fitted = [intercept + slope * xi for xi in x]
    ss_res = sum((yi - fi) ** 2 for yi, fi in zip(y, fitted))
    ss_tot = sum((yi - my) ** 2 for yi in y)
    return {"x": names[0], "y": names[1], "slope": slope, "intercept": intercept, "r_squared": 1 - ss_res / ss_tot if ss_tot else 0}


def logistic_regression(cols: dict[str, list[float]]) -> dict[str, Any]:
    names = list(cols)
    if len(names) < 2:
        raise ValueError("logistic-regression requires predictor and binary target columns")
    x, y = cols[names[0]], [1.0 if v > 0 else 0.0 for v in cols[names[1]]]
    n = min(len(x), len(y))
    x, y = x[:n], y[:n]
    b0 = b1 = 0.0
    for _ in range(300):
        g0 = g1 = 0.0
        for xi, yi in zip(x, y):
            p = 1 / (1 + math.exp(-(b0 + b1 * xi)))
            g0 += p - yi
            g1 += (p - yi) * xi
        b0 -= 0.05 * g0 / n
        b1 -= 0.05 * g1 / n
    return {"predictor": names[0], "target": names[1], "intercept": b0, "coefficient": b1}


def pca(cols: dict[str, list[float]]) -> dict[str, Any]:
    names = list(cols)[:2]
    if len(names) < 2:
        raise ValueError("pca requires at least two numeric columns")
    a, b = cols[names[0]], cols[names[1]]
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    va, vb = _variance(a), _variance(b)
    cov = sum((x - _mean(a)) * (y - _mean(b)) for x, y in zip(a, b)) / max(n - 1, 1)
    trace = va + vb
    disc = math.sqrt(max((va - vb) ** 2 + 4 * cov * cov, 0))
    eig1, eig2 = (trace + disc) / 2, (trace - disc) / 2
    return {"columns": names, "explained_variance": [eig1, eig2], "explained_variance_ratio": [eig1 / trace if trace else 0, eig2 / trace if trace else 0]}


def kmeans(cols: dict[str, list[float]], k: int = 2) -> dict[str, Any]:
    names = list(cols)[:2]
    points = list(zip(cols[names[0]], cols[names[1]] if len(names) > 1 else cols[names[0]]))
    centers = [list(point) for point in points[:k]]
    labels = [0] * len(points)
    for _ in range(20):
        labels = [min(range(k), key=lambda i: (p[0] - centers[i][0]) ** 2 + (p[1] - centers[i][1]) ** 2) for p in points]
        for i in range(k):
            assigned = [p for p, label in zip(points, labels) if label == i]
            if assigned:
                centers[i] = [sum(p[0] for p in assigned) / len(assigned), sum(p[1] for p in assigned) / len(assigned)]
    return {"columns": names, "k": k, "centers": centers, "labels": labels}


def hierarchical(cols: dict[str, list[float]]) -> dict[str, Any]:
    names = list(cols)
    pairs = correlation(cols)
    return {"method": "correlation-distance summary", "columns": names, "nearest_pairs": sorted(pairs.items(), key=lambda item: 1 - abs(item[1]["pearson"]))[:5]}


def time_series(cols: dict[str, list[float]]) -> dict[str, Any]:
    name, values = next(iter(cols.items()))
    diffs = [b - a for a, b in zip(values, values[1:])]
    return {"column": name, "n": len(values), "mean": _mean(values), "first_difference_mean": _mean(diffs) if diffs else 0, "lag1_autocorrelation": _pearson(values[:-1], values[1:]) if len(values) > 2 else 0}


def t_test(cols: dict[str, list[float]]) -> dict[str, Any]:
    values = next(iter(cols.values()))
    mid = len(values) // 2
    a, b = values[:mid], values[mid:]
    if len(a) < 2 or len(b) < 2:
        raise ValueError("t-test requires at least two observations in each split group")
    se = math.sqrt(_variance(a) / len(a) + _variance(b) / len(b))
    stat = 0.0 if se == 0 else (_mean(a) - _mean(b)) / se
    return {"test": "Welch t-test normal approximation", "statistic": stat, "p_value_approx": 2 * (1 - _normal_cdf(abs(stat)))}


def chi_square(rows: list[dict[str, str]]) -> dict[str, Any]:
    names = list(rows[0])[:2]
    table: dict[tuple[str, str], int] = {}
    for row in rows:
        table[(row.get(names[0], ""), row.get(names[1], ""))] = table.get((row.get(names[0], ""), row.get(names[1], "")), 0) + 1
    return {"test": "chi-square contingency summary", "columns": names, "observed": {f"{a}|{b}": v for (a, b), v in table.items()}}


def anova(rows: list[dict[str, str]], cols: dict[str, list[float]]) -> dict[str, Any]:
    names = list(rows[0])
    group_col = next((name for name in names if name not in cols), None)
    value_col = next(iter(cols))
    if not group_col:
        raise ValueError("anova requires at least one categorical group column")
    groups: dict[str, list[float]] = {}
    for row in rows:
        value = _float(row.get(value_col))
        if value is not None:
            groups.setdefault(row.get(group_col, ""), []).append(value)
    grand = _mean([v for values in groups.values() for v in values])
    ssb = sum(len(values) * (_mean(values) - grand) ** 2 for values in groups.values() if values)
    ssw = sum(sum((v - _mean(values)) ** 2 for v in values) for values in groups.values() if values)
    dfb, dfw = max(len(groups) - 1, 1), max(sum(len(v) for v in groups.values()) - len(groups), 1)
    return {"test": "one-way ANOVA", "group": group_col, "value": value_col, "f_statistic": (ssb / dfb) / (ssw / dfw) if ssw else 0}


def optional_wrapper(kind: str) -> dict[str, Any]:
    missing = [pkg for pkg in OPTIONAL_PACKAGES[kind] if importlib.util.find_spec(pkg) is None]
    return {"algorithm": kind, "optional": True, "status": "missing_optional_dependencies" if missing else "available", "missing_dependencies": missing}


def run(kind: str, rows: list[dict[str, str]], columns: str | None) -> dict[str, Any]:
    cols = _numeric_columns(rows, columns)
    actions = {
        "descriptive": lambda: descriptive(cols),
        "missing": lambda: missing(rows),
        "scale": lambda: scale(cols),
        "correlation": lambda: correlation(cols),
        "linear-regression": lambda: linear_regression(cols),
        "logistic-regression": lambda: logistic_regression(cols),
        "pca": lambda: pca(cols),
        "kmeans": lambda: kmeans(cols),
        "hierarchical-clustering": lambda: hierarchical(cols),
        "time-series": lambda: time_series(cols),
        "t-test": lambda: t_test(cols),
        "chi-square": lambda: chi_square(rows),
        "anova": lambda: anova(rows, cols),
        "random-forest": lambda: optional_wrapper("random-forest"),
        "gradient-boosting": lambda: optional_wrapper("gradient-boosting"),
    }
    if kind == "all-light":
        selected = [name for name in actions if name not in OPTIONAL_PACKAGES]
        return {name: actions[name]() for name in selected}
    if kind not in actions:
        raise ValueError(f"unsupported tool-kind: {kind}")
    return actions[kind]()


def main() -> int:
    parser = argparse.ArgumentParser(description="SuperMedicine lightweight Python data-analysis algorithms")
    parser.add_argument("--input", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--tool-kind", default="all-light")
    parser.add_argument("--columns", default=None)
    parser.add_argument("--check-deps", action="store_true")
    args = parser.parse_args()
    if args.check_deps:
        print("Baseline Python data-analysis actions use only the standard library; heavy ML wrappers are optional.")
        return 0
    try:
        payload = {"status": "ok", "tool_kind": args.tool_kind, "result": run(args.tool_kind, _read_rows(args.input), args.columns)}
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        if args.output:
            Path(args.output).write_text(text + "\n", encoding="utf-8")
        else:
            print(text)
        return 0
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
