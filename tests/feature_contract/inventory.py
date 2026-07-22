"""Side-effect-free static inventory for feature-preservation contracts."""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

import yaml


def _literal_text(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def discover_cli_commands(root: Path) -> set[str]:
    tree = ast.parse((root / "cli" / "parser.py").read_text(encoding="utf-8"))
    commands: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "add_parser" or not node.args:
            continue
        name = _literal_text(node.args[0])
        if name:
            commands.add(f"cli:{name}")
    return commands


def discover_web_routes(root: Path) -> set[str]:
    routes: set[str] = set()
    for source_path in sorted((root / "core" / "web").glob("*.py")):
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call) or not isinstance(
                    decorator.func, ast.Attribute
                ):
                    continue
                method = decorator.func.attr
                if method not in {
                    "get",
                    "post",
                    "put",
                    "patch",
                    "delete",
                    "websocket",
                } or not decorator.args:
                    continue
                path = _literal_text(decorator.args[0])
                if path:
                    routes.add(f"web:{method.upper()} {path}")
    return routes


def discover_plugin_provides(root: Path) -> set[str]:
    provides: set[str] = set()
    for manifest_path in sorted((root / "plugins").glob("**/*.*yaml")):
        data = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        for item in data.get("provides", []):
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                provides.add(f"plugin_provide:{item['id']}")
    return provides


def discover_adapter_names(root: Path) -> set[str]:
    names: set[str] = set()
    for adapter_path in (root / "adapters").glob("*/adapter.py"):
        name = adapter_path.parent.name.replace("_", "-")
        names.add(f"adapter:{name}")
    return names


def discover_tui_actions(root: Path) -> set[str]:
    actions: set[str] = set()
    for source_path in (root / "core" / "tui").glob("**/*.py"):
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("action_"):
                actions.add(f"tui_action:{node.name.removeprefix('action_')}")
    bridge_path = root / "core" / "tui" / "bridge.py"
    if bridge_path.is_file():
        tree = ast.parse(bridge_path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, ast.Assign) or not any(
                isinstance(target, ast.Name) and target.id == "_FACADE_METHODS"
                for target in node.targets
            ):
                continue
            if isinstance(node.value, (ast.Set, ast.Tuple, ast.List)):
                for item in node.value.elts:
                    if isinstance(item, ast.Constant) and isinstance(item.value, str):
                        actions.add(f"tui_action:{item.value.replace('.', '_')}")
    return actions


def discover_config_environment_keys(root: Path) -> set[str]:
    keys: set[str] = set()
    source_paths = [
        *sorted((root / "core").glob("**/*.py")),
        *sorted((root / "cli").glob("**/*.py")),
        root / "cli_entry.py",
        root / "install_entry.py",
        root / "gui_entry.py",
    ]
    for source_path in source_paths:
        if not source_path.is_file():
            continue
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            value = _literal_text(node)
            if value:
                keys.update(f"config_env:{match}" for match in re.findall(r"\bSM_[A-Z0-9_]+\b", value))
    return keys


def discover_release_entrypoints(root: Path) -> set[str]:
    entrypoints = {
        f"entrypoint:{path.name}"
        for path in (
            root / "cli_entry.py",
            root / "gui_entry.py",
            root / "install_entry.py",
            root / "uninstall_entry.py",
        )
        if path.is_file()
    }
    entrypoints.update(
        f"release_builder:{path.relative_to(root).as_posix()}"
        for path in (root / "scripts" / "ci").glob("build_*.py")
    )
    return entrypoints


def discover_database_tables(root: Path) -> set[str]:
    tables: set[str] = set()
    for source_path in (root / "core" / "database").glob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        tables.update(
            f"database_table:{name.lower()}"
            for name in re.findall(
                r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([A-Za-z_][A-Za-z0-9_]*)",
                source,
                flags=re.IGNORECASE,
            )
        )
    return tables


def _tracked_production_python_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "*.py"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    excluded_roots = {"tests", "docs", "build", "dist"}
    return [
        root / relative
        for line in result.stdout.splitlines()
        if (relative := Path(line)).parts
        and relative.parts[0] not in excluded_roots
    ]


def _production_sources(
    root: Path, git_ref: str | None
) -> list[tuple[Path, str]]:
    if git_ref is None:
        return [
            (path.relative_to(root), path.read_text(encoding="utf-8"))
            for path in _tracked_production_python_files(root)
        ]

    result = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", git_ref],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    excluded_roots = {"tests", "docs", "build", "dist"}
    relative_paths = [
        relative
        for line in result.stdout.splitlines()
        if (relative := Path(line)).parts
        and relative.suffix == ".py"
        and relative.parts[0] not in excluded_roots
    ]
    sources: list[tuple[Path, str]] = []
    for relative in relative_paths:
        source = subprocess.run(
            ["git", "show", f"{git_ref}:{relative.as_posix()}"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout
        sources.append((relative, source))
    return sources


def collect_metrics(root: Path, *, git_ref: str | None = None) -> dict[str, int]:
    source_items = _production_sources(root, git_ref)
    raw_loc = 0
    effective_loc = 0
    functions: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    public_symbols = 0
    dependency_edges: set[tuple[str, str]] = set()
    project_modules = {
        relative.parts[0]
        for relative, _source in source_items
    }

    for relative, source in source_items:
        lines = source.splitlines()
        raw_loc += len(lines)
        effective_loc += sum(
            1 for line in lines if line.strip() and not line.lstrip().startswith("#")
        )
        tree = ast.parse(source)
        functions.extend(
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        public_symbols += sum(
            1
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and not node.name.startswith("_")
        )

        source_module = relative.parts[0]
        for node in tree.body:
            imported: str | None = None
            if isinstance(node, ast.Import) and node.names:
                imported = node.names[0].name.split(".", maxsplit=1)[0]
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported = node.module.split(".", maxsplit=1)[0]
            if imported in project_modules and imported != source_module:
                dependency_edges.add((source_module, imported))

    function_lengths = [
        (node.end_lineno or node.lineno) - node.lineno + 1 for node in functions
    ]
    return {
        "production_python_files": len(source_items),
        "production_python_loc": raw_loc,
        "production_python_effective_loc": effective_loc,
        "functions_and_methods": len(functions),
        "public_top_level_symbols": public_symbols,
        "functions_over_60_lines": sum(length > 60 for length in function_lengths),
        "functions_over_100_lines": sum(length > 100 for length in function_lengths),
        "top_level_dependency_edges": len(dependency_edges),
    }


def discovered_surface(root: Path) -> dict[str, set[str]]:
    return {
        "cli": discover_cli_commands(root),
        "web": discover_web_routes(root),
        "plugin_provide": discover_plugin_provides(root),
        "adapter": discover_adapter_names(root),
        "tui_action": discover_tui_actions(root),
        "config_env": discover_config_environment_keys(root),
        "release_entrypoint": discover_release_entrypoints(root),
        "database_table": discover_database_tables(root),
    }
