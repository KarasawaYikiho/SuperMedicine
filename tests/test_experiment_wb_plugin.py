from __future__ import annotations

from core.plugin_registry import PluginRegistry


def _plugin():
    registry = PluginRegistry("plugins")
    metas = registry.discover()
    meta = registry.get_meta("experiment-wb")
    assert meta is not None
    assert meta.name in [item.name for item in metas]
    return registry.get("experiment-wb")


def test_experiment_wb_plugin_is_discovered_with_actions():
    registry = PluginRegistry("plugins")
    registry.discover()
    meta = registry.get_meta("experiment-wb")

    assert meta is not None
    assert {item["id"] for item in meta.provides} == {
        "experiment.wb.normalize_loading",
        "experiment.wb.antibody_dilution",
    }


def test_normalize_loading_returns_deterministic_wb_volumes():
    result = _plugin().execute(
        "experiment.wb.normalize_loading",
        {
            "target_protein_amount": 20,
            "final_well_volume": 20,
            "max_sample_volume": 15,
            "samples": [
                {"name": "A", "concentration": 2.0},
                {"name": "B", "concentration": 1.0},
            ],
        },
    )

    assert result["status"] == "success"
    assert result["plugin"] == "experiment-wb"
    assert result["action"] == "experiment.wb.normalize_loading"
    output = result["output"]
    assert output["target_protein_amount"] == 20.0
    assert output["volume_unit"] == "ul"
    assert output["samples"][0]["sample_volume"] == 10.0
    assert output["samples"][0]["diluent_volume"] == 10.0
    assert output["samples"][0]["within_limits"] is True
    assert output["samples"][1]["sample_volume"] == 20.0
    assert output["samples"][1]["diluent_volume"] == 0.0
    assert output["samples"][1]["within_limits"] is False
    assert output["samples"][1]["warnings"][0]["code"] == "sample_volume_exceeds_max"
    assert result["metadata"]["contract"]["calculation_scope"] == "deterministic_arithmetic"


def test_antibody_dilution_returns_deterministic_reagent_volumes():
    result = _plugin().execute(
        "experiment.wb.antibody_dilution",
        {"total_volume": 10000, "dilution_ratio": "1:5000", "antibody_name": "anti-ACTB"},
    )

    assert result["status"] == "success"
    assert result["output"] == {
        "antibody_name": "anti-ACTB",
        "total_volume": 10000.0,
        "dilution_ratio": "1:5000",
        "antibody_volume": 2.0,
        "diluent_volume": 9998.0,
        "volume_unit": "ul",
    }


def test_experiment_wb_invalid_input_is_structured_plugin_error():
    result = _plugin().execute(
        "experiment.wb.normalize_loading",
        {"target_protein_amount": 20, "samples": [{"name": "A", "concentration": 0}]},
    )

    assert result["status"] == "plugin_error"
    assert result["output"] is None
    assert "Invalid experiment-wb input" in result["error"]
    assert "concentration" in result["error"]


def test_experiment_wb_missing_input_is_structured_plugin_error():
    result = _plugin().execute("experiment.wb.antibody_dilution", {"total_volume": 1000})

    assert result["status"] == "plugin_error"
    assert result["output"] is None
    assert "dilution_ratio is required" in result["error"]


def test_experiment_wb_unknown_action_is_rejected_without_calculation_output():
    result = _plugin().execute(
        "experiment.wb.external_lookup",
        {"query": "should-not-run"},
    )

    assert result["status"] == "plugin_error"
    assert result["plugin"] == "experiment-wb"
    assert result["action"] == "experiment.wb.external_lookup"
    assert result["output"] is None
    assert "Unsupported experiment-wb action" in result["error"]
    assert result["metadata"]["contract"]["calculation_scope"] == "deterministic_arithmetic"
