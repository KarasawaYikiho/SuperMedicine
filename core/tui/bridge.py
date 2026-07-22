"""Authenticated loopback NDJSON bridge for the OpenTUI child process."""

from __future__ import annotations

import hmac
import json
import multiprocessing
import secrets
import socket
import threading
import time
from dataclasses import dataclass, field
from functools import partial
from multiprocessing.connection import Connection
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable

from core.application import AppResult, ApplicationFacade
from core.runtime_paths import RuntimePaths
from core.workspace import WorkspaceManager

PROTOCOL_VERSION = 1
DEFAULT_MAX_FRAME_BYTES = 1024 * 1024
BRIDGE_TOPOLOGY = "python-parent-managed-isolated-worker"
Handler = Callable[["BridgeContext", dict[str, Any]], Any]


class BridgeCancelled(RuntimeError):
    """Raised cooperatively when the peer cancels a request."""


class _OutboundTooLarge(ValueError):
    pass


class _WorkerTerminal(RuntimeError):
    pass


def _encode_frame(frame: dict[str, Any], max_frame_bytes: int) -> bytes:
    payload = (
        json.dumps(
            frame,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode()
    if len(payload) > max_frame_bytes:
        raise _OutboundTooLarge
    return payload


def _fallback_frame(request_id: str, code: str, max_frame_bytes: int) -> bytes:
    return _encode_frame(
        {
            "version": PROTOCOL_VERSION,
            "id": request_id,
            "type": "error",
            "error": {"code": code, "message": "bridge response failed"},
        },
        max_frame_bytes,
    )


@dataclass(slots=True, eq=False)
class _Connection:
    socket: socket.socket
    send_lock: threading.Lock = field(default_factory=threading.Lock)

    def send_bytes(self, payload: bytes) -> None:
        with self.send_lock:
            self.socket.sendall(payload)


@dataclass(slots=True)
class _ActiveRequest:
    request_id: str
    connection: _Connection
    cancelled: Any = field(default_factory=threading.Event)
    process: Any = None
    pipe: Any = None
    terminal: bool = False
    retired: bool = False
    timer: threading.Timer | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)
    retire_lock: threading.Lock = field(default_factory=threading.Lock)
    stop_lock: threading.Lock = field(default_factory=threading.Lock)


class BridgeContext:
    """Request context used by long-running handlers for events and cancellation."""

    def __init__(
        self,
        emit: Callable[[str, Any], None],
        cancelled: Any,
    ) -> None:
        self._emit = emit
        self._cancelled = cancelled

    def emit(self, event: str, data: Any = None) -> None:
        if event not in {"progress", "chunk", "completed"}:
            raise ValueError(f"unsupported bridge event: {event}")
        self.raise_if_cancelled()
        self._emit(event, data)

    def raise_if_cancelled(self) -> None:
        if self._cancelled.is_set():
            raise BridgeCancelled("request cancelled")


_FACADE_METHODS = {
    "status",
    "ui.request",
    "workspace.list",
    "workspace.get",
    "workspace.create",
    "workspace.delete",
}


def _call_facade(
    application: ApplicationFacade, method: str, params: dict[str, Any]
) -> Any:
    if method == "status":
        return {
            "ok": True,
            "workspace_count": len(application.list_workspaces().data or []),
        }
    if method == "ui.request":
        from core.tui.service_bridge import bridge_request

        return bridge_request(params, application.paths.project_root)
    if method == "workspace.list":
        return application.list_workspaces(**params)
    if method == "workspace.get":
        return application.get_workspace(**params)
    if method == "workspace.create":
        return application.create_workspace(**params)
    return application.delete_workspace(**params)


def _request_worker(
    pipe: Connection,
    cancelled: Any,
    paths: Any,
    method: str,
    params: dict[str, Any],
    handler: Handler | None,
    request_id: str,
    max_frame_bytes: int,
) -> None:
    """Run one request outside the bridge parent so it can be terminated safely."""

    def emit(event: str, data: Any) -> None:
        try:
            payload = _encode_frame(
                {
                    "version": PROTOCOL_VERSION,
                    "id": request_id,
                    "type": "event",
                    "event": event,
                    "data": data,
                },
                max_frame_bytes,
            )
        except _OutboundTooLarge:
            pipe.send(
                (
                    "terminal",
                    _fallback_frame(
                        request_id, "response_too_large", max_frame_bytes
                    ),
                )
            )
            raise _WorkerTerminal
        except (TypeError, ValueError):
            pipe.send(
                (
                    "terminal",
                    _fallback_frame(request_id, "internal_error", max_frame_bytes),
                )
            )
            raise _WorkerTerminal
        pipe.send(("event", event, payload))

    def terminal(frame: dict[str, Any]) -> None:
        try:
            payload = _encode_frame(frame, max_frame_bytes)
        except _OutboundTooLarge:
            payload = _fallback_frame(
                request_id, "response_too_large", max_frame_bytes
            )
        except (TypeError, ValueError):
            payload = _fallback_frame(request_id, "internal_error", max_frame_bytes)
        pipe.send(("terminal", payload))

    try:
        context = BridgeContext(emit, cancelled)
        application = ApplicationFacade(paths)
        if handler is None:
            application._workspace_service()
            if method == "ui.request":
                from core.tui import service_bridge  # noqa: F401
        pipe.send(("ready",))
        result = (
            handler(context, params)
            if handler is not None
            else _call_facade(application, method, params)
        )
        if isinstance(result, AppResult):
            if result.ok:
                terminal(
                    {
                        "version": PROTOCOL_VERSION,
                        "id": request_id,
                        "type": "result",
                        "result": result.data,
                    }
                )
            else:
                error = result.error
                terminal(
                    {
                        "version": PROTOCOL_VERSION,
                        "id": request_id,
                        "type": "error",
                        "error": {
                            "code": error.code if error else "internal_error",
                            "message": error.message
                            if error
                            else "application operation failed",
                            **({"details": error.details} if error and error.details is not None else {}),
                        },
                    }
                )
        else:
            terminal(
                {
                    "version": PROTOCOL_VERSION,
                    "id": request_id,
                    "type": "result",
                    "result": result,
                }
            )
    except _WorkerTerminal:
        pass
    except BridgeCancelled:
        terminal(
            {
                "version": PROTOCOL_VERSION,
                "id": request_id,
                "type": "error",
                "error": {"code": "cancelled", "message": "request cancelled"},
            }
        )
    except Exception:
        try:
            terminal(
                {
                    "version": PROTOCOL_VERSION,
                    "id": request_id,
                    "type": "error",
                    "error": {
                        "code": "internal_error",
                        "message": "bridge handler failed",
                    },
                }
            )
        except Exception:
            pass
    finally:
        pipe.close()


def _self_test_never(_context: BridgeContext, _params: dict[str, Any]) -> None:
    while True:
        time.sleep(1)


class TUIBridgeServer:
    """Serve facade operations to authenticated loopback clients.

    Each request runs in a spawn worker process. Cancellation, timeout, disconnect,
    and close terminate and join that worker before exposing terminal state.
    The existing Python parent owns both TCP and workers; Bun only connects to the
    environment-provided loopback port and never starts Python or a worker.
    """

    def __init__(
        self,
        application: ApplicationFacade,
        *,
        handlers: dict[str, Handler] | None = None,
        max_frame_bytes: int = DEFAULT_MAX_FRAME_BYTES,
        request_timeout: float = 30.0,
        worker_start_timeout: float = 5.0,
        concurrency_limit: int = 8,
        connection_limit: int | None = None,
        authentication_timeout: float = 2.0,
        idle_timeout: float = 30.0,
        close_timeout: float = 2.0,
    ) -> None:
        if connection_limit is None:
            connection_limit = max(4, concurrency_limit * 2)
        if (
            max_frame_bytes < 256
            or request_timeout <= 0
            or worker_start_timeout <= 0
            or concurrency_limit < 1
            or connection_limit < 1
            or authentication_timeout <= 0
            or idle_timeout <= 0
            or close_timeout <= 0
        ):
            raise ValueError("invalid bridge resource limit")
        self.application = application
        self.token = secrets.token_urlsafe(32)
        self.max_frame_bytes = max_frame_bytes
        self.request_timeout = request_timeout
        self.worker_start_timeout = worker_start_timeout
        self.concurrency_limit = concurrency_limit
        self.connection_limit = connection_limit
        self.authentication_timeout = authentication_timeout
        self.idle_timeout = idle_timeout
        self.close_timeout = close_timeout
        self._listener: socket.socket | None = None
        self._address: tuple[str, int] | None = None
        self._closing = threading.Event()
        self._service_threads: set[threading.Thread] = set()
        self._workers: set[Any] = set()
        self._connections: set[_Connection] = set()
        self._active: dict[tuple[int, str], _ActiveRequest] = {}
        self._lock = threading.Lock()
        self._slots = threading.BoundedSemaphore(concurrency_limit)
        self._handlers = dict(handlers or {})
        self._mp = multiprocessing.get_context("spawn")
        self._worker_target = _request_worker

    @property
    def address(self) -> tuple[str, int]:
        if self._address is None:
            raise RuntimeError("bridge is not started")
        return self._address

    @property
    def active_request_count(self) -> int:
        with self._lock:
            return len(self._active)

    @property
    def connection_count(self) -> int:
        with self._lock:
            return len(self._connections)

    @property
    def worker_count(self) -> int:
        with self._lock:
            return sum(process.is_alive() for process in self._workers)

    def child_environment(self) -> dict[str, str]:
        host, port = self.address
        return {
            "SUPERMEDICINE_TUI_BRIDGE_HOST": host,
            "SUPERMEDICINE_TUI_BRIDGE_PORT": str(port),
            "SUPERMEDICINE_TUI_BRIDGE_TOKEN": self.token,
        }

    def start(self) -> "TUIBridgeServer":
        if self._listener is not None:
            return self
        WorkspaceManager(
            self.application.paths.project_root
        ).recover_atomic_transactions()
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen(self.connection_limit)
        listener.settimeout(0.1)
        self._listener = listener
        host, port = listener.getsockname()
        self._address = (str(host), int(port))
        self._spawn_service(self._accept_loop, "tui-bridge-accept")
        return self

    def close(self) -> None:
        if self._closing.is_set():
            return
        self._closing.set()
        listener, self._listener = self._listener, None
        if listener is not None:
            listener.close()
        with self._lock:
            active = list(self._active.values())
            connections = list(self._connections)
        for request in active:
            self._abort(request)
        for connection in connections:
            try:
                connection.socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            connection.socket.close()
        deadline = time.monotonic() + self.close_timeout
        while True:
            with self._lock:
                threads = [
                    thread
                    for thread in self._service_threads
                    if thread is not threading.current_thread() and thread.is_alive()
                ]
            if not threads or time.monotonic() >= deadline:
                break
            for thread in threads:
                thread.join(timeout=min(0.05, max(0.0, deadline - time.monotonic())))

    def _spawn_service(self, target: Callable[[], None], name: str) -> None:
        thread = threading.Thread(target=target, name=name, daemon=True)
        with self._lock:
            self._service_threads = {
                existing for existing in self._service_threads if existing.is_alive()
            }
            self._service_threads.add(thread)
        thread.start()

    def _accept_loop(self) -> None:
        while not self._closing.is_set():
            try:
                listener = self._listener
                if listener is None:
                    break
                client, _ = listener.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            client.settimeout(0.1)
            connection = _Connection(client)
            with self._lock:
                admitted = len(self._connections) < self.connection_limit
                if admitted:
                    self._connections.add(connection)
            if not admitted:
                client.close()
                continue
            self._spawn_service(
                partial(self._connection_loop, connection),
                f"tui-bridge-client-{client.fileno()}",
            )

    def _connection_loop(self, connection: _Connection) -> None:
        client = connection.socket
        buffer = bytearray()
        authenticated = False
        deadline = time.monotonic() + self.authentication_timeout
        try:
            while not self._closing.is_set():
                if time.monotonic() >= deadline:
                    with self._lock:
                        busy = any(
                            connection_id == id(connection)
                            for connection_id, _ in self._active
                        )
                    if not busy:
                        break
                    deadline = time.monotonic() + self.idle_timeout
                try:
                    chunk = client.recv(65536)
                except socket.timeout:
                    continue
                except OSError:
                    break
                if not chunk:
                    break
                buffer.extend(chunk)
                if len(buffer) > self.max_frame_bytes and b"\n" not in buffer:
                    self._error(
                        connection, None, "frame_too_large", "frame exceeds limit"
                    )
                    break
                while b"\n" in buffer:
                    raw, _, remainder = buffer.partition(b"\n")
                    buffer = bytearray(remainder)
                    if len(raw) > self.max_frame_bytes:
                        self._error(
                            connection, None, "frame_too_large", "frame exceeds limit"
                        )
                        return
                    authenticated, keep = self._handle_frame(
                        connection, bytes(raw), authenticated
                    )
                    if not keep:
                        return
                    deadline = time.monotonic() + (
                        self.idle_timeout
                        if authenticated
                        else self.authentication_timeout
                    )
        finally:
            key = id(connection)
            with self._lock:
                self._connections.discard(connection)
                requests = [
                    value
                    for (connection_id, _), value in self._active.items()
                    if connection_id == key
                ]
            for request in requests:
                self._abort(request)
            try:
                client.close()
            except OSError:
                pass

    @staticmethod
    def _reject_constant(value: str) -> None:
        raise ValueError(f"invalid JSON constant: {value}")

    def _handle_frame(
        self, connection: _Connection, raw: bytes, authenticated: bool
    ) -> tuple[bool, bool]:
        try:
            frame = json.loads(raw, parse_constant=self._reject_constant)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            self._error(connection, None, "invalid_json", "invalid JSON frame")
            return authenticated, authenticated
        request_id = frame.get("id") if isinstance(frame, dict) else None
        required = {"version", "id", "type", "method", "params", "token"}
        if not isinstance(frame, dict) or not required.issubset(frame):
            self._error(connection, request_id, "invalid_frame", "missing frame fields")
            return authenticated, authenticated
        token = frame["token"]
        if not isinstance(token, str) or not hmac.compare_digest(token, self.token):
            self._error(
                connection, request_id, "authentication_failed", "authentication failed"
            )
            return authenticated, False
        authenticated = True
        if (
            frame["version"] != PROTOCOL_VERSION
            or not isinstance(request_id, str)
            or not request_id
            or len(request_id) > 128
            or not isinstance(frame["method"], str)
            or not isinstance(frame["params"], dict)
        ):
            self._error(connection, request_id, "invalid_frame", "invalid frame fields")
            return authenticated, True
        if frame["type"] == "cancel":
            self._cancel(connection, request_id)
        elif frame["type"] == "request":
            self._dispatch(connection, request_id, frame["method"], frame["params"])
        else:
            self._error(
                connection, request_id, "invalid_frame", "unsupported frame type"
            )
        return authenticated, True

    def _dispatch(
        self,
        connection: _Connection,
        request_id: str,
        method: str,
        params: dict[str, Any],
    ) -> None:
        handler = self._handlers.get(method)
        if handler is None and method not in _FACADE_METHODS:
            self._error(connection, request_id, "unknown_method", "unknown method")
            return
        if not self._slots.acquire(blocking=False):
            self._error(connection, request_id, "concurrency_limit", "bridge is busy")
            return
        active = _ActiveRequest(request_id, connection)
        key = (id(connection), request_id)
        with self._lock:
            if key in self._active:
                self._slots.release()
                self._error(
                    connection, request_id, "duplicate_id", "request id is active"
                )
                return
            self._active[key] = active
        parent_pipe, child_pipe = self._mp.Pipe(duplex=False)
        cancelled = self._mp.Event()
        active.pipe = parent_pipe
        active.cancelled = cancelled
        process = self._mp.Process(
            target=self._worker_target,
            args=(
                child_pipe,
                cancelled,
                self.application.paths,
                method,
                params,
                handler,
                request_id,
                self.max_frame_bytes,
            ),
            name=f"tui-worker-{request_id[:12]}",
        )
        active.process = process
        with self._lock:
            self._workers.add(process)
        timer = threading.Timer(
            self.worker_start_timeout,
            lambda: self._terminate_error(
                active, "timeout", "bridge worker startup timed out"
            ),
        )
        timer.daemon = True
        active.timer = timer
        timer.start()
        try:
            with active.stop_lock:
                if active.cancelled.is_set() or self._closing.is_set():
                    started = False
                else:
                    process.start()
                    started = True
        except Exception:
            child_pipe.close()
            parent_pipe.close()
            with self._lock:
                self._workers.discard(process)
            self._finish_error(active, "internal_error", "bridge worker failed")
            return
        if not started:
            child_pipe.close()
            parent_pipe.close()
            with self._lock:
                self._workers.discard(process)
            self._abort(active)
            return
        child_pipe.close()
        self._spawn_service(
            lambda: self._monitor_worker(active),
            f"tui-bridge-worker-{request_id[:12]}",
        )

    def _cancel(self, connection: _Connection, request_id: str) -> None:
        with self._lock:
            active = self._active.get((id(connection), request_id))
        if active is None:
            self._error(connection, request_id, "not_found", "request is not active")
            return
        self._terminate_error(active, "cancelled", "request cancelled")

    def _monitor_worker(self, active: _ActiveRequest) -> None:
        pipe = active.pipe
        process = active.process
        if pipe is None or process is None:
            return
        try:
            while True:
                try:
                    if pipe.poll(0.05):
                        message = pipe.recv()
                    elif process.is_alive():
                        continue
                    else:
                        self._stop_worker(active)
                        self._finish_error(
                            active, "internal_error", "bridge worker failed"
                        )
                        return
                except (EOFError, OSError):
                    self._stop_worker(active)
                    self._finish_error(active, "internal_error", "bridge worker failed")
                    return
                kind = message[0]
                if kind == "ready":
                    with active.lock:
                        if active.terminal:
                            return
                        startup_timer = active.timer
                        timer = threading.Timer(
                            self.request_timeout,
                            lambda: self._terminate_error(
                                active, "timeout", "request timed out"
                            ),
                        )
                        timer.daemon = True
                        active.timer = timer
                    if startup_timer is not None:
                        startup_timer.cancel()
                    timer.start()
                    continue
                if kind == "event":
                    self._send_event_bytes(active, message[2])
                    continue
                self._stop_worker(active)
                if kind == "terminal":
                    self._finish_bytes(active, message[1])
                else:
                    self._finish_error(active, "internal_error", "bridge worker failed")
                return
        finally:
            pipe.close()

    def _stop_worker(self, active: _ActiveRequest, *, terminate: bool = False) -> None:
        process = active.process
        if process is None:
            return
        with active.stop_lock:
            try:
                if terminate and process.is_alive():
                    process.terminate()
                process.join(timeout=self.close_timeout)
                if process.is_alive():
                    process.kill()
                    process.join(timeout=self.close_timeout)
                if process.is_alive():
                    raise RuntimeError("bridge worker did not terminate")
            except (AssertionError, ValueError):
                pass
            finally:
                if not process.is_alive():
                    with self._lock:
                        self._workers.discard(process)

    def _abort(self, active: _ActiveRequest) -> None:
        with active.lock:
            if active.terminal:
                return
            active.terminal = True
            active.cancelled.set()
        self._stop_worker(active, terminate=True)
        self._retire(active)

    def _terminate_error(
        self, active: _ActiveRequest, code: str, message: str
    ) -> None:
        with active.lock:
            if active.terminal:
                return
            active.terminal = True
            active.cancelled.set()
        self._stop_worker(active, terminate=True)
        encoded = self._prepare_terminal(
            active,
            {
                "version": PROTOCOL_VERSION,
                "id": active.request_id,
                "type": "error",
                "error": {"code": code, "message": message},
            },
        )
        self._retire(active)
        try:
            active.connection.send_bytes(encoded)
        except OSError:
            pass

    def _encode(self, frame: dict[str, Any]) -> bytes:
        return _encode_frame(frame, self.max_frame_bytes)

    def _fallback_error_bytes(self, request_id: str, code: str) -> bytes:
        return _fallback_frame(request_id, code, self.max_frame_bytes)

    def _prepare_terminal(self, active: _ActiveRequest, frame: dict[str, Any]) -> bytes:
        try:
            return self._encode(frame)
        except _OutboundTooLarge:
            return self._fallback_error_bytes(active.request_id, "response_too_large")
        except (TypeError, ValueError):
            return self._fallback_error_bytes(active.request_id, "internal_error")

    def _send_event_bytes(self, active: _ActiveRequest, payload: bytes) -> None:
        failed = False
        with active.lock:
            if active.terminal:
                return
            try:
                active.connection.send_bytes(payload)
            except OSError:
                failed = True
        if failed:
            self._abort(active)

    def _finish_bytes(self, active: _ActiveRequest, payload: bytes) -> None:
        with active.lock:
            if active.terminal:
                return
            active.terminal = True
        self._retire(active)
        try:
            active.connection.send_bytes(payload)
        except OSError:
            active.cancelled.set()

    def _finish(self, active: _ActiveRequest, frame_type: str, **payload: Any) -> None:
        with active.lock:
            if active.terminal:
                return
            encoded = self._prepare_terminal(
                active,
                {
                    "version": PROTOCOL_VERSION,
                    "id": active.request_id,
                    "type": frame_type,
                    **payload,
                },
            )
            active.terminal = True
        self._retire(active)
        try:
            active.connection.send_bytes(encoded)
        except OSError:
            active.cancelled.set()

    def _finish_error(
        self,
        active: _ActiveRequest,
        code: str,
        message: str,
        *,
        details: Any = None,
    ) -> None:
        error = {"code": code, "message": message}
        if details is not None:
            error["details"] = details
        self._finish(active, "error", error=error)

    def _retire(self, active: _ActiveRequest) -> None:
        with active.retire_lock:
            if active.retired:
                return
            active.retired = True
            timer = active.timer
        if timer is not None and timer is not threading.current_thread():
            timer.cancel()
        self._slots.release()
        with self._lock:
            self._active.pop((id(active.connection), active.request_id), None)

    def _error(
        self, connection: _Connection, request_id: Any, code: str, message: str
    ) -> None:
        safe_id = (
            request_id
            if isinstance(request_id, str) and len(request_id) <= 128
            else None
        )
        try:
            payload = self._encode(
                {
                    "version": PROTOCOL_VERSION,
                    "id": safe_id,
                    "type": "error",
                    "error": {"code": code, "message": message},
                }
            )
            connection.send_bytes(payload)
        except (OSError, TypeError, ValueError, _OutboundTooLarge):
            pass


def bridge_worker_self_test(project_root: str | Path | None = None) -> dict[str, Any]:
    """Exercise a real source/frozen-compatible worker request/cancel/exit cycle."""

    temporary = TemporaryDirectory() if project_root is None else None
    if temporary is not None:
        root = Path(temporary.name)
    else:
        assert project_root is not None
        root = Path(project_root)
    paths = RuntimePaths.resolve(project_root=root, source_root=root)
    server = TUIBridgeServer(
        ApplicationFacade(paths),
        handlers={"self-test.never": _self_test_never},
        request_timeout=10,
        concurrency_limit=1,
    ).start()
    request_result = "failed"
    cancel_result = "failed"
    peer = socket.create_connection(server.address, timeout=20)
    reader = peer.makefile("r", encoding="utf-8", newline="\n")

    def send(request_id: str, method: str, frame_type: str = "request") -> None:
        peer.sendall(
            (
                json.dumps(
                    {
                        "version": PROTOCOL_VERSION,
                        "id": request_id,
                        "type": frame_type,
                        "method": method,
                        "params": {},
                        "token": server.token,
                    }
                )
                + "\n"
            ).encode()
        )

    try:
        send("status", "status")
        request_result = (
            "ok" if json.loads(reader.readline()).get("type") == "result" else "failed"
        )
        send("cancel", "self-test.never")
        send("cancel", "self-test.never", "cancel")
        response = json.loads(reader.readline())
        cancel_result = response.get("error", {}).get("code", "failed")
    finally:
        reader.close()
        peer.close()
        server.close()
        if temporary is not None:
            temporary.cleanup()
    return {
        "topology": BRIDGE_TOPOLOGY,
        "request": request_result,
        "cancel": cancel_result,
        "workers_after_exit": server.worker_count,
        "connections_after_exit": server.connection_count,
        "bun_spawns_python": False,
        "worker_start_method": server._mp.get_start_method(),
    }


__all__ = [
    "BRIDGE_TOPOLOGY",
    "BridgeCancelled",
    "BridgeContext",
    "TUIBridgeServer",
    "bridge_worker_self_test",
]
