"""Generate the reviewed current-tree contract for human maintenance work."""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from tests.feature_contract.inventory import collect_metrics, discovered_surface


EXCLUDED_ROOTS = {"build", "dist", "docs", "tests"}
INTERFACE_PREFIXES = ("cli/", "core/tui/", "core/web/")
RELEASE_PREFIXES = ("installer/", "scripts/ci/")
RELEASE_FILES = {
    "gui_entry.py",
    "gui_standalone.py",
    "install.py",
    "install_entry.py",
    "setup.py",
    "uninstall_entry.py",
}
CANDIDATE_FILES = {"core/application.py", "core/time_utils.py"}
DATA_FILES = {
    "core/experiment_protocols.py",
    "core/kernel_constants.py",
    "core/workspace_tool_spec.py",
}
HIGH_RISK_CATEGORIES = {
    "multi_agent_role",
    "opentui",
    "release_entrypoint",
    "tui_action",
    "web",
}


def _production_python_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.py"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    paths = {
        root / relative
        for line in result.stdout.splitlines()
        if (relative := Path(line)).parts
        and relative.parts[0] not in EXCLUDED_ROOTS
    }
    return sorted(path for path in paths if path.is_file())


def _is_docstring(node: ast.stmt) -> bool:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _file_role(relative: str, tree: ast.Module) -> str:
    if relative in RELEASE_FILES or relative.startswith(RELEASE_PREFIXES):
        return "generated/release"
    if relative.startswith(INTERFACE_PREFIXES) or relative == "cli_entry.py":
        return "interface"
    if relative in DATA_FILES:
        return "data"
    if relative in CANDIDATE_FILES:
        return "candidate"
    meaningful = [node for node in tree.body if not _is_docstring(node)]
    if meaningful and all(isinstance(node, (ast.Import, ast.ImportFrom)) for node in meaningful):
        return "compat"
    return "authority"


def _signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
    result = f"{prefix}({ast.unparse(node.args)})"
    if node.returns is not None:
        result += f" -> {ast.unparse(node.returns)}"
    return result


def _walk_public_functions(
    nodes: list[ast.stmt], prefix: str = ""
) -> list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]]:
    functions: list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]] = []
    for node in nodes:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                functions.append((f"{prefix}{node.name}", node))
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            functions.extend(_walk_public_functions(node.body, f"{prefix}{node.name}."))
    return functions


def collect_file_inventory(root: Path) -> tuple[dict[str, Any], dict[str, str]]:
    files: dict[str, Any] = {}
    signatures: dict[str, str] = {}
    for path in _production_python_files(root):
        relative = path.relative_to(root).as_posix()
        source = path.read_text(encoding="utf-8-sig")
        tree = ast.parse(source, filename=relative)
        functions = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        public_symbols = [
            node.name
            for node in tree.body
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            and not node.name.startswith("_")
        ]
        lengths = [
            int(node.end_lineno or node.lineno) - node.lineno + 1
            for node in functions
        ]
        files[relative] = {
            "role": _file_role(relative, tree),
            "group": Path(relative).parts[0],
            "raw_loc": len(source.splitlines()),
            "effective_loc": sum(
                1
                for line in source.splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            ),
            "functions_and_methods": len(functions),
            "public_top_level_symbols": len(public_symbols),
            "longest_function": max(lengths, default=0),
        }
        for qualified_name, node in _walk_public_functions(tree.body):
            signatures[f"{relative}::{qualified_name}"] = _signature(node)
    return files, dict(sorted(signatures.items()))


def _manifest_authorities(root: Path) -> dict[str, str]:
    authorities: dict[str, str] = {}
    for path in sorted((root / "plugins").glob("**/*.*yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        relative = path.relative_to(root).as_posix()
        for item in data.get("provides", []):
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                authorities[f"plugin_provide:{item['id']}"] = relative
    return authorities


def _authority_for(root: Path, record: dict[str, Any], plugin_map: dict[str, str]) -> str:
    category = record["category"]
    entrypoint = record["entrypoint"]
    if entrypoint in plugin_map:
        return plugin_map[entrypoint]
    if category == "cli":
        return "cli/parser.py"
    if category == "web":
        return "core/web/routes.py"
    if category in {"tui_action", "opentui"}:
        return "core/tui/opentui_runtime.mjs" if category == "opentui" else "core/tui/app.py"
    if category == "adapter":
        slug = entrypoint.split(":", 1)[1].replace("-", "_")
        candidate = f"adapters/{slug}/adapter.py"
        return candidate if (root / candidate).is_file() else "adapters/base_adapter.py"
    if category == "multi_agent_role":
        return "agents/roles.py"
    if category == "database_table":
        return "core/database/migrations.py"
    if category == "config_env":
        token = entrypoint.split(":", 1)[1]
        for path in _production_python_files(root):
            if token in path.read_text(encoding="utf-8-sig"):
                return path.relative_to(root).as_posix()
        return "core/config_center.py"
    if category in {"release_entrypoint", "installer"}:
        value = entrypoint.split(":", 1)[1]
        return value if (root / value).is_file() else "installer/entrypoint.py"
    if category == "plugin":
        return "plugins/harness/plugin.yaml" if "harness" in entrypoint else "plugins/rag/plugin.yaml"
    return "feature_manifest.json"


def collect_feature_map(root: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    plugin_map = _manifest_authorities(root)
    rows = []
    for record in manifest["features"]:
        category = record["category"]
        rows.append(
            {
                "feature_id": record["feature_id"],
                "authority": _authority_for(root, record, plugin_map),
                "compatibility_entrypoint": record["entrypoint"],
                "contract_test": record["contract_test"],
                "merge_candidate": category in {"cli", "config_env", "plugin_provide"},
                "risk": "high" if category in HIGH_RISK_CATEGORIES else "medium",
            }
        )
    return rows


def build_snapshot(root: Path) -> dict[str, Any]:
    manifest = json.loads((root / "feature_manifest.json").read_text(encoding="utf-8"))
    files, signatures = collect_file_inventory(root)
    groups: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for item in files.values():
        group = groups[item["group"]]
        for key in (
            "raw_loc",
            "effective_loc",
            "functions_and_methods",
            "public_top_level_symbols",
        ):
            group[key] += item[key]
        group["production_python_files"] += 1
    surfaces = discovered_surface(root)
    feature_ids = sorted(record["feature_id"] for record in manifest["features"])
    return {
        "schema_version": 1,
        "feature_ids": feature_ids,
        "surface_entries": {key: sorted(values) for key, values in surfaces.items()},
        "structural_metrics": collect_metrics(root),
        "groups": {key: dict(value) for key, value in sorted(groups.items())},
        "files": files,
        "public_signatures": signatures,
        "feature_implementation_map": collect_feature_map(root, manifest),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/maintainers/human-maintenance-baseline.json"),
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = args.output if args.output.is_absolute() else root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(build_snapshot(root), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
