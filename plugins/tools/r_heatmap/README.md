# R Heatmap Tool

This workspace-local visualization tool renders heatmaps with R packages such
as `readr`, `ggplot2`, and `pheatmap`. It is intended for exploratory research
output.

## Usage

```bash
Rscript runner.R --check-deps
Rscript runner.R --input data.csv --output heatmap.png
```

Keep input and output paths inside the selected workspace. Confirm matrix
orientation, scaling, labels, missing-value handling, and color mapping before
using a generated figure in a report or publication.
