# R UMAP Tool

Workspace-local UMAP dimensionality-reduction helper using R packages such as
`readr`, `ggplot2`, and `umap`.

## Commands

```bash
Rscript runner.R --check-deps
Rscript runner.R --input data.csv --output embedding.png
```

Inputs and outputs should stay inside the workspace. Review generated embeddings
before using them in reports or publications.
