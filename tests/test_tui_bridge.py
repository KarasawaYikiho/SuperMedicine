from __future__ import annotations

import json
import multiprocessing
import os
import socket
import subprocess
import threading
import shutil
import time
from pathlib import Path

import pytest

from core.application import ApplicationFacade
from core.runtime_paths import RuntimePaths
from core.tui import opentui_runtime
from core.tui.bridge import BridgeContext, TUIBridgeServer


def _never_returns(_context: BridgeContext, _params: dict) -> None:
    while True:
        time.sleep(1)


def _never_ready_worker(*_args) -> None:
    while True:
        time.sleep(1)


def _bootstrap_failure_worker(*_args) -> None:
    raise RuntimeError("bootstrap failed")


def _delayed_side_effect(_context: BridgeContext, params: dict) -> None:
    time.sleep(float(params["delay"]))
    Path(params["path"]).write_text("mutated", encoding="utf-8")


def _stream_forever(context: BridgeContext, _params: dict) -> None:
    context.emit("progress", {"value": 0.5})
    context.emit("chunk", {"text": "half"})
    while True:
        time.sleep(0.01)
        context.raise_if_cancelled()


def _late_stream(context: BridgeContext, _params: dict) -> None:
    time.sleep(0.08)
    context.emit("progress", {"value": 0.5})
    context.emit("chunk", {"text": "late"})
    while True:
        time.sleep(0.01)
        context.raise_if_cancelled()


def _complete_stream(context: BridgeContext, params: dict) -> dict:
    context.emit("progress", {"value": 1})
    context.emit("chunk", {"text": "done"})
    context.emit("completed", {"done": True})
    return {"echo": params["value"]} if "value" in params else {"text": "done"}


def _fail_handler(_context: BridgeContext, _params: dict) -> None:
    raise RuntimeError("secret exception detail")


def _bad_result(_context: BridgeContext, _params: dict) -> dict:
    return {"bad": object()}


def _bad_event(context: BridgeContext, _params: dict) -> None:
    context.emit("chunk", {"bad": object()})


def _large_result(_context: BridgeContext, _params: dict) -> str:
    return "x" * 1000


def _large_event(context: BridgeContext, _params: dict) -> None:
    context.emit("chunk", "x" * 1000)


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


def _wait_until(predicate, timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return bool(predicate())


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
    peer.send(
        _request(
            "catalog",
            "ui.request",
            {"operation": "catalog"},
            token=bridge.token,
        )
    )
    catalog = peer.receive()

    assert created["type"] == "result" and created["id"] == "create"
    assert created["result"]["id"] == "bridge-one"
    assert listed["type"] == "result" and listed["id"] == "list"
    assert [item["id"] for item in listed["result"]] == ["bridge-one"]
    assert catalog["type"] == "result"
    assert catalog["result"]["ok"] is True
    assert "workspace" in catalog["result"]["data"]["pages"]
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
    assert peer.reader.readline() == ""
    peer.close()


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_nonstandard_json_constants_are_rejected(bridge, constant) -> None:
    peer = BridgePeer(bridge)
    peer.socket.sendall(
        (
            '{"version":1,"id":"bad-number","type":"request",'
            '"method":"status","params":{"value":'
            + constant
            + '},"token":"'
            + bridge.token
            + '"}\n'
        ).encode()
    )
    assert peer.receive()["error"]["code"] == "invalid_json"
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
    server = TUIBridgeServer(
        _application(tmp_path),
        handlers={"test.stream": _stream_forever},
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
        peer.close()
        server.close()

    server = TUIBridgeServer(
        _application(tmp_path),
        handlers={"test.stream": _stream_forever},
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
        peer.close()
        server.close()


def test_stream_completes_with_correlated_events_and_result(tmp_path) -> None:
    server = TUIBridgeServer(
        _application(tmp_path), handlers={"test.complete": _complete_stream}
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


@pytest.mark.parametrize("terminal", ["timeout", "cancelled"])
def test_noncooperative_handler_is_terminated_before_terminal_and_close(
    tmp_path, terminal
) -> None:
    server = TUIBridgeServer(
        _application(tmp_path),
        handlers={"test.never": _never_returns},
        concurrency_limit=1,
        request_timeout=0.08,
        close_timeout=0.2,
    ).start()
    peer = BridgePeer(server)
    try:
        peer.send(_request("never", "test.never", token=server.token))
        if terminal == "cancelled":
            peer.send(
                {
                    **_request("never", "test.never", token=server.token),
                    "type": "cancel",
                }
            )
        response = peer.receive()
        assert response["error"]["code"] == terminal
        assert _wait_until(lambda: server.active_request_count == 0)

        peer.send(_request("after", "status", token=server.token))
        after = peer.receive()
        assert after["type"] == "result", after
        started = time.monotonic()
        server.close()
        assert time.monotonic() - started < 0.5
        assert not [
            thread
            for thread in threading.enumerate()
            if thread.name.startswith("tui-bridge-")
        ]
        assert server.worker_count == 0
        assert not [
            process
            for process in multiprocessing.active_children()
            if process.name.startswith("tui-worker-")
        ]
    finally:
        peer.close()
        server.close()


def test_close_terminates_an_active_noncooperative_worker(tmp_path) -> None:
    server = TUIBridgeServer(
        _application(tmp_path),
        handlers={"test.never": _never_returns},
        request_timeout=10,
        close_timeout=0.5,
    ).start()
    peer = BridgePeer(server)
    try:
        peer.send(_request("never", "test.never", token=server.token))
        assert _wait_until(lambda: server.worker_count == 1)
        started = time.monotonic()
        server.close()
        assert time.monotonic() - started < 1
        assert server.worker_count == 0
        assert server.active_request_count == 0
        assert not [
            process
            for process in multiprocessing.active_children()
            if process.name.startswith("tui-worker-")
        ]
    finally:
        peer.close()
        server.close()


@pytest.mark.parametrize(
    ("worker_target", "expected", "timeout"),
    [
        (_never_ready_worker, "timeout", 0.15),
        (_bootstrap_failure_worker, "internal_error", 5),
    ],
)
def test_worker_bootstrap_is_bounded_before_ready_and_slot_is_reusable(
    tmp_path, worker_target, expected, timeout
) -> None:
    server = TUIBridgeServer(
        _application(tmp_path),
        request_timeout=5,
        worker_start_timeout=timeout,
        concurrency_limit=1,
    ).start()
    normal_target = server._worker_target
    server._worker_target = worker_target
    peer = BridgePeer(server)
    try:
        peer.send(_request("bootstrap", "status", token=server.token))
        response = peer.receive()
        assert response["error"]["code"] == expected
        assert server.worker_count == 0
        assert server.active_request_count == 0

        server._worker_target = normal_target
        server.worker_start_timeout = 5
        peer.send(_request("after-bootstrap", "status", token=server.token))
        assert peer.receive()["type"] == "result"
    finally:
        peer.close()
        server.close()


def test_cancelled_handler_cannot_apply_a_late_side_effect(tmp_path) -> None:
    mutation = tmp_path / "late-mutation.txt"
    server = TUIBridgeServer(
        _application(tmp_path),
        handlers={"test.side-effect": _delayed_side_effect},
        request_timeout=1,
    ).start()
    peer = BridgePeer(server)
    try:
        peer.send(
            _request(
                "side-effect",
                "test.side-effect",
                {"path": str(mutation), "delay": 0.3},
                token=server.token,
            )
        )
        peer.send(
            {
                **_request(
                    "side-effect", "test.side-effect", token=server.token
                ),
                "type": "cancel",
            }
        )
        assert peer.receive()["error"]["code"] == "cancelled"
        server.close()
        time.sleep(0.4)
        assert not mutation.exists()
        assert server.worker_count == 0
    finally:
        peer.close()
        server.close()


def test_connection_limit_and_authentication_deadline_bound_idle_clients(
    tmp_path,
) -> None:
    server = TUIBridgeServer(
        _application(tmp_path),
        concurrency_limit=1,
        connection_limit=1,
        authentication_timeout=0.12,
    ).start()
    clients = []
    try:
        for _ in range(40):
            try:
                clients.append(socket.create_connection(server.address, timeout=0.1))
            except OSError:
                pass
        max_connections = 0
        max_readers = 0
        deadline = time.monotonic() + 0.4
        while time.monotonic() < deadline:
            max_connections = max(max_connections, server.connection_count)
            max_readers = max(
                max_readers,
                len(
                    [
                        thread
                        for thread in threading.enumerate()
                        if thread.name.startswith("tui-bridge-client-")
                    ]
                ),
            )
            time.sleep(0.005)
        assert max_connections <= 1
        assert max_readers <= 1
        assert _wait_until(lambda: server.connection_count == 0, timeout=1)
    finally:
        for client in clients:
            client.close()
        server.close()


def test_authenticated_idle_connection_has_read_deadline(tmp_path) -> None:
    server = TUIBridgeServer(_application(tmp_path), idle_timeout=0.1).start()
    peer = BridgePeer(server)
    try:
        peer.send(_request("status", "status", token=server.token))
        assert peer.receive()["type"] == "result"
        assert _wait_until(lambda: server.connection_count == 0, timeout=1)
        assert peer.reader.readline() == ""
    finally:
        peer.close()
        server.close()


@pytest.mark.parametrize("source", ["result", "event"])
def test_unserializable_handler_output_gets_one_terminal_internal_error(
    tmp_path, source
) -> None:
    server = TUIBridgeServer(
        _application(tmp_path),
        handlers={
            "test.bad": _bad_event if source == "event" else _bad_result
        },
    ).start()
    peer = BridgePeer(server)
    try:
        peer.send(_request("bad", "test.bad", token=server.token))
        response = peer.receive()
        assert response["type"] == "error"
        assert response["error"]["code"] == "internal_error"
        peer.socket.settimeout(0.1)
        with pytest.raises(socket.timeout):
            peer.socket.recv(1)
    finally:
        peer.close()
        server.close()


@pytest.mark.parametrize("source", ["result", "event"])
def test_outbound_frame_limit_returns_bounded_error(tmp_path, source) -> None:
    server = TUIBridgeServer(
        _application(tmp_path),
        handlers={
            "test.large": _large_event if source == "event" else _large_result
        },
        max_frame_bytes=256,
    ).start()
    peer = BridgePeer(server)
    try:
        peer.send(_request("large", "test.large", token=server.token))
        raw = peer.reader.readline().encode()
        assert len(raw) <= 256
        assert json.loads(raw)["error"]["code"] == "response_too_large"
    finally:
        peer.close()
        server.close()


def test_shutdown_closes_clients_and_leaves_no_bridge_threads(bridge) -> None:
    peer = BridgePeer(bridge)
    bridge.close()
    try:
        closed = peer.reader.readline()
    except ConnectionResetError:
        closed = ""
    assert closed == ""
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
def test_real_bun_client_python_bridge_lifecycle_integration(tmp_path) -> None:
    bun_path = shutil.which("bun")
    if not bun_path:
        pytest.skip("Bun is not installed")
    bun = [bun_path]
    server = TUIBridgeServer(
        _application(tmp_path),
        handlers={
            "test.complete": _complete_stream,
            "test.fail": _fail_handler,
            "test.slow": _stream_forever,
            "test.never": _never_returns,
        },
        request_timeout=2.0,
        concurrency_limit=2,
    ).start()
    script = tmp_path / "bridge-client.mjs"
    bridge_module = Path(__file__).parents[1] / "core" / "tui" / "opentui" / "bridge.ts"
    script.write_text(
        "import { BridgeClient } from " + json.dumps(bridge_module.as_uri()) + ";\n"
        "const env = process.env;\n"
        "const bad = new BridgeClient(env.SUPERMEDICINE_TUI_BRIDGE_HOST, Number(env.SUPERMEDICINE_TUI_BRIDGE_PORT), 'wrong', 1048576, 1000);\n"
        "await bad.connect();\n"
        "const auth = await bad.request('status').catch(error => error.code);\n"
        "if (auth !== 'authentication_failed') throw new Error('auth path failed');\n"
        "bad.close();\n"
        "const client = BridgeClient.fromEnvironment();\n"
        "await client.connect();\n"
        "const workspace = await client.request('workspace.create', {workspace_id:'from-bun'});\n"
        "if (workspace.id !== 'from-bun') throw new Error('workspace path failed');\n"
        "const catalog = await client.request('ui.request', {operation:'catalog'});\n"
        "if (!catalog.ok || !catalog.data.pages.workspace.some(item => item.activation?.id === 'from-bun')) throw new Error('catalog path failed');\n"
        "const logged = await client.request('ui.request', {operation:'submit', route:'log', value:'OpenTUI bridge log'});\n"
        "if (!logged.ok) throw new Error('submit path failed');\n"
        "const events = [];\n"
        "const streamed = await client.request('test.complete', {}, (event) => events.push(event));\n"
        "if (streamed.text !== 'done' || events.join(',') !== 'progress,chunk,completed') throw new Error('stream path failed');\n"
        "const failed = await client.request('test.fail').catch(error => error.code);\n"
        "if (failed !== 'internal_error') throw new Error('error path failed');\n"
        "const cancelled = client.startRequest('test.slow');\n"
        "setTimeout(cancelled.cancel, 20);\n"
        "if (await cancelled.promise.catch(error => error.code) !== 'cancelled') throw new Error('cancel path failed');\n"
        "if (await client.request('test.never').catch(error => error.code) !== 'timeout') throw new Error('timeout path failed');\n"
        "const interrupted = client.startRequest('test.slow');\n"
        "setTimeout(() => client.disconnect(), 20);\n"
        "const disconnected = await interrupted.promise.catch(error => error);\n"
        "if (!disconnected.recoverable || disconnected.code !== 'disconnected') throw new Error('disconnect path failed');\n"
        "await client.connect();\n"
        "if (!(await client.request('status')).ok) throw new Error('reconnect path failed');\n"
        "client.close();\n"
        "process.stdout.write('REAL_BRIDGE_OK\\n');\n",
        encoding="utf-8",
    )
    try:
        environment = {**os.environ, **server.child_environment()}
        completed = subprocess.run(
            [*bun, str(script)],
            capture_output=True,
            text=True,
            timeout=30,
            env=environment,
        )
        assert completed.returncode == 0, completed.stderr
        assert completed.stdout == "REAL_BRIDGE_OK\n"
        assert _application(tmp_path).get_workspace("from-bun").ok is True
        assert server.token not in completed.stdout + completed.stderr
    finally:
        server.close()
    assert server.active_request_count == 0
    assert server.connection_count == 0
    assert server.worker_count == 0
    assert not [
        thread
        for thread in threading.enumerate()
        if thread.name.startswith("tui-bridge-")
    ]


@pytest.mark.skipif(not os.environ.get("PATH"), reason="runtime lookup unavailable")
def test_real_bun_client_keeps_socket_after_late_abandoned_stream(
    tmp_path,
    monkeypatch,
) -> None:
    bun_path = shutil.which("bun")
    if not bun_path:
        pytest.skip("Bun is not installed")
    bun = [bun_path]
    server = TUIBridgeServer(
        _application(tmp_path),
        handlers={"test.late": _late_stream},
        request_timeout=4,
    ).start()
    original_cancel = server._cancel

    def delayed_cancel(connection, request_id) -> None:
        time.sleep(1.5)
        original_cancel(connection, request_id)

    monkeypatch.setattr(server, "_cancel", delayed_cancel)
    emitted: list[str] = []
    original_send_event = server._send_event_bytes

    def record_event(active, payload) -> None:
        emitted.append(json.loads(payload)["event"])
        original_send_event(active, payload)

    monkeypatch.setattr(server, "_send_event_bytes", record_event)
    script = tmp_path / "late-bridge-client.mjs"
    bridge_module = Path(__file__).parents[1] / "core" / "tui" / "opentui" / "bridge.ts"
    script.write_text(
        "import { BridgeClient } from " + json.dumps(bridge_module.as_uri()) + ";\n"
        "const env = process.env;\n"
        "const client = new BridgeClient(env.SUPERMEDICINE_TUI_BRIDGE_HOST, Number(env.SUPERMEDICINE_TUI_BRIDGE_PORT), env.SUPERMEDICINE_TUI_BRIDGE_TOKEN, 1048576, 10000);\n"
        "await client.connect();\n"
        "if (await client.request('test.late', {}, undefined, 25).catch(error => error.code) !== 'client_timeout') throw new Error('client timeout missing');\n"
        "await Bun.sleep(1800);\n"
        "if (!(await client.request('status')).ok) throw new Error('socket was not reusable');\n"
        "client.close();\n"
        "process.stdout.write('LATE_STREAM_OK\\n');\n",
        encoding="utf-8",
    )
    try:
        completed = subprocess.run(
            [*bun, str(script)],
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, **server.child_environment()},
        )
        assert completed.returncode == 0, completed.stderr
        assert completed.stdout == "LATE_STREAM_OK\n"
        assert emitted == ["progress", "chunk"]
    finally:
        server.close()
    assert server.worker_count == 0
    assert server.active_request_count == 0
