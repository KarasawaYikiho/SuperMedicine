# Journal Figure Specifications

Hard requirements for submission figures from major journals. **Check the target journal first** before opening matplotlib -- note the column width, font size, DPI, recommended fonts, and vector format preference.

## Table of Contents

- [Nature Series](#nature-series)
- [Science](#science)
- [IEEE](#ieee)
- [Elsevier Series](#elsevier-series)
- [PNAS](#pnas)
- [Chinese Core Journals](#chinese-core-journals)
- [Cross-Journal Quick Reference](#cross-journal-quick-reference)
- [CJK Font Installation Guide](#cjk-font-installation-guide)

---

## Nature Series

Covers *Nature*, *Nature Methods*, *Nature Communications*, *Nature Machine Intelligence*, etc.

| Dimension | Requirement |
|---|---|
| Single-column width | **89 mm = 3.5 inch** |
| Double-column width | **183 mm = 7.2 inch** |
| Max height | 247 mm = 9.7 inch (no more than one page) |
| Font size | Labels/ticks 5-7 pt, never less than 5 pt |
| Recommended font | **Helvetica / Arial** (sans-serif) |
| Vector preferred | **EPS** / PDF / AI |
| Raster | TIFF / PNG, **>= 300 DPI**; color RGB; line art >= 600 DPI |
| Line width | 0.25-1 pt (matplotlib default 1 pt is thick, recommend 0.6) |
| Color | RGB; colorblind safe; avoid red-green contrast |
| Panel labels | **a, b, c** (lowercase, bold, top-left corner) |

**Pitfall**: Nature emphasizes "export at final size" -- the submission system calculates font size compliance in mm.

Reference: [Nature Figure Guide](https://www.nature.com/nature/for-authors/formatting-guide)

---

## Science

| Dimension | Requirement |
|---|---|
| Single-column width | **55 mm = 2.2 inch** (very narrow) |
| 1.5-column width | **120 mm = 4.7 inch** |
| Double-column width | **183 mm = 7.2 inch** |
| Font size | 5-7 pt |
| Recommended font | **Helvetica / Arial** |
| Vector preferred | PDF / EPS / AI |
| Raster | TIFF / PNG **>= 300 DPI**; line/grid art 600 |
| Panel labels | **A, B, C** (uppercase, bold, top-left) |

**Pitfall**: single-column is extremely narrow (2.2 in); most cases choose 1.5-column to avoid squishing.

---

## IEEE

Covers *Trans on PAMI* / *Trans on Image Processing* / conferences (CVPR, ICCV, etc.).

| Dimension | Requirement |
|---|---|
| Single-column width | **3.5 inch = 88.9 mm** |
| Double-column width | **7.16 inch = 181.9 mm** |
| Font size | 8-10 pt |
| Recommended font | **Times New Roman** (serif); Helvetica/Arial OK inside figures |
| Vector preferred | PDF / EPS |
| Raster | **600 DPI** (line art) / 300 DPI (photos/grayscale) |
| B&W readable | **Explicitly required** -- color figures must remain distinguishable in grayscale |
| Panel labels | (a) (b) (c) lowercase with parentheses |

**Pitfall**: IEEE is strict about **B&W readability** -- conference printing is often B&W. **Line style + marker + color triple redundancy** encoding is required.

Reference: [IEEE Author Tools](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-graphics-for-your-article/)

---

## Elsevier Series

Covers *Cell* / *Neuron* / *Cell Reports* / most Elsevier journals.

| Dimension | Requirement |
|---|---|
| Single-column width | **90 mm = 3.54 inch** |
| 1.5-column width | 140 mm = 5.5 inch |
| Double-column width | **190 mm = 7.48 inch** |
| Font size | 7-9 pt |
| Recommended font | Helvetica / Arial (sans-serif) |
| Vector preferred | EPS / PDF |
| Raster | **300 DPI (color + grayscale)**; line art 1000 DPI |
| Panel labels | (A) (B) (C) uppercase with parentheses |
| Color | RGB; color blind safe |

Reference: [Elsevier Artwork Guidelines](https://www.elsevier.com/authors/policies-and-guidelines/artwork-and-media-instructions)

---

## PNAS

| Dimension | Requirement |
|---|---|
| Single-column width | **8.7 cm = 3.42 inch** |
| 1.5-column width | **11.4 cm = 4.5 inch** |
| Double-column width | **17.8 cm = 7.0 inch** |
| Font size | 6-8 pt |
| Recommended font | Helvetica / Arial / Times (both serif and sans-serif accepted) |
| Vector preferred | PDF / EPS |
| Raster | 300 DPI (color) / 600 DPI (B&W) |
| Panel labels | (A) (B) (C) |

---

## Chinese Core Journals

Applies to *Science China* series, *Acta Physica Sinica*, *Chinese Medical Journal*, EI core journals, Chinese CCF B/C journals, etc. **Check specific journal submission guidelines** -- below are general conventions.

| Dimension | General Requirement |
|---|---|
| Single-column width | **8 cm = 3.15 inch** |
| Double-column width | **17 cm = 6.7 inch** |
| Font size | Chinese No. 6 (=8 pt) / No. 5 (=9 pt) |
| Font | **Chinese Song + Western/digits Times New Roman** mixed typesetting |
| Vector | EPS / PDF (some accept TIFF) |
| Raster | **>= 600 DPI** (line art) / 300 DPI (photos) |
| Color | Some journals only accept B&W; must check submission guidelines |
| Panel labels | (a) (b) (c) or (Jia) (Yi) (Bing), matching journal examples |

**Pitfall 1**: Chinese journal EPS uploads often show boxes in preview -- use PDF instead of EPS (EPS has poor TrueType Chinese support).

**Pitfall 2**: Numbers, variable names, units **must** use Times New Roman (Western serif), not Chinese Song -- this is typographic convention.

---

## Cross-Journal Quick Reference

| Journal | Single-col (in) | Double-col (in) | Font (pt) | Recommended Font | DPI | Vector First |
|---|---|---|---|---|---|---|
| Nature | 3.5 | 7.2 | 5-7 | Helvetica/Arial | 300+ | EPS/PDF |
| Science | 2.2 | 7.2 | 5-7 | Helvetica/Arial | 300+ | PDF/EPS |
| IEEE | 3.5 | 7.16 | 8-10 | Times | 600 | PDF/EPS |
| Elsevier | 3.54 | 7.48 | 7-9 | Helvetica/Arial | 300+ | EPS/PDF |
| PNAS | 3.42 | 7.0 | 6-8 | Helvetica/Times | 300+ | PDF/EPS |
| Chinese Core | 3.15 | 6.7 | 8-9 | Song+TNR | 600 | PDF |

---

## CJK Font Installation Guide

The style tool (`setup_style(lang='zh')`) searches by priority:

```
Noto Sans CJK SC  >  Source Han Sans SC  >  SimHei  >  Microsoft YaHei
```

Song-style mixed typesetting (`serif_for_zh=True`) priority:

```
Noto Serif CJK SC  >  Source Han Serif SC  >  SimSun  >  STSong
```

If none found, raises a clear installation guide instead of silently rendering boxes.

### Linux

```bash
# Debian / Ubuntu
sudo apt install fonts-noto-cjk fonts-noto-cjk-extra

# Fedora / RHEL / CentOS
sudo dnf install google-noto-sans-cjk-fonts google-noto-serif-cjk-fonts

# Refresh matplotlib font cache after install
python -c "import matplotlib.font_manager; matplotlib.font_manager._load_fontmanager(try_read_cache=False)"
```

### macOS

```bash
# Recommended: Homebrew Cask
brew install --cask font-noto-sans-cjk-sc font-noto-serif-cjk-sc

# Or download manually from Google Fonts / Adobe
# https://fonts.google.com/noto/specimen/Noto+Sans+SC
```

macOS ships with PingFang SC / Heiti SC / Songti SC, which is usually sufficient.

### Windows

1. Go to https://github.com/notofonts/noto-cjk/releases, download `Noto_Sans_CJK_SC.zip`
2. Extract, select all `.otf`/`.ttf` files, right-click **"Install for all users"**
3. Restart Python, **or** delete matplotlib cache:
   ```bash
   python -c "import matplotlib; print(matplotlib.get_cachedir())"
   # Delete fontlist*.json in that directory
   ```

Windows ships with SimHei / SimSun / Microsoft YaHei, minimum sufficient.

### Verification

List available CJK fonts using the figure-style tool's list-fonts action. If the list is empty, cache wasn't refreshed -- clear cache and retry.
