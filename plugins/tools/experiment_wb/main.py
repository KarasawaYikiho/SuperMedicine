"""Western Blot experiment calculation plugin entry point.

The plugin exposes deterministic bench-calculation helpers through the standard
``plugin.yaml + main.py execute(action, params, context)`` contract. It performs
only arithmetic and input validation; it does not provide clinical advice or
replace local laboratory SOP review.
"""

from __future__ import annotations

from typing import Any

from plugins.base_plugin import plugin_result


PLUGIN_NAME = "experiment-wb"

MEDICAL_BOUNDARY = (
    "Current-stage SuperMedicine output: deterministic experiment calculation "
    "helper only; not clinical medical advice, not a validated wet-lab SOP, and "
    "requires qualified human review before laboratory use."
)

ACTION_CONTRACTS: dict[str, dict[str, Any]] = {
    "experiment.wb.normalize_loading": {
        "required_params": {
            "samples": "list[dict{name, concentration}]",
            "target_protein_amount": "number",
        },
        "optional_params": {
            "final_well_volume": "number",
            "max_sample_volume": "number",
            "concentration_unit": "ug_per_ul|mg_per_ml",
            "volume_unit": "ul",
        },
        "output_fields": [
            "samples",
            "target_protein_amount",
            "final_well_volume",
            "volume_unit",
        ],
    },
    "experiment.wb.antibody_dilution": {
        "required_params": {
            "total_volume": "number",
            "dilution_ratio": "number|str 1:N",
        },
        "optional_params": {"antibody_name": "str", "volume_unit": "ul"},
        "output_fields": [
            "antibody_volume",
            "diluent_volume",
            "total_volume",
            "dilution_ratio",
        ],
    },
}


def normalize_loading(
    samples: list[dict[str, Any]],
    target_protein_amount: float,
    *,
    final_well_volume: float | None = None,
    max_sample_volume: float | None = None,
    concentration_unit: str = "ug_per_ul",
    volume_unit: str = "ul",
) -> dict[str, Any]:
    """Calculate sample and diluent volumes for WB loading normalization."""
    if concentration_unit not in {"ug_per_ul", "mg_per_ml"}:
        raise ValueError("concentration_unit must be 'ug_per_ul' or 'mg_per_ml'")
    if volume_unit != "ul":
        raise ValueError("volume_unit must be 'ul'")
    if target_protein_amount <= 0:
        raise ValueError("target_protein_amount must be > 0")
    if final_well_volume is not None and final_well_volume <= 0:
        raise ValueError("final_well_volume must be > 0 when provided")
    if max_sample_volume is not None and max_sample_volume <= 0:
        raise ValueError("max_sample_volume must be > 0 when provided")
    if not isinstance(samples, list) or not samples:
        raise ValueError("samples must be a non-empty list")

    rows: list[dict[str, Any]] = []
    for index, sample in enumerate(samples):
        if not isinstance(sample, dict):
            raise ValueError(f"samples[{index}] must be a dictionary")
        name = sample.get("name", f"sample-{index + 1}")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                f"samples[{index}].name must be a non-empty string when provided"
            )
        concentration = _positive_float(
            sample.get("concentration"), f"samples[{index}].concentration"
        )
        sample_volume = target_protein_amount / concentration
        violates_max_sample_volume = (
            max_sample_volume is not None and sample_volume > max_sample_volume
        )
        if final_well_volume is not None:
            diluent_volume = final_well_volume - sample_volume
            below_final_volume = diluent_volume < 0
        else:
            diluent_volume = 0.0
            below_final_volume = False
        rows.append(
            {
                "name": name,
                "concentration": _round(concentration),
                "concentration_unit": concentration_unit,
                "target_protein_amount": _round(target_protein_amount),
                "protein_amount_unit": "ug",
                "sample_volume": _round(sample_volume),
                "diluent_volume": _round(diluent_volume),
                "final_well_volume": _round(final_well_volume)
                if final_well_volume is not None
                else _round(sample_volume),
                "volume_unit": volume_unit,
                "within_limits": not violates_max_sample_volume
                and not below_final_volume,
                "warnings": _normalization_warnings(
                    violates_max_sample_volume, below_final_volume
                ),
            }
        )

    return {
        "samples": rows,
        "target_protein_amount": _round(target_protein_amount),
        "protein_amount_unit": "ug",
        "final_well_volume": _round(final_well_volume)
        if final_well_volume is not None
        else None,
        "max_sample_volume": _round(max_sample_volume)
        if max_sample_volume is not None
        else None,
        "volume_unit": volume_unit,
        "concentration_unit": concentration_unit,
    }


def antibody_dilution(
    total_volume: float,
    dilution_ratio: float,
    *,
    antibody_name: str | None = None,
    volume_unit: str = "ul",
) -> dict[str, Any]:
    """Calculate antibody stock and diluent volumes for a 1:N dilution."""
    if volume_unit != "ul":
        raise ValueError("volume_unit must be 'ul'")
    if total_volume <= 0:
        raise ValueError("total_volume must be > 0")
    if dilution_ratio <= 1:
        raise ValueError("dilution_ratio must be > 1 and represent a 1:N dilution")

    antibody_volume = total_volume / dilution_ratio
    diluent_volume = total_volume - antibody_volume
    return {
        "antibody_name": antibody_name,
        "total_volume": _round(total_volume),
        "dilution_ratio": f"1:{_format_ratio(dilution_ratio)}",
        "antibody_volume": _round(antibody_volume),
        "diluent_volume": _round(diluent_volume),
        "volume_unit": volume_unit,
    }


def execute(
    action: str,
    params: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute supported WB experiment calculation actions."""
    params = params or {}
    metadata = _base_metadata(context or {})
    try:
        if action == "experiment.wb.normalize_loading":
            output = normalize_loading(
                _required_samples(params),
                _positive_float(
                    params.get("target_protein_amount"), "target_protein_amount"
                ),
                final_well_volume=_optional_positive_float(
                    params.get("final_well_volume"), "final_well_volume"
                ),
                max_sample_volume=_optional_positive_float(
                    params.get("max_sample_volume"), "max_sample_volume"
                ),
                concentration_unit=str(params.get("concentration_unit", "ug_per_ul")),
                volume_unit=str(params.get("volume_unit", "ul")),
            )
        elif action == "experiment.wb.antibody_dilution":
            output = antibody_dilution(
                _positive_float(params.get("total_volume"), "total_volume"),
                _dilution_ratio(params.get("dilution_ratio")),
                antibody_name=_optional_str(
                    params.get("antibody_name"), "antibody_name"
                ),
                volume_unit=str(params.get("volume_unit", "ul")),
            )
        else:
            return plugin_result(
                status="plugin_error",
                plugin=PLUGIN_NAME,
                action=action,
                error=f"Unsupported experiment-wb action: {action}",
                metadata=metadata,
            )
    except (TypeError, ValueError) as exc:
        return plugin_result(
            status="plugin_error",
            plugin=PLUGIN_NAME,
            action=action,
            error=f"Invalid experiment-wb input: {exc}",
            metadata=metadata,
        )

    return plugin_result(
        status="success",
        plugin=PLUGIN_NAME,
        action=action,
        output=output,
        metadata=metadata,
    )


def _base_metadata(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "medical_boundary": MEDICAL_BOUNDARY,
        "resource": {
            "kind": "experiment_calculation",
            "plugin": PLUGIN_NAME,
            "experiment": "western_blot",
        },
        "contract": {
            "actions": ACTION_CONTRACTS,
            "calculation_scope": "deterministic_arithmetic",
        },
        "audit": {
            "interface_only": True,
            "deterministic_calculation": True,
            "context_keys": sorted(context.keys()),
        },
    }


def _required_samples(params: dict[str, Any]) -> list[dict[str, Any]]:
    if "samples" not in params:
        raise ValueError("samples is required")
    samples = params["samples"]
    if not isinstance(samples, list):
        raise ValueError("samples must be a list")
    return samples


def _positive_float(value: Any, name: str) -> float:
    if value is None:
        raise ValueError(f"{name} is required")
    number = float(value)
    if number <= 0:
        raise ValueError(f"{name} must be > 0")
    return number


def _optional_positive_float(value: Any, name: str) -> float | None:
    if value is None:
        return None
    return _positive_float(value, name)


def _optional_str(value: Any, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string when provided")
    return value


def _dilution_ratio(value: Any) -> float:
    if value is None:
        raise ValueError("dilution_ratio is required")
    if isinstance(value, str):
        text = value.strip().lower()
        if text.startswith("1:"):
            return _positive_float(text.split(":", 1)[1], "dilution_ratio")
        if text.endswith("x"):
            text = text[:-1]
        return _positive_float(text, "dilution_ratio")
    return _positive_float(value, "dilution_ratio")


def _normalization_warnings(
    violates_max_sample_volume: bool, below_final_volume: bool
) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    if violates_max_sample_volume:
        warnings.append(
            {
                "code": "sample_volume_exceeds_max",
                "message": "Calculated sample volume exceeds max_sample_volume.",
            }
        )
    if below_final_volume:
        warnings.append(
            {
                "code": "sample_volume_exceeds_final",
                "message": "Calculated sample volume exceeds final_well_volume.",
            }
        )
    return warnings


def _round(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 4)


def _format_ratio(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(_round(value))
