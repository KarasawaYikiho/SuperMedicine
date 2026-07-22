"""Smoke guards for the SuperMedicine OpenTUI runtime bridge."""

from __future__ import annotations

import json
import os
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
    interaction_matrix_opentui_runtime,
    opentui_command,
    runtime_info,
)
from core.services import WorkspaceService
from core.tui.service_bridge import bridge_request, catalog_snapshot, multi_agent_operation


def test_tui_dry_run_and_manifests_report_approved_opentui_runtime(
    tmp_path: Path,
) -> None:
    status = launch_tui(dry_run=True, project_root=tmp_path)
    root = Path(__file__).resolve().parents[1]
    package = json.loads(root.joinpath("package.json").read_text(encoding="utf-8"))
    lock = json.loads(root.joinpath("package-lock.json").read_text(encoding="utf-8"))

    assert status.runtime_name == "@opentui/core"
    assert status.runtime_version == "0.4.3"
    assert package["dependencies"]["@opentui/core"] == "0.4.3"
    locked = lock["packages"]["node_modules/@opentui/core"]
    assert locked["version"] == "0.4.3"
    assert locked["license"] == "MIT"

    assert package["scripts"]["opentui:smoke"].startswith("bun ")
    assert not package["scripts"]["opentui:smoke"].startswith("node ")
    assert package["scripts"]["opentui:test"] == "bun test core/tui/opentui/__tests__"
    assert package["scripts"]["opentui:test:all"] == (
        "bun run opentui:test && bun core/tui/opentui_runtime.mjs --automated-nav "
        "&& bun core/tui/opentui_runtime.mjs --full-page-interactions"
    )


@pytest.mark.parametrize(
    ("command_kwargs", "expected_flag"),
    [
        ({"smoke": True}, "--smoke"),
        ({"automated_nav": True}, "--automated-nav"),
        ({"full_page_interactions": True}, "--full-page-interactions"),
        ({"interaction_matrix": True}, "--interaction-matrix"),
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
    assert "--python-executable" in command
    assert command[command.index("--python-executable") + 1]


def test_opentui_multi_agent_bridge_views_and_toggles_shared_service(tmp_path):
    assert multi_agent_operation("status", tmp_path)["data"] == {"enabled": False}
    assert multi_agent_operation("enable", tmp_path)["data"] == {"enabled": True}
    assert multi_agent_operation("status", tmp_path)["data"] == {"enabled": True}
    assert multi_agent_operation("disable", tmp_path)["data"] == {"enabled": False}

def test_opentui_catalog_uses_real_services_without_demo_records(tmp_path):
    WorkspaceService(tmp_path).create("real-study", name="Real Study")
    snapshot = catalog_snapshot(tmp_path)

    assert snapshot["ok"] is True
    pages = snapshot["data"]["pages"]
    assert set(pages) == {
        "chat",
        "dashboard",
        "workspace",
        "paper",
        "experience",
        "tool",
        "dialog",
        "llm",
        "experiment",
        "log",
        "permission",
        "self-evolution",
        "diagnose",
    }
    assert any(item.get("id") == "real-study" for item in pages["workspace"])
    capabilities = snapshot["data"]["capabilities"]
    assert capabilities["rag-interface"]["enabled"] is True
    assert capabilities["harness-core"]["enabled"] is True

    bridge_source = (
        Path(__file__).resolve().parents[1] / "core" / "tui" / "opentui_runtime.mjs"
    ).read_text(encoding="utf-8")
    for demo_text in ("study-a", "heatmap.py", "User #1", "openai          ready"):
        assert demo_text not in bridge_source


def test_opentui_feature_contract_covers_pages_and_interactions():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads(root.joinpath("feature_manifest.json").read_text(encoding="utf-8"))
    feature_ids = {record["feature_id"] for record in manifest["features"]}
    page_ids = {
        f"opentui:page:{page}"
        for page in (
            "chat",
            "dashboard",
            "workspace",
            "paper-rag",
            "experience",
            "tool",
            "dialog",
            "llm",
            "experiment",
            "log",
            "permission",
            "self-evolution",
            "diagnose",
        )
    }
    interaction_ids = {
        f"opentui:interaction:{interaction}"
        for interaction in (
            "keyboard",
            "mouse",
            "scroll",
            "focus",
            "resize",
            "unicode-long-text",
            "stream-cancel",
            "error-recovery",
            "state-restore",
            "jsonl-bridge",
        )
    }
    assert page_ids | interaction_ids <= feature_ids

    tui_root = root / "core" / "tui" / "opentui"
    wrapper = root.joinpath("core/tui/opentui_runtime.mjs").read_text(encoding="utf-8")
    main_source = (tui_root / "main.ts").read_text(encoding="utf-8")
    component_source = (tui_root / "components.ts").read_text(encoding="utf-8")
    renderer_tests = (tui_root / "__tests__" / "renderer.test.mjs").read_text(
        encoding="utf-8"
    )

    assert 'import { runCli } from "./opentui/main.ts"' in wrapper
    assert "PAGE_CATALOG" not in wrapper + main_source
    assert "onMouseUp" in component_source
    assert "mockMouse" in renderer_tests
    assert "resize(60, 20)" in main_source
    assert "[80, 24, 20]" in main_source
    assert "[120, 30, 26]" in main_source
    assert "中文123粘贴456" in main_source


def test_service_bridge_jsonl_handles_multiple_requests(tmp_path):
    command = [
        __import__("sys").executable,
        "-m",
        "core.tui.service_bridge",
        "--jsonl",
        str(tmp_path),
    ]
    result = subprocess.run(
        command,
        input=(
            json.dumps({"operation": "multi-agent", "action": "status"})
            + "\n"
            + json.dumps({"operation": "catalog"})
            + "\n"
        ),
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONIOENCODING": "cp1252"},
    )
    payloads = [json.loads(line) for line in result.stdout.splitlines()]
    assert result.returncode == 0
    assert len(payloads) == 2
    assert payloads[0]["data"] == {"enabled": False}
    assert set(payloads[1]["data"]["pages"]) >= {"chat", "diagnose"}


def test_opentui_activation_persists_workspace_and_provider_state(tmp_path):
    WorkspaceService(tmp_path).create("study-one", name="Study One")
    selected_workspace = bridge_request(
        {
            "operation": "activate",
            "route": "workspace",
            "record": {"id": "study-one"},
        },
        tmp_path,
    )
    assert selected_workspace["ok"] is True

    from core.services import LLMService, PermissionLogSystemService

    llm = LLMService(tmp_path)
    llm.add_provider(
        "local-provider",
        {
            "base_url": "https://llm.test/v1",
            "model": "test-model",
            "api_key": "sk-opentui-test",
        },
    )
    selected_provider = bridge_request(
        {
            "operation": "activate",
            "route": "llm",
            "record": {"provider": "local-provider"},
        },
        tmp_path,
    )
    assert selected_provider["ok"] is True

    state = PermissionLogSystemService(tmp_path).runtime_state().data
    assert state["last_workspace_id"] == "study-one"
    providers = LLMService(tmp_path).list_providers().data
    assert providers["current_provider"] == "local-provider"
    assert providers["last_provider"] == "local-provider"


def test_opentui_submit_uses_real_workspace_chat_and_log_services(tmp_path):
    created = bridge_request(
        {"operation": "submit", "route": "workspace", "value": "study-two"},
        tmp_path,
    )
    assert created["ok"] is True

    chat = bridge_request(
        {"operation": "submit", "route": "chat", "value": "summarize trial"},
        tmp_path,
    )
    assert chat["ok"] is True

    log = bridge_request(
        {"operation": "submit", "route": "log", "value": "runtime healthy"},
        tmp_path,
    )
    assert log["ok"] is True
    refreshed = catalog_snapshot(tmp_path)["data"]["pages"]
    assert any(record.get("summary") == "summarize trial" for record in refreshed["chat"])
    assert any(record.get("status") != "empty" for record in refreshed["log"])


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

    def fake_run(
        command: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
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


def test_interaction_matrix_helper_uses_real_runtime_mode(tmp_path, monkeypatch):
    captured: list[str] = []

    def fake_run(
        command: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        captured.extend(command)
        return subprocess.CompletedProcess(
            command,
            0,
            "SUPERMEDICINE_OPENTUI_MATRIX_OK viewport=80x24>120x30 mouse=true cancel=true recovered=true\n",
            "",
        )

    monkeypatch.setenv("SUPERMEDICINE_OPENTUI_JS_RUNTIME", "bun")
    monkeypatch.setattr("core.tui.opentui_runtime.subprocess.run", fake_run)
    result = interaction_matrix_opentui_runtime(project_root=tmp_path)
    assert "--interaction-matrix" in captured
    assert "mouse=true cancel=true recovered=true" in result.stdout


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
