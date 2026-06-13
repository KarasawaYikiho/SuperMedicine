#!/usr/bin/env python3
"""SuperMedicine GUI Launcher.

This script launches the SuperMedicine web GUI directly when double-clicked.
It starts the web server in the background and opens the default browser.
"""

from __future__ import annotations

import sys
import time
import threading
import webbrowser
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def open_browser(url: str, delay: float = 2.0) -> None:
    """Open the default browser after a delay."""
    time.sleep(delay)
    webbrowser.open(url)


def main() -> None:
    """Launch the SuperMedicine web GUI."""
    from core.web.server import start_server
    
    host = "127.0.0.1"
    port = 8000
    url = f"http://{host}:{port}"
    
    print(f"Starting SuperMedicine Web GUI...")
    print(f"Opening browser to {url}")
    print(f"Press Ctrl+C to stop the server.")
    
    # Start browser in a separate thread
    browser_thread = threading.Thread(target=open_browser, args=(url,), daemon=True)
    browser_thread.start()
    
    # Start the web server (this will block)
    try:
        start_server(host, port)
    except KeyboardInterrupt:
        print("\nShutting down SuperMedicine...")
        sys.exit(0)


if __name__ == "__main__":
    main()
