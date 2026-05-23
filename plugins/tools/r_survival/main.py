"""Survival analysis plugin prototype entry point.

Current contract: this module exposes deterministic interface/test paths around
Kaplan-Meier, log-rank, and Cox-style survival actions. The pure Python fallback
and optional R bridge are prototype paths only, not production-grade or
clinical-grade statistical implementations.
"""
from __future__ import annotations

import logging
from typing import Any

from plugins.base_plugin import plugin_result

from .kaplan_meier import kaplan_meier
from .logrank import logrank_test
from .cox_model import cox_ph

logger = logging.getLogger(__name__)

MEDICAL_BOUNDARY = (
    "Current-stage SuperMedicine output: prototype/interface test path only; "
    "not production/clinical medical advice and not clinical-grade statistics; "
    "requires expert review before any research, regulatory, or clinical use."
)

STATISTICS_BOUNDARY = (
    "Current phase provides interfaces, deterministic contract tests, and "
    "prototype survival calculations only; no production-grade or clinical-grade "
    "statistical accuracy is promised; no production-grade statistical guarantee."
)

ACTION_CONTRACTS: dict[str, dict[str, Any]] = {
    "r.survival.km": {
        "required_params": {"times": "list[number]", "events": "list[0|1]", "same_length": True},
        "output_fields": ["time_points", "median_survival", "total_subjects", "total_events"],
        "prototype": True,
    },
    "r.survival.logrank": {
        "required_params": {
            "times1": "list[number]", "events1": "list[0|1]",
            "times2": "list[number]", "events2": "list[0|1]", "same_length_by_group": True,
        },
        "output_fields": ["statistic", "p_value", "df", "median_group1", "median_group2"],
        "prototype": True,
    },
    "r.survival.cox": {
        "required_params": {
            "times": "list[number]", "events": "list[0|1]", "covariates": "list[list[number]]",
            "same_subject_count": True,
        },
        "output_fields": [
            "coefficients", "hazard_ratios", "standard_errors", "confidence_intervals",
            "p_values", "log_likelihood", "n_subjects", "n_events",
        ],
        "prototype": True,
    },
}

DEFAULT_PARAMS: dict[str, dict[str, Any]] = {
    "r.survival.km": {"times": [1, 2, 3, 4, 5], "events": [1, 1, 0, 1, 0]},
    "r.survival.logrank": {
        "times1": [1, 2, 3, 4, 5], "events1": [1, 1, 1, 1, 1],
        "times2": [2, 3, 4, 5, 6], "events2": [1, 1, 1, 1, 1],
    },
    "r.survival.cox": {
        "times": [1, 2, 3, 4, 5], "events": [1, 1, 0, 1, 0], "covariates": [[0, 1, 0, 1, 0]],
    },
}

# Optional R Backend — Rpy2 may not be Installed
try:
    import rpy2  # Noqa: F401
    _HAS_RPY2 = True
except ImportError:
    _HAS_RPY2 = False
    logger.debug("Rpy2 not Installed — Using Pure Python Survival Analysis Fallback")


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
    """Log-Rank 检验工具接口"""
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


def execute(
    action: str,
    params: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """真实执行生存分析插件动作（当前阶段接口，不承诺生产级统计）。"""
    params = params or {}
    metadata = {
        "medical_boundary": MEDICAL_BOUNDARY,
        "statistics_boundary": STATISTICS_BOUNDARY,
        "resource": "local-survival-analysis",
        "contract": {
            "stage": "prototype-interface-tests-only",
            "actions": ACTION_CONTRACTS,
            "default_params_are_smoke_test_fixtures": True,
        },
        "audit": {"interface_only": True, "prototype_path": True, "rpy2_available": _HAS_RPY2, "context_keys": sorted((context or {}).keys())},
    }
    try:
        if action == "r.survival.km":
            result = km_tool(
                _as_float_list(_param_or_default(params, action, "times"), "times"),
                _as_event_list(_param_or_default(params, action, "events"), "events"),
            )
        elif action == "r.survival.logrank":
            result = logrank_tool(
                _as_float_list(_param_or_default(params, action, "times1"), "times1"),
                _as_event_list(_param_or_default(params, action, "events1"), "events1"),
                _as_float_list(_param_or_default(params, action, "times2"), "times2"),
                _as_event_list(_param_or_default(params, action, "events2"), "events2"),
            )
        elif action == "r.survival.cox":
            result = cox_tool(
                _as_float_list(_param_or_default(params, action, "times"), "times"),
                _as_event_list(_param_or_default(params, action, "events"), "events"),
                _as_float_groups(_param_or_default(params, action, "covariates"), "covariates"),
            )
        else:
            return plugin_result(
                status="plugin_error",
                plugin="r-survival",
                action=action,
                error=f"Unsupported r-survival action: {action}",
                metadata=metadata,
            )
    except (TypeError, ValueError, ZeroDivisionError, IndexError) as exc:
        return plugin_result(
            status="plugin_error",
            plugin="r-survival",
            action=action,
            error=f"Invalid r-survival input: {exc}",
            metadata=metadata,
        )

    return plugin_result(
        status="success",
        plugin="r-survival",
        action=action,
        output=result,
        metadata=metadata,
    )


def _param_or_default(params: dict[str, Any], action: str, key: str) -> Any:
    """Return explicit input or smoke-test fixture input for compatibility."""
    if key in params:
        return params[key]
    return DEFAULT_PARAMS[action][key]


def _as_float_list(value: Any, name: str) -> list[float]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list of numbers")
    return [float(item) for item in value]


def _as_event_list(value: Any, name: str) -> list[int]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list of 0/1 event indicators")
    events = [int(item) for item in value]
    if any(item not in (0, 1) for item in events):
        raise ValueError(f"{name} must contain only 0 or 1")
    return events


def _as_float_groups(value: Any, name: str) -> list[list[float]]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list of numeric lists")
    return [_as_float_list(group, f"{name}[{index}]") for index, group in enumerate(value)]
