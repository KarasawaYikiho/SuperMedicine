---
name: supermedicine-python-stats
description: Statistical analysis tools in Python — descriptive statistics, t-test, ANOVA, linear regression
---

# Python Statistics

Statistical analysis toolkit for medical research data.

## Capabilities
- Descriptive statistics — mean, median, std, quartiles, skewness, kurtosis
- Student's t-test — independent and paired samples
- One-way ANOVA — with F-statistic and p-value
- Linear regression — coefficients, R-squared, p-values

## Usage
```python
from plugins.tools.python_stats.main import descriptive_stats, ttest_independent
stats = descriptive_stats([1.2, 2.3, 3.1, 4.0, 5.2])
result = ttest_independent(group_a=[1,2,3,4,5], group_b=[2,3,4,5,6])
```

## Trigger
Use when performing statistical analysis on medical research data, including
descriptive summaries, group comparisons, or regression modeling.
