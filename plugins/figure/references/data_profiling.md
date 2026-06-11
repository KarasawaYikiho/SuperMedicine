# Data Profiling Report Interpretation Guide

After running the figure profile tool, it outputs a markdown report. This document explains: **how to read this report + how to translate each fact into a plotting decision**.

## Table of Contents

- [What a Report Looks Like](#what-a-report-looks-like)
- [Column Type Identification Rules](#column-type-identification-rules)
- [Impact of Sample Size](#impact-of-sample-size)
- [Impact of Distribution Shape](#impact-of-distribution-shape)
- [Impact of Group Structure](#impact-of-group-structure)
- [Correlation / Multicollinearity Hints](#correlation--multicollinearity-hints)
- [Missing Values and Outliers](#missing-values-and-outliers)
- [From Report to Plotting Decision Flow](#from-report-to-plotting-decision-flow)

---

## What a Report Looks Like

The profiling tool outputs four core sections:

1. **Columns** -- each column's type, sample size, missing rate, key statistics
2. **Group structure** -- min/median/max sample sizes per group
3. **Correlations** -- Pearson r between numeric columns (sorted by |r|)
4. **Warnings + Chart suggestions** -- auto-generated hints and preliminary chart recommendations

---

## Column Type Identification Rules

The profiler classifies columns into 6 types:

| Type | Identification Rule | Plotting Implication |
|---|---|---|
| `continuous` | numeric dtype, unique values > 7 or contains decimals | Default y-axis; scatter, line, boxplot |
| `ordinal` | numeric dtype, unique integer values <= 7 (e.g., Likert 1-5) | Can be x-axis, but **don't draw lines** (unless confirmed ordered) |
| `categorical` | object or categorical dtype, unique values <= 30 and ratio < 0.5 | x-axis / hue |
| `boolean` | bool dtype or all 0/1 | Split into 2 groups for comparison |
| `datetime` | datetime dtype, or first 10 non-null values parseable as dates | Time axis; line chart preferred x |
| `text` | object dtype, too many unique values to be categorical | Usually ID/notes, **don't plot** |

**Pitfall**: automatic type identification can be wrong. Common misclassifications:

- Experiment ID is numeric (e.g., 1-10), classified as ordinal, **but you want categorical**. Manually `df['expt_id'] = df['expt_id'].astype(str)`
- Category labels are numeric (0=control, 1=drug A, 2=drug B), classified as ordinal. Manually convert to str
- Time stored as string ("2024-01-01"), auto-identification works, but **don't use as categorical**

After running the report, **first check if type identification is correct**; if wrong, fix the data type and re-run.

---

## Impact of Sample Size

The `Columns` section shows actual available sample count per column (excluding missing). The `Group structure` section shows sample count per group.

### Thresholds

| n per group | What to use | What NOT to use |
|---|---|---|
| n < 3 | **Show each point directly** (dot plot) | Mean bar, boxplot, violin (statistical estimates meaningless) |
| 3 <= n < 10 | stripplot / beeswarm / dot plot | Mean bar (hides too much); boxplot cautiously |
| 10 <= n < 30 | **Box + overlay stripplot** | Mean-only bar (**strictly forbidden**) |
| n >= 30 | Box / violin / bar with error all OK | -- |

### Why These Thresholds

- At n=3, the "boxplot" quartile is propped up by only 1 point -- the "median" is the middle one, the "quartile" is completely meaningless
- At n=5, the mean standard error is approximately SD/sqrt(5) = SD x 0.45, **the confidence interval is almost as wide as the raw distribution** -- error bar charts are actually misleading
- Not showing raw points at n<10 = throwing away half the data information; reviewers will immediately question

### Small Sample Warnings in the Report

```
- **WARN**: at least one group has n<10 -- use box/violin + stripplot
  rather than mean-only bar chart.
```

Seeing this -> immediately switch chart type from "mean bar" to "box + stripplot".

---

## Impact of Distribution Shape

The `Columns` section gives each continuous variable:

```
mean=35.2, sd=129, range=[0.9, 500], skew=3.13 (highly skewed); outliers=3 (IQR); -> log axis
```

### Skewness

| skew | Meaning | Decision |
|---|---|---|
| \|skew\| < 0.5 | Roughly symmetric | Mean +/- SD credible; box, violin all suitable |
| 0.5 <= \|skew\| < 1 | Moderately skewed | Prefer **median +/- IQR**; switch bar to box |
| \|skew\| >= 1 | Highly skewed | Must use box / violin; consider **log transform** or log y-axis |

**Why not mean bar for skewed distributions**: mean is pulled by extremes; "mean +/- SD" can draw a lower bound beyond the data range (e.g., mean=2, SD=5, lower bound -3 but all data is positive). Reviewers spot this immediately.

### Orders of Magnitude -> Log Axis

The report's `-> log axis` hint: variable max/min > 100, and all positive.

- Dose-response: doses 0.1 / 1 / 10 / 100 -> log x-axis
- Protein abundance: spanning 6 orders of magnitude -> log y-axis
- Time constants: ms to tens of seconds -> log y-axis

### Outliers

`outliers=3 (IQR)` means IQR method (Q1-1.5*IQR to Q3+1.5*IQR) found 3 points.

**Three options (must report choice in figure legend)**:

1. **Show**: plot them, let readers see the full distribution (recommended)
2. **Annotate**: keep but add annotation (e.g., "sample #17, instrument error")
3. **Remove**: must have clear methodological justification (e.g., "obvious data entry error"), **cannot remove just because you don't like them**

Absolutely forbidden: silently deleting outlier points without reporting.

---

## Impact of Group Structure

The `Group structure` section maps grouping dimensions to sample sizes:

```
- Grouped by: `group`, `condition`
- Number of groups: 6
- Group size: min=1, median=3, max=3
- **WARN**: at least one group has n<3 ...
```

### Single vs Multiple Grouping Dimensions

| Grouping Dimension | Mapping Suggestion |
|---|---|
| Single (e.g., group: A/B/C) | x-axis |
| Double (e.g., group x condition) | x-axis + hue color |
| Triple (e.g., group x condition x sex) | x-axis + hue + subplot (facet) |
| Four+ | **Split figure** or select subset; visual channels exhausted |

### Balanced vs Unbalanced

- min approximately max: balanced, convenient for statistical inference
- min << max: unbalanced, needs mixed model or weights; **don't draw "group mean" directly** which misleads perception

---

## Correlation / Multicollinearity Hints

The `Correlations` section lists top 10 by |r|:

```
- `response_time` <-> `score` : r = -0.394 (moderate)
```

### Usage

1. **Highly correlated columns** (|r| > 0.7) -- these are redundant for scatter plots; don't use both as x-axis or both as hue
2. **Multicollinearity warning** -- for regression/PCA, strongly correlated variables make models unstable; use pairplot to see clearly
3. **Decide pairplot subset** -- 20 columns all pairplotted is unreadable; use r ranking to select top 5-8

---

## Missing Values and Outliers

In the report:

```
| `age` | continuous | 89 | 11 (11%) | ... |
```

`11 (11%)` means 11% missing.

| Missing Rate | Action |
|---|---|
| < 5% | Default ignore; dropna when plotting |
| 5-20% | Report in legend: "n=89 of 100 (11% missing)" |
| > 20% | **Cannot silently ignore** -- check if grouping causes systematic missing; use missingno to check patterns |

---

## From Report to Plotting Decision Flow

```
Profiling tool outputs report
        |
1. Check Columns section: are types correct?
   - Wrong types? Fix with .astype(...) and re-run
        |
2. Check Group structure: enough samples?
   - n<10 warning -> switch to box+stripplot
   - n<3 warning -> show each point, no statistical plots
        |
3. Check Columns skewness:
   - skew>1 -> box/violin + consider log axis
   - "-> log axis" hint -> add log axis
        |
4. Check Group structure groups x Columns categories:
   - Dimension combinations >12 -> split figure, don't force it
        |
5. Check Correlations:
   - Decide scatter hue/style configuration
   - Decide pairplot subset
        |
6. Check Warnings: resolve every one
        |
7. Check Chart suggestions: use as starting point, but **final decision combines argumentative intent**
        |
Consult chart_selection.md to match "data shape" with "what you want to say", finalize chart type.
```

Remember: **the profiling tool gives data facts, chart_selection.md combines facts with arguments to choose charts -- both are essential**.
