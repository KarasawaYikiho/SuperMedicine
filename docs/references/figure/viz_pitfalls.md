# Scientific Visualization Pitfall Checklist

Each error follows this structure: **what the error is -> why it's wrong (reviewer perspective) -> correct approach**. This is the "active interception" checklist -- when a user's request triggers any of these, **explain the problem first and offer alternatives, don't silently comply**.

## Table of Contents

- [P1. Mean Bar Chart Hides Distribution and Sample Size](#p1-mean-bar-chart-hides-distribution-and-sample-size)
- [P2. Dual Y-axis is Misleading](#p2-dual-y-axis-is-misleading)
- [P3. Pie Charts and 3D Charts](#p3-pie-charts-and-3d-charts)
- [P4. Improper Y-axis Truncation](#p4-improper-y-axis-truncation)
- [P5. Continuous Color Scale Without Colorbar](#p5-continuous-color-scale-without-colorbar)
- [P6. Connecting Discrete Points with Lines](#p6-connecting-discrete-points-with-lines)
- [P7. Overuse of Colors](#p7-overuse-of-colors)
- [P8. Missing or Unclear Legend](#p8-missing-or-unclear-legend)
- [P9. Unspecified Error Type](#p9-unspecified-error-type)
- [P10. Over-decoration (Chartjunk)](#p10-over-decoration-chartjunk)
- [P11. Resolution / Format Non-compliance](#p11-resolution--format-non-compliance)
- [P12. Multiple Arguments in One Figure](#p12-multiple-arguments-in-one-figure)
- [P13. Red-Green Contrast, No Colorblind Check](#p13-red-green-contrast-no-colorblind-check)
- [P14. rainbow / jet Colormap](#p14-rainbow--jet-colormap)
- [P15. Significance Symbol Abuse](#p15-significance-symbol-abuse)
- [P16. Garbled Text: CJK / Minus / Special Symbols as Boxes](#p16-garbled-text-cjk--minus--special-symbols-as-boxes)
- [P17. Text Clipping and Legend Occlusion](#p17-text-clipping-and-legend-occlusion)
- [P18. Multi-panel Label Misalignment](#p18-multi-panel-label-misalignment)

> P16-P18 are "layout/rendering" pitfalls -- unlike the first 15, they often **aren't visible during plotting, only after export**. Built-in safety nets: `setup_style` (fonts + constrained_layout), `layout_tools` (alignment + layout), `visual_qa` (program check), `visual_review.md` (AI visual review loop).

---

## P1. Mean Bar Chart Hides Distribution and Sample Size

**Error**: Only a bar for each group's mean, with a tiny error bar, no raw data points.

**Reviewer perspective**:
- n=3 and n=300 look the same height; cannot judge evidence strength
- Bimodal, severely skewed, single outlier dominating -- all eaten by mean
- Since 2020, multiple journals (PLoS Biology, Nature Methods commentary) have publicly called for stopping "bare mean bars"

**Correct approach**:
1. n >= 10 -> **box/violin + overlay stripplot showing raw points**
2. n < 10 -> **direct stripplot / dot plot**, don't draw statistical bars at all
3. Must use bar (e.g., dose-response historical convention) -> at least **overlay stripplot**, must show error bars (explicitly state SD/SEM)

```python
sns.boxplot(data=df, x='group', y='value', showfliers=False)
sns.stripplot(data=df, x='group', y='value', color='black',
              size=3, alpha=0.6, dodge=True)
```

---

## P2. Dual Y-axis is Misleading

**Error**: Left y-axis for one dataset, right y-axis for another, on the same figure.

**Reviewer perspective**:
- Two axes' scales can be adjusted arbitrarily; the visual "overlap" or "divergence" of A and B is entirely fabricated by the plotter
- Tufte criticized this in 1983; Edward Tufte said "there is essentially no honest use of dual Y-axes"

**Correct approach**:
1. Same units -> share one y-axis
2. Different units but want to see correlation -> scatter (x=var1, y=var2, one point per timepoint)
3. Different units, want to see trends -> **split into two stacked subplots** sharing x-axis; or **normalize** both to [0,1] then share axis

---

## P3. Pie Charts and 3D Charts

**Error**: Pie chart for proportions; 3D bar/3D pie/3D surface.

**Reviewer perspective**:
- Human angle discrimination is at least 3x worse than length comparison -- pie charts are essentially unreadable
- 3D perspective distorts all values: front 3D bars look taller than back ones, unrelated to actual data
- Multiple journals (Nature, Science, PNAS) explicitly reject in figure guidelines

**Correct approach**:
1. Proportions -> **horizontal bar chart** (sorted, category names on y-axis)
2. Total decomposition -> stacked bar (single or multiple)
3. Need to show 3D data -> **2D heatmap** + colorbar; or contour plot

---

## P4. Improper Y-axis Truncation

**Error**: y-axis starts at a non-zero value, making small differences look large.

**Reviewer perspective**:
- Classic misleading technique; common in news charts, immediately caught in academia
- Truncation makes "2% increase" look like "doubled"

**Correct approach**:
1. y is proportion/probability/accuracy -> **start at 0** (or reasonable baseline like random 25%)
2. y spans orders of magnitude -> **log axis** instead of truncating linear axis
3. Must truncate (e.g., showing "98% vs 98.5%" difference) -> **draw explicit break marks** (two small diagonal lines) and explain in legend

---

## P5. Continuous Color Scale Without Colorbar

**Error**: Color depth maps to continuous value (e.g., expression level), but no colorbar.

**Reviewer perspective**:
- Reader cannot know what "deep red" corresponds to numerically
- Different figures' "deep red" may be inconsistent

**Correct approach**:
1. Any figure mapping values to color (heatmap, scatter with continuous hue, KDE contours) -> **must include colorbar**
2. Colorbar must have **label** (variable name + unit)
3. Comparing multiple figures -> **lock** `vmin` / `vmax` consistent, otherwise visual comparison is meaningless

---

## P6. Connecting Discrete Points with Lines

**Error**: x is categorical (A/B/C/D), but `plt.plot` connects group means with lines.

**Reviewer perspective**:
- Line = implies continuous relationship between x values; connecting categories has no mathematical meaning
- Readers will mistake "from A to B is a continuous transition"

**Correct approach**:
1. x is categorical -> bar / box / dot plot
2. x is ordered but discrete (e.g., Likert 1-5, dose levels) -> dot plot, **optionally** use ultra-thin "guide lines" but annotate "lines for reading guidance only"
3. x is truly continuous (time, dose value) -> use lines

---

## P7. Overuse of Colors

**Error**: 10+ colors to distinguish categories in one figure; or same variable different colors across figures.

**Reviewer perspective**:
- Short-term memory capacity 7 +/- 2; >7 colors cannot be stably distinguished
- Same variable different colors across figures = cross-figure comparison requires re-checking legend

**Correct approach**:
1. <=5 categories -> color + dual encoding (line style/marker)
2. 6-12 categories -> **direct annotation** (label names at line ends) + color as auxiliary
3. >12 -> split figure or cluster merge, or use small multiples
4. **Cross-figure color consistency**: build `palette = {"control": "#999999", "drug_A": "#E69F00", ...}`, share across all figures

---

## P8. Missing or Unclear Legend

**Error**: Multiple datasets but no legend; legend position obscures data; legend labels are `Series1` / `df["col"]` internal names.

**Correct approach**:
1. Any hue mapping must have legend
2. Legend labels are **human-readable** ("Drug A, 10 mg/kg") not variable names
3. Legend position: `loc='best'` not always best; manually place in blank area
4. Many categories -> `bbox_to_anchor` outside figure, or direct annotation replacing legend
5. `frameon=False` for cleaner look (remove legend box)

---

## P9. Unspecified Error Type

**Error**: Figure has error bars / shading / boxplots, but legend doesn't state SD / SEM / 95% CI.

**Reviewer perspective**:
- SD and SEM differ by sqrt(n); CI is yet another thing -- **confusion can completely reverse conclusions**
- This is a high-frequency rejection reason

**Correct approach**: Legend must include:

```
"data are mean +/- SEM, n = 12 per group"
"box plots show median, IQR, and 1.5xIQR whiskers; outliers shown as dots"
"shaded band = 95% confidence interval, n = 8 replicates"
```

Significance symbols similarly:

```
"* p<0.05, ** p<0.01, *** p<0.001 by Mann-Whitney U test;
 Bonferroni-corrected for 6 comparisons"
```

---

## P10. Over-decoration (Chartjunk)

**Error**: Dense gridlines, background gradients, 3D shadows, fancy markers, each bar different color (no meaning).

**Reviewer perspective**:
- Tufte's "data-ink ratio": ink should serve data; decoration is waste
- Decoration **drowns** real data contrast

**Correct approach**:
1. Turn off default grid (`ax.grid(False)`) or keep only horizontal/vertical main grid, dashed light gray
2. Remove top/right spines (`despine`)
3. Same-category data **same color** (unless grouping meaning)
4. Markers: `o` / `s` / `^` suffice

---

## P11. Resolution / Format Non-compliance

**Error**:
- Submit JPEG data figure (lossy compression + edge artifacts)
- Submit 72 DPI PNG
- Submit "screenshot" raster
- PDF embeds Type 3 fonts (multiple journals reject)

**Correct approach**:
1. Data figures (line/bar/scatter/heatmap/box) -> **vector** PDF / SVG / EPS
2. Photos / microscopy -> **raster** PNG / TIFF, **>=300 DPI**
3. Never use JPEG
4. PDF set `rcParams['pdf.fonttype'] = 42` (TrueType)

---

## P12. Multiple Arguments in One Figure

**Error**: 5 panels in one figure, each saying different things; or 8 curves in one panel trying to say multiple things.

**Reviewer perspective**:
- Reader should grasp one core message in 5 seconds at first glance
- Multiple arguments = no argument

**Correct approach**:
1. One figure -> one core conclusion
2. Multiple things to say -> split into multiple figures; each panel one independent point
3. One set of panels (same Figure number a/b/c/d) -> around **same theme** from different angles, not unrelated content crammed together

---

## P13. Red-Green Contrast, No Colorblind Check

**Error**: Red/green to distinguish two groups (most classic colorblind-unfriendly contrast); no grayscale version check.

**Reviewer perspective**:
- 8% of men, 0.5% of women have color vision deficiency; most common is red-green colorblind
- Colorblind readers see your figure as two **completely indistinguishable** gray lines

**Correct approach**:
1. Use **Okabe-Ito** 8-color or seaborn `colorblind` palette
2. Different categories **add redundant encoding**: color + line style / marker
3. `export_figure(..., grayscale_preview=True)` auto-generates grayscale version
4. Still distinguishable in grayscale? No -> add marker / change line style

---

## P14. rainbow / jet Colormap

**Error**: Continuous values use `rainbow` / `jet` / `hsv` colormap.

**Reviewer perspective**:
- These colormaps are **perceptually non-uniform** -- visual "brightness gradient" doesn't correspond to actual value gradient
- Yellow band is visually extremely bright, creating false "peaks"
- IEEE / Nature etc. have explicitly recommended viridis series

**Correct approach**:
- Unidirectional continuous (all positive/all negative) -> `viridis` / `magma` / `inferno` / `cividis`
- Bidirectional (positive and negative, 0 is baseline) -> `RdBu_r` / `PiYG` / `seismic` + `center=0`
- Categorical (discrete) -> `tab10` / `Set2` / Okabe-Ito, **not** rainbow subsampled

---

## P15. Significance Symbol Abuse

**Error**:
- Every combination gets a *, entire figure is stars
- Used significance but didn't state which test
- No multiple comparison correction
- Treated "n=3, p=0.04" as significant conclusion

**Reviewer perspective**:
- Small sample p<0.05 is often noise
- Uncorrected multiple comparisons are p-hacking red flags

**Correct approach**:
1. Only annotate the **few comparisons relevant to the argument**, not all
2. Legend must state: test type + correction method + symbol definition
3. n<10 "significance" should be cautious; consider showing effect size (Cohen's d) not just p

---

## P16. Garbled Text: CJK / Minus / Special Symbols as Boxes

**Error**: Output figure shows CJK text as box characters; minus sign becomes box; plus-minus, multiplication, mu, delta, Greek letters, subscripts/superscripts missing.

**Root cause**:
- matplotlib default font (DejaVu Sans etc.) **does not contain CJK character set** -- writing Chinese guarantees boxes.
- Some fonts lack Unicode minus sign U+2212; with `axes.unicode_minus=True` (default), minus renders as box.
- The worst part: matplotlib on missing glyphs **only issues a warning, still draws the figure**, no error -- so **you might not notice during plotting, only after submission**.

**Correct approach**:
1. **Chinese figures: configure fonts first**: `setup_style(lang='zh')` auto-searches `Noto Sans CJK SC > Source Han Sans > SimHei > Microsoft YaHei`; for Chinese journal Song-style mixed typesetting, pass `serif_for_zh=True`.
2. **Minus sign boxes**: setup_style already defaults `axes.unicode_minus=False` (uses ASCII minus, available in almost all fonts) -- no manual setting needed.
3. **Pre-export program check catches it**: `audit_layout(fig)` intercepts both matplotlib warning and logging channels, **any missing glyph directly judged FAIL**, catching boxes before export.
4. Unsure what CJK fonts are available: use the figure-style tool's list-fonts action.

```python
setup_style(journal='general', lang='zh')
# ... plot ...
print_report(audit_layout(fig))   # missing glyph -> FAIL, immediately visible
```

---

## P17. Text Clipping and Legend Occlusion

**Error**:
- Title / x-axis / y-axis labels cut off by canvas edge.
- Legend (legend) sitting on data points, curves, or bars.
- Rotated long tick labels going out of bounds.

**Reviewer perspective**:
- Clipped labels = missing information, figure not self-consistent; reviewer cannot determine axis meaning.
- Legend over data = key data points invisible, equivalent to hiding data.

**Correct approach**:
1. **At source**: setup_style defaults `constrained_layout` on, auto-reserves space for titles/labels.
2. **Safety net**: run `finalize_figure(fig)` before export; export with `bbox_inches='tight'`.
3. **Move legend outside data area**:

```python
ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1.0), frameon=False)
# Or for many categories, annotate directly at line ends, eliminate legend entirely
```

4. **Long tick labels**: `ax.tick_params(axis='x', rotation=30)` + `ha='right'`; or shorten labels.
5. **Final check**: `audit_layout(fig)` detects text clipping (WARN), then AI visual review confirms whether legend covers data (perceptual issue hard for program to judge, see visual_review.md).

---

## P18. Multi-panel Label Misalignment

**Error**: In a composite figure, a/b/c/d labels placed manually using each subplot's own coordinates, resulting in **rows and columns not aligned** -- common pattern:

```python
# WRONG: using axes fraction coordinates, different y-axis tick widths cause misalignment
for ax, lab in zip(axes.flat, 'abcd'):
    ax.text(-0.20, 1.05, lab, transform=ax.transAxes, fontweight='bold')
```

**Reviewer perspective**:
- Misaligned panel labels, inconsistent font size/style (mixing `a` and `(a)`) = unprofessional typesetting.
- Labels are the reader's roadmap for "which panel to look at first"; messy placement breaks reading order.

**Correct approach**: Use `add_panel_labels()` -- it anchors labels at each subplot's `axes fraction (0,1)` (top-left) then applies **uniform points offset**. Because same-column subplots share figure-x, same-row share figure-y, uniform offset produces **perfect horizontal and vertical alignment**, unaffected by different y-axis tick widths:

```python
# CORRECT: one call, auto-aligned + style-consistent
finalize_figure(fig)
add_panel_labels(fig, style='nature')      # a b c d (IEEE: style='ieee' -> (a)(b)(c))
```

Font size defaults to `axes.labelsize` with bold; style controlled uniformly by `style` parameter -- no more `a` and `(a)` mixing.

---

## Interception Language

When a user's request triggers any of the above, this system should:

1. **State the problem first**: which pitfall was triggered
2. **Explain why** (one sentence, reviewer perspective)
3. **Offer alternatives** (specifically actionable)
4. **Ask if they still want to proceed** -- respect the user's final decision, but **leave a clear record of the warning**

Example language:

> Your requested "mean bar chart with 3 groups of 5 samples each" triggers P1 (mean bar hides distribution):
> n=5 is too small; bars would make reviewers suspect you're hiding something. I recommend switching to
> **box + stripplot overlay showing each point**, where all 5 points are directly visible and the distribution shape is clear.
> Do you still want to proceed with the original plan?
