"""Python 统计分析工具实现"""
from __future__ import annotations

import math
from typing import Any


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


def ttest(group1: list[float], group2: list[float]) -> dict[str, float]:
    """独立样本 t 检验（Welch's t-test）"""
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


def anova(*groups: list[float]) -> dict[str, float]:
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
    ss_within = 0
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


def regression(x: list[float], y: list[float]) -> dict[str, float]:
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