#!/usr/bin/env python3
"""SuperMedicine 独立 GUI 应用。

启动带内嵌 Web 服务的原生 Chromium 窗口。
可双击运行，无需浏览器或终端。
"""

from __future__ import annotations

import os
import sys
import socket
import logging
import threading
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Setup logging for GUI mode (no console)
def setup_gui_logging():
    """配置 GUI 应用日志。"""
    from core.log_report_handler import (
        configure_application_log_storage,
        install_log_report_streams,
    )

    project_dir = Path(__file__).parent
    session_id = configure_application_log_storage(project_dir)
    install_log_report_streams(project_dir, session_id=session_id)
    if sys.stdin is None:
        sys.stdin = open(os.devnull, "r")

    return logging.getLogger(__name__)


def find_available_port(host: str = "127.0.0.1") -> int:
    """查找 Web 服务可用端口。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return s.getsockname()[1]


def start_web_server(host: str, port: int, ready_event: threading.Event):
    """在线程中启动 FastAPI Web 服务。"""
    try:
        from core.web.server import create_app
        import uvicorn

        app = create_app()
        ready_event.set()

        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="warning",
            access_log=False
        )
        server = uvicorn.Server(config)
        server.run()
    except Exception as e:
        logging.error(f"Web 服务错误: {e}")
        ready_event.set()


def main():
    """启动 SuperMedicine GUI 应用。"""
    logger = setup_gui_logging()
    logger.info("正在启动 SuperMedicine GUI...")

    import webview  # type: ignore[import-not-found]

    host = "127.0.0.1"
    port = find_available_port(host)
    url = f"http://{host}:{port}"

    logger.info(f"Web 服务将在 {url} 启动")

    # Start web server in background thread
    ready_event = threading.Event()
    server_thread = threading.Thread(
        target=start_web_server,
        args=(host, port, ready_event),
        daemon=True
    )
    server_thread.start()

    # Wait for server to be ready
    ready_event.wait(timeout=10)
    time.sleep(1)  # Give server a moment to fully start

    logger.info(f"正在打开 GUI 窗口：{url}")

    # Resolve icon path
    # In a frozen PyInstaller executable, bundled data is extracted to sys._MEIPASS.
    # In development, assets/ lives next to this script.
    if getattr(sys, "frozen", False):
        _base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        _base = Path(__file__).parent
    icon_path = _base / "assets" / "logo.ico"

    # Create and start the GUI window
    webview.create_window(
        title="SuperMedicine 桌面版",
        url=url,
        width=1200,
        height=800,
        min_size=(800, 600),
        resizable=True,
        text_select=True,
        icon=str(icon_path)
    )

    # Start the GUI (this blocks until window is closed)
    webview.start(debug=False)

    logger.info("GUI 窗口已关闭，正在退出...")


if __name__ == "__main__":
    main()
