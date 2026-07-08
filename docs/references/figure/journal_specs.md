# Journal Figure Specs

Always check the target journal's current author instructions. This file is a
starting reference only.

## Common Sizes

| Venue | Single column | Double column | Typical font | Notes |
| --- | --- | --- | --- | --- |
| Nature family | 89 mm / 3.5 in | 183 mm / 7.2 in | 5-7 pt Helvetica/Arial | Export at final size. |
| Science | 55 mm / 2.2 in | 183 mm / 7.2 in | 5-7 pt Helvetica/Arial | Single column is very narrow. |
| IEEE | 3.5 in | 7.16 in | 8-10 pt Times/Arial | Must remain readable in grayscale. |
| Elsevier | 90 mm / 3.54 in | 190 mm / 7.48 in | 7-9 pt Helvetica/Arial | Check journal family rules. |
| PNAS | 8.7 cm / 3.42 in | 17.8 cm / 7.0 in | 6-8 pt | PDF/EPS preferred. |

## Export Defaults

- Prefer vector output (`PDF`, `EPS`, or journal-specific vector formats).
- Use at least 300 DPI for color raster images.
- Use at least 600 DPI for line art when raster output is required.
- Use colorblind-safe palettes.
- Avoid red/green-only encodings.
- Use line style, marker, and color together when grayscale printing is possible.

## CJK Fonts

For Chinese labels, prefer Noto Sans CJK SC or Source Han Sans SC. For serif
Chinese output, prefer Noto Serif CJK SC or Source Han Serif SC. Refresh the
matplotlib font cache after installing fonts.
