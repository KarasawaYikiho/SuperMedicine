"""Authenticated loopback NDJSON bridge for the OpenTUI child process."""

from __future__ import annotations

import json
import secrets
import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable

from core.application import AppResult, ApplicationFacade

PROTOCOL_VERSION = 1
DEFAULT_MAX_FRAME_BYTES = 1024 * 1024
Handler = Callable[["BridgeContext", dict[str, Any]], Any]


class BridgeCancelled(RuntimeError):
    """Raised cooperatively when the peer cancels a request."""


@dataclass(slots=True)
class _Connection:
    socket: socket.socket
    send_lock: threading.Lock = field(default_factory=threading.Lock)

    def send(self, frame: dict[str, Any]) -> None:
        payload = (
            json.dumps(frame, ensure_ascii=False, separators=(",", ":")) + "\n"
        ).encode()
        with self.send_lock:
            self.socket.sendall(payload)


@dataclass(slots=True)
class _ActiveRequest:
    request_id: str
    connection: _Connection
    cancelled: threading.Event = field(default_factory=threading.Event)
    terminal: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)


class BridgeContext:
    """Request context used by long-running handlers for events and cancellation."""

    def __init__(self, server: "TUIBridgeServer", active: _ActiveRequest) -> None:
        self._server = server
        self._active = active

    def emit(self, event: str, data: Any = None) -> None:
        if event not in {"progress", "chunk", "completed"}:
            raise ValueError(f"unsupported bridge event: {event}")
        self.raise_if_cancelled()
        self._server._send_event(self._active, event, data)

    def raise_if_cancelled(self) -> None:
        if self._active.cancelled.is_set():
            raise BridgeCancelled("request cancelled")


class TUIBridgeServer:
    """Serve facade operations to one or more authenticated loopback clients."""

    def __init__(
        self,
        application: ApplicationFacade,
        *,
        handlers: dict[str, Handler] | None = None,
        max_frame_bytes: int = DEFAULT_MAX_FRAME_BYTES,
        request_timeout: float = 30.0,
        concurrency_limit: int = 8,
    ) -> None:
        if max_frame_bytes < 128 or request_timeout <= 0 or concurrency_limit < 1:
            raise ValueError("invalid bridge resource limit")
        self.application = application
        self.token = secrets.token_urlsafe(32)
        self.max_frame_bytes = max_frame_bytes
        self.request_timeout = request_timeout
        self.concurrency_limit = concurrency_limit
        self._listener: socket.socket | None = None
        self._address: tuple[str, int] | None = None
        self._closing = threading.Event()
        self._threads: set[threading.Thread] = set()
        self._connections: set[socket.socket] = set()
        self._active: dict[tuple[int, str], _ActiveRequest] = {}
        self._lock = threading.Lock()
        self._slots = threading.BoundedSemaphore(concurrency_limit)
        self._executor = ThreadPoolExecutor(
            max_workers=concurrency_limit, thread_name_prefix="tui-bridge-worker"
        )
        self._handlers = self._facade_handlers()
        self._handlers.update(handlers or {})

    @property
    def address(self) -> tuple[str, int]:
        if self._address is None:
            raise RuntimeError("bridge is not started")
        return self._address

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
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        listener.settimeout(0.2)
        self._listener = listener
        host, port = listener.getsockname()
        self._address = (str(host), int(port))
        self._spawn(self._accept_loop, "tui-bridge-accept")
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
            request.cancelled.set()
        for connection in connections:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            connection.close()
        for thread in list(self._threads):
            if thread is not threading.current_thread():
                thread.join(timeout=2)
        self._executor.shutdown(wait=True, cancel_futures=True)

    def _spawn(self, target: Callable[[], None], name: str) -> None:
        thread = threading.Thread(target=target, name=name, daemon=True)
        with self._lock:
            self._threads.add(thread)
        thread.start()

    def _accept_loop(self) -> None:
        try:
            while not self._closing.is_set():
                try:
                    client, _ = (
                        self._listener.accept() if self._listener else (None, None)
                    )
                except (OSError, socket.timeout):
                    continue
                if client is None:
                    continue
                client.settimeout(0.2)
                with self._lock:
                    self._connections.add(client)
                self._spawn(
                    lambda client=client: self._connection_loop(client),
                    f"tui-bridge-client-{client.fileno()}",
                )
        finally:
            with self._lock:
                self._threads.discard(threading.current_thread())

    def _connection_loop(self, client: socket.socket) -> None:
        connection = _Connection(client)
        buffer = bytearray()
        try:
            while not self._closing.is_set():
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
                    self._handle_frame(connection, bytes(raw))
        finally:
            with self._lock:
                self._connections.discard(client)
                requests = [
                    value
                    for (descriptor, _), value in self._active.items()
                    if descriptor == client.fileno()
                ]
                self._threads.discard(threading.current_thread())
            for request in requests:
                request.cancelled.set()
            try:
                client.close()
            except OSError:
                pass

    def _handle_frame(self, connection: _Connection, raw: bytes) -> None:
        try:
            frame = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._error(connection, None, "invalid_json", "invalid JSON frame")
            return
        request_id = frame.get("id") if isinstance(frame, dict) else None
        required = {"version", "id", "type", "method", "params", "token"}
        if not isinstance(frame, dict) or not required.issubset(frame):
            self._error(connection, request_id, "invalid_frame", "missing frame fields")
            return
        if frame["token"] != self.token:
            self._error(
                connection, request_id, "authentication_failed", "authentication failed"
            )
            return
        if (
            frame["version"] != PROTOCOL_VERSION
            or not isinstance(request_id, str)
            or not request_id
            or not isinstance(frame["method"], str)
            or not isinstance(frame["params"], dict)
        ):
            self._error(connection, request_id, "invalid_frame", "invalid frame fields")
            return
        if frame["type"] == "cancel":
            self._cancel(connection, request_id)
        elif frame["type"] == "request":
            self._dispatch(connection, request_id, frame["method"], frame["params"])
        else:
            self._error(
                connection, request_id, "invalid_frame", "unsupported frame type"
            )

    def _dispatch(
        self,
        connection: _Connection,
        request_id: str,
        method: str,
        params: dict[str, Any],
    ) -> None:
        handler = self._handlers.get(method)
        if handler is None:
            self._error(connection, request_id, "unknown_method", "unknown method")
            return
        if not self._slots.acquire(blocking=False):
            self._error(connection, request_id, "concurrency_limit", "bridge is busy")
            return
        active = _ActiveRequest(request_id, connection)
        key = (connection.socket.fileno(), request_id)
        with self._lock:
            if key in self._active:
                self._slots.release()
                self._error(
                    connection, request_id, "duplicate_id", "request id is active"
                )
                return
            self._active[key] = active
        timer = threading.Timer(
            self.request_timeout,
            lambda: self._finish_error(
                active, "timeout", "request timed out", cancel=True
            ),
        )
        timer.daemon = True
        timer.start()

        def run() -> None:
            try:
                result = handler(BridgeContext(self, active), params)
                if isinstance(result, AppResult):
                    if result.ok:
                        self._finish(active, "result", result=result.data)
                    else:
                        error = result.error
                        self._finish_error(
                            active,
                            error.code if error else "internal_error",
                            error.message if error else "application operation failed",
                            details=error.details if error else None,
                        )
                else:
                    self._finish(active, "result", result=result)
            except BridgeCancelled:
                self._finish_error(active, "cancelled", "request cancelled")
            except Exception:
                self._finish_error(active, "internal_error", "bridge handler failed")
            finally:
                timer.cancel()
                with self._lock:
                    self._active.pop(key, None)
                self._slots.release()

        self._executor.submit(run)

    def _cancel(self, connection: _Connection, request_id: str) -> None:
        with self._lock:
            active = self._active.get((connection.socket.fileno(), request_id))
        if active is None:
            self._error(connection, request_id, "not_found", "request is not active")
            return
        self._finish_error(active, "cancelled", "request cancelled", cancel=True)

    def _send_event(self, active: _ActiveRequest, event: str, data: Any) -> None:
        with active.lock:
            if active.terminal:
                return
            self._send(
                active.connection,
                {
                    "version": PROTOCOL_VERSION,
                    "id": active.request_id,
                    "type": "event",
                    "event": event,
                    "data": data,
                },
            )

    def _finish(self, active: _ActiveRequest, frame_type: str, **payload: Any) -> None:
        with active.lock:
            if active.terminal:
                return
            active.terminal = True
            self._send(
                active.connection,
                {
                    "version": PROTOCOL_VERSION,
                    "id": active.request_id,
                    "type": frame_type,
                    **payload,
                },
            )

    def _finish_error(
        self,
        active: _ActiveRequest,
        code: str,
        message: str,
        *,
        details: Any = None,
        cancel: bool = False,
    ) -> None:
        if cancel:
            active.cancelled.set()
        error = {"code": code, "message": message}
        if details is not None:
            error["details"] = details
        self._finish(active, "error", error=error)

    def _error(
        self, connection: _Connection, request_id: Any, code: str, message: str
    ) -> None:
        self._send(
            connection,
            {
                "version": PROTOCOL_VERSION,
                "id": request_id,
                "type": "error",
                "error": {"code": code, "message": message},
            },
        )

    @staticmethod
    def _send(connection: _Connection, frame: dict[str, Any]) -> None:
        try:
            connection.send(frame)
        except OSError:
            pass

    def _facade_handlers(self) -> dict[str, Handler]:
        app = self.application
        return {
            "status": lambda _context, _params: {
                "ok": True,
                "workspace_count": len(app.list_workspaces().data or []),
            },
            "workspace.list": lambda _context, _params: app.list_workspaces(),
            "workspace.get": lambda _context, params: app.get_workspace(**params),
            "workspace.create": lambda _context, params: app.create_workspace(**params),
            "workspace.delete": lambda _context, params: app.delete_workspace(**params),
        }


__all__ = ["BridgeCancelled", "BridgeContext", "TUIBridgeServer"]
