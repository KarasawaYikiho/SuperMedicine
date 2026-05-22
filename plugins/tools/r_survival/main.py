"""R 生存分析工具入口"""
from __future__ import annotations

import logging

from .kaplan_meier import kaplan_meier
from .logrank import logrank_test
from .cox_model import cox_ph

logger = logging.getLogger(__name__)

# Optional R backend — rpy2 may not be installed
try:
    import rpy2  # noqa: F401
    _HAS_RPY2 = True
except ImportError:
    _HAS_RPY2 = False
    logger.debug("rpy2 not installed — using pure Python survival analysis fallback")


def km_tool(times: list[float], events: list[int]) -> dict:
    """Kaplan-Meier 生存分析工具接口"""
    result = kaplan_meier(times, events)
    return {
        "time_points": [
            {
                "time": p.time,
                "survival_prob": p.survival_prob,
                "confidence_lower": p.confidence_lower,
                "confidence_upper": p.confidence_upper,
                "at_risk": p.at_risk,
                "events": p.events,
                "censored": p.censored,
            }
            for p in result.time_points
        ],
        "median_survival": result.median_survival,
        "total_subjects": result.total_subjects,
        "total_events": result.total_events,
    }


def logrank_tool(
    times1: list[float],
    events1: list[int],
    times2: list[float],
    events2: list[int],
) -> dict:
    """Log-rank 检验工具接口"""
    result = logrank_test(times1, events1, times2, events2)
    return {
        "statistic": result.statistic,
        "p_value": result.p_value,
        "df": result.df,
        "median_group1": result.median_group1,
        "median_group2": result.median_group2,
    }


def cox_tool(
    times: list[float],
    events: list[int],
    covariates: list[list[float]],
) -> dict:
    """Cox 比例风险模型工具接口"""
    result = cox_ph(times, events, covariates)
    return {
        "coefficients": result.coefficients,
        "hazard_ratios": result.hazard_ratios,
        "standard_errors": result.standard_errors,
        "confidence_intervals": [
            list(ci) for ci in result.confidence_intervals
        ],
        "p_values": result.p_values,
        "log_likelihood": result.log_likelihood,
        "n_subjects": result.n_subjects,
        "n_events": result.n_events,
    }
