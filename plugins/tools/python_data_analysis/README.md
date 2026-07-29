# Python Data Analysis Tool

This workspace-local tool provides lightweight exploratory analyses for
research prototypes. Baseline actions use the Python standard library so
scanner discovery and import do not require NumPy, pandas, scikit-learn,
XGBoost, or LightGBM.

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

## Review Boundary

This is research-support prototype tooling. It is not production-grade,
clinical-grade, or regulatory-grade statistical software. Keep inputs and outputs
inside the selected workspace and review results with qualified domain and
statistical expertise.
