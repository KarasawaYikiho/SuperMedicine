#!/usr/bin/env python3
"""Python heatmap visualization workspace tool."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


def missing(packages: list[str]) -> list[str]:
    return [pkg for pkg in packages if importlib.util.find_spec(pkg) is None]


def main() -> int:
    parser = argparse.ArgumentParser(description="SuperMedicine Python heatmap tool")
    parser.add_argument("--input", default=None, help="CSV/TSV data matrix path")
    parser.add_argument("--output", default=None, help="Output PNG image path")
    parser.add_argument("--tool-kind", default="heatmap")
    parser.add_argument("--check-deps", action="store_true")
    args = parser.parse_args()

    required = ["pandas", "matplotlib", "seaborn"]
    if args.check_deps:
        unavailable = missing(required)
        if unavailable:
            print(json.dumps({"status": "missing", "packages": unavailable}))
            return 2
        print(json.dumps({"status": "ok", "packages": required}))
        return 0

    unavailable = missing(required)
    if unavailable:
        print(
            f"Missing optional Python dependencies: {', '.join(unavailable)}",
            file=sys.stderr,
        )
        print("Install them before running this tool.", file=sys.stderr)
        return 2

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import pandas as pd
        import seaborn as sns  # type: ignore[import-untyped]

        if args.input:
            input_path = Path(args.input)
            if not input_path.is_file():
                raise FileNotFoundError(f"input file not found: {args.input}")
            sep = "\t" if input_path.suffix.lower() in (".tsv", ".tab") else ","
            df = pd.read_csv(input_path, sep=sep)
        else:
            df = pd.DataFrame(
                {
                    "gene_a": [1.2, 3.4, 2.1, 4.5, 0.8],
                    "gene_b": [2.3, 1.1, 4.2, 0.9, 3.6],
                    "gene_c": [3.1, 2.8, 1.5, 3.2, 2.0],
                    "gene_d": [0.5, 4.1, 2.9, 1.3, 3.8],
                },
                index=["sample_1", "sample_2", "sample_3", "sample_4", "sample_5"],
            )

        numeric_df = df.select_dtypes(include="number")
        if numeric_df.empty:
            raise ValueError("no numeric columns found for heatmap")

        fig, ax = plt.subplots(figsize=(8, 6))
        sns.heatmap(numeric_df, annot=True, fmt=".2f", cmap="YlOrRd", ax=ax)
        ax.set_title("Heatmap")

        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(output_path, dpi=150, bbox_inches="tight")
            result = {"status": "ok", "output": str(output_path), "shape": list(numeric_df.shape)}
        else:
            result = {
                "status": "ok",
                "shape": list(numeric_df.shape),
                "columns": list(numeric_df.columns),
                "message": "Heatmap generated. Use --output to save as PNG.",
            }
        plt.close(fig)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
