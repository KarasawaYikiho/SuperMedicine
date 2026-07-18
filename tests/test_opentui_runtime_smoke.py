"""Smoke guards for the SuperMedicine OpenTUI runtime bridge."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from core.tui.app import launch_tui
from core.tui.opentui_runtime import (
    OpenTUIRuntimeError,
    _preferred_js_runtime,
    automated_nav_opentui_runtime,
    full_page_interactions_opentui_runtime,
    opentui_command,
    runtime_info,
)


def test_tui_dry_run_and_manifests_report_approved_opentui_runtime(
    tmp_path: Path,
) -> None:
    status = launch_tui(dry_run=True, project_root=tmp_path)
    root = Path(__file__).resolve().parents[1]
    package = json.loads(root.joinpath("package.json").read_text(encoding="utf-8"))
    lock = json.loads(root.joinpath("package-lock.json").read_text(encoding="utf-8"))

    assert status.runtime_name == "@opentui/core"
    assert status.runtime_version == "0.4.1"
    assert package["dependencies"]["@opentui/core"] == "0.4.1"
    locked = lock["packages"]["node_modules/@opentui/core"]
    assert locked["version"] == "0.4.1"
    assert locked["license"] == "MIT"

    assert package["scripts"]["opentui:smoke"].startswith("bun ")
    assert not package["scripts"]["opentui:smoke"].startswith("node ")


@pytest.mark.parametrize(
    ("command_kwargs", "expected_flag"),
    [
        ({"smoke": True}, "--smoke"),
        ({"automated_nav": True}, "--automated-nav"),
        ({"full_page_interactions": True}, "--full-page-interactions"),
    ],
)
def test_opentui_command_targets_bridge(
    tmp_path: Path,
    monkeypatch,
    command_kwargs: dict[str, bool],
    expected_flag: str,
) -> None:
    monkeypatch.setenv("SUPERMEDICINE_OPENTUI_JS_RUNTIME", "bun")

    command = opentui_command(project_root=tmp_path, **command_kwargs)
    info = runtime_info()

    assert command[0] == "bun"
    bridge = Path(command[1])
    assert bridge.name == "opentui_runtime.mjs"
    assert bridge.as_posix().lower().endswith(info.bridge.lower())
    assert expected_flag in command
    assert "--project-root" in command


def test_opentui_command_prefers_release_bridge_when_npm_dependencies_exist(
    tmp_path: Path,
    monkeypatch,
) -> None:
    release_bridge = tmp_path / "core" / "tui" / "opentui_runtime.mjs"
    release_bridge.parent.mkdir(parents=True)
    release_bridge.write_text("// release bridge\n", encoding="utf-8")
    opentui_package = tmp_path / "node_modules" / "@opentui" / "core"
    opentui_package.mkdir(parents=True)

    monkeypatch.setenv("SUPERMEDICINE_OPENTUI_JS_RUNTIME", "bun")

    command = opentui_command(project_root=tmp_path, smoke=True)

    assert Path(command[1]) == release_bridge


@pytest.mark.parametrize(
    ("runner", "expected_flag", "stdout", "expected_signal"),
    [
        (
            automated_nav_opentui_runtime,
            "--automated-nav",
            "SUPERMEDICINE_OPENTUI_NAV_OK route=llm stack=chat>dashboard>llm focus=content\n",
            "route=llm",
        ),
        (
            full_page_interactions_opentui_runtime,
            "--full-page-interactions",
            "SUPERMEDICINE_OPENTUI_FULL_PAGE_OK route=permission stack=chat>permission focus=content action=Access Mode\n",
            "route=permission",
        ),
    ],
)
def test_scripted_opentui_helpers_use_expected_modes(
    tmp_path: Path,
    monkeypatch,
    runner: Callable[..., subprocess.CompletedProcess[str]],
    expected_flag: str,
    stdout: str,
    expected_signal: str,
) -> None:
    captured_command: list[str] = []
    captured_kwargs: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured_command.extend(command)
        captured_kwargs.update(kwargs)
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout=stdout,
            stderr="",
        )

    monkeypatch.setenv("SUPERMEDICINE_OPENTUI_JS_RUNTIME", "bun")
    monkeypatch.setattr("core.tui.opentui_runtime.subprocess.run", fake_run)

    result = runner(project_root=tmp_path)

    assert expected_flag in captured_command
    assert captured_kwargs["cwd"] == tmp_path
    assert captured_kwargs["encoding"] == "utf-8"
    assert captured_kwargs["errors"] == "replace"
    assert stdout.split(" ", maxsplit=1)[0] in result.stdout
    assert expected_signal in result.stdout


@pytest.mark.parametrize(
    "mode",
    ["explicit-node", "missing-bun-with-node-present"],
)
def test_opentui_runtime_rejects_node_host_and_node_fallback(monkeypatch, mode) -> None:
    if mode == "explicit-node":
        monkeypatch.setenv("SUPERMEDICINE_OPENTUI_JS_RUNTIME", "node")
        expected_message = "requires Bun"
    else:
        monkeypatch.delenv("SUPERMEDICINE_OPENTUI_JS_RUNTIME", raising=False)

        def fake_which(name: str) -> str | None:
            if name == "bun":
                return None
            if name == "node":
                return "node"
            return None

        monkeypatch.setattr("core.tui.opentui_runtime.shutil.which", fake_which)
        expected_message = "Node.js fallback is intentionally disabled"

    with pytest.raises(OpenTUIRuntimeError, match=expected_message):
        _preferred_js_runtime()
