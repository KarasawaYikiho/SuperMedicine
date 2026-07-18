"""Side-effect-free static inventory for feature-preservation contracts."""

from __future__ import annotations

import ast
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
    tree = ast.parse((root / "core" / "web" / "server.py").read_text(encoding="utf-8"))
    routes: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue
            method = decorator.func.attr
            if method not in {"get", "post", "put", "patch", "delete", "websocket"} or not decorator.args:
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


def discovered_surface(root: Path) -> dict[str, set[str]]:
    return {
        "cli": discover_cli_commands(root),
        "web": discover_web_routes(root),
        "plugin_provide": discover_plugin_provides(root),
        "adapter": discover_adapter_names(root),
    }
