"""Builtin workspace tool templates and runner script constants."""

from __future__ import annotations


import yaml

from core.workspace_tool_models import MANIFEST_FILE, ToolLanguage


def _manifest_text(
    tool_id: str,
    language: ToolLanguage,
    name: str,
    description: str,
    entrypoint: str,
    dependencies: list[str],
) -> str:
    return yaml.safe_dump(
        {
            "id": tool_id,
            "language": language,
            "name": name,
            "description": description,
            "entrypoint": entrypoint,
            "dependencies": dependencies,
            "inputs": [
                {
                    "name": "input",
                    "description": "Input matrix/table path",
                    "required": False,
                }
            ],
            "outputs": [
                {
                    "name": "output",
                    "description": "Output artifact path",
                    "required": False,
                }
            ],
            "version": "1.0.0",
        },
        sort_keys=False,
        allow_unicode=True,
    )


PYTHON_RUNNER = '''#!/usr/bin/env python3
"""Workspace-local optional Python visualization runner."""
from __future__ import annotations

import argparse
import importlib.util
import sys


def missing(packages: list[str]) -> list[str]:
    return [package for package in packages if importlib.util.find_spec(package) is None]


def main() -> int:
    parser = argparse.ArgumentParser(description="Optional SuperMedicine Python workspace tool")
    parser.add_argument("--input", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--check-deps", action="store_true")
    parser.add_argument("--tool-kind", default="visualization")
    args = parser.parse_args()
    required = ["pandas", "matplotlib", "seaborn"]
    if args.tool_kind == "umap":
        required.append("umap")
    unavailable = missing(required)
    if unavailable:
        print("Missing optional Python dependencies: " + ", ".join(unavailable))
        print("Install them in your workspace environment before running this tool.")
        return 2
    if args.check_deps:
        print("All optional Python dependencies are available.")
        return 0
    print("Dependencies are available; implement project-specific data loading before execution.")
    print(f"input={args.input!r} output={args.output!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

R_RUNNER = """#!/usr/bin/env Rscript
args <- commandArgs(trailingOnly = TRUE)
tool_kind <- "visualization"
if ("--tool-kind" %in% args) {
  idx <- match("--tool-kind", args)
  if (!is.na(idx) && length(args) >= idx + 1) tool_kind <- args[[idx + 1]]
}
required <- c("ggplot2", "readr")
if (tool_kind == "heatmap") required <- c(required, "pheatmap")
if (tool_kind == "umap") required <- c(required, "umap")
missing <- required[!vapply(required, requireNamespace, quietly = TRUE, FUN.VALUE = logical(1))]
if (length(missing) > 0) {
  cat("Missing optional R dependencies:", paste(missing, collapse = ", "), "\n")
  cat("Install them in your workspace R library before running this tool.\n")
  quit(status = 2)
}
cat("All optional R dependencies are available. Add project-specific data loading before execution.\n")
"""


BUILTIN_TEMPLATES: dict[tuple[ToolLanguage, str], dict[str, str]] = {
    ("python", "heatmap"): {
        MANIFEST_FILE: _manifest_text(
            "heatmap",
            "python",
            "Python heatmap",
            "Optional Python heatmap template",
            "runner.py",
            ["pandas", "matplotlib", "seaborn"],
        ),
        "README.md": "# Python heatmap\n\nWorkspace-local heatmap scaffold. Optional dependencies are reported by `runner.py`.\n",
        "runner.py": PYTHON_RUNNER.replace(
            '--tool-kind", default="visualization"', '--tool-kind", default="heatmap"'
        ),
    },
    ("python", "umap"): {
        MANIFEST_FILE: _manifest_text(
            "umap",
            "python",
            "Python UMAP",
            "Optional Python UMAP template",
            "runner.py",
            ["pandas", "matplotlib", "umap-learn"],
        ),
        "README.md": "# Python UMAP\n\nWorkspace-local UMAP scaffold. Optional dependencies are reported by `runner.py`.\n",
        "runner.py": PYTHON_RUNNER.replace(
            '--tool-kind", default="visualization"', '--tool-kind", default="umap"'
        ),
    },
    ("r", "heatmap"): {
        MANIFEST_FILE: _manifest_text(
            "heatmap",
            "r",
            "R heatmap",
            "Optional R heatmap template",
            "runner.R",
            ["ggplot2", "readr", "pheatmap"],
        ),
        "README.md": "# R heatmap\n\nWorkspace-local R heatmap scaffold. Optional dependencies are reported by `runner.R`.\n",
        "runner.R": R_RUNNER.replace(
            'tool_kind <- "visualization"', 'tool_kind <- "heatmap"'
        ),
    },
    ("r", "umap"): {
        MANIFEST_FILE: _manifest_text(
            "umap",
            "r",
            "R UMAP",
            "Optional R UMAP template",
            "runner.R",
            ["ggplot2", "readr", "umap"],
        ),
        "README.md": "# R UMAP\n\nWorkspace-local R UMAP scaffold. Optional dependencies are reported by `runner.R`.\n",
        "runner.R": R_RUNNER.replace(
            'tool_kind <- "visualization"', 'tool_kind <- "umap"'
        ),
    },
}
