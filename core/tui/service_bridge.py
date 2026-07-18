"""JSON subprocess bridge from the Bun OpenTUI shell to application services."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from core.services import PermissionLogSystemService


def multi_agent_operation(action: str, project_root: str | Path) -> dict[str, Any]:
    service = PermissionLogSystemService(project_root)
    if action == "status":
        result = service.multi_agent_status()
    elif action == "enable":
        result = service.set_multi_agent_enabled(True)
    elif action == "disable":
        result = service.set_multi_agent_enabled(False)
    else:
        raise ValueError(f"Unsupported multi-agent bridge action: {action}")
    return result.to_dict()


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 3 or argv[0] != "multi-agent":
        raise SystemExit(
            "usage: service_bridge multi-agent <status|enable|disable> <root>"
        )
    payload = multi_agent_operation(argv[1], argv[2])
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
