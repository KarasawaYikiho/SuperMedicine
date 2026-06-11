# Seven Chart Recipes

Each section provides **directly runnable Python code** -- copy, change data, and plot. All code assumes `setup_style()` has been called.

## Table of Contents

- [Common Setup](#common-setup)
- [1. Line Chart (with Error Band)](#1-line-chart-with-error-band)
- [2. Bar Chart (Grouped + Error Bars)](#2-bar-chart-grouped--error-bars)
- [3. Scatter Plot (Multi-semantic Mapping + Regression)](#3-scatter-plot-multi-semantic-mapping--regression)
- [4. Box / Violin Plot (Overlay stripplot)](#4-box--violin-plot-overlay-stripplot)
- [5. Heatmap (Perceptually Uniform Colormap)](#5-heatmap-perceptually-uniform-colormap)
- [6. Error Bar Plot](#6-error-bar-plot)
- [7. Distribution Plot (Histogram / KDE)](#7-distribution-plot-histogram--kde)
- [8. Correlation Matrix / Scatter Matrix](#8-correlation-matrix--scatter-matrix)
- [9. Multi-panel Composite Figure](#9-multi-panel-composite-figure)
- [10. Plotly Interactive Chart](#10-plotly-interactive-chart)

---

## Common Setup

```python
import sys, os
sys.path.insert(0, '../scripts')
from setup_style import setup_style
from export_figure import export_figure

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# One-time style setup
setup_style(journal='nature', lang='en')

# Okabe-Ito 8-color (colorblind safe)
OKABE = ['#000000', '#E69F00', '#56B4E9', '#009E73',
         '#F0E442', '#0072B2', '#D55E00', '#CC79A7']
# Or use seaborn colorblind palette
PAL = sns.color_palette('colorblind')
```

---

## 1. Line Chart (with Error Band)

**When to use**: Time series, x is continuous variable, need to show mean +/- error.

```python
def lineplot_with_band(ax, x, y_mean, y_err, label, color, ls='-'):
    """y_err can be SD/SEM/95%CI, must annotate in legend."""
    ax.plot(x, y_mean, color=color, linewidth=1.0, linestyle=ls, label=label)
    ax.fill_between(x, y_mean - y_err, y_mean + y_err,
                    color=color, alpha=0.2, linewidth=0)

# --- Example ---
rng = np.random.default_rng(42)
x = np.linspace(0, 10, 100)
n = 12
y1_samples = np.sin(x)[:, None] + rng.normal(0, 0.3, (100, n))
y2_samples = np.cos(x)[:, None] + rng.normal(0, 0.3, (100, n))
y1_mean, y1_sem = y1_samples.mean(1), y1_samples.std(1, ddof=1) / np.sqrt(n)
y2_mean, y2_sem = y2_samples.mean(1), y2_samples.std(1, ddof=1) / np.sqrt(n)

fig, ax = plt.subplots(figsize=(3.5, 2.625))
lineplot_with_band(ax, x, y1_mean, y1_sem, 'Condition A',
                   color=OKABE[2], ls='-')
lineplot_with_band(ax, x, y2_mean, y2_sem, 'Condition B',
                   color=OKABE[6], ls='--')
ax.set_xlabel('Time (s)')
ax.set_ylabel('Response (a.u.)')
ax.legend(frameon=False, loc='lower right')

export_figure(fig, 'figs/01_line', formats=['pdf', 'svg', 'png'],
              size_inches=(3.5, 2.625), dpi=300, grayscale_preview=True)
```

**Pitfalls**:
- `fill_between` must have explicit `linewidth=0`, otherwise PDF will show thin lines at shadow edges
- Different curves **must** have distinction beyond color (line style / marker), otherwise unreadable in grayscale

---

## 2. Bar Chart (Grouped + Error Bars)

**When to use**: Categorical variable mean comparison, between-group comparison.

```python
rng = np.random.default_rng(0)
groups = ['Control', 'Drug A', 'Drug B']
conditions = ['Before', 'After']
data = pd.DataFrame({
    'group': np.repeat(groups, 2 * 10),
    'condition': np.tile(np.repeat(conditions, 10), 3),
    'value': np.concatenate([
        rng.normal(loc, 1.0, 10)
        for loc in [1, 2, 3, 4, 2, 3]
    ]),
})

fig, ax = plt.subplots(figsize=(3.5, 2.625))
sns.barplot(
    data=data, x='group', y='value', hue='condition',
    palette=[OKABE[2], OKABE[6]],
    errorbar='se',
    capsize=0.15,
    err_kws={'linewidth': 0.8},
    ax=ax,
)
sns.stripplot(
    data=data, x='group', y='value', hue='condition',
    palette=[OKABE[2], OKABE[6]],
    dodge=True, size=2, alpha=0.6, edgecolor='black', linewidth=0.3,
    ax=ax, legend=False,
)
ax.set_xlabel(''); ax.set_ylabel('Score (a.u.)')
ax.legend(title='', frameon=False, loc='upper left')

export_figure(fig, 'figs/02_bar', formats=['pdf', 'svg', 'png'],
              size_inches=(3.5, 2.625), dpi=300)
```

**Pitfalls**:
- Bar chart **must not** be bare bars without error bars -- reviewers will suspect no replicates
- Multi-group comparisons: keep color consistent across figures (same condition = same color)
- `barplot` default 95% CI is bootstrap, **slow**; explicitly write `errorbar='se'` or `'sd'`

---

## 3. Scatter Plot (Multi-semantic Mapping + Regression)

**When to use**: Correlation, bivariate relationship; can map hue (color) + style (marker) + size simultaneously.

```python
rng = np.random.default_rng(1)
N = 80
df = pd.DataFrame({
    'x': rng.normal(0, 1, N),
    'group': rng.choice(['A', 'B'], N),
})
df['y'] = 0.6 * df['x'] + np.where(df['group']=='B', 0.5, 0) + rng.normal(0, 0.5, N)

fig, ax = plt.subplots(figsize=(3.5, 3.0))
sns.scatterplot(
    data=df, x='x', y='y',
    hue='group', style='group',
    palette=[OKABE[2], OKABE[6]],
    s=25, alpha=0.85, edgecolor='black', linewidth=0.3,
    ax=ax,
)
sns.regplot(data=df[df.group=='A'], x='x', y='y',
            scatter=False, color=OKABE[2], line_kws={'lw': 1.0}, ax=ax)
sns.regplot(data=df[df.group=='B'], x='x', y='y',
            scatter=False, color=OKABE[6], line_kws={'lw': 1.0}, ax=ax)

from scipy.stats import pearsonr
for g, c in zip(['A', 'B'], [OKABE[2], OKABE[6]]):
    sub = df[df.group == g]
    r, p = pearsonr(sub.x, sub.y)
    ax.text(0.05 if g=='A' else 0.05, 0.95 if g=='A' else 0.88,
            f'{g}: r={r:.2f}, p={p:.1e}',
            transform=ax.transAxes, fontsize=6, color=c, va='top')

ax.set_xlabel('Predictor x'); ax.set_ylabel('Response y')
ax.legend(title='Group', frameon=False, loc='lower right')

export_figure(fig, 'figs/03_scatter', formats=['pdf', 'svg', 'png'],
              size_inches=(3.5, 3.0), dpi=300)
```

**Pitfalls**:
- Large sample (>1000): set alpha=0.2-0.3 to prevent overplotting, or use `sns.jointplot` with marginal density
- Labeling r and p on the figure **saves reviewers time**, bonus points
- regplot's `scatter=False` is mandatory, otherwise scatter gets drawn twice

---

## 4. Box / Violin Plot (Overlay stripplot)

**When to use**: Group distribution comparison; boxplot shows quartiles, violin shows density. **Best practice**: box/violin + stripplot overlay showing raw points.

```python
fig, ax = plt.subplots(figsize=(3.5, 2.625))
sns.boxplot(
    data=data, x='group', y='value', hue='condition',
    palette=[OKABE[2], OKABE[6]],
    showfliers=False,
    width=0.6,
    linewidth=0.8,
    ax=ax,
)
sns.stripplot(
    data=data, x='group', y='value', hue='condition',
    palette=[OKABE[2], OKABE[6]],
    dodge=True, size=2.5, alpha=0.6,
    edgecolor='black', linewidth=0.3,
    ax=ax, legend=False,
)
ax.set_xlabel(''); ax.set_ylabel('Score (a.u.)')
ax.legend(title='', frameon=False)

export_figure(fig, 'figs/04_box', formats=['pdf', 'svg', 'png'],
              size_inches=(3.5, 2.625), dpi=300)
```

**Pitfalls**:
- Violin plots are **more misleading** than boxplots -- density estimation unreliable at n<10
- Significance annotations must state: what test, whether multiple comparison correction applied

---

## 5. Heatmap (Perceptually Uniform Colormap)

**When to use**: Matrix data, correlation matrix, confusion matrix, gene expression matrix.

```python
rng = np.random.default_rng(2)
mat = rng.uniform(-1, 1, (8, 8))
mat = (mat + mat.T) / 2
np.fill_diagonal(mat, 1.0)
labels = [f'f{i+1}' for i in range(8)]

fig, ax = plt.subplots(figsize=(3.5, 3.0))
hm = sns.heatmap(
    mat, ax=ax,
    cmap='RdBu_r',
    vmin=-1, vmax=1,
    center=0,
    annot=True, fmt='.2f',
    annot_kws={'fontsize': 5},
    cbar_kws={'label': "Pearson's r", 'shrink': 0.8},
    linewidths=0.5, linecolor='white',
    xticklabels=labels, yticklabels=labels,
    square=True,
)
ax.tick_params(labelsize=6)
hm.collections[0].colorbar.ax.tick_params(labelsize=6)

export_figure(fig, 'figs/05_heatmap', formats=['pdf', 'svg', 'png'],
              size_inches=(3.5, 3.0), dpi=300)
```

**Pitfalls**:
- **Never use** rainbow / jet / hsv -- perceptually non-uniform, creates false peaks
- Bidirectional data must use diverging colormap + `center=0`
- `square=True` makes each cell square, more professional

---

## 6. Error Bar Plot

**When to use**: Few data points with mean +/- error comparison; typical for different doses, different timepoints.

```python
doses = np.array([0, 1, 3, 10, 30, 100])
n = 8
rng = np.random.default_rng(3)
responses = (np.log10(doses + 1) * 2 + rng.normal(0, 0.5, (n, doses.size)))
mean = responses.mean(0)
sem = responses.std(0, ddof=1) / np.sqrt(n)

fig, ax = plt.subplots(figsize=(3.5, 2.625))
ax.errorbar(
    doses, mean, yerr=sem,
    fmt='o',
    color=OKABE[2], ecolor=OKABE[2],
    elinewidth=0.8, capsize=2, capthick=0.8,
    markersize=5, markeredgecolor='black', markeredgewidth=0.4,
    label='Compound X',
)
ax.set_xscale('symlog', linthresh=1)
ax.set_xlabel('Dose (uM)')
ax.set_ylabel('Response (a.u.)')
ax.legend(frameon=False, loc='lower right')

export_figure(fig, 'figs/06_errbar', formats=['pdf', 'svg', 'png'],
              size_inches=(3.5, 2.625), dpi=300)
```

**Pitfalls**:
- `capsize=2` (default 0 has no cap), caps improve readability
- `symlog` better than `log` for dose axes containing 0

---

## 7. Distribution Plot (Histogram / KDE)

**When to use**: View single continuous variable distribution -- symmetric, bimodal, skewed, outlier presence.

```python
rng = np.random.default_rng(7)
data1 = np.concatenate([rng.normal(0, 1, 200), rng.normal(4, 1, 200)])
data2 = rng.lognormal(0, 0.5, 400)

fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.8), constrained_layout=True)

ax = axes[0]
ax.hist(data1, bins=30, density=True, alpha=0.55,
        color=OKABE[2], edgecolor='black', linewidth=0.4)
sns.kdeplot(data1, ax=ax, color=OKABE[6], linewidth=1.2)
sns.rugplot(data1, ax=ax, color='black', height=0.04, alpha=0.4)
ax.set_xlabel('Value'); ax.set_ylabel('Density')
ax.set_title('Bimodal distribution')

ax = axes[1]
ax.hist(data2, bins=30, density=True, alpha=0.55,
        color=OKABE[3], edgecolor='black', linewidth=0.4)
sns.kdeplot(data2, ax=ax, color=OKABE[6], linewidth=1.2)
ax.axvline(data2.mean(), color='red', linestyle='--', linewidth=0.8,
           label=f'mean={data2.mean():.2f}')
ax.axvline(np.median(data2), color='black', linestyle=':', linewidth=0.8,
           label=f'median={np.median(data2):.2f}')
ax.set_xlabel('Value (log-normal)'); ax.set_ylabel('Density')
ax.legend(frameon=False, fontsize=6)

export_figure(fig, 'figs/07_distribution', formats=['pdf', 'svg', 'png'],
              size_inches=(7.0, 2.8), dpi=300)
```

**Pitfalls**:
- Too many `bins` -> noise; too few -> over-smoothed. `bins='auto'` is a good start
- KDE unreliable at n<30 -- histogram is more honest
- Seeing bimodal: immediately alert -- is there unsplit grouping structure?

---

## 8. Correlation Matrix / Scatter Matrix

**When to use**: Multiple continuous variables (3-20+) to see pairwise relationships. **Variables <=8 use pairplot, >8 use heatmap**.

### 8a. Correlation Heatmap

```python
rng = np.random.default_rng(8)
n = 200
base = rng.normal(0, 1, n)
df = pd.DataFrame({
    'feature_A': base + rng.normal(0, 0.5, n),
    'feature_B': base + rng.normal(0, 0.3, n),
    'feature_C': -base + rng.normal(0, 0.4, n),
    'feature_D': rng.normal(0, 1, n),
    'feature_E': rng.normal(0, 1, n),
    'feature_F': base * 0.5 + rng.normal(0, 0.6, n),
})
corr = df.corr(method='pearson')
mask = np.triu(np.ones_like(corr, dtype=bool), k=1)

fig, ax = plt.subplots(figsize=(4.0, 3.5))
sns.heatmap(
    corr, mask=mask,
    cmap='RdBu_r', vmin=-1, vmax=1, center=0,
    annot=True, fmt='.2f', annot_kws={'fontsize': 6},
    cbar_kws={'label': "Pearson's r", 'shrink': 0.7},
    linewidths=0.5, linecolor='white',
    square=True, ax=ax,
)
ax.tick_params(labelsize=6)

export_figure(fig, 'figs/08a_corr_heatmap', formats=['pdf', 'svg', 'png'],
              size_inches=(4.0, 3.5), dpi=300)
```

---

## 9. Multi-panel Composite Figure

**When to use**: A paper's Figure usually has 2-6 subplots; ensure consistent font size, color, axis scales.

```python
fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.4), constrained_layout=True)

ax = axes[0, 0]
ax.plot(np.linspace(0, 10, 50), np.sin(np.linspace(0, 10, 50)),
        color=OKABE[2], label='A')
ax.set_xlabel('Time (s)'); ax.set_ylabel('Signal')
ax.legend(frameon=False, fontsize=6)

ax = axes[0, 1]
ax.scatter(rng.normal(0,1,50), rng.normal(0,1,50),
           c=OKABE[3], s=12, edgecolor='black', linewidth=0.3)
ax.set_xlabel('PC1'); ax.set_ylabel('PC2')

ax = axes[1, 0]
vals = [3.2, 4.5, 2.8]; errs = [0.3, 0.2, 0.4]
ax.bar(['G1','G2','G3'], vals, yerr=errs, capsize=2,
       color=[OKABE[2], OKABE[6], OKABE[3]], edgecolor='black', linewidth=0.5)
ax.set_ylabel('Score')

ax = axes[1, 1]
data_box = [rng.normal(loc, 1, 30) for loc in [0, 0.7, 1.4]]
ax.boxplot(data_box, tick_labels=['G1','G2','G3'],
           patch_artist=True, widths=0.5,
           boxprops=dict(facecolor=OKABE[2], alpha=0.6, linewidth=0.6),
           medianprops=dict(color='black', linewidth=1.0))
ax.set_ylabel('Value')

export_figure(fig, 'figs/09_panels', formats=['pdf', 'svg', 'png'],
              size_inches=(7.2, 5.4), dpi=300, grayscale_preview=True)
```

**Pitfalls**:
- **Unified colors**: same variable = same color across subplots
- **Unified scales**: comparable subplots share ylim/xlim
- `constrained_layout=True` preferred; auto-coordinates subplot spacing

---

## 10. Plotly Interactive Chart

**When to use**: Supplementary materials, blogs, web display needing hover data. **Formal submission PDFs do not use plotly** -- submission systems don't accept HTML.

```python
import plotly.express as px
import plotly.io as pio

pio.templates.default = 'plotly_white'
df = pd.DataFrame({
    'dose': np.repeat([0, 1, 3, 10, 30, 100], 8),
    'response': np.tile(np.arange(8), 6) + np.random.randn(48),
    'group': np.tile(['A', 'B'] * 4, 6),
})
fig = px.scatter(
    df, x='dose', y='response', color='group', symbol='group',
    log_x=True,
    color_discrete_sequence=['#56B4E9', '#D55E00'],
    template='plotly_white',
)
fig.write_html('figs/10_interactive.html')
```

**Pitfalls**:
- Saving plotly PDF/SVG requires `kaleido` package (`pip install -U kaleido`)
- plotly default background is gray; add `template='plotly_white'`
