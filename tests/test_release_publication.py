from __future__ import annotations

import json
import subprocess

import pytest

from scripts.ci import publish_release, validate_release_tag


def test_release_toml_readers_support_python_310():
    root = validate_release_tag.REPOSITORY_ROOT
    for relative in (
        "scripts/ci/validate_release_tag.py",
        "scripts/ci/build_release_zip.py",
    ):
        source = (root / relative).read_text(encoding="utf-8")
        assert "except ModuleNotFoundError" in source
        assert "import tomli as tomllib" in source


def _completed(
    args: tuple[str, ...],
    *,
    returncode: int = 0,
    stdout: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args, returncode, stdout=stdout, stderr="")


def test_automatic_release_uses_expected_version_and_exact_source_sha(monkeypatch):
    source_sha = "a" * 40
    calls: list[tuple[str, ...]] = []

    monkeypatch.setattr(validate_release_tag, "package_version", lambda: "0.5.0b0")

    def fake_run(*command: str, check: bool = True):
        calls.append(command)
        assert check is True
        assert command == ("git", "rev-parse", "HEAD")
        return _completed(command, stdout=f"{source_sha}\n")

    monkeypatch.setattr(validate_release_tag, "_run", fake_run)

    result = validate_release_tag.validate(
        "master",
        source_sha,
        dry_run=False,
        allow_non_tag=True,
    )

    assert result == {
        "release_label": "v0.5.0b0",
        "release_title": "SuperMedicine 0.5.0b0",
        "archive_name": "SuperMedicine v0.5.0b0.zip",
        "source_sha": source_sha,
    }
    assert calls == [("git", "rev-parse", "HEAD")]


def test_release_validation_rejects_wrong_checked_out_commit(monkeypatch):
    monkeypatch.setattr(validate_release_tag, "package_version", lambda: "0.5.0b0")
    monkeypatch.setattr(
        validate_release_tag,
        "_run",
        lambda *command, check=True: _completed(command, stdout=f"{'b' * 40}\n"),
    )

    with pytest.raises(ValueError, match="does not match source commit"):
        validate_release_tag.validate(
            "master",
            "a" * 40,
            dry_run=False,
            allow_non_tag=True,
        )


@pytest.mark.parametrize("existing", [False, True])
def test_publish_release_creates_or_refreshes_through_verified_draft(
    tmp_path, monkeypatch, existing
):
    notes = tmp_path / "release-notes.md"
    archive = tmp_path / "SuperMedicine v0.5.0b0.zip"
    checksum = tmp_path / "SuperMedicine v0.5.0b0.zip.sha256"
    notes.write_text("notes", encoding="utf-8")
    archive.write_bytes(b"archive")
    checksum.write_text("digest", encoding="ascii")
    calls: list[tuple[tuple[str, ...], bool]] = []

    def fake_gh(*args: str, check: bool = True):
        calls.append((args, check))
        if args[:2] == ("release", "view") and "--json" not in args:
            return _completed(args, returncode=0 if existing else 1)
        if args[:2] == ("release", "view"):
            payload = {
                "isDraft": True,
                "assets": [{"name": archive.name}, {"name": checksum.name}],
            }
            return _completed(args, stdout=json.dumps(payload))
        return _completed(args)

    monkeypatch.setattr(publish_release, "_gh", fake_gh)

    publish_release.publish(
        "v0.5.0b0",
        "SuperMedicine 0.5.0b0",
        notes,
        archive,
        checksum,
        dry_run=False,
    )

    action = "edit" if existing else "create"
    assert calls[1][0][:2] == ("release", action)
    upload = next(args for args, _ in calls if args[:2] == ("release", "upload"))
    assert upload[-1] == "--clobber"
    assert calls[-1][0] == ("release", "edit", "v0.5.0b0", "--draft=false")
