# SuperMedicine Web GUI Launcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a new GUI entry point that launches the web server and opens the browser automatically when the EXE is double-clicked, without requiring terminal interaction.

**Architecture:** Create a new `gui_entry.py` script that starts the web server in a background thread and opens the default browser. Update the PyInstaller spec to use this entry point with `console=False` to hide the terminal window.

**Tech Stack:** Python, FastAPI, uvicorn, webbrowser module, threading

---

## File Structure

### Files to Create:
- `gui_entry.py` - New GUI launcher entry point
- `tests/test_gui_entrypoint.py` - Tests for the GUI launcher

### Files to Modify:
- `.pyinstaller-spec/SuperMedicine.spec` - Update entry point and console setting

---

## Task 1: Create GUI Entry Point Script

**Files:**
- Create: `gui_entry.py`

- [ ] **Step 1: Create the GUI launcher script**

```python
#!/usr/bin/env python3
"""SuperMedicine GUI Launcher - launches web server and opens browser."""

from __future__ import annotations

import logging
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

logger = logging.getLogger(__name__)


def _open_browser(host: str = "127.0.0.1", port: int = 8000, delay: float = 2.0) -> None:
    """Open the default browser after a delay to allow server startup."""
    time.sleep(delay)
    url = f"http://{host}:{port}"
    logger.info("Opening browser: %s", url)
    webbrowser.open(url)


def main() -> None:
    """Launch the SuperMedicine web server and open the browser."""
    from core.web.server import start_server

    host = "127.0.0.1"
    port = 8000
    
    # Start browser opener in a background thread
    browser_thread = threading.Thread(
        target=_open_browser,
        args=(host, port),
        daemon=True,
    )
    browser_thread.start()
    
    # Start the web server (this blocks)
    logger.info("Starting SuperMedicine Web GUI...")
    start_server(host, port)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run syntax check**

Run: `python -m py_compile gui_entry.py`
Expected: No output (success)

- [ ] **Step 3: Commit**

```bash
git add gui_entry.py
git commit -m "feat: add GUI launcher entry point for web browser interface"
```

---

## Task 2: Update PyInstaller Spec for GUI Mode

**Files:**
- Modify: `.pyinstaller-spec/SuperMedicine.spec`

- [ ] **Step 1: Update the spec file to use GUI entry point**

Change the Analysis entry point from `cli_entry.py` to `gui_entry.py` and set `console=False`:

```python
# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['..\\gui_entry.py'],  # Changed from cli_entry.py
    pathex=[],
    binaries=[],
    datas=[('D:\\GIT\\SuperMedicine\\core\\tui\\app.tcss', 'core\\tui'), ('D:\\GIT\\SuperMedicine\\assets', 'assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SuperMedicine',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Changed from True to False for GUI mode
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

- [ ] **Step 2: Verify spec file syntax**

Run: `python -c "import PyInstaller; print('PyInstaller available')"`
Expected: `PyInstaller available`

- [ ] **Step 3: Commit**

```bash
git add .pyinstaller-spec/SuperMedicine.spec
git commit -m "feat: update PyInstaller spec for GUI mode (console=False)"
```

---

## Task 3: Add GUI Entry Point Tests

**Files:**
- Create: `tests/test_gui_entrypoint.py`

- [ ] **Step 1: Create test file**

```python
from __future__ import annotations

import pytest
import threading
import time
from unittest.mock import patch, MagicMock
from pathlib import Path

from gui_entry import _open_browser, main


def test_open_browser_opens_correct_url():
    """Test that _open_browser opens the correct URL after delay."""
    with patch("webbrowser.open") as mock_open:
        _open_browser(host="127.0.0.1", port=8000, delay=0.01)
        mock_open.assert_called_once_with("http://127.0.0.1:8000")


def test_open_browser_respects_custom_host_port():
    """Test that _open_browser uses custom host and port."""
    with patch("webbrowser.open") as mock_open:
        _open_browser(host="0.0.0.0", port=9000, delay=0.01)
        mock_open.assert_called_once_with("http://0.0.0.0:9000")


def test_main_starts_server():
    """Test that main() starts the web server."""
    with patch("gui_entry.start_server") as mock_start:
        with patch("gui_entry.threading.Thread") as mock_thread:
            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance
            
            # Call main
            main()
            
            # Verify thread was created and started
            mock_thread.assert_called_once()
            mock_thread_instance.start.assert_called_once()
            
            # Verify server was started
            mock_start.assert_called_once_with("127.0.0.1", 8000)


def test_main_uses_default_host_port():
    """Test that main() uses default host and port."""
    with patch("gui_entry.start_server") as mock_start:
        with patch("gui_entry.threading.Thread"):
            main()
            mock_start.assert_called_once_with("127.0.0.1", 8000)


def test_browser_thread_is_daemon():
    """Test that browser thread is daemon so it doesn't block exit."""
    with patch("gui_entry.start_server"):
        with patch("gui_entry.threading.Thread") as mock_thread:
            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance
            
            main()
            
            # Check that daemon=True was passed
            call_kwargs = mock_thread.call_args[1]
            assert call_kwargs.get("daemon") is True
```

- [ ] **Step 2: Run the tests**

Run: `python -m pytest tests/test_gui_entrypoint.py -v`
Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add tests/test_gui_entrypoint.py
git commit -m "test: add tests for GUI launcher entry point"
```

---

## Task 4: Add CLI Fallback Command (Optional)

**Files:**
- Modify: `cli_entry.py` (already has `web` method, no changes needed)

The CLI already has a `web` command that can be used as a fallback:
```
supermedicine web
```

This provides backwards compatibility for users who want to launch the web interface from the command line.

---

## Task 5: Update Documentation

**Files:**
- Modify: `README.md`
- Modify: `README.zh-CN.md`

- [ ] **Step 1: Add GUI launcher documentation to README.md**

Add a new section after the installation section:

```markdown
## Quick Start - GUI Mode

Double-click `SuperMedicine.exe` to launch the web interface automatically. The browser will open to `http://localhost:8000`.

### Command Line Options

- `SuperMedicine.exe web` - Launch web interface from command line
- `SuperMedicine.exe tui` - Launch terminal UI
- `SuperMedicine.exe --help` - Show all available commands
```

- [ ] **Step 2: Add GUI launcher documentation to README.zh-CN.md**

Add the same section in Chinese:

```markdown
## 快速开始 - GUI 模式

双击 `SuperMedicine.exe` 即可自动启动 Web 界面。浏览器将自动打开 `http://localhost:8000`。

### 命令行选项

- `SuperMedicine.exe web` - 从命令行启动 Web 界面
- `SuperMedicine.exe tui` - 启动终端 UI
- `SuperMedicine.exe --help` - 显示所有可用命令
```

- [ ] **Step 3: Commit**

```bash
git add README.md README.zh-CN.md
git commit -m "docs: add GUI launcher quick start instructions"
```

---

## Dependencies

- Task 1 (Create GUI Entry Point) must be completed before Task 3 (Add Tests)
- Task 2 (Update PyInstaller Spec) is independent of Task 1 and Task 3
- Task 5 (Update Documentation) can be done in parallel with other tasks

---

## Verification Checklist

After implementation, verify:

- [ ] `gui_entry.py` exists and passes syntax check
- [ ] `tests/test_gui_entrypoint.py` exists and all tests pass
- [ ] `.pyinstaller-spec/SuperMedicine.spec` uses `gui_entry.py` and `console=False`
- [ ] Building the EXE with PyInstaller produces a working GUI launcher
- [ ] Double-clicking the EXE opens the browser to `http://localhost:8000`
- [ ] The EXE runs without showing a terminal window
- [ ] The `supermedicine web` CLI command still works as a fallback
- [ ] Documentation is updated with GUI launcher instructions

---

## Notes

- The browser opens after a 2-second delay to allow the server to start
- The browser thread is daemon so it doesn't prevent the application from exiting
- The web server runs in the main thread and blocks until stopped
- Default host is `127.0.0.1` (localhost only) for security
- Default port is `8000` to match existing web server configuration
