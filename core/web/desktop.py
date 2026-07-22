"""Native desktop runtime for the shared SuperMedicine Web application."""

from __future__ import annotations

import importlib.resources
import importlib.util
import http.client
import json
import os
import socket
import sys
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class DesktopPaths:
    data_dir: Path
    log_dir: Path


def desktop_paths() -> DesktopPaths:
    """Return persistent user-owned paths, never the frozen bundle directory."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData/Local")
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
    data_dir = base / "SuperMedicine"
    return DesktopPaths(
        data_dir=data_dir,
        log_dir=data_dir / ".supermedicine" / "logs",
    )


def ensure_desktop_paths(paths: DesktopPaths | None = None) -> DesktopPaths:
    selected = paths or desktop_paths()
    selected.data_dir.mkdir(parents=True, exist_ok=True)
    selected.log_dir.mkdir(parents=True, exist_ok=True)
    return selected


def frontend_directory() -> Path:
    """Resolve packaged frontend resources independently of the current directory."""
    resource = importlib.resources.files("core.web").joinpath("frontend")
    directory = Path(str(resource))
    required = (directory / "index.html", directory / "app.js", directory / "style.css")
    if not directory.is_dir() or not all(path.is_file() for path in required):
        raise FileNotFoundError(
            "SuperMedicine frontend resources are missing; reinstall the desktop package"
        )
    return directory


def reserve_loopback_socket(host: str = "127.0.0.1") -> socket.socket:
    """Bind and retain an ephemeral loopback socket to avoid port TOCTOU."""
    reserved = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    reserved.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    reserved.bind((host, 0))
    return reserved


def wait_for_url(url: str, *, timeout: float = 10.0) -> bytes:
    from urllib.parse import urlsplit

    parsed = urlsplit(url)
    if parsed.scheme != "http" or not parsed.hostname:
        raise ValueError(f"Desktop health URL must be loopback HTTP: {url}")
    host = parsed.hostname
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        connection: http.client.HTTPConnection | None = None
        try:
            connection = http.client.HTTPConnection(
                host, parsed.port, timeout=0.5
            )
            connection.request("GET", parsed.path or "/")
            response = connection.getresponse()
            if 200 <= response.status < 300:
                return response.read()
        except OSError as exc:
            last_error = exc
        finally:
            if connection is not None:
                connection.close()
        time.sleep(0.05)
    raise TimeoutError(f"Desktop backend did not become healthy at {url}: {last_error}")


class DesktopServer:
    """Run Uvicorn on one pre-bound socket and expose deterministic shutdown."""

    def __init__(self, app: Any, *, host: str = "127.0.0.1") -> None:
        self.app = app
        self.host = host
        self.socket = reserve_loopback_socket(host)
        self.port = int(self.socket.getsockname()[1])
        self.url = f"http://{host}:{self.port}"
        self._server: Any = None
        self._thread: threading.Thread | None = None

    def start(self, *, timeout: float = 10.0) -> None:
        import uvicorn

        config = uvicorn.Config(
            self.app, log_level="warning", access_log=False, log_config=None
        )
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(
            target=self._server.run,
            kwargs={"sockets": [self.socket]},
            name="supermedicine-desktop-backend",
            daemon=True,
        )
        self._thread.start()
        wait_for_url(f"{self.url}/api/v1/health", timeout=timeout)

    def stop(self) -> None:
        if self._server is not None:
            self._server.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        try:
            self.socket.close()
        except OSError:
            pass


def webview_diagnostics() -> dict[str, Any]:
    available = importlib.util.find_spec("webview") is not None
    details: dict[str, Any] = {
        "available": available,
        "backend": "edgechromium" if sys.platform == "win32" else "platform-default",
    }
    if not available:
        details["action"] = "Install SuperMedicine with the desktop extra: pip install .[desktop,web]"
    elif sys.platform == "win32":
        details["action"] = (
            "If the window cannot open, install Microsoft Edge WebView2 Runtime "
            "from the official Microsoft installer."
        )
    return details


def desktop_self_test(*, timeout: float = 10.0) -> dict[str, Any]:
    """Exercise packaged resources and a real ephemeral backend without opening a window."""
    paths = ensure_desktop_paths()
    checks = {
        "backend": False,
        "frontend": False,
        "health": False,
        "logs": paths.log_dir.is_dir(),
        "resources": False,
        "user_data": paths.data_dir.is_dir(),
        "webview": bool(webview_diagnostics()["available"]),
    }
    error = ""
    server: DesktopServer | None = None
    try:
        frontend = frontend_directory()
        checks["resources"] = True
        from core.web.server import create_app

        server = DesktopServer(create_app())
        server.start(timeout=timeout)
        checks["backend"] = True
        health = json.loads(
            wait_for_url(f"{server.url}/api/v1/health", timeout=timeout).decode("utf-8")
        )
        checks["health"] = health.get("status") == "ok"
        page = wait_for_url(f"{server.url}/", timeout=timeout).decode("utf-8")
        checks["frontend"] = "SuperMedicine" in page and frontend.is_dir()
    except Exception as exc:  # report every self-test failure in one stable payload
        error = str(exc)
    finally:
        if server is not None:
            server.stop()
    report: dict[str, Any] = {
        "ok": all(checks.values()),
        "checks": checks,
        "paths": {name: str(value) for name, value in asdict(paths).items()},
        "webview": webview_diagnostics(),
    }
    if error:
        report["error"] = error
    return report


def launch_desktop(*, timeout: float = 15.0) -> None:
    """Start the shared backend, verify health, then open the native window."""
    paths = ensure_desktop_paths()
    os.chdir(paths.data_dir)
    from core.log_report_handler import (
        configure_application_log_storage,
        install_log_report_streams,
    )
    from core.web.server import create_app

    session_id = configure_application_log_storage(paths.data_dir)
    install_log_report_streams(paths.data_dir, session_id=session_id)
    server = DesktopServer(create_app())
    server.start(timeout=timeout)
    try:
        try:
            import webview
        except ImportError as exc:
            raise RuntimeError(webview_diagnostics()["action"]) from exc
        webview.create_window("SuperMedicine", server.url, min_size=(960, 640))
        try:
            webview.start(gui="edgechromium" if sys.platform == "win32" else None)
        except Exception as exc:
            action = webview_diagnostics().get("action", "Check the desktop runtime")
            raise RuntimeError(f"Unable to start the desktop WebView: {exc}. {action}") from exc
    finally:
        server.stop()
