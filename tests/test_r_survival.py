from plugins.tools.r_survival.kaplan_meier import kaplan_meier
from plugins.tools.r_survival.logrank import logrank_test
from plugins.tools.r_survival.cox_model import cox_ph
from plugins.tools.r_survival import main as r_survival_main
from plugins.tools.r_survival.main import execute


# Synthetic toy vectors derived from general R survival::Surv/survfit behavior.
# These fixtures are self-contained and are not copied from external raw project data.
TOY_TIMES = [1, 2, 3, 4, 5]
TOY_EVENTS = [1, 1, 0, 1, 0]


def assert_prototype_contract(result, action):
    assert result["status"] == "success"
    assert result["plugin"] == "r-survival"
    assert result["action"] == action
    assert result["error"] is None
    assert result["metadata"]["audit"]["interface_only"] is True
    assert result["metadata"]["audit"]["prototype_path"] is True
    assert result["metadata"]["prototype_only"] is True
    assert result["metadata"]["not_for_clinical_decision"] is True
    assert result["metadata"]["requires_human_review"] is True
    assert result["metadata"]["contract"]["stage"] == "prototype-interface-tests-only"
    assert result["metadata"]["contract"]["actions"][action]["prototype"] is True
    assert "no production-grade or clinical-grade" in result["metadata"]["statistics_boundary"]


class TestKaplanMeier:
    def test_basic(self):
        times = [1, 2, 3, 4, 5]
        events = [1, 1, 0, 1, 0]
        result = kaplan_meier(times, events)
        assert result.total_subjects == 5
        assert result.total_events == 3
        assert len(result.time_points) == 3  # 3 个事件时间点

    def test_all_events(self):
        times = [1, 2, 3]
        events = [1, 1, 1]
        result = kaplan_meier(times, events)
        assert result.total_events == 3
        assert result.time_points[-1].survival_prob == 0.0

    def test_all_censored(self):
        times = [1, 2, 3]
        events = [0, 0, 0]
        result = kaplan_meier(times, events)
        assert result.total_events == 0
        assert len(result.time_points) == 0

    def test_median_survival(self):
        times = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        events = [1, 1, 1, 1, 1, 0, 0, 0, 0, 0]
        result = kaplan_meier(times, events)
        assert result.median_survival == 5  # 生存概率在 t=5 时降到 0.5


class TestLogRank:
    def test_different_groups(self):
        times1 = [1, 2, 3, 4, 5]
        events1 = [1, 1, 1, 1, 1]
        times2 = [6, 7, 8, 9, 10]
        events2 = [1, 1, 1, 1, 1]
        result = logrank_test(times1, events1, times2, events2)
        assert result.statistic > 0
        assert result.p_value < 0.05

    def test_same_groups(self):
        times1 = [1, 2, 3, 4, 5]
        events1 = [1, 1, 1, 1, 1]
        times2 = [1, 2, 3, 4, 5]
        events2 = [1, 1, 1, 1, 1]
        result = logrank_test(times1, events1, times2, events2)
        assert result.p_value > 0.05  # 不应显著


class TestCoxPH:
    def test_basic(self):
        times = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        events = [1, 1, 1, 1, 1, 0, 0, 0, 0, 0]
        covariates = [[0, 0, 0, 0, 0, 1, 1, 1, 1, 1]]
        result = cox_ph(times, events, covariates)
        assert len(result.coefficients) == 1
        assert len(result.hazard_ratios) == 1
        assert result.n_subjects == 10


class TestRSurvivalContract:
    def test_km_execute_contract_is_deterministic_prototype(self):
        result = execute("r.survival.km", {"times": TOY_TIMES, "events": TOY_EVENTS}, {"caller": "test"})
        assert_prototype_contract(result, "r.survival.km")
        assert result["output"]["total_subjects"] == 5
        assert result["output"]["total_events"] == 3
        assert result["output"]["time_points"][0]["time"] == 1.0
        assert result["output"]["time_points"][0]["survival_prob"] == 0.8
        assert result["metadata"]["r_backend"]["selected"] == "python"

    def test_logrank_execute_contract_shape(self):
        result = execute("r.survival.logrank", {
            "times1": [1, 2, 3, 4, 5], "events1": [1, 1, 1, 1, 1],
            "times2": [1, 2, 3, 4, 5], "events2": [1, 1, 1, 1, 1],
        })
        assert_prototype_contract(result, "r.survival.logrank")
        assert set(result["output"]) == {"statistic", "p_value", "df", "median_group1", "median_group2"}

    def test_invalid_event_indicator_returns_structured_error(self):
        result = execute("r.survival.km", {"times": [1, 2, 3], "events": [1, 2, 0]})
        assert result["status"] == "plugin_error"
        assert result["output"] is None
        assert "Invalid r-survival input" in result["error"]
        assert result["metadata"]["contract"]["stage"] == "prototype-interface-tests-only"

    def test_unsupported_action_returns_structured_error_with_boundary(self):
        result = execute("r.survival.missing", {})
        assert result["status"] == "plugin_error"
        assert result["output"] is None
        assert "Unsupported r-survival action" in result["error"]
        assert "not production/clinical medical advice" in result["metadata"]["medical_boundary"]

    def test_requested_r_backend_unavailable_returns_structured_unavailable(self, monkeypatch):
        r_survival_main._r_backend_status.cache_clear()
        monkeypatch.setattr(
            r_survival_main,
            "_r_backend_status",
            lambda: {
                "available": False,
                "reason": "rpy2_or_r_unavailable",
                "detail": "synthetic missing rpy2/R",
                "rpy2_available": False,
                "r_survival_available": False,
            },
        )
        result = execute("r.survival.km", {"backend": "r", "times": TOY_TIMES, "events": TOY_EVENTS})
        assert result["status"] == "plugin_unavailable"
        assert result["output"] is None
        assert "R survival backend unavailable" in result["error"]
        assert result["metadata"]["r_backend"]["requested"] is True
        assert result["metadata"]["r_backend"]["selected"] == "python"
        assert result["metadata"]["r_backend"]["reason"] == "rpy2_or_r_unavailable"
        assert result["metadata"]["audit"]["r_backend_available"] is False

    def test_requested_r_backend_km_uses_r_path_when_available(self, monkeypatch):
        monkeypatch.setattr(
            r_survival_main,
            "_r_backend_status",
            lambda: {
                "available": True,
                "reason": None,
                "detail": None,
                "rpy2_available": True,
                "r_survival_available": True,
                "r_version": "R version synthetic",
                "r_package": "survival",
            },
        )
        monkeypatch.setattr(
            r_survival_main,
            "km_tool_r",
            lambda times, events: {"backend_marker": "r", "total_subjects": len(times), "total_events": sum(events)},
        )
        result = execute("r.survival.km", {"backend": "r", "times": TOY_TIMES, "events": TOY_EVENTS})
        assert_prototype_contract(result, "r.survival.km")
        assert result["output"] == {"backend_marker": "r", "total_subjects": 5, "total_events": 3}
        assert result["metadata"]["r_backend"]["requested"] is True
        assert result["metadata"]["r_backend"]["selected"] == "r"
        assert result["metadata"]["r_backend"]["r_survival_available"] is True
