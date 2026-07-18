from __future__ import annotations

import json
import re
import socket
import subprocess
import sys
from pathlib import Path


def test_desktop_paths_use_user_storage_not_bundle_root(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "Local App Data"))
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "bundle"), raising=False)

    from core.web.desktop import desktop_paths

    paths = desktop_paths()
    assert paths.data_dir == tmp_path / "Local App Data" / "SuperMedicine"
    assert paths.log_dir == paths.data_dir / ".supermedicine" / "logs"
    assert not paths.data_dir.is_relative_to(Path(sys._MEIPASS))


def test_desktop_server_reserves_bound_loopback_socket():
    from core.web.desktop import reserve_loopback_socket

    reserved = reserve_loopback_socket()
    try:
        host, port = reserved.getsockname()
        assert host == "127.0.0.1"
        assert port > 0
        competitor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            assert competitor.connect_ex((host, port)) != 0
        finally:
            competitor.close()
    finally:
        reserved.close()


def test_desktop_self_test_checks_backend_health_frontend_and_storage(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "Desktop Data"))
    monkeypatch.chdir(tmp_path)

    from core.web.desktop import desktop_self_test

    report = desktop_self_test(timeout=10.0)
    assert report["ok"] is True, report
    assert report["checks"] == {
        "backend": True,
        "frontend": True,
        "health": True,
        "logs": True,
        "resources": True,
        "user_data": True,
        "webview": True,
    }
    assert Path(report["paths"]["data_dir"]).is_dir()
    assert Path(report["paths"]["log_dir"]).is_dir()


def test_gui_entry_self_test_is_machine_readable_from_non_repo_directory(tmp_path):
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / "gui_entry.py"), "--self-test"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["checks"]["frontend"] is True


def test_desktop_extra_and_gui_builder_install_desktop_and_web_extras():
    root = Path(__file__).resolve().parents[1]
    pyproject = root.joinpath("pyproject.toml").read_text(encoding="utf-8")
    builder = root.joinpath("scripts/ci/build_gui_exe.py").read_text(encoding="utf-8")
    assert "desktop = [" in pyproject
    assert '"pywebview' in pyproject
    assert '"websockets>=12,<16"' in pyproject
    assert ".[desktop,web]" in builder
    assert '"websockets"' in builder


def test_frontend_all_buttons_are_wired_and_packaged_for_offline_access():
    frontend = Path(__file__).resolve().parents[1] / "core" / "web" / "frontend"
    html = frontend.joinpath("index.html").read_text(encoding="utf-8")
    javascript = frontend.joinpath("app.js").read_text(encoding="utf-8")
    styles = frontend.joinpath("style.css").read_text(encoding="utf-8")
    button_ids = {
        value
        for value in re.findall(r'id="([^"]+)"', html)
        if value.startswith("btn-")
        or value in {"hamburger-btn", "drawer-close-btn", "send-btn"}
    }
    assert len(button_ids) == 47
    assert not {button_id for button_id in button_ids if button_id not in javascript}
    assert html.count('data-tab="') == 13
    assert "https://fonts." not in html
    assert "prefers-reduced-motion" in styles
