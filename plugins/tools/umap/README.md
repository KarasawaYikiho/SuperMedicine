# Python UMAP Tool

This workspace-local tool produces exploratory UMAP embeddings with pandas,
matplotlib, and `umap-learn`.

## Usage

```bash
python runner.py --check-deps
python runner.py --input data.csv --output embedding.png
```

Keep input and output paths inside the selected workspace. Record preprocessing,
random-state, neighborhood, and distance settings, and validate interpretation
before using an embedding in a report or publication.
