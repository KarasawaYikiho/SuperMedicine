#!/usr/bin/env python3
"""Python UMAP dimensionality reduction workspace tool."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


def missing(packages: list[str]) -> list[str]:
    return [pkg for pkg in packages if importlib.util.find_spec(pkg) is None]


def main() -> int:
    parser = argparse.ArgumentParser(description="SuperMedicine Python UMAP tool")
    parser.add_argument("--input", default=None, help="CSV/TSV data matrix path")
    parser.add_argument("--output", default=None, help="Output JSON or PNG path")
    parser.add_argument("--tool-kind", default="umap")
    parser.add_argument("--check-deps", action="store_true")
    parser.add_argument("--n-components", type=int, default=2, help="Number of UMAP dimensions")
    parser.add_argument("--n-neighbors", type=int, default=15, help="Number of neighbors for UMAP")
    args = parser.parse_args()

    required = ["pandas", "matplotlib", "umap"]
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
        import numpy as np
        import pandas as pd
        import umap  # type: ignore[import-not-found]

        if args.input:
            input_path = Path(args.input)
            if not input_path.is_file():
                raise FileNotFoundError(f"input file not found: {args.input}")
            sep = "\t" if input_path.suffix.lower() in (".tsv", ".tab") else ","
            df = pd.read_csv(input_path, sep=sep)
        else:
            np.random.seed(42)
            df = pd.DataFrame(
                np.random.randn(20, 5),
                columns=[f"feature_{i}" for i in range(5)],
                index=[f"sample_{i}" for i in range(20)],
            )

        numeric_df = df.select_dtypes(include="number")
        if numeric_df.empty:
            raise ValueError("no numeric columns found for UMAP")

        reducer = umap.UMAP(n_components=args.n_components, n_neighbors=args.n_neighbors)
        embedding = reducer.fit_transform(numeric_df.values)

        embedding_df = pd.DataFrame(
            embedding,
            columns=[f"UMAP{i+1}" for i in range(args.n_components)],
            index=numeric_df.index,
        )

        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if output_path.suffix.lower() in (".png", ".jpg", ".svg"):
                fig, ax = plt.subplots(figsize=(8, 6))
                ax.scatter(embedding[:, 0], embedding[:, 1], s=50, alpha=0.7)
                for i, label in enumerate(embedding_df.index):
                    ax.annotate(label, (embedding[i, 0], embedding[i, 1]), fontsize=8)
                ax.set_xlabel("UMAP1")
                ax.set_ylabel("UMAP2")
                ax.set_title("UMAP Projection")
                fig.savefig(output_path, dpi=150, bbox_inches="tight")
                plt.close(fig)
            else:
                output_path.write_text(
                    embedding_df.to_json(orient="index", indent=2) + "\n",
                    encoding="utf-8",
                )
            result = {"status": "ok", "output": str(output_path), "shape": list(embedding.shape)}
        else:
            result = {
                "status": "ok",
                "shape": list(embedding.shape),
                "embedding_sample": embedding_df.head(5).to_dict(orient="index"),
                "message": "UMAP embedding computed. Use --output to save.",
            }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
