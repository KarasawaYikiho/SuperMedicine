#!/usr/bin/env python3
"""Verify a built release archive and its checksum without rebuilding."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path


REQUIRED_MEMBERS = {
    "install.py",
    "dist/SuperMedicine.exe",
    "SuperMedicineGUI.exe",
    "SuperMedicineInstaller.exe",
}


def verify(archive: Path, checksum: Path) -> dict[str, object]:
    if not archive.is_file():
        raise ValueError(f"release archive does not exist: {archive}")
    if not checksum.is_file():
        raise ValueError(f"checksum does not exist: {checksum}")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    declared = checksum.read_text(encoding="utf-8").split()[0].lower()
    if digest != declared:
        raise ValueError("release archive checksum mismatch")

    with zipfile.ZipFile(archive) as bundle:
        members = bundle.namelist()
    roots = {member.split("/", maxsplit=1)[0] for member in members if "/" in member}
    if len(roots) != 1:
        raise ValueError(f"release archive must have one root directory: {sorted(roots)}")
    root = next(iter(roots))
    relative_members = {
        member[len(root) + 1 :] for member in members if member.startswith(f"{root}/")
    }
    missing = sorted(REQUIRED_MEMBERS - relative_members)
    if missing:
        raise ValueError(f"release archive is missing required members: {missing}")
    return {
        "archive": archive.name,
        "sha256": digest,
        "root": root,
        "members": sorted(relative_members),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--checksum", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = verify(args.archive, args.checksum)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    args.report.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8", newline=""
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
