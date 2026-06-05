"""Log-rank prototype test implementation.

Interface boundary: deterministic test fixture path only. This implementation is
not a production-grade, clinical-grade, or regulatory survival analysis engine.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class LogRankResult:
    """Log-Rank 检验结果"""

    statistic: float
    p_value: float
    df: int
    median_group1: float | None
    median_group2: float | None


def logrank_test(
    times1: list[float],
    events1: list[int],
    times2: list[float],
    events2: list[int],
) -> LogRankResult:
    """
    两组 Log-rank 检验

    Args:
        times1: 第一组观察时间
        events1: 第一组事件指示
        times2: 第二组观察时间
        events2: 第二组事件指示

    Returns:
        LogRankResult 包含检验统计量和 p 值
    """
    if len(times1) != len(events1) or len(times2) != len(events2):
        raise ValueError("时间和事件列表长度必须相同")
    if not times1 or not times2:
        raise ValueError("每组数据不能为空")
    if any(event not in (0, 1) for event in events1 + events2):
        raise ValueError("事件指示必须只包含 0 或 1")

    n1 = len(times1)
    n2 = len(times2)

    # 合并所有时间点
    all_times = sorted(set(times1 + times2))

    # 计算观察-期望统计量
    o_minus_e = 0.0
    variance = 0.0

    at_risk1 = n1
    at_risk2 = n2

    for t in all_times:
        # 在时间 t 的事件数
        d1 = sum(1 for ti, ei in zip(times1, events1) if ti == t and ei == 1)
        d2 = sum(1 for ti, ei in zip(times2, events2) if ti == t and ei == 1)
        d = d1 + d2

        # 在时间 t 的风险集
        n = at_risk1 + at_risk2

        if n > 0:
            # 期望事件数
            e1 = d * at_risk1 / n
            o_minus_e += d1 - e1

            # 方差
            if n > 1:
                variance += d * at_risk1 * at_risk2 * (n - d) / (n * n * (n - 1))

        # 更新风险集（移除事件和删失）
        censored1 = sum(1 for ti, ei in zip(times1, events1) if ti == t and ei == 0)
        censored2 = sum(1 for ti, ei in zip(times2, events2) if ti == t and ei == 0)

        at_risk1 -= d1 + censored1
        at_risk2 -= d2 + censored2

    # 卡方统计量
    if variance > 0:
        chi2 = o_minus_e**2 / variance
    else:
        chi2 = 0.0

    # p 值（自由度为 1 的卡方分布）
    p_value = 1 - _chi2_cdf(chi2, 1)

    # 计算中位生存时间
    from .kaplan_meier import kaplan_meier

    km1 = kaplan_meier(times1, events1)
    km2 = kaplan_meier(times2, events2)

    return LogRankResult(
        statistic=round(chi2, 4),
        p_value=round(p_value, 6),
        df=1,
        median_group1=km1.median_survival,
        median_group2=km2.median_survival,
    )


def _chi2_cdf(x: float, k: int) -> float:
    """卡方分布 CDF（正态近似）"""
    if x <= 0:
        return 0
    # 使用正态近似
    z = math.sqrt(2 * x) - math.sqrt(2 * k - 1)
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))
