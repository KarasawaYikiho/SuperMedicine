#!/usr/bin/env python3
"""SuperMedicine Standalone GUI Application.

Launches a native Chromium-based window with embedded web server.
Double-click to run - no browser or terminal needed.
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
    """Configure logging for GUI application."""
    log_dir = Path.home() / ".supermedicine" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "gui_standalone.log"

    # Redirect stdout/stderr if None (no console)
    if sys.stdout is None:
        sys.stdout = open(log_file, "a", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(log_file, "a", encoding="utf-8")
    if sys.stdin is None:
        sys.stdin = open(os.devnull, "r")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)


def find_available_port(host: str = "127.0.0.1") -> int:
    """Find an available port for the web server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return s.getsockname()[1]


def start_web_server(host: str, port: int, ready_event: threading.Event):
    """Start the FastAPI web server in a thread."""
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
        logging.error(f"Server error: {e}")
        ready_event.set()


def main():
    """Launch the SuperMedicine GUI application."""
    logger = setup_gui_logging()
    logger.info("Starting SuperMedicine GUI...")

    import webview

    host = "127.0.0.1"
    port = find_available_port(host)
    url = f"http://{host}:{port}"

    logger.info(f"Server will start on {url}")

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

    logger.info(f"Opening GUI window at {url}")

    # Create and start the GUI window
    webview.create_window(
        title="SuperMedicine",
        url=url,
        width=1200,
        height=800,
        min_size=(800, 600),
        resizable=True,
        text_select=True
    )

    # Start the GUI (this blocks until window is closed)
    webview.start(debug=False)

    logger.info("GUI window closed, shutting down...")


if __name__ == "__main__":
    main()
