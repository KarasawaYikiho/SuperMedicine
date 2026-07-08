# Visualization Pitfalls

Avoid these common figure problems.

## Misleading Summaries

- Mean-only bars for small or skewed samples.
- Error bars without saying SD, SEM, CI, or range.
- Boxplots for `n < 3`.
- Smooth density plots for tiny samples.

## Bad Encodings

- Pie charts for precise comparison.
- 3D bars or 3D pies.
- Rainbow/jet/hsv palettes.
- Lines connecting unordered categories.
- Red/green-only distinction.

## Layout Problems

- Too many legend items.
- Rotated labels that still collide.
- Multiple claims in one cramped figure.
- Fonts that are readable on screen but not at final publication size.

## Reporting Problems

- Missing sample size.
- Silent outlier removal.
- Missing data hidden by `dropna`.
- Statistical annotation without matching test description.
