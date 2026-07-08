# Chart Selection

Choose the chart from the question, not from the plotting library.

## Quick Guide

| Data shape | Default chart | Avoid |
| --- | --- | --- |
| One continuous variable | Histogram or KDE | Pie, line |
| One categorical variable | Sorted horizontal bar | Pie, 3D pie |
| Categorical x continuous | Box/violin plus raw points | Mean-only bar for small n |
| Two continuous variables | Scatter plus fit/CI when useful | Line unless x is ordered |
| Time or dose series | Line plus uncertainty band | Bar |
| Correlation matrix | Heatmap with centered diverging palette | Rainbow/jet |
| Many variables | Clustered heatmap, PCA, or UMAP | Pairplot overload |

## Sample Size Rules

- `n < 3`: show each point; do not draw box/violin/error bars.
- `3 <= n < 10`: use dot/strip/beeswarm plots.
- `10 <= n < 30`: use box/violin with raw point overlay.
- `n >= 30`: box, violin, or summarized error plots can be reasonable.

## Split the Figure When

- more than 6 legend items are needed;
- more than 8 x-axis categories collide;
- the y-axis spans orders of magnitude and a log scale is unsuitable;
- the figure is trying to make two different arguments.

## Safety

Figure helpers provide research-support guidance. They do not validate study
design, statistical correctness, clinical meaning, or journal acceptance.
