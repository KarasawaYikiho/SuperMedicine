"""Python statistics plugin prototype.

Current contract: this module exposes deterministic interface/test paths for
basic statistics actions. The implementations are intentionally lightweight and
must not be described as production-grade, clinical-grade, or regulatory-grade
statistics.
"""
from __future__ import annotations

import math
from typing import Any

from plugins.base_plugin import plugin_result
from plugins.tools._common import as_float_groups, as_float_list, param_or_default


MEDICAL_BOUNDARY = (
    "Current-stage SuperMedicine output: prototype/interface test path only; "
    "not production/clinical medical advice and not clinical-grade statistics; "
    "requires expert review before any research, regulatory, or clinical use."
)

STATISTICS_BOUNDARY = (
    "Current phase provides interfaces, deterministic contract tests, and "
    "prototype calculations only; no production-grade or clinical-grade "
    "statistical accuracy is promised; no production-grade statistical guarantee."
)

ACTION_CONTRACTS: dict[str, dict[str, Any]] = {
    "stats.descriptive": {
        "required_params": {"data": "list[number]"},
        "output_fields": ["count", "mean", "std", "min", "max", "median"],
        "prototype": True,
    },
    "stats.ttest": {
        "required_params": {"group1": "list[number]", "group2": "list[number]"},
        "output_fields": ["statistic", "p_value", "effect_size"],
        "prototype": True,
    },
    "stats.anova": {
        "required_params": {"groups": "list[list[number]]"},
        "output_fields": ["f_statistic", "p_value", "df_between", "df_within"],
        "prototype": True,
    },
    "stats.regression": {
        "required_params": {"x": "list[number]", "y": "list[number]", "same_length": True},
        "output_fields": ["slope", "intercept", "r_squared", "n"],
        "prototype": True,
    },
}

DEFAULT_PARAMS: dict[str, dict[str, Any]] = {
    "stats.descriptive": {"data": [1, 2, 3, 4, 5]},
    "stats.ttest": {"group1": [1, 2, 3, 4, 5], "group2": [2, 3, 4, 5, 6]},
    "stats.anova": {"groups": [[1, 2, 3], [2, 3, 4]]},
    "stats.regression": {"x": [1, 2, 3, 4, 5], "y": [2, 4, 6, 8, 10]},
}


def descriptive(data: list[float]) -> dict[str, float]:
    """描述性统计"""
    n = len(data)
    if n == 0:
        return {"count": 0, "mean": 0, "std": 0, "min": 0, "max": 0, "median": 0}

    mean = sum(data) / n
    sorted_data = sorted(data)
    if n % 2 == 0:
        median = (sorted_data[n // 2 - 1] + sorted_data[n // 2]) / 2
    else:
        median = sorted_data[n // 2]

    variance = sum((x - mean) ** 2 for x in data) / (n - 1) if n > 1 else 0
    std = math.sqrt(variance)

    return {
        "count": n,
        "mean": round(mean, 4),
        "std": round(std, 4),
        "min": min(data),
        "max": max(data),
        "median": round(median, 4),
    }


def ttest(group1: list[float], group2: list[float]) -> dict[str, float | str]:
    """独立样本 T 检验（Welch'S T-Test）"""
    n1, n2 = len(group1), len(group2)
    if n1 < 2 or n2 < 2:
        return {"statistic": 0, "p_value": 1.0, "error": "样本量不足"}

    mean1 = sum(group1) / n1
    mean2 = sum(group2) / n2
    var1 = sum((x - mean1) ** 2 for x in group1) / (n1 - 1)
    var2 = sum((x - mean2) ** 2 for x in group2) / (n2 - 1)

    se = math.sqrt(var1 / n1 + var2 / n2)
    if se == 0:
        return {"statistic": 0, "p_value": 1.0}

    t_stat = (mean1 - mean2) / se

    # 近似 p 值（使用正态近似）
    z = abs(t_stat)
    p_value = 2 * (1 - _normal_cdf(z))

    # Cohen's d
    pooled_std = math.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    effect_size = (mean1 - mean2) / pooled_std if pooled_std > 0 else 0

    return {
        "statistic": round(t_stat, 4),
        "p_value": round(p_value, 6),
        "effect_size": round(effect_size, 4),
    }


def anova(*groups: list[float]) -> dict[str, float | str]:
    """单因素方差分析"""
    k = len(groups)
    if k < 2:
        return {"f_statistic": 0, "p_value": 1.0, "error": "至少需要 2 组"}

    all_data = [x for g in groups for x in g]
    grand_mean = sum(all_data) / len(all_data)
    n_total = len(all_data)

    # 组间平方和
    ss_between = sum(len(g) * (sum(g) / len(g) - grand_mean) ** 2 for g in groups)

    # 组内平方和
    ss_within = 0.0
    for g in groups:
        g_mean = sum(g) / len(g)
        ss_within += sum((x - g_mean) ** 2 for x in g)

    df_between = k - 1
    df_within = n_total - k

    if df_within == 0 or ss_within == 0:
        return {"f_statistic": 0, "p_value": 1.0}

    ms_between = ss_between / df_between
    ms_within = ss_within / df_within
    f_stat = ms_between / ms_within

    # 近似 p 值
    p_value = 1 - _f_cdf(f_stat, df_between, df_within)

    return {
        "f_statistic": round(f_stat, 4),
        "p_value": round(p_value, 6),
        "df_between": df_between,
        "df_within": df_within,
    }


def regression(x: list[float], y: list[float]) -> dict[str, float | str]:
    """简单线性回归"""
    n = len(x)
    if n < 2 or len(y) < 2:
        return {"error": "样本量不足"}

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    ss_xy = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    ss_xx = sum((xi - mean_x) ** 2 for xi in x)
    ss_yy = sum((yi - mean_y) ** 2 for yi in y)

    if ss_xx == 0:
        return {"error": "x 方差为 0"}

    slope = ss_xy / ss_xx
    intercept = mean_y - slope * mean_x

    # R²
    ss_res = sum((yi - (slope * xi + intercept)) ** 2 for xi, yi in zip(x, y))
    r_squared = 1 - ss_res / ss_yy if ss_yy > 0 else 0

    return {
        "slope": round(slope, 4),
        "intercept": round(intercept, 4),
        "r_squared": round(r_squared, 4),
        "n": n,
    }


def execute(
    action: str,
    params: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """真实执行 Python 统计插件动作（当前阶段接口，不承诺生产级统计）。"""
    params = params or {}
    metadata = {
        "medical_boundary": MEDICAL_BOUNDARY,
        "statistics_boundary": STATISTICS_BOUNDARY,
        "prototype_only": True,
        "not_for_clinical_decision": True,
        "requires_human_review": True,
        "resource": "local-python-statistics",
        "contract": {
            "stage": "prototype-interface-tests-only",
            "actions": ACTION_CONTRACTS,
            "default_params_are_smoke_test_fixtures": True,
        },
        "audit": {"interface_only": True, "prototype_path": True, "context_keys": sorted((context or {}).keys())},
    }
    try:
        if action == "stats.descriptive":
            data = param_or_default(params, "data", DEFAULT_PARAMS[action]["data"])
            result: dict[str, Any] = descriptive(as_float_list(data, "data"))
        elif action == "stats.ttest":
            group1 = param_or_default(params, "group1", DEFAULT_PARAMS[action]["group1"])
            group2 = param_or_default(params, "group2", DEFAULT_PARAMS[action]["group2"])
            result = ttest(as_float_list(group1, "group1"), as_float_list(group2, "group2"))
        elif action == "stats.anova":
            groups = param_or_default(params, "groups", DEFAULT_PARAMS[action]["groups"])
            result = anova(*as_float_groups(groups, "groups"))
        elif action == "stats.regression":
            x = as_float_list(param_or_default(params, "x", DEFAULT_PARAMS[action]["x"]), "x")
            y = as_float_list(param_or_default(params, "y", DEFAULT_PARAMS[action]["y"]), "y")
            if len(x) != len(y):
                raise ValueError("x and y must have the same length")
            result = regression(x, y)
        else:
            return plugin_result(
                status="plugin_error",
                plugin="python-stats",
                action=action,
                error=f"Unsupported python-stats action: {action}",
                metadata=metadata,
            )
    except (TypeError, ValueError, ZeroDivisionError) as exc:
        return plugin_result(
            status="plugin_error",
            plugin="python-stats",
            action=action,
            error=f"Invalid python-stats input: {exc}",
            metadata=metadata,
        )

    return plugin_result(
        status="success",
        plugin="python-stats",
        action=action,
        output=result,
        metadata=metadata,
    )


def _normal_cdf(z: float) -> float:
    """标准正态分布 CDF 近似"""
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def _f_cdf(f: float, d1: int, d2: int) -> float:
    """F 分布 CDF 近似（使用正态近似）"""
    if f <= 0:
        return 0
    # 近似公式
    z = ((f ** (1/3)) * (1 - 2 / (9 * d2)) - (1 - 2 / (9 * d1))) / math.sqrt(2 / (9 * d1) + (f ** (2/3)) * 2 / (9 * d2))
    return _normal_cdf(z)
