"""Derive public GitHub Release names from the package version."""

from __future__ import annotations

import re


_BETA_VERSION = re.compile(r"^(\d+\.\d+\.\d+)b0$")


def release_names(version: str) -> tuple[str, str, str]:
    match = _BETA_VERSION.fullmatch(version)
    if match is None:
        raise ValueError(f"unsupported release version: {version!r}")
    api_version = match.group(1)
    release_label = f"Beta{api_version}"
    return (
        release_label,
        f"Beta {api_version}",
        f"SuperMedicine.{release_label}.zip",
    )


__all__ = ["release_names"]
