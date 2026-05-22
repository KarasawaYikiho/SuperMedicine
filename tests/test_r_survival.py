import pytest
from plugins.tools.r_survival.kaplan_meier import kaplan_meier
from plugins.tools.r_survival.logrank import logrank_test
from plugins.tools.r_survival.cox_model import cox_ph


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
