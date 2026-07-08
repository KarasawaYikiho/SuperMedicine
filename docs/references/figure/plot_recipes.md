# Plot Recipes

Use these as starting points. Confirm assumptions before publishing figures.

## Distribution

Use histogram or KDE for one continuous variable. For small samples, show raw
points instead of smoothing.

## Group Comparison

Use box/violin plus raw point overlay for categorical x continuous data. Avoid
mean-only bars unless sample size and distribution justify them.

## Relationship

Use scatter plots for two continuous variables. Add regression lines and
confidence bands only when the relationship is meaningful and assumptions are
reasonable.

## Time or Dose

Use line plots for ordered x-values such as time, dose, or sequence. Do not
connect unrelated categories with lines.

## Correlation

Use heatmaps for many numeric variables. Center diverging palettes at zero when
positive and negative values both matter.

## Matrix Data

Use heatmaps with perceptually uniform palettes. Avoid `jet`, `rainbow`, and
3D effects.
