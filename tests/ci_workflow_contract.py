from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIRECTORY = REPOSITORY_ROOT / ".github" / "workflows"


def workflow_sources() -> dict[str, str]:
    return {
        path.name: path.read_text(encoding="utf-8")
        for path in sorted(WORKFLOW_DIRECTORY.glob("*.yml"))
    }


def combined_workflow_source() -> str:
    return "\n".join(
        f"# workflow: {name}\n{source}"
        for name, source in workflow_sources().items()
    )


def load_workflow(name: str) -> dict[str, Any]:
    return yaml.load(workflow_sources()[name], Loader=yaml.BaseLoader)


def jobs_with_write_permission() -> set[tuple[str, str]]:
    writers: set[tuple[str, str]] = set()
    for workflow_name in workflow_sources():
        workflow = load_workflow(workflow_name)
        for job_name, definition in workflow.get("jobs", {}).items():
            permissions = definition.get("permissions", {})
            if permissions.get("contents") == "write":
                writers.add((workflow_name, job_name))
    return writers
