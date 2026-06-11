# Pre-submission Figure Compliance Checklist

Check every figure before submission. Any FAIL requires re-export -- the figure check tool is the machine version of this checklist.

> This checklist only checks **format compliance** (size, DPI, font size, error annotation). **Semantic compliance** (mean bar hides distribution, dual Y-axis misleading, pie chart, etc.) is in `viz_pitfalls.md` -- both must pass before submission.

## Table of Contents

- [Size & Resolution](#size--resolution)
- [File Format](#file-format)
- [Font & Size](#font--size)
- [Color & Colorblind](#color--colorblind)
- [Axes & Labels](#axes--labels)
- [Legend & Panel Labels](#legend--panel-labels)
- [Error & Statistics Annotation](#error--statistics-annotation)
- [Semantic Compliance (viz_pitfalls Cross-check)](#semantic-compliance-viz_pitfalls-cross-check)
- [Chinese Figure Extras](#chinese-figure-extras)
- [Final Check](#final-check)

---

## Size & Resolution

- [ ] `figsize` set directly to target journal's final size (**single-col ~3.5 in / double-col ~7.2 in**)
- [ ] **No** rescaling in Word / LaTeX / PPT after export
- [ ] Raster DPI >= 300 (standard color) / >= 600 (line art, IEEE)
- [ ] Verified with figure check tool: actual size within 0.1 in of target

## File Format

- [ ] Data figures (line/bar/scatter/heatmap/box) -> **vector** PDF / SVG / EPS
- [ ] Microscopy, photos -> **raster** PNG / TIFF (>=300 DPI)
- [ ] **No JPEG anywhere** (data figures forbidden; photos prefer TIFF)
- [ ] PDF embeds TrueType fonts (**fonttype 42**), no Type 3
- [ ] SVG has **no base64-embedded bitmaps** (loses vector advantage)

## Font & Size

- [ ] Font matches journal: Nature/Science/Elsevier/PNAS -> Helvetica/Arial; IEEE -> Times; Chinese -> Song+TNR
- [ ] At final size: body labels 7-9 pt, tick numbers 6-8 pt, **minimum font >= 6 pt**
- [ ] All characters readable, no boxes (must check for Chinese)
- [ ] No more than 2 font families per figure

## Color & Colorblind

- [ ] Default Okabe-Ito or seaborn `colorblind`, **avoid red-green contrast**
- [ ] Different categories have **dual encoding**: different color + line style / marker
- [ ] Grayscale preview exported (`export_figure(grayscale_preview=True)`), still distinguishable in grayscale
- [ ] Heatmap uses **perceptually uniform** colormap (viridis / magma / inferno / cividis / RdBu_r), **not** rainbow / jet
- [ ] Bidirectional data uses diverging colormap + `center=0`

## Axes & Labels

- [ ] x / y axes both have labels, including **variable name + unit** (e.g., `Time (s)`, `Dose (uM)`)
- [ ] Tick number precision reasonable, no `1.0000` or `1.23456789`
- [ ] Log axis clearly labeled (e.g., `Dose (uM, log)`)
- [ ] No forced 0 origin unless data meaningfully contains 0
- [ ] No `axes.unicode_minus` boxes (auto-fixed by setup_style)

## Legend & Panel Labels

- [ ] Legend **clearly readable**, `frameon=False` for clean look
- [ ] Legend position does not obscure data
- [ ] Categories >5: consider direct annotation (label at line end) instead of legend
- [ ] Panel labels match journal format: Nature `a/b/c` lowercase bold; Science/PNAS `A/B/C`; IEEE `(a)/(b)/(c)`
- [ ] Panel label positions consistent (recommend top-left, `transform=ax.transAxes`)
- [ ] Multi-panel font size, color, axis scales **consistent**

## Error & Statistics Annotation

- [ ] Any error bars / shading / boxplots -> **legend** must state:
  - [ ] Error type (SD / SEM / 95% CI / IQR)
  - [ ] Sample size n
  - [ ] Significance test method (t-test / Mann-Whitney / ANOVA / correction)
  - [ ] Significance symbol definition (`* p<0.05, ** p<0.01, *** p<0.001`)
- [ ] Significance annotations don't obscure data
- [ ] No "mean bar without error bars" -- reviewers will suspect no replicates

## Semantic Compliance (viz_pitfalls Cross-check)

Format compliance != semantic compliance. These 8 items are the **must-pass** subset from `viz_pitfalls.md`:

- [ ] **P1**: n<10/group -> **no** mean bar chart -- overlay stripplot or switch to box
- [ ] **P2**: No dual Y-axis (unless both variables have same units)
- [ ] **P3**: No pie chart, no 3D bar/3D pie/3D surface
- [ ] **P4**: y-axis origin reasonable (proportions/ratios start at 0; truncation has clear break mark)
- [ ] **P5**: All continuous color scales have colorbar with label + unit
- [ ] **P6**: If x is categorical, **no** line connecting group means
- [ ] **P12**: One figure = one core conclusion (multiple arguments -> split figures)
- [ ] **P14**: Continuous values use viridis / magma / RdBu_r, **no** rainbow / jet

Full 15 items: see `viz_pitfalls.md`.

## Chinese Figure Extras

- [ ] `setup_style(lang='zh')` called
- [ ] CJK font available (verify with list-fonts action)
- [ ] Chinese + digits/Western mixed: Chinese uses CJK font, **digits and variable names use Times New Roman**
- [ ] Minus sign displays correctly, not boxes (`axes.unicode_minus = False`)
- [ ] Chinese journal PDF preferred over EPS (EPS has poor TrueType Chinese support)
- [ ] Figure legend, axis labels all in Chinese (unless submitting to English journal)

## Final Check

- [ ] Run the figure check tool with --strict mode on all exported figures
- [ ] Exit code 0 = PASS.
- [ ] **Print** exported PDF (or zoom to actual paper size) and visually inspect -- font big enough? Lines clear? Color contrast sufficient?
- [ ] Check with colorblind simulation tool (Color Oracle / Coblis)
- [ ] Show to a non-expert (family/friend) -- can they understand three things: what is x, what is y, what is the difference between lines/bars -- if not, the figure communication has failed

---

## One-line Summary

```bash
# 1. Export (already done)
# 2. End-to-end audit
python check_figure.py figs/*.pdf figs/*.png \
       --min-dpi 300 --width-in 3.5 --height-in 2.625 --strict

# 3. Visual final check
ls figs/ | xargs -I{} echo "open figs/{}"   # open one by one
```

Any FAIL -> fix -> re-run -> until PASS.
