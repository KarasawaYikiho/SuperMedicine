# Data Profiling

The figure profiling report describes columns, sample sizes, missing values,
groups, correlations, and plotting warnings. Use it to choose a chart, then
verify the decision manually.

## Read the Report in This Order

1. Confirm column types.
2. Check sample size per group.
3. Check missing values.
4. Check skew and outliers.
5. Check correlations.
6. Choose a chart from [chart_selection.md](chart_selection.md).

## Column Types

| Type | Meaning | Common use |
| --- | --- | --- |
| continuous | numeric with many values | y-axis, scatter, distribution |
| ordinal | small ordered integers | ordered x-axis when truly ordered |
| categorical | labels or few repeated values | x-axis, hue, facets |
| boolean | two values | split/grouping variable |
| datetime | dates/times | time axis |
| text | ids or notes | usually not plotted |

## Warnings

- Small groups need raw point display.
- Highly skewed values may need median/IQR, box/violin, or a log axis.
- Missingness above 5% should be reported; above 20% needs investigation.
- Outliers should be shown, annotated, or removed only with a documented reason.

Profiling output is a decision aid, not a statistical review.
