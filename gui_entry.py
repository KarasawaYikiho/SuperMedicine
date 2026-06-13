#!/usr/bin/env python3
"""SuperMedicine GUI Launcher.

This script launches the SuperMedicine web GUI directly when double-clicked.
It starts the web server in the background and opens the default browser.
"""

from __future__ import annotations

import os
import sys
import time
import threading
import webbrowser
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def setup_logging_for_gui() -> None:
    """Set up logging when running without a console window."""
    # Redirect stdout/stderr to a log file if they are None (no console)
    log_dir = Path.home() / ".supermedicine" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "gui.log"

    if sys.stdout is None:
        sys.stdout = open(log_file, "a", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(log_file, "a", encoding="utf-8")

    # Also redirect stdin if needed
    if sys.stdin is None:
        sys.stdin = open(os.devnull, "r")


def open_browser(url: str, delay: float = 2.0) -> None:
    """Open the default browser after a delay."""
    time.sleep(delay)
    webbrowser.open(url)


def main() -> None:
    """Launch the SuperMedicine web GUI."""
    # Set up logging for GUI mode
    setup_logging_for_gui()

    from core.web.server import start_server

    host = "127.0.0.1"
    port = 8000
    url = f"http://{host}:{port}"

    print("Starting SuperMedicine Web GUI...")
    print(f"Opening browser to {url}")
    print("Logs are being written to ~/.supermedicine/logs/gui.log")

    # Start browser in a separate thread
    browser_thread = threading.Thread(target=open_browser, args=(url,), daemon=True)
    browser_thread.start()

    # Start the web server (this will block)
    try:
        start_server(host, port, log_level="warning")
    except KeyboardInterrupt:
        print("\nShutting down SuperMedicine...")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
