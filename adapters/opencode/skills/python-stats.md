---
name: supermedicine-python-stats
description: Statistical analysis tools in Python — descriptive statistics, t-test, ANOVA, linear regression
---

# Python Statistics

Statistical analysis toolkit for medical research data. Current implementations
are prototype/interface test paths only, not production-grade or clinical-grade
statistics, and require expert review before research, regulatory, or clinical use.

## Capabilities
- Descriptive statistics — mean, median, std, quartiles, skewness, kurtosis
- Student's t-test — independent and paired samples
- One-way ANOVA — with F-statistic and p-value
- Linear regression — coefficients, R-squared, p-values

## Usage
```python
from plugins.tools.python_stats.main import execute

stats = execute("stats.descriptive", {"data": [1.2, 2.3, 3.1, 4.0, 5.2]})
ttest = execute("stats.ttest", {"group1": [1, 2, 3, 4, 5], "group2": [2, 3, 4, 5, 6]})
```

Direct function API example:

```python
from plugins.tools.python_stats.main import descriptive, ttest

stats = descriptive([1.2, 2.3, 3.1, 4.0, 5.2])
result = ttest([1, 2, 3, 4, 5], [2, 3, 4, 5, 6])
```

## Trigger
Use when performing statistical analysis on medical research data, including
descriptive summaries, group comparisons, or regression modeling.
