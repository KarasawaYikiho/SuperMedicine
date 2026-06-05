# Python Data Analysis Workspace Tool

Workspace tool with stable, light-dependency implementations for common
data-analysis workflows. It uses only the Python standard library for baseline
actions so importing/scanning the catalog does not require NumPy, pandas,
scikit-learn, XGBoost, or LightGBM.

Supported light actions: descriptive statistics, missing-value analysis, standardization/min-max normalization, Pearson/Spearman correlation, linear regression, simple logistic regression, PCA, KMeans, hierarchical clustering summary, time-series basics, Welch t-test, chi-square test, and one-way ANOVA.

Optional heavy actions: random forest and gradient boosting wrappers report missing optional packages (`scikit-learn`, `xgboost`, `lightgbm`) without importing them eagerly.

## Safety Boundary

This tool is for research-support prototyping only. It is not production-grade,
clinical-grade, or regulatory-grade statistical software. Keep inputs and outputs
inside the selected workspace, do not embed credentials, and review all results
with qualified statistical and domain expertise.
