"""Verify that a clean target install discovers every packaged plugin manifest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", type=Path)
    args = parser.parse_args(argv)
    target = args.target.resolve()
    if not target.is_dir():
        parser.error(f"wheel install target does not exist: {target}")

    sys.path.insert(0, str(target))
    from core.plugin_registry import PluginRegistry

    plugin_root = target / "plugins"
    manifests = set(plugin_root.rglob("plugin.yaml"))
    manifests.update(
        path
        for path in plugin_root.rglob("tool.yaml")
        if path.with_name("plugin.yaml") not in manifests
    )
    registry = PluginRegistry(plugin_root)
    discovered = registry.discover()
    if registry.diagnostics() or len(discovered) != len(manifests):
        raise SystemExit(
            "wheel plugin discovery mismatch: "
            f"manifests={len(manifests)} discovered={len(discovered)} "
            f"diagnostics={registry.diagnostics()}"
        )
    names = sorted(meta.name for meta in discovered)
    required = {"rag-interface", "harness-core"}
    if not required.issubset(names):
        raise SystemExit(f"wheel is missing required plugins: {sorted(required - set(names))}")
    print(json.dumps({"plugins": names, "manifest_count": len(manifests)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
