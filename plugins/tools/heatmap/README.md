# Python Heatmap Tool

This workspace-local visualization tool renders heatmaps with pandas,
matplotlib, and seaborn. It is intended for exploratory research output.

## Usage

```bash
python runner.py --check-deps
python runner.py --input data.csv --output heatmap.png
```

Keep input and output paths inside the selected workspace. Confirm matrix
orientation, scaling, labels, missing-value handling, and color mapping before
using a generated figure in a report or publication.
