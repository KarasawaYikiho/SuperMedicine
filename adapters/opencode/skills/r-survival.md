---
name: supermedicine-r-survival
description: Survival analysis tools via R — Kaplan-Meier estimation, log-rank test, Cox proportional hazards
---

# R Survival Analysis

Survival analysis toolkit for time-to-event medical research data. Current
implementations are prototype/interface test paths only, not production-grade or
clinical-grade statistics, and require expert review before research, regulatory,
or clinical use.

This optional OpenCode-facing summary documents the survival-analysis boundary
locally because the skill may be consumed independently of the full repository
documentation.

OpenCode AI provider metadata is supplied by installer flags, `SM_LLM_*`
environment variables, provider key environment variables, or `.supermedicine/config.yaml`.
The add-on declares OpenAI-compatible, Anthropic-compatible, and OpenRouter
gateway formats, supports custom compatible BaseURL values, redacts secrets as
`<redacted>`, and degrades without an injected orchestrator/runtime bridge. Do not
include plaintext API keys, private endpoints, or raw logs in skill docs.

## Capabilities
- Kaplan-Meier estimator — survival curve estimation with confidence intervals
- Log-rank test — compare survival between groups
- Cox proportional hazards model — multivariate survival regression

## Prerequisites
The plugin exposes a pure-Python fallback. Optional formal R backend support
requires R >= 4.3, the R `survival` package, and rpy2 Python package:
```bash
pip install -e ".[r]"
R -e "install.packages('survival', repos='https://cran.r-project.org')"
```
Request the R backend by passing `"backend": "r"`; unavailable R dependencies
return a structured `plugin_unavailable` result.

## Usage
```python
from plugins.tools.r_survival.main import execute

result = execute(
    "r.survival.km",
    {
        "times": [5, 10, 15, 20, 25],
        "events": [1, 1, 0, 1, 0],
    },
)
time_points = result["output"]["time_points"]
```

Direct Kaplan-Meier function API example:

```python
from plugins.tools.r_survival.kaplan_meier import kaplan_meier

result = kaplan_meier(
    times=[5, 10, 15, 20, 25],
    events=[1, 1, 0, 1, 0],
)
```

## Trigger
Use when analyzing time-to-event data in clinical trials, cohort studies,
or any medical research involving censored survival data.
