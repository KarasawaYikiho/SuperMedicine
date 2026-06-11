# Chart Type Selection Decision Framework

This document is the "brain" of the figure tools. Every figure should start here -- **decide what to draw before deciding how to draw it**.

## Table of Contents

- [Three Decision Axes](#three-decision-axes)
- [Data Shape -> Recommended Chart Quick Reference](#data-shape---recommended-chart-quick-reference)
- [By Data Shape](#by-data-shape)
  - [1. Single Continuous Variable: Distribution](#1-single-continuous-variable-distribution)
  - [2. Single Categorical Variable: Proportions](#2-single-categorical-variable-proportions)
  - [3. One Categorical + One Continuous (Group Comparison)](#3-one-categorical--one-continuous-group-comparison)
  - [4. Two Continuous Variables: Relationship](#4-two-continuous-variables-relationship)
  - [5. Time Series: Trends](#5-time-series-trends)
  - [6. Multi-variable Correlation](#6-multi-variable-correlation)
  - [7. Matrix Data](#7-matrix-data)
  - [8. Nested/Cross Grouping (Multi-dimensional)](#8-nestedcross-grouping-multi-dimensional)
- [Same Data, Different Arguments -> Different Charts](#same-data-different-arguments---different-charts)
- [When to Split Figures](#when-to-split-figures)
- [Chart Type Semantic Boundaries](#chart-type-semantic-boundaries)

---

## Three Decision Axes

Ask three questions before every figure:

### Axis 1: Variable Count and Type

| Combination | Variable Structure |
|---|---|
| 1x continuous | Distribution |
| 1x categorical | Proportions |
| 1x categorical + 1x continuous | Group comparison |
| 2x continuous | Relationship |
| 1x time + 1x continuous | Trend |
| Multiple continuous | Correlation |
| 2D matrix (n x m numeric) | Patterns |
| Nested grouping (A contains B, B contains C) | Hierarchy |

### Axis 2: What You Want to Say (Argumentative Intent)

**This is the most often overlooked axis.** Same data, different goals, different charts.

- **Distribution** -- "What does this data look like" -> histogram / KDE / boxplot
- **Comparison** -- "A is higher/lower/different from B" -> box / bar (with error) / violin
- **Relationship** -- "X increases, Y increases" -> scatter + regression
- **Trend** -- "Changes over time/dose" -> line + error band
- **Composition** -- "Total split into parts" -> stacked bar (**not pie**)
- **Correlation** -- "Which variables correlate" -> heatmap / pairplot
- **Difference** -- "Is group difference significant" -> box + significance annotation
- **Uncertainty** -- "How precise is the estimate" -> error bars / confidence bands

### Axis 3: Data Scale

| Sample Size | Recommendation |
|---|---|
| n >= 30 per group | Box, bar (with error), violin all work; distribution is stable |
| 10 <= n < 30 | Prefer box/violin; bar must overlay stripplot showing raw points |
| 3 <= n < 10 | **Strongly recommend** direct scatter/stripplot; boxplot cautiously |
| n < 3 | **Do not draw box/violin** -- statistical estimates meaningless. Show each point |
| Total > 10^4 | Scatter with alpha=0.1-0.3 to prevent overplotting, or use hexbin/2D KDE |

---

## Data Shape -> Recommended Chart Quick Reference

| Data Shape | First Choice | Alternative | Should NOT Use |
|---|---|---|---|
| Single continuous distribution | KDE / histogram | Box / violin | Pie / line |
| Single categorical proportions | Horizontal bar (sorted) | Stacked bar (single) | **Pie chart** |
| 1 categorical vs 1 continuous, n>=10/group | Box + stripplot | Violin / bar with error | Mean-only bar |
| 1 categorical vs 1 continuous, n<10/group | Stripplot / beeswarm | Dot plot | Box (unreliable) / mean bar |
| 2 continuous | Scatter + regression | 2D KDE / hexbin (large n) | Line (unless ordered) |
| Time vs continuous | Line + error band | Step / scatter | Bar |
| Multiple continuous (3-20 vars) | Correlation heatmap | pairplot | Parallel coordinates (unless interactive) |
| Multiple continuous (>20 vars) | Heatmap + clustering | PCA / UMAP scatter | pairplot overload |
| Matrix data | Heatmap (perceptually uniform colormap) | Table | 3D surface |
| Composition | Stacked bar / treemap | 100% stacked bar | **Pie / 3D pie** |
| Binary prediction performance | ROC / PR curve | Confusion matrix heatmap | Accuracy bar only |

---

## By Data Shape

### 1. Single Continuous Variable: Distribution

**First choice**: KDE (kernel density estimate) -- smooth, shows trends; use histogram for small or discrete data.

**Alternatives**:
- **Boxplot**: shows quartiles + median + outliers
- **Violin**: boxplot + KDE hybrid
- **Rug plot overlay**: small vertical lines at each data point, visible for small n

**When not to use**: All "distribution" plots are unreliable for n < 5; just list points.

### 2. Single Categorical Variable: Proportions

**First choice**: Horizontal bar chart, sorted by value, category names on y-axis.

**Problems with pie charts** (many journals reject them):
- Human angle judgment is at least 3x worse than length comparison
- Colors insufficient for >5 categories
- 3D pie charts distort all proportions

### 3. One Categorical + One Continuous (Group Comparison)

**This is the most common research figure. Decision tree**:

```
Sample size per group n?
├── n < 3          -> show each point (dot plot); no statistical plots
├── 3 <= n < 10    -> stripplot / beeswarm / dot plot; boxplot cautiously
├── 10 <= n < 30   -> box/violin + stripplot overlay (mandatory!)
└── n >= 30        -> box / violin / bar with error all OK
```

**Why "overlay raw points" matters**:
- Mean bar chart makes n=5 and n=500 look the same height
- Boxplot hides bimodal distributions
- Overlay raw points = show the truth of the distribution

### 4. Two Continuous Variables: Relationship

**First choice**: Scatter + regression fit line + 95% CI band.

**Extra signals**:
- Third dimension categorical -> `hue` (color) + `style` (marker shape) dual encoding
- Third dimension continuous -> color mapping (must add colorbar); or marker size
- **n > 1000**: alpha=0.1-0.3 to prevent overplotting; or hexbin / 2D KDE

### 5. Time Series: Trends

**First choice**: Line chart + error band (SEM shading or 95% CI).

**When to connect with lines**: x is truly time or sequence (dose, age group, etc.)

**Multiple lines on one figure**:
- 2-3 lines: color + line style dual encoding
- 4-6 lines: color + marker dual encoding, label names directly at line ends
- >6 lines: split figure, or use small multiples (n x n grid, one line each)

### 6. Multi-variable Correlation

**First choice**: Correlation heatmap (n columns x n columns).

**Configuration**:
- Bidirectional data (positive/negative meaningful) -> diverging colormap `RdBu_r` + `center=0`
- Add `annot` to show r values
- Large matrix (>20 columns) + hierarchical clustering to reorder rows/columns

### 7. Matrix Data

Classic scenarios: gene expression matrix, confusion matrix, feature map, similarity matrix.

**Colormap selection**:
- Unidirectional (all positive) -> `viridis` / `magma` / `inferno` / `cividis`
- Bidirectional -> `RdBu_r` / `PiYG` / `seismic` + `center=0`
- **Never use** `rainbow` / `jet` / `hsv` -- perceptually non-uniform

### 8. Nested/Cross Grouping (Multi-dimensional)

Example: 3 dose x 4 timepoint x 2 sex x multiple replicates measuring one response.

**Mapping strategy** -- map dimensions to visual channels:

| Mapping | Priority | Capacity |
|---|---|---|
| x-axis | 1 | Medium (5-10 categories) |
| Color | 2 | Small (3-5) |
| Marker / line style | 3 | Very small (2-3) |
| Subplot (small multiples / facet) | 4 | Medium (2-8 panels) |
| y-axis | y is response variable, not for grouping | -- |

**Rule**: dimension count <= channel capacity product, otherwise **split figure**.

---

## Same Data, Different Arguments -> Different Charts

### Example 1: Drug A and B effect on response time

Data: 30 subjects x 2 drugs x 5 timepoints = 300 measurements.

| Argument | Recommended Chart | Why |
|---|---|---|
| "Drug A overall faster than B" | Boxplot (x=drug, y=time, all timepoints merged) | Flatten time dimension, focus on groups |
| "A and B diverge most at t=3" | Line (x=time, y=mean, hue=drug + error band) | Highlight temporal dynamics |
| "Subject variability is huge" | spaghetti plot (one thin line per subject) + thick mean | Visualize variability |
| "AB significantly different at t=3" | Paired boxplot + significance bracket | Single-point comparison + stats annotation |

**Same data, 4 completely different charts.** Step 0 must clarify the argument.

---

## When to Split Figures

### Split Criteria

Split if **any** of these are met:

1. **Dimension combinations > 12**: e.g., 4x4 = 16 panels -- fits but reader can't process
2. **x-axis label collision**: >8 categories, need 45+ rotation
3. **Legend >6 items**: exceeds short-term memory capacity
4. **y-axis spans orders of magnitude + can't use log**: split into two figures by scale
5. **Two different things to say**: e.g., "A is faster" + "A is more accurate" = two figures

### Split Strategies

- **By grouping dimension**: original hue=sex, split into fig 1 (male) + fig 2 (female)
- **By panel**: original 2x2, split into fig 1 (a,b) + fig 2 (c,d)
- **By argument**: original wants to say three things, split into three independent figures
- **Main + supplementary**: main figure only shows core conclusions, rest goes to supplementary

---

## Chart Type Semantic Boundaries

### Line vs Scatter

| | Line | Scatter |
|---|---|---|
| Continuous relationship between points | **Must have** | Not required |
| x is | Time / dose / sequence | Anything |
| Suitable for | Trends, dynamics | Relationships, correlations |
| Misconnection risk | **Connecting points that shouldn't be connected** -- implies non-existent trend | Overplotting |

### Bar vs Boxplot

| | Bar (with error) | Boxplot |
|---|---|---|
| Shows | Mean +/- error | Median + quartiles + outliers |
| Assumes | Unimodal, near-Gaussian | No assumption |
| Suitable n | >=30 | >=10 |
| Bimodal distribution | Invisible, eaten by mean | Also hard to see (but better than bar) |
| **Best practice** | Overlay stripplot | Overlay stripplot |

**Core**: when n is small or distribution shape unknown, **default boxplot > bar**.

### Heatmap vs Scatter Matrix

| | Heatmap | Scatter Matrix |
|---|---|---|
| Information density | High | Medium |
| Shows | Single statistic (r, expression value) | Full bivariate distribution |
| Suitable dimensions | 5-50+ columns | 2-8 columns |
| Weakness | Only one statistic | Blurry with many dimensions |

Rule: >8 variables use heatmap directly; 2-8 use pairplot for richer distributions.
