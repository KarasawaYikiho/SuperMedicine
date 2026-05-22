from plugins.tools.python_stats.main import descriptive, ttest, anova, regression


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
