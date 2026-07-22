"""Behavior tests for the shared PyInstaller build engine."""

from __future__ import annotations

from types import SimpleNamespace

from scripts.ci import _pyinstaller_builder as builder


def test_builder_does_not_install_project_when_required_modules_exist(
    tmp_path, monkeypatch
):
    (tmp_path / "entry.py").write_text("pass", encoding="utf-8")
    (tmp_path / "logo.ico").write_bytes(b"icon")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nversion = "1.0.0"\n', encoding="utf-8"
    )
    commands: list[list[str]] = []

    def fake_run(command, **_kwargs):
        commands.append(command)
        if "PyInstaller" in command:
            output = tmp_path / "dist" / "Demo.exe"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"exe")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(builder.subprocess, "run", fake_run)
    monkeypatch.setattr(builder.importlib.util, "find_spec", lambda _name: object())
    target = builder.PyInstallerTarget(
        entry_script="entry.py",
        output_name="Demo",
        data_items=(),
        hidden_imports=(),
        icon=tmp_path / "logo.ico",
        build_extras=".[desktop,web]",
        required_modules=("PyInstaller", "webview"),
    )

    assert builder.build_executable(tmp_path, target) == tmp_path / "dist" / "Demo.exe"
    assert not any("pip" in command for command in commands)


def test_add_data_places_single_file_at_its_declared_relative_path(tmp_path):
    (tmp_path / "install.json").write_text("{}", encoding="utf-8")

    args = builder._add_data_args(tmp_path, ("install.json",))

    assert args == [f"--add-data={tmp_path / 'install.json'}{builder._separator()}."]


def test_add_data_supports_an_explicit_bundle_destination(tmp_path):
    payload = tmp_path / "stage" / "release_payload"
    payload.mkdir(parents=True)

    args = builder._add_data_args(
        tmp_path, (("stage/release_payload", "release_payload"),)
    )

    assert args == [f"--add-data={payload}{builder._separator()}release_payload"]


def test_application_executable_preserves_console_mode(tmp_path, monkeypatch):
    captured = {}

    def fake_build(root, target):
        captured["root"] = root
        captured["target"] = target
        return None

    monkeypatch.setattr(builder, "build_executable", fake_build)
    builder.build_application(tmp_path)

    assert captured["root"] == tmp_path
    assert captured["target"].windowed is False


def test_windows_version_info_comes_from_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nversion = "1.2.3b4"\n', encoding="utf-8"
    )
    target = builder.PyInstallerTarget(
        entry_script="entry.py",
        output_name="Demo",
        data_items=(),
        hidden_imports=(),
        icon=tmp_path / "logo.ico",
    )

    version_file = builder._write_version_info(tmp_path, tmp_path / "build", target)

    source = version_file.read_text(encoding="utf-8")
    assert "filevers=(1, 2, 3, 4)" in source
    assert "ProductVersion', '1.2.3b4'" in source
