"""Workspace tool authoring specification and LLM context builder.

This module contains the canonical tool authoring specification constant
and the builder function that produces LLM chat context for tool creation.
"""

from __future__ import annotations

from typing import Any

import yaml

from core.workspace_tool_models import (
    MANIFEST_FILE,
    PYTHON_TOOL_STORAGE,
    R_TOOL_STORAGE,
    TOOL_SOURCE_ROOT,
    ToolLanguage,
)


TOOL_AUTHORING_SPEC: dict[str, Any] = {
    "purpose": "Author Python/R workspace tools that SuperMedicine can scan, validate, import, and prepare for guarded execution.",
    "source_directory": TOOL_SOURCE_ROOT,
    "storage": {
        "python": PYTHON_TOOL_STORAGE,
        "r": R_TOOL_STORAGE,
    },
    "tool_folder_format": {
        "source": "plugins/tools/<tool-directory>/",
        "required_manifest": MANIFEST_FILE,
        "required_entrypoint": "A relative script path inside the tool folder; .py for python, .R for r.",
        "recommended_files": [MANIFEST_FILE, "README.md", "runner.py or runner.R"],
    },
    "manifest_fields": {
        "id": "Required lowercase slug matching ^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$.",
        "language": "Required; one of: python, r.",
        "name": "Required human-readable name.",
        "description": "Required concise research-use description.",
        "entrypoint": "Required relative path inside the folder; no absolute paths and no '..'.",
        "dependencies": "Required list of package names as strings. Python uses pip/import package names; R uses CRAN/Bioconductor package names.",
        "inputs": "Required list of mappings. Each mapping should describe name, description, type/path expectation, and whether required.",
        "outputs": "Required list of mappings. Each mapping should describe name, description, type/path expectation, and whether required.",
        "version": "Required semantic or project version string.",
    },
    "input_output_conventions": {
        "cli_flags": [
            "--input <workspace-relative-path>",
            "--output <workspace-relative-path>",
            "--check-deps optional",
        ],
        "paths": "Runtime input/output paths must stay inside the selected workspace; entrypoints must stay inside the tool folder.",
        "stdout": "Print concise progress and dependency/error messages; avoid secrets and raw sensitive data.",
        "exit_codes": "Return 0 for success, 2 for missing optional dependencies or invalid user input, non-zero for execution failures.",
    },
    "dependency_declaration": "Declare every non-stdlib Python package or R package in tool.yaml dependencies as a list of strings; scripts should check availability before heavy imports when practical.",
    "error_handling": [
        "Validate required input files and report the missing path/package/field explicitly.",
        "Fail with a clear non-zero exit status instead of silently producing partial outputs.",
        "Do not hide scanner/validator reasons; import errors surface candidate warnings and error text.",
    ],
    "security_limits": [
        "Do not use absolute entrypoint paths or '..' traversal.",
        "Do not read or write outside the workspace-provided input/output paths.",
        "Do not embed secrets, API keys, credentials, or unapproved network access.",
        "Do not execute shell commands unless the permission policy and user explicitly allow it.",
        "Treat prompt text as advisory only; runtime permission checks still gate execution.",
    ],
    "scan_validate_import_flow": [
        "Scanner reads plugins/tools/* directories and ignores non-directories/__pycache__.",
        "Scanner prefers tool.yaml; plugin.yaml is only fallback metadata and produces a warning.",
        "Language is validated as python/r or inferred from an r_ directory prefix when metadata is missing.",
        "Entrypoint is checked to be relative, inside the source folder, present on disk, and language-matched by suffix.",
        "Manifest dependencies/inputs/outputs must be lists; invalid candidate metadata is surfaced as warnings or import errors.",
        "Import copies a ready candidate into workspaces/<id>/tools/<language>/<tool-id>/ and rewrites a normalized tool.yaml.",
        "Workspace load requires the normalized manifest fields and an existing entrypoint before invocation can be prepared.",
    ],
    "llm_authoring_rule": "When asked to create a tool, generate the folder under plugins/tools/<tool-directory>/ with tool.yaml plus the matching runner.py/runner.R; never save Python/R tools outside the documented source directory or workspace import directories.",
}


def build_tool_authoring_llm_context() -> dict[str, Any]:
    """Return the canonical Python/R tool authoring rules injected into LLM chat."""

    return dict(TOOL_AUTHORING_SPEC)


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
