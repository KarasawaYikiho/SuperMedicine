from __future__ import annotations

from plugins.tools.python_stats.main import (
    execute,
    descriptive,
    ttest,
    anova,
    regression,
)


def assert_prototype_contract(result, action):
    assert result["status"] == "success"
    assert result["plugin"] == "python-stats"
    assert result["action"] == action
    assert result["error"] is None
    assert result["metadata"]["audit"]["interface_only"] is True
    assert result["metadata"]["audit"]["prototype_path"] is True
    assert result["metadata"]["prototype_only"] is True
    assert result["metadata"]["not_for_clinical_decision"] is True
    assert result["metadata"]["requires_human_review"] is True
    assert result["metadata"]["contract"]["stage"] == "prototype-interface-tests-only"
    assert result["metadata"]["contract"]["actions"][action]["prototype"] is True
    assert (
        "no production-grade or clinical-grade"
        in result["metadata"]["statistics_boundary"]
    )


class TestDescriptive:
    def test_basic(self):
        result = descriptive([1, 2, 3, 4, 5])
        assert result["count"] == 5
        assert result["mean"] == 3.0
        assert result["min"] == 1
        assert result["max"] == 5

    def test_empty(self):
        result = descriptive([])
        assert result["count"] == 0


class TestTtest:
    def test_different_groups(self):
        g1 = [1, 2, 3, 4, 5]
        g2 = [6, 7, 8, 9, 10]
        result = ttest(g1, g2)
        assert result["p_value"] < 0.05
        assert result["statistic"] < 0

    def test_same_groups(self):
        g1 = [1, 2, 3, 4, 5]
        g2 = [1, 2, 3, 4, 5]
        result = ttest(g1, g2)
        assert result["statistic"] == 0


class TestAnova:
    def test_three_groups(self):
        g1 = [1, 2, 3]
        g2 = [4, 5, 6]
        g3 = [7, 8, 9]
        result = anova(g1, g2, g3)
        assert result["f_statistic"] > 0
        assert result["p_value"] < 0.05


class TestRegression:
    def test_linear(self):
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]
        result = regression(x, y)
        assert result["slope"] == 2.0
        assert result["intercept"] == 0.0
        assert result["r_squared"] == 1.0


class TestPythonStatsContract:
    def test_descriptive_execute_contract_is_deterministic_prototype(self):
        result = execute(
            "stats.descriptive", {"data": [1, 2, 3, 4, 5]}, {"caller": "test"}
        )
        assert_prototype_contract(result, "stats.descriptive")
        assert result["output"] == {
            "count": 5,
            "mean": 3.0,
            "std": 1.5811,
            "min": 1.0,
            "max": 5.0,
            "median": 3.0,
        }

    def test_regression_rejects_mismatched_input_with_structured_error(self):
        result = execute("stats.regression", {"x": [1, 2, 3], "y": [2, 4]})
        assert result["status"] == "plugin_error"
        assert result["output"] is None
        assert "Invalid python-stats input" in result["error"]
        assert (
            result["metadata"]["contract"]["stage"] == "prototype-interface-tests-only"
        )

    def test_unsupported_action_returns_structured_error_with_boundary(self):
        result = execute("stats.missing", {})
        assert result["status"] == "plugin_error"
        assert result["output"] is None
        assert "Unsupported python-stats action" in result["error"]
        assert (
            "not production/clinical medical advice"
            in result["metadata"]["medical_boundary"]
        )
