---
name: supermedicine-r-survival
description: Survival analysis tools via R — Kaplan-Meier estimation, log-rank test, Cox proportional hazards
---

# R Survival Analysis

Survival analysis toolkit for time-to-event medical research data.

## Capabilities
- Kaplan-Meier estimator — survival curve estimation with confidence intervals
- Log-rank test — compare survival between groups
- Cox proportional hazards model — multivariate survival regression

## Prerequisites
Requires R >= 4.3 and rpy2 Python package:
```bash
pip install rpy2
```

## Usage
```python
from plugins.tools.r_survival.kaplan_meier import kaplan_meier
result = kaplan_meier(
    times=[5, 10, 15, 20, 25],
    events=[1, 1, 0, 1, 0],
    groups=["A", "A", "B", "B", "B"]
)
```

## Trigger
Use when analyzing time-to-event data in clinical trials, cohort studies,
or any medical research involving censored survival data.
