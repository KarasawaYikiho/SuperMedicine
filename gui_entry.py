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
    from core.log_report_handler import (
        configure_application_log_storage,
        install_log_report_streams,
    )

    project_dir = Path(__file__).parent
    session_id = configure_application_log_storage(project_dir)
    install_log_report_streams(project_dir, session_id=session_id)

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
    print("Logs are being written to the current .supermedicine/logs session file")

    # Start browser in a separate thread
    browser_thread = threading.Thread(target=open_browser, args=(url,), daemon=True)
    browser_thread.start()

    # Start the web server (this will block)
    try:
        start_server(host, port)
    except KeyboardInterrupt:
        print("\nShutting down SuperMedicine...")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
