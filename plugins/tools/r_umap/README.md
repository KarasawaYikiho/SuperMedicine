# R UMAP Tool

This workspace-local tool produces exploratory UMAP embeddings with R packages
such as `readr`, `ggplot2`, and `umap`.

## Usage

```bash
Rscript runner.R --check-deps
Rscript runner.R --input data.csv --output embedding.png
```

Keep input and output paths inside the selected workspace. Record preprocessing,
random-state, neighborhood, and distance settings, and validate interpretation
before using an embedding in a report or publication.
