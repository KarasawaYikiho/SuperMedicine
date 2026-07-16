"""Authenticated loopback NDJSON bridge for the OpenTUI child process."""

from __future__ import annotations

import hmac
import json
import secrets
import socket
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from core.application import AppResult, ApplicationFacade

PROTOCOL_VERSION = 1
DEFAULT_MAX_FRAME_BYTES = 1024 * 1024
Handler = Callable[["BridgeContext", dict[str, Any]], Any]


class BridgeCancelled(RuntimeError):
    """Raised cooperatively when the peer cancels a request."""


class _OutboundTooLarge(ValueError):
    pass


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
    cancelled: threading.Event = field(default_factory=threading.Event)
    terminal: bool = False
    retired: bool = False
    timer: threading.Timer | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)
    retire_lock: threading.Lock = field(default_factory=threading.Lock)


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
    """Serve facade operations to authenticated loopback clients.

    Python cannot terminate arbitrary threads safely. Timed-out non-cooperative
    handlers are therefore detached daemon work with a separate hard capacity;
    protocol slots and all socket service threads remain immediately reclaimable.
    """

    def __init__(
        self,
        application: ApplicationFacade,
        *,
        handlers: dict[str, Handler] | None = None,
        max_frame_bytes: int = DEFAULT_MAX_FRAME_BYTES,
        request_timeout: float = 30.0,
        concurrency_limit: int = 8,
        connection_limit: int | None = None,
        handler_capacity: int | None = None,
        authentication_timeout: float = 2.0,
        idle_timeout: float = 30.0,
        close_timeout: float = 2.0,
    ) -> None:
        if connection_limit is None:
            connection_limit = max(4, concurrency_limit * 2)
        if handler_capacity is None:
            handler_capacity = max(concurrency_limit + 1, concurrency_limit * 2)
        if (
            max_frame_bytes < 256
            or request_timeout <= 0
            or concurrency_limit < 1
            or connection_limit < 1
            or handler_capacity < concurrency_limit
            or authentication_timeout <= 0
            or idle_timeout <= 0
            or close_timeout <= 0
        ):
            raise ValueError("invalid bridge resource limit")
        self.application = application
        self.token = secrets.token_urlsafe(32)
        self.max_frame_bytes = max_frame_bytes
        self.request_timeout = request_timeout
        self.concurrency_limit = concurrency_limit
        self.connection_limit = connection_limit
        self.handler_capacity = handler_capacity
        self.authentication_timeout = authentication_timeout
        self.idle_timeout = idle_timeout
        self.close_timeout = close_timeout
        self._listener: socket.socket | None = None
        self._address: tuple[str, int] | None = None
        self._closing = threading.Event()
        self._service_threads: set[threading.Thread] = set()
        self._handler_threads: set[threading.Thread] = set()
        self._connections: set[_Connection] = set()
        self._active: dict[tuple[int, str], _ActiveRequest] = {}
        self._lock = threading.Lock()
        self._slots = threading.BoundedSemaphore(concurrency_limit)
        self._handler_slots = threading.BoundedSemaphore(handler_capacity)
        self._handlers = self._facade_handlers()
        self._handlers.update(handlers or {})

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
    def detached_handler_count(self) -> int:
        with self._lock:
            return sum(thread.is_alive() for thread in self._handler_threads)

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
            request.cancelled.set()
            self._retire(request)
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
                lambda connection=connection: self._connection_loop(connection),
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
                    break
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
                request.cancelled.set()
                self._retire(request)
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
        if handler is None:
            self._error(connection, request_id, "unknown_method", "unknown method")
            return
        if not self._slots.acquire(blocking=False):
            self._error(connection, request_id, "concurrency_limit", "bridge is busy")
            return
        if not self._handler_slots.acquire(blocking=False):
            self._slots.release()
            self._error(
                connection, request_id, "worker_capacity", "bridge workers are busy"
            )
            return
        active = _ActiveRequest(request_id, connection)
        key = (id(connection), request_id)
        with self._lock:
            if key in self._active:
                self._handler_slots.release()
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
        active.timer = timer
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
                self._retire(active)
                self._handler_slots.release()
                with self._lock:
                    self._handler_threads.discard(threading.current_thread())

        thread = threading.Thread(
            target=run,
            name=f"tui-handler-{request_id[:12]}",
            daemon=True,
        )
        with self._lock:
            self._handler_threads.add(thread)
        thread.start()

    def _cancel(self, connection: _Connection, request_id: str) -> None:
        with self._lock:
            active = self._active.get((id(connection), request_id))
        if active is None:
            self._error(connection, request_id, "not_found", "request is not active")
            return
        self._finish_error(active, "cancelled", "request cancelled", cancel=True)

    def _encode(self, frame: dict[str, Any]) -> bytes:
        payload = (
            json.dumps(
                frame,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode()
        if len(payload) > self.max_frame_bytes:
            raise _OutboundTooLarge
        return payload

    def _fallback_error_bytes(self, request_id: str, code: str) -> bytes:
        return self._encode(
            {
                "version": PROTOCOL_VERSION,
                "id": request_id,
                "type": "error",
                "error": {"code": code, "message": "bridge response failed"},
            }
        )

    def _prepare_terminal(self, active: _ActiveRequest, frame: dict[str, Any]) -> bytes:
        try:
            return self._encode(frame)
        except _OutboundTooLarge:
            return self._fallback_error_bytes(active.request_id, "response_too_large")
        except (TypeError, ValueError):
            return self._fallback_error_bytes(active.request_id, "internal_error")

    def _send_event(self, active: _ActiveRequest, event: str, data: Any) -> None:
        retire = False
        with active.lock:
            if active.terminal:
                return
            try:
                payload = self._encode(
                    {
                        "version": PROTOCOL_VERSION,
                        "id": active.request_id,
                        "type": "event",
                        "event": event,
                        "data": data,
                    }
                )
            except _OutboundTooLarge:
                payload = self._fallback_error_bytes(
                    active.request_id, "response_too_large"
                )
                active.terminal = True
                active.cancelled.set()
                retire = True
            except (TypeError, ValueError):
                payload = self._fallback_error_bytes(
                    active.request_id, "internal_error"
                )
                active.terminal = True
                active.cancelled.set()
                retire = True
            try:
                active.connection.send_bytes(payload)
            except OSError:
                active.terminal = True
                active.cancelled.set()
                retire = True
        if retire:
            self._retire(active)

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
            try:
                active.connection.send_bytes(encoded)
            except OSError:
                active.cancelled.set()
        self._retire(active)

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

    def _retire(self, active: _ActiveRequest) -> None:
        with active.retire_lock:
            if active.retired:
                return
            active.retired = True
            timer = active.timer
        if timer is not None and timer is not threading.current_thread():
            timer.cancel()
        with self._lock:
            self._active.pop((id(active.connection), active.request_id), None)
        self._slots.release()

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
