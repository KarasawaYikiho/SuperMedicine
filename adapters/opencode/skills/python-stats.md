---
name: supermedicine-python-stats
description: Statistical analysis tools in Python — descriptive statistics, t-test, ANOVA, linear regression
---

# Python Statistics

Statistical analysis toolkit for medical research data. Current implementations
are prototype/interface test paths only, not production-grade or clinical-grade
statistics, and require expert review before research, regulatory, or clinical use.

This optional OpenCode-facing summary documents the available prototype actions
without changing plugin APIs or claiming clinical/statistical certification.

OpenCode AI provider metadata is supplied by installer flags, `SM_LLM_*`
environment variables, provider key environment variables, or `.supermedicine/config.yaml`.
The add-on declares OpenAI-compatible, Anthropic-compatible, and OpenRouter
gateway formats, supports custom compatible BaseURL values, redacts secrets as
`<redacted>`, and degrades without an injected orchestrator/runtime bridge. Do not
include plaintext API keys, private endpoints, or raw logs in skill docs.

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
