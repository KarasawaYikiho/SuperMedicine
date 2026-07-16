from __future__ import annotations

import json
import os
import socket
import subprocess
import threading
import shutil
from pathlib import Path

import pytest

from core.application import ApplicationFacade
from core.runtime_paths import RuntimePaths
from core.tui import opentui_runtime
from core.tui.bridge import BridgeContext, TUIBridgeServer


def _application(tmp_path: Path) -> ApplicationFacade:
    return ApplicationFacade(
        RuntimePaths.resolve(project_root=tmp_path, source_root=tmp_path)
    )


def _request(request_id: str, method: str, params=None, *, token: str) -> dict:
    return {
        "version": 1,
        "id": request_id,
        "type": "request",
        "method": method,
        "params": params or {},
        "token": token,
    }


class BridgePeer:
    def __init__(self, server: TUIBridgeServer) -> None:
        self.socket = socket.create_connection(server.address, timeout=2)
        self.socket.settimeout(2)
        self.reader = self.socket.makefile("r", encoding="utf-8", newline="\n")

    def send(self, frame: dict) -> None:
        self.socket.sendall((json.dumps(frame) + "\n").encode())

    def receive(self) -> dict:
        return json.loads(self.reader.readline())

    def close(self) -> None:
        self.reader.close()
        self.socket.close()


@pytest.fixture
def bridge(tmp_path):
    server = TUIBridgeServer(_application(tmp_path), request_timeout=0.15)
    server.start()
    try:
        yield server
    finally:
        server.close()


def test_loopback_authentication_request_ids_and_workspace_facade(bridge) -> None:
    assert bridge.address[0] == "127.0.0.1"
    assert bridge.address[1] > 0
    assert len(bridge.token) >= 43

    peer = BridgePeer(bridge)
    peer.send(
        _request(
            "create",
            "workspace.create",
            {"workspace_id": "bridge-one"},
            token=bridge.token,
        )
    )
    created = peer.receive()
    peer.send(_request("list", "workspace.list", token=bridge.token))
    listed = peer.receive()

    assert created["type"] == "result" and created["id"] == "create"
    assert created["result"]["id"] == "bridge-one"
    assert listed["type"] == "result" and listed["id"] == "list"
    assert [item["id"] for item in listed["result"]] == ["bridge-one"]
    peer.close()


@pytest.mark.parametrize(
    "payload,code",
    [
        (b"not-json\n", "invalid_json"),
        (None, "authentication_failed"),
    ],
)
def test_invalid_json_and_wrong_token_are_rejected(bridge, payload, code) -> None:
    peer = BridgePeer(bridge)
    if payload is None:
        peer.send(_request("bad-auth", "workspace.list", token="wrong"))
    else:
        peer.socket.sendall(payload)
    response = peer.receive()
    assert response["type"] == "error"
    assert response["error"]["code"] == code
    assert bridge.token not in json.dumps(response)
    peer.close()


def test_oversized_frame_and_unknown_method_are_rejected(tmp_path) -> None:
    server = TUIBridgeServer(_application(tmp_path), max_frame_bytes=256)
    server.start()
    peer = BridgePeer(server)
    try:
        peer.socket.sendall(b"{" + b"x" * 300 + b"}\n")
        assert peer.receive()["error"]["code"] == "frame_too_large"
    finally:
        peer.close()
        server.close()

    server = TUIBridgeServer(_application(tmp_path))
    server.start()
    peer = BridgePeer(server)
    try:
        peer.send(_request("missing", "does.not.exist", token=server.token))
        response = peer.receive()
        assert response["id"] == "missing"
        assert response["error"]["code"] == "unknown_method"
    finally:
        peer.close()
        server.close()


def test_concurrency_limit_timeout_stream_events_and_cancel(tmp_path) -> None:
    release = threading.Event()

    def stream(context: BridgeContext, params: dict) -> dict:
        context.emit("progress", {"value": 0.5})
        context.emit("chunk", {"text": "half"})
        while not release.wait(0.01):
            context.raise_if_cancelled()
        context.emit("completed", {"done": True})
        return {"text": "done"}

    server = TUIBridgeServer(
        _application(tmp_path),
        handlers={"test.stream": stream},
        concurrency_limit=1,
        request_timeout=0.12,
    )
    server.start()
    peer = BridgePeer(server)
    try:
        peer.send(_request("stream", "test.stream", token=server.token))
        assert [peer.receive()["event"] for _ in range(2)] == ["progress", "chunk"]
        peer.send(_request("busy", "test.stream", token=server.token))
        assert peer.receive()["error"]["code"] == "concurrency_limit"
        peer.send(
            {
                **_request("stream", "test.stream", token=server.token),
                "type": "cancel",
            }
        )
        cancelled = peer.receive()
        assert cancelled["id"] == "stream"
        assert cancelled["error"]["code"] == "cancelled"

    finally:
        release.set()
        peer.close()
        server.close()

    release.clear()
    server = TUIBridgeServer(
        _application(tmp_path),
        handlers={"test.stream": stream},
        request_timeout=0.08,
    )
    server.start()
    peer = BridgePeer(server)
    try:
        peer.send(_request("timeout", "test.stream", token=server.token))
        assert [peer.receive()["event"] for _ in range(2)] == ["progress", "chunk"]
        timed_out = peer.receive()
        assert timed_out["id"] == "timeout"
        assert timed_out["error"]["code"] == "timeout"
    finally:
        release.set()
        peer.close()
        server.close()


def test_stream_completes_with_correlated_events_and_result(tmp_path) -> None:
    def complete(context: BridgeContext, params: dict) -> dict:
        context.emit("progress", {"value": 1})
        context.emit("chunk", {"text": "done"})
        context.emit("completed", {"done": True})
        return {"echo": params["value"]}

    server = TUIBridgeServer(
        _application(tmp_path), handlers={"test.complete": complete}
    ).start()
    peer = BridgePeer(server)
    try:
        peer.send(
            _request("complete", "test.complete", {"value": "ok"}, token=server.token)
        )
        frames = [peer.receive() for _ in range(4)]
        assert [frame["id"] for frame in frames] == ["complete"] * 4
        assert [frame.get("event") for frame in frames[:3]] == [
            "progress",
            "chunk",
            "completed",
        ]
        assert frames[3]["type"] == "result"
        assert frames[3]["result"] == {"echo": "ok"}
    finally:
        peer.close()
        server.close()


def test_shutdown_closes_clients_and_leaves_no_bridge_threads(bridge) -> None:
    peer = BridgePeer(bridge)
    bridge.close()
    assert peer.reader.readline() == ""
    assert not [t for t in threading.enumerate() if t.name.startswith("tui-bridge-")]
    peer.close()


def test_python_launcher_passes_bridge_only_in_environment_and_closes_it(
    tmp_path, monkeypatch
) -> None:
    seen: dict = {}

    class Child:
        def __init__(self, command, *, cwd, env) -> None:
            seen.update(command=command, cwd=cwd, env=env)
            with socket.create_connection(
                (
                    env["SUPERMEDICINE_TUI_BRIDGE_HOST"],
                    int(env["SUPERMEDICINE_TUI_BRIDGE_PORT"]),
                ),
                timeout=2,
            ) as peer:
                peer.sendall(
                    (
                        json.dumps(
                            _request(
                                "status",
                                "status",
                                token=env["SUPERMEDICINE_TUI_BRIDGE_TOKEN"],
                            )
                        )
                        + "\n"
                    ).encode()
                )
                assert (
                    json.loads(peer.makefile("r", encoding="utf-8").readline())["type"]
                    == "result"
                )

        @staticmethod
        def wait(timeout=None) -> int:
            return 0

    monkeypatch.setattr(
        opentui_runtime, "opentui_command", lambda **_kwargs: ["bun", "main.ts"]
    )
    monkeypatch.setattr(opentui_runtime.subprocess, "Popen", Child)

    assert opentui_runtime.launch_opentui_runtime(project_root=tmp_path) == 0
    token = seen["env"]["SUPERMEDICINE_TUI_BRIDGE_TOKEN"]
    assert token not in " ".join(seen["command"])
    assert not [t for t in threading.enumerate() if t.name.startswith("tui-bridge-")]


def test_python_launcher_exception_still_closes_bridge(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(opentui_runtime, "opentui_command", lambda **_kwargs: ["bun"])

    def fail(*_args, **_kwargs):
        raise RuntimeError("child failed")

    monkeypatch.setattr(opentui_runtime.subprocess, "Popen", fail)
    with pytest.raises(RuntimeError, match="child failed"):
        opentui_runtime.launch_opentui_runtime(project_root=tmp_path)
    assert not [t for t in threading.enumerate() if t.name.startswith("tui-bridge-")]


@pytest.mark.skipif(not os.environ.get("PATH"), reason="runtime lookup unavailable")
def test_bun_client_creates_workspace_in_python_temporary_root(tmp_path) -> None:
    bun = (
        [shutil.which("bun")]
        if shutil.which("bun")
        else [shutil.which("npx"), "--yes", "bun"]
    )
    if not bun[0]:
        pytest.skip("Bun is not installed")
    server = TUIBridgeServer(_application(tmp_path))
    server.start()
    script = tmp_path / "bridge-client.mjs"
    bridge_module = Path(__file__).parents[1] / "core" / "tui" / "opentui" / "bridge.ts"
    script.write_text(
        "import { BridgeClient } from " + json.dumps(bridge_module.as_uri()) + ";\n"
        "const client = BridgeClient.fromEnvironment();\n"
        "await client.connect();\n"
        "const result = await client.request('workspace.create', {workspace_id:'from-bun'});\n"
        "if (result.id !== 'from-bun') throw new Error('unexpected bridge result');\n"
        "client.close();\n",
        encoding="utf-8",
    )
    try:
        environment = {**os.environ, **server.child_environment()}
        completed = subprocess.run(
            [*bun, str(script)],
            capture_output=True,
            text=True,
            timeout=10,
            env=environment,
        )
        assert completed.returncode == 0, completed.stderr
        assert _application(tmp_path).get_workspace("from-bun").ok is True
        assert server.token not in completed.stdout + completed.stderr
    finally:
        server.close()
