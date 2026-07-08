# Python Data Analysis Tool

Workspace-local data-analysis helper for lightweight research prototypes. The
baseline actions use the Python standard library so the tool can be scanned and
imported without NumPy, pandas, scikit-learn, XGBoost, or LightGBM.

## Baseline Actions

- descriptive statistics
- missing-value summary
- standardization and min-max normalization
- Pearson and Spearman correlation
- linear regression
- simple logistic regression
- PCA
- KMeans
- hierarchical clustering summary
- time-series basics
- Welch t-test
- chi-square test
- one-way ANOVA

Optional random-forest and gradient-boosting actions report missing optional
packages instead of importing them eagerly.

## Boundary

This is research-support prototype tooling. It is not production-grade,
clinical-grade, or regulatory-grade statistical software. Keep inputs and outputs
inside the selected workspace and review results with qualified domain and
statistical expertise.
