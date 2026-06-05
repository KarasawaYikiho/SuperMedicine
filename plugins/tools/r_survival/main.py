"""Survival analysis plugin entry point.

This module exposes deterministic interface/test paths around Kaplan-Meier,
log-rank, and Cox-style survival actions. When R, rpy2, and the R ``survival``
package are available, callers may request the formal R backend. The pure Python
fallback and R bridge are not clinical-grade statistical implementations.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from plugins.base_plugin import plugin_result
from plugins.tools._common import as_float_groups, as_float_list, param_or_default

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
        "required_params": {
            "times": "list[number]",
            "events": "list[0|1]",
            "same_length": True,
        },
        "output_fields": [
            "time_points",
            "median_survival",
            "total_subjects",
            "total_events",
        ],
        "prototype": True,
    },
    "r.survival.logrank": {
        "required_params": {
            "times1": "list[number]",
            "events1": "list[0|1]",
            "times2": "list[number]",
            "events2": "list[0|1]",
            "same_length_by_group": True,
        },
        "output_fields": [
            "statistic",
            "p_value",
            "df",
            "median_group1",
            "median_group2",
        ],
        "prototype": True,
    },
    "r.survival.cox": {
        "required_params": {
            "times": "list[number]",
            "events": "list[0|1]",
            "covariates": "list[list[number]]",
            "same_subject_count": True,
        },
        "output_fields": [
            "coefficients",
            "hazard_ratios",
            "standard_errors",
            "confidence_intervals",
            "p_values",
            "log_likelihood",
            "n_subjects",
            "n_events",
        ],
        "prototype": True,
    },
}

DEFAULT_PARAMS: dict[str, dict[str, Any]] = {
    "r.survival.km": {"times": [1, 2, 3, 4, 5], "events": [1, 1, 0, 1, 0]},
    "r.survival.logrank": {
        "times1": [1, 2, 3, 4, 5],
        "events1": [1, 1, 1, 1, 1],
        "times2": [2, 3, 4, 5, 6],
        "events2": [1, 1, 1, 1, 1],
    },
    "r.survival.cox": {
        "times": [1, 2, 3, 4, 5],
        "events": [1, 1, 0, 1, 0],
        "covariates": [[0, 1, 0, 1, 0]],
    },
}

R_BACKEND_REQUEST_VALUES = {"r", "rpy2", "survival"}
PYTHON_BACKEND_REQUEST_VALUES = {"python", "pure_python", "fallback"}


def _optional_int(value: Any) -> int | None:
    return int(value) if value is not None else None


def _r_backend_imports() -> tuple[Any, Any, Any, Any, Any]:
    """Import rpy2/R dependencies lazily so Python-only installs still work."""
    from rpy2 import robjects
    from rpy2.robjects import default_converter, pandas2ri
    from rpy2.robjects.conversion import localconverter
    from rpy2.robjects.packages import importr

    return robjects, default_converter, pandas2ri, localconverter, importr


@lru_cache(maxsize=1)
def _r_backend_status() -> dict[str, Any]:
    """Return structured availability for rpy2, R, and R survival package."""
    try:
        robjects, _default_converter, _pandas2ri, _localconverter, importr = (
            _r_backend_imports()
        )
    except Exception as exc:  # ImportError, R discovery/runtime failures
        logger.debug("R backend unavailable while importing rpy2/R: %s", exc)
        return {
            "available": False,
            "reason": "rpy2_or_r_unavailable",
            "detail": str(exc),
            "rpy2_available": False,
            "r_survival_available": False,
        }

    try:
        version_text = str(robjects.r("R.version.string")[0])
    except Exception as exc:
        logger.debug("R backend unavailable while querying R version: %s", exc)
        return {
            "available": False,
            "reason": "r_runtime_unavailable",
            "detail": str(exc),
            "rpy2_available": True,
            "r_survival_available": False,
        }

    try:
        importr("survival")
    except Exception as exc:
        logger.debug("R survival package unavailable: %s", exc)
        return {
            "available": False,
            "reason": "r_survival_package_unavailable",
            "detail": str(exc),
            "rpy2_available": True,
            "r_survival_available": False,
            "r_version": version_text,
        }

    return {
        "available": True,
        "reason": None,
        "detail": None,
        "rpy2_available": True,
        "r_survival_available": True,
        "r_version": version_text,
        "r_package": "survival",
    }


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
        "confidence_intervals": [list(ci) for ci in result.confidence_intervals],
        "p_values": result.p_values,
        "log_likelihood": result.log_likelihood,
        "n_subjects": result.n_subjects,
        "n_events": result.n_events,
    }


def km_tool_r(times: list[float], events: list[int]) -> dict[str, Any]:
    """Kaplan-Meier via R survival::survfit."""
    robjects, _default_converter, _pandas2ri, _localconverter, importr = (
        _r_backend_imports()
    )
    importr("survival")
    r = robjects.r
    globalenv = robjects.globalenv
    previous = {
        name: globalenv.find(name) if name in globalenv else None
        for name in ("sm_time", "sm_event")
    }
    try:
        globalenv["sm_time"] = robjects.FloatVector(times)
        globalenv["sm_event"] = robjects.IntVector(events)
        fit = r("survfit(Surv(sm_time, sm_event) ~ 1, conf.type = 'log')")
        summary = r["summary"](fit)
    finally:
        for name, value in previous.items():
            if value is None:
                try:
                    del globalenv[name]
                except KeyError:
                    pass
            else:
                globalenv[name] = value
    names = list(summary.names)
    time_values = list(summary.rx2("time")) if "time" in names else []
    surv_values = list(summary.rx2("surv")) if "surv" in names else []
    lower_values = (
        list(summary.rx2("lower")) if "lower" in names else [None] * len(time_values)
    )
    upper_values = (
        list(summary.rx2("upper")) if "upper" in names else [None] * len(time_values)
    )
    n_risk_values = (
        list(summary.rx2("n.risk")) if "n.risk" in names else [None] * len(time_values)
    )
    n_event_values = (
        list(summary.rx2("n.event"))
        if "n.event" in names
        else [None] * len(time_values)
    )
    n_censor_values = (
        list(summary.rx2("n.censor"))
        if "n.censor" in names
        else [None] * len(time_values)
    )
    table = fit.rx2("table")
    table_names = list(table.names) if table.names is not None else []
    median_survival = None
    if "median" in table_names:
        median_value = float(table.rx2("median")[0])
        median_survival = None if _is_r_na_or_infinite(median_value) else median_value
    return {
        "time_points": [
            {
                "time": float(time),
                "survival_prob": float(survival),
                "confidence_lower": _none_if_r_missing(lower_values[index]),
                "confidence_upper": _none_if_r_missing(upper_values[index]),
                "at_risk": _optional_int(n_risk_values[index]),
                "events": _optional_int(n_event_values[index]),
                "censored": _optional_int(n_censor_values[index]),
            }
            for index, (time, survival) in enumerate(zip(time_values, surv_values))
        ],
        "median_survival": median_survival,
        "total_subjects": len(times),
        "total_events": sum(events),
    }


def logrank_tool_r(
    times1: list[float],
    events1: list[int],
    times2: list[float],
    events2: list[int],
) -> dict[str, Any]:
    """Log-rank test via R survival::survdiff."""
    robjects, _default_converter, _pandas2ri, _localconverter, importr = (
        _r_backend_imports()
    )
    importr("survival")
    r = robjects.r
    all_times = times1 + times2
    all_events = events1 + events2
    groups = ["group1"] * len(times1) + ["group2"] * len(times2)
    globalenv = robjects.globalenv
    previous = {
        name: globalenv.find(name) if name in globalenv else None
        for name in ("sm_time", "sm_event", "sm_group")
    }
    try:
        globalenv["sm_time"] = robjects.FloatVector(all_times)
        globalenv["sm_event"] = robjects.IntVector(all_events)
        globalenv["sm_group"] = robjects.FactorVector(robjects.StrVector(groups))
        fit = r("survdiff(Surv(sm_time, sm_event) ~ sm_group, rho = 0)")
    finally:
        for name, value in previous.items():
            if value is None:
                try:
                    del globalenv[name]
                except KeyError:
                    pass
            else:
                globalenv[name] = value
    statistic = float(fit.rx2("chisq")[0])
    df = max(len(fit.rx2("n")) - 1, 0)
    p_value = (
        float(r["pchisq"](statistic, df, **{"lower.tail": False})[0]) if df else 1.0
    )
    return {
        "statistic": statistic,
        "p_value": p_value,
        "df": df,
        "median_group1": km_tool_r(times1, events1)["median_survival"],
        "median_group2": km_tool_r(times2, events2)["median_survival"],
    }


def cox_tool_r(
    times: list[float],
    events: list[int],
    covariates: list[list[float]],
) -> dict[str, Any]:
    """Cox proportional hazards model via R survival::coxph."""
    robjects, _default_converter, _pandas2ri, _localconverter, importr = (
        _r_backend_imports()
    )
    importr("survival")
    r = robjects.r
    globalenv = robjects.globalenv
    covariate_names = [f"x{index + 1}" for index in range(len(covariates))]
    names_to_restore = ["sm_time", "sm_event", *covariate_names]
    previous = {
        name: globalenv.find(name) if name in globalenv else None
        for name in names_to_restore
    }
    try:
        globalenv["sm_time"] = robjects.FloatVector(times)
        globalenv["sm_event"] = robjects.IntVector(events)
        for name, values in zip(covariate_names, covariates):
            globalenv[name] = robjects.FloatVector(values)
        formula = "Surv(sm_time, sm_event) ~ " + " + ".join(covariate_names)
        fit = r(f"coxph({formula})")
        summary = r["summary"](fit)
        coefficients_matrix = summary.rx2("coefficients")
        confint_matrix = summary.rx2("conf.int")
    finally:
        for name, value in previous.items():
            if value is None:
                try:
                    del globalenv[name]
                except KeyError:
                    pass
            else:
                globalenv[name] = value

    n_covariates = len(covariates)
    coefficients = [
        float(coefficients_matrix.rx(row + 1, 1)[0]) for row in range(n_covariates)
    ]
    hazard_ratios = [
        float(coefficients_matrix.rx(row + 1, 2)[0]) for row in range(n_covariates)
    ]
    standard_errors = [
        float(coefficients_matrix.rx(row + 1, 3)[0]) for row in range(n_covariates)
    ]
    p_values = [
        float(coefficients_matrix.rx(row + 1, 5)[0]) for row in range(n_covariates)
    ]
    confidence_intervals = [
        [
            float(confint_matrix.rx(row + 1, 3)[0]),
            float(confint_matrix.rx(row + 1, 4)[0]),
        ]
        for row in range(n_covariates)
    ]
    log_likelihood_values = list(fit.rx2("loglik"))
    return {
        "coefficients": coefficients,
        "hazard_ratios": hazard_ratios,
        "standard_errors": standard_errors,
        "confidence_intervals": confidence_intervals,
        "p_values": p_values,
        "log_likelihood": float(log_likelihood_values[-1]),
        "n_subjects": len(times),
        "n_events": sum(events),
    }


def execute(
    action: str,
    params: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """真实执行生存分析插件动作（当前阶段接口，不承诺生产级统计）。"""
    params = params or {}
    backend = str(params.get("backend", "python")).lower()
    r_backend_requested = backend in R_BACKEND_REQUEST_VALUES
    if backend not in R_BACKEND_REQUEST_VALUES | PYTHON_BACKEND_REQUEST_VALUES:
        backend = "python"
        r_backend_requested = False
    r_backend = _r_backend_status()
    metadata = {
        "medical_boundary": MEDICAL_BOUNDARY,
        "statistics_boundary": STATISTICS_BOUNDARY,
        "prototype_only": True,
        "not_for_clinical_decision": True,
        "requires_human_review": True,
        "resource": "local-survival-analysis",
        "contract": {
            "stage": "prototype-interface-tests-only",
            "actions": ACTION_CONTRACTS,
            "default_params_are_smoke_test_fixtures": True,
        },
        "r_backend": {
            "requested": r_backend_requested,
            "selected": "r"
            if r_backend_requested and r_backend["available"]
            else "python",
            "available": r_backend["available"],
            "reason": r_backend.get("reason"),
            "detail": r_backend.get("detail"),
            "rpy2_available": r_backend.get("rpy2_available", False),
            "r_survival_available": r_backend.get("r_survival_available", False),
            "r_version": r_backend.get("r_version"),
            "r_package": r_backend.get("r_package"),
        },
        "audit": {
            "interface_only": True,
            "prototype_path": True,
            "rpy2_available": r_backend.get("rpy2_available", False),
            "r_backend_available": r_backend["available"],
            "r_backend_selected": "r"
            if r_backend_requested and r_backend["available"]
            else "python",
            "context_keys": sorted((context or {}).keys()),
        },
    }
    if r_backend_requested and not r_backend["available"]:
        return plugin_result(
            status="plugin_unavailable",
            plugin="r-survival",
            action=action,
            error=f"R survival backend unavailable: {r_backend['reason']}",
            metadata=metadata,
        )
    try:
        if action == "r.survival.km":
            times = as_float_list(
                param_or_default(params, "times", DEFAULT_PARAMS[action]["times"]),
                "times",
            )
            events = _as_event_list(
                param_or_default(params, "events", DEFAULT_PARAMS[action]["events"]),
                "events",
            )
            result = (
                km_tool_r(times, events)
                if r_backend_requested
                else km_tool(times, events)
            )
        elif action == "r.survival.logrank":
            times1 = as_float_list(
                param_or_default(params, "times1", DEFAULT_PARAMS[action]["times1"]),
                "times1",
            )
            events1 = _as_event_list(
                param_or_default(params, "events1", DEFAULT_PARAMS[action]["events1"]),
                "events1",
            )
            times2 = as_float_list(
                param_or_default(params, "times2", DEFAULT_PARAMS[action]["times2"]),
                "times2",
            )
            events2 = _as_event_list(
                param_or_default(params, "events2", DEFAULT_PARAMS[action]["events2"]),
                "events2",
            )
            result = (
                logrank_tool_r(times1, events1, times2, events2)
                if r_backend_requested
                else logrank_tool(times1, events1, times2, events2)
            )
        elif action == "r.survival.cox":
            times = as_float_list(
                param_or_default(params, "times", DEFAULT_PARAMS[action]["times"]),
                "times",
            )
            events = _as_event_list(
                param_or_default(params, "events", DEFAULT_PARAMS[action]["events"]),
                "events",
            )
            covariates = as_float_groups(
                param_or_default(
                    params, "covariates", DEFAULT_PARAMS[action]["covariates"]
                ),
                "covariates",
            )
            result = (
                cox_tool_r(times, events, covariates)
                if r_backend_requested
                else cox_tool(times, events, covariates)
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


def _none_if_r_missing(value: Any) -> float | None:
    number = float(value)
    return None if _is_r_na_or_infinite(number) else number


def _is_r_na_or_infinite(value: float) -> bool:
    return value != value or value in (float("inf"), float("-inf"))


def _as_event_list(value: Any, name: str) -> list[int]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list of 0/1 event indicators")
    events = [int(item) for item in value]
    if any(item not in (0, 1) for item in events):
        raise ValueError(f"{name} must contain only 0 or 1")
    return events
