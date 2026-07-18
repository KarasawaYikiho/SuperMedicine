"""Kaplan-Meier prototype survival curve estimator.

Interface boundary: deterministic test fixture path only. This implementation is
not a production-grade, clinical-grade, or regulatory survival analysis engine.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from plugins.tools._common import validate_survival_sample


@dataclass
class KMSurvivalPoint:
    """生存曲线数据点"""

    time: float
    survival_prob: float
    confidence_lower: float
    confidence_upper: float
    at_risk: int
    events: int
    censored: int


@dataclass
class KMResult:
    """Kaplan-Meier 分析结果"""

    time_points: list[KMSurvivalPoint]
    median_survival: float | None
    total_subjects: int
    total_events: int


def kaplan_meier(times: list[float], events: list[int]) -> KMResult:
    """
    Kaplan-Meier 生存曲线估计

    Args:
        times: 观察时间列表
        events: 事件指示列表 (1=事件发生, 0=删失)

    Returns:
        KMResult 包含生存曲线数据点和中位生存时间
    """
    validate_survival_sample(times, events)

    n = len(times)

    # 按时间排序
    paired = sorted(zip(times, events), key=lambda x: x[0])
    sorted_times = [p[0] for p in paired]
    sorted_events = [p[1] for p in paired]

    # 获取唯一事件时间点
    unique_times = sorted(set(t for t, e in zip(sorted_times, sorted_events) if e == 1))

    # 计算每个时间点的生存概率
    survival_prob = 1.0
    at_risk = n
    result_points = []
    greenwood_var = 0.0

    for t in unique_times:
        # 在时间 t 之前的删失
        censored_before = sum(
            1 for ti, ei in zip(sorted_times, sorted_events) if ti < t and ei == 0
        )
        at_risk -= censored_before

        # 在时间 t 的事件数
        d = sum(1 for ti, ei in zip(sorted_times, sorted_events) if ti == t and ei == 1)

        # 在时间 t 的删失数
        c = sum(1 for ti, ei in zip(sorted_times, sorted_events) if ti == t and ei == 0)

        # 更新生存概率
        if at_risk > 0:
            survival_prob *= 1 - d / at_risk
            # Greenwood 公式
            if at_risk - d > 0:
                greenwood_var += d / (at_risk * (at_risk - d))

        # 置信区间（Log-Log 变换）
        se = math.sqrt(greenwood_var) * survival_prob if greenwood_var > 0 else 0
        ci_lower = max(0, survival_prob - 1.96 * se)
        ci_upper = min(1, survival_prob + 1.96 * se)

        result_points.append(
            KMSurvivalPoint(
                time=t,
                survival_prob=round(survival_prob, 4),
                confidence_lower=round(ci_lower, 4),
                confidence_upper=round(ci_upper, 4),
                at_risk=at_risk,
                events=d,
                censored=c,
            )
        )

        at_risk -= d

    # 计算中位生存时间
    median_survival = None
    for point in result_points:
        if point.survival_prob <= 0.5:
            median_survival = point.time
            break

    total_events = sum(events)

    return KMResult(
        time_points=result_points,
        median_survival=median_survival,
        total_subjects=n,
        total_events=total_events,
    )
