# Visual Self-check Loop: Let AI Review Its Own Figures

This is the core capability for post-render quality assurance. Normal plotting tools end after rendering -- **nobody reviews the output**, so CJK boxes, clipped text, legends over data, misaligned panel labels all survive until submission when reviewers catch them. This document defines a **post-render feedback loop**:

```
Render -> 1. Render PNG preview -> 2. Program self-check (visual_qa) -> 3. AI visual review
                                                       | problems found
         5. Pass <- 4. Fix at source -> re-render -> re-review <-┘
```

## Why "Render to PNG First, Then Let AI See"

- **Vector PDF/SVG cannot be "seen" at the pixel level** for overlap and occlusion -- must rasterize to PNG first.
- **Program checks are limited**: missing glyphs, clipping, tick overlap are deterministic (visual_qa catches these), but "legend sitting right on a data cluster", "two annotation texts overlapping each other", "colors look gray and indistinguishable" are **perceptual** issues that only emerge from viewing the image.
- This system runs on AI with **multimodal image reading capability** -- can use the Read tool to directly read PNG. So this loop **actually executes**, not just a slogan.

## Division of Labor: Program Check vs AI Review

| Layer | Tool | Catches |
|---|---|---|
| Program check | `audit_layout(fig)` | Missing glyphs, text clipping, tick overlap (deterministic) |
| AI visual review | This checklist + Read PNG | Legend over data, label alignment, color/grayscale separability, overall aesthetics (perceptual) |

**Both layers must pass.** Program PASS doesn't mean the figure looks good; AI review is the final check.

## Standard Operating Procedure

### Step 1: Render Preview

```python
from visual_qa import render_preview
preview = render_preview(fig, "figs/_preview.png", dpi=150)
```

> Use 150 dpi: sufficient to see text and overlaps, not so large it slows review. Do this **before exporting the final vector** -- find problems at the source.

### Step 2: Program Self-check

```python
issues = audit_layout(fig)
print_report(issues)
```

Any `FAIL` (almost always missing glyphs) **must be fixed first**. `WARN` (clipping/overlap) should be noted for Step 3 review.

### Step 3: AI Visual Review (Key Step)

Use the Read tool to read `figs/_preview.png`, then **item by item** against the checklist below. Don't just glance and say "looks fine" -- check each item.

#### Visual Review Checklist

1. **Garbled / Boxes**
   - Did Chinese text become box characters?
   - Are minus signs, plus-minus, multiplication, mu, delta, Greek letters, subscripts/superscripts missing?
   - -> Hit: see "Fix Reference Table" missing glyph row.

2. **Text Clipping**
   - Are title, x/y axis labels, legend, numeric annotations cut off at canvas edges?
   - Are rotated long tick labels cut off at bottom?

3. **Text Occlusion / Overlap**
   - **Does the legend cover data** (points, lines, bars)?
   - Do significance annotations, numeric labels, annotation texts overlap each other?
   - Are x-axis tick labels bunched together, interpenetrating?

4. **Panel Label Alignment** (multi-panel must check)
   - Are a/b/c/d aligned **horizontally in a row, vertically in a column**? Same row labels at same height? Same column labels left-aligned?
   - Are font size, bold, style consistent (no mixing `a` and `(a)`)?
   - -> Not aligned: use `add_panel_labels(fig)` to re-label uniformly.

5. **Subplot Spacing / Mutual Invasion**
   - Do subplots overlap? Does one subplot's y-axis label invade its left neighbor?
   - Is colorbar squeezed against or covering subplot data?

6. **Color & Grayscale**
   - Can categories be distinguished by color? Any red-green contrast (colorblind-unfriendly)?
   - If `_grayscale.png` was generated, still distinguishable in grayscale? No -> add line style/marker redundancy.

7. **Data Completeness**
   - Are data points / curves / error bars cut off by axis range?
   - Are error bar tips, tallest bars, outermost points all visible within the frame?

8. **Cross-subplot Consistency**
   - Same variable in multiple subplots: **same color, same marker, same scale**?
   - Shared-axis ranges consistent (for horizontal comparison)?

### Step 4: Fix Reference Table

When problems are found, go back to the corresponding stage to fix -- **do not manually edit the preview image**:

| Visual Finding | Fix Action |
|---|---|
| CJK/symbol garbled boxes | `setup_style(lang='zh')`; check list-fonts; minus boxes confirm `axes.unicode_minus=False` |
| Text clipped | `finalize_figure(fig)`; export with `bbox_inches='tight'`; shorten long titles |
| Legend over data | `ax.legend(loc=..., bbox_to_anchor=(1.02,1), frameon=False)` move outside; or direct annotation instead of legend |
| Annotation texts overlap | Adjust `xytext` offset; or use `adjustText`; reduce annotation count |
| x-axis tick overlap | `ax.tick_params(axis='x', rotation=30)`; reduce tick count; shorten labels |
| Panel labels misaligned | `add_panel_labels(fig, style='nature')` re-label uniformly |
| Subplots overlapping | `finalize_figure(fig)` or use `constrained_layout=True` at creation |
| Color indistinguishable/grayscale | Switch to Okabe-Ito / `colorblind` palette + add line style/marker |
| Data cut off | Widen `set_xlim/set_ylim`, or `ax.margins(0.05)` |

### Step 5: Re-render, Re-review

After fixing **go back to Step 1** to re-render preview and re-review. Loop until:

- Program check has no `FAIL`, AND
- All 8 visual review items pass, **OR**
- Remaining issues are clearly communicated to user and accepted.

## Loop Discipline

- **Re-render after each fix** -- don't fix five things at once and guess the result; if you can't see it, it's not verified.
- **Max 3 rounds**: if still failing after 3 rounds, likely the chart type is wrong (go back to chart_selection.md) or too many dimensions (split figure).
- **Leave a trace**: briefly tell the user what was found and fixed each round, so they know why the figure looks the way it does.

## Complete Example

```python
import matplotlib.pyplot as plt
from setup_style import setup_style
from layout_tools import finalize_figure, add_panel_labels
from visual_qa import render_preview, audit_layout, print_report
from export_figure import export_figure

setup_style(journal='nature', lang='zh')

fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.4))
# ... plot on axes ...

# -- Self-check loop --
finalize_figure(fig)
add_panel_labels(fig, style='nature')
render_preview(fig, 'figs/_preview.png')
print_report(audit_layout(fig))
# Then: Read figs/_preview.png, check against 8-item checklist
# Problems -> fix per table -> re-render -> re-read; after all pass:

export_figure(fig, 'figs/fig1', formats=['pdf', 'svg'],
              size_inches=(7.2, 5.4), grayscale_preview=True)
```

**Remember**: exporting the vector is the **last step**, after all visual review items pass. Catch problems before export, not after submission.
