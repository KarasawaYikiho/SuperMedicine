from __future__ import annotations

import io
import base64
import hashlib
import subprocess
import tarfile
import zipfile
from pathlib import Path

from setuptools import setup  # type: ignore[import-untyped]
from setuptools.command.build_py import build_py as _build_py  # type: ignore[import-untyped]
from setuptools.command.sdist import sdist as _sdist  # type: ignore[import-untyped]

try:
    from wheel.bdist_wheel import bdist_wheel as _bdist_wheel  # type: ignore[import-untyped]
except Exception:  # pragma: no cover - wheel is a build dependency in pyproject
    _bdist_wheel = None  # type: ignore[assignment]


LOWERCASE_INSTALL_NAME = "install.py"
UPPERCASE_INSTALL_NAME = "install_entry.py"
LOWERCASE_INSTALL_BYTES = b'''#!/usr/bin/env python3
"""Lowercase compatibility entrypoint for the SuperMedicine installer."""
from __future__ import annotations

from installer.entrypoint import main


if __name__ == "__main__":
    main()
'''
UPPERCASE_INSTALL_BYTES = b'''#!/usr/bin/env python3
"""Compatibility wrapper for the stable lowercase installer entrypoint."""
from __future__ import annotations

from installer import entrypoint as _entrypoint

globals().update(
    {
        name: getattr(_entrypoint, name)
        for name in dir(_entrypoint)
        if not (name.startswith("__") and name.endswith("__"))
    }
)

__all__ = [name for name in globals() if not (name.startswith("__") and name.endswith("__"))]

if __name__ == "__main__":
    try:
        _entrypoint.main()
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc
'''

STALE_DISTRIBUTION_MEMBERS = frozenset({"plugins/tools/r_template/plugin.yaml"})


def _repo_root() -> Path:
    return Path(__file__).resolve().parent


def _lowercase_install_bytes() -> bytes:
    """Return exact lowercase wrapper bytes without relying on case-only files."""

    try:
        result = subprocess.run(
            ["git", "show", ":install.py"],
            cwd=_repo_root(),
            check=False,
            capture_output=True,
        )
    except (OSError, ValueError):
        return LOWERCASE_INSTALL_BYTES
    if (
        result.returncode == 0
        and b"from installer.entrypoint import main" in result.stdout
    ):
        return result.stdout.replace(b"\r\n", b"\n")
    return LOWERCASE_INSTALL_BYTES


def _uppercase_install_bytes() -> bytes:
    """Return exact uppercase wrapper bytes without relying on case-only files."""

    try:
        result = subprocess.run(
            ["git", "show", ":install_entry.py"],
            cwd=_repo_root(),
            check=False,
            capture_output=True,
        )
    except (OSError, ValueError):
        result = None
    if (
        result is not None
        and result.returncode == 0
        and b"installer.entrypoint" in result.stdout
    ):
        return result.stdout.replace(b"\r\n", b"\n")
    return UPPERCASE_INSTALL_BYTES


def _install_payloads() -> dict[str, bytes]:
    return {
        LOWERCASE_INSTALL_NAME: _lowercase_install_bytes(),
        UPPERCASE_INSTALL_NAME: _uppercase_install_bytes(),
    }


def _write_case_distinct_installs(target_dir: str | Path) -> None:
    root = Path(target_dir)
    root.mkdir(parents=True, exist_ok=True)
    for name, payload in _install_payloads().items():
        (root / name).write_bytes(payload)


def _remove_stale_distribution_members(target_dir: str | Path) -> None:
    root = Path(target_dir)
    for relative_name in STALE_DISTRIBUTION_MEMBERS:
        stale_path = root / relative_name
        try:
            stale_path.unlink()
        except FileNotFoundError:
            pass


def _supports_case_distinct_names(directory: str | Path) -> bool:
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    upper = root / "CaseProbe.tmp"
    lower = root / "caseprobe.tmp"
    try:
        upper.write_text("upper", encoding="utf-8")
        lower.write_text("lower", encoding="utf-8")
        names = {child.name for child in root.iterdir()}
        return upper.name in names and lower.name in names
    finally:
        for path in (upper, lower):
            try:
                path.unlink()
            except FileNotFoundError:
                pass


class build_py(_build_py):
    """Ensure build dirs get exact installer wrappers when case-distinct names work."""

    def run(self) -> None:
        _remove_stale_distribution_members(self.build_lib)
        super().run()
        _remove_stale_distribution_members(self.build_lib)
        if _supports_case_distinct_names(self.build_lib):
            _write_case_distinct_installs(self.build_lib)


def _ensure_zip_members(
    archive_path: Path,
    payloads: dict[str, bytes],
    *,
    remove_members: set[str] | frozenset[str] | None = None,
) -> None:
    remove_members = remove_members or frozenset()
    rewritten: dict[str, bytes] = {}
    if archive_path.exists():
        with zipfile.ZipFile(archive_path, "r") as archive:
            for name in archive.namelist():
                if name not in payloads and name not in remove_members:
                    rewritten[name] = archive.read(name)
    rewritten.update(payloads)
    with zipfile.ZipFile(
        archive_path, "w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        for name, data in rewritten.items():
            archive.writestr(name, data)


def _wheel_record_name(names: list[str]) -> str | None:
    for name in names:
        if name.endswith(".dist-info/RECORD"):
            return name
    return None


def _record_line(path: str, payload: bytes) -> str:
    digest = (
        base64.urlsafe_b64encode(hashlib.sha256(payload).digest())
        .rstrip(b"=")
        .decode("ascii")
    )
    return f"{path},sha256={digest},{len(payload)}"


def _ensure_wheel_members(
    archive_path: Path,
    payloads: dict[str, bytes],
    *,
    remove_members: set[str] | frozenset[str] | None = None,
) -> None:
    remove_members = remove_members or frozenset()
    rewritten: dict[str, bytes] = {}
    with zipfile.ZipFile(archive_path, "r") as archive:
        names = archive.namelist()
        record_name = _wheel_record_name(names)
        for name in names:
            if name not in {*payloads, record_name} and name not in remove_members:
                rewritten[name] = archive.read(name)

        if record_name is not None:
            existing_records = archive.read(record_name).decode("utf-8").splitlines()
            kept_records = [
                line
                for line in existing_records
                if not any(
                    line.startswith(f"{member_name},") for member_name in payloads
                )
                and not line.startswith(f"{record_name},")
                and not any(
                    line.startswith(f"{member_name},") for member_name in remove_members
                )
            ]
            for member_name, payload in payloads.items():
                kept_records.append(_record_line(member_name, payload))
            kept_records.append(f"{record_name},,")
            rewritten[record_name] = ("\n".join(kept_records) + "\n").encode("utf-8")

    rewritten.update(payloads)
    with zipfile.ZipFile(
        archive_path, "w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        for name, data in rewritten.items():
            archive.writestr(name, data)


def _sdist_root_member(archive: tarfile.TarFile) -> str:
    for member in archive.getmembers():
        root = member.name.split("/", maxsplit=1)[0]
        if root:
            return root
    return "supermedicine"


def _ensure_tar_gz_members(archive_path: Path, payloads: dict[str, bytes]) -> None:
    with tarfile.open(archive_path, "r:gz") as archive:
        members = archive.getmembers()
        root = _sdist_root_member(archive)
        wanted_names = {f"{root}/{relative_name}" for relative_name in payloads}
        stale_names = {
            f"{root}/{relative_name}" for relative_name in STALE_DISTRIBUTION_MEMBERS
        }
        kept: list[tuple[tarfile.TarInfo, bytes | None]] = []
        for member in members:
            if member.name in wanted_names or member.name in stale_names:
                continue
            if member.isfile():
                extracted = archive.extractfile(member)
                kept.append(
                    (member, extracted.read() if extracted is not None else b"")
                )
            else:
                kept.append((member, None))

    for relative_name, payload in payloads.items():
        info = tarfile.TarInfo(f"{root}/{relative_name}")
        info.size = len(payload)
        info.mode = 0o644
        kept.append((info, payload))

    with tarfile.open(archive_path, "w:gz") as archive:
        for member, data in kept:
            if data is None:
                archive.addfile(member)
            else:
                archive.addfile(member, io.BytesIO(data))


class sdist(_sdist):
    """Ensure sdists include exact lowercase install.py before commit/archive checks."""

    def make_distribution(self) -> None:
        super().make_distribution()
        payloads = _install_payloads()
        for archive_name in self.archive_files:
            archive_path = Path(archive_name)
            if archive_path.suffix == ".zip":
                root = archive_path.stem
                _ensure_zip_members(
                    archive_path,
                    {f"{root}/{name}": payload for name, payload in payloads.items()},
                    remove_members={
                        f"{root}/{name}" for name in STALE_DISTRIBUTION_MEMBERS
                    },
                )
            elif archive_path.name.endswith(".tar.gz"):
                _ensure_tar_gz_members(archive_path, payloads)


cmdclass = {"build_py": build_py, "sdist": sdist}

if _bdist_wheel is not None:

    class bdist_wheel(_bdist_wheel):  # type: ignore[misc, valid-type]
        """Post-process wheel archives as a safety net for case-insensitive builds."""

        def run(self) -> None:
            super().run()
            payloads = _install_payloads()
            for wheel_path in Path(self.dist_dir).glob("*.whl"):
                if wheel_path.is_file():
                    _ensure_wheel_members(
                        wheel_path,
                        payloads,
                        remove_members=STALE_DISTRIBUTION_MEMBERS,
                    )

    cmdclass["bdist_wheel"] = bdist_wheel


setup(cmdclass=cmdclass)
