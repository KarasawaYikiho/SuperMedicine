"""Figure export plugin.

Unified figure export to multiple formats at exact final size.

- Vector preferred: PDF / SVG / EPS for line/bar/scatter (lossless, journal-friendly).
- Raster for photos / micrographs: PNG / TIFF at >= 300 DPI; never JPEG for data figures.
- Embeds TrueType fonts (fonttype 42) so journals don't reject Type-3 PDFs.
- Optional grayscale preview to sanity-check colorblind safety.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Iterable

import matplotlib.pyplot as plt


VECTOR_FORMATS = {"pdf", "svg", "eps"}
RASTER_FORMATS = {"png", "tiff", "tif", "jpg", "jpeg"}
SUPPORTED_FORMATS = VECTOR_FORMATS | RASTER_FORMATS


def _ensure_parent(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def export_figure(
    fig,
    basename: str,
    formats: Iterable[str] | None = None,
    dpi: int = 300,
    size_inches: tuple[float, float] | None = None,
    grayscale_preview: bool = False,
    tight: bool = True,
    pad_inches: float = 0.05,
    transparent: bool = False,
) -> list[str]:
    """
    Export a matplotlib Figure to one or more formats at exact final size.

    Args:
        fig: matplotlib Figure object.
        basename: output path prefix (without extension); subdirs auto-created.
        formats: list/tuple of extensions, e.g. ['pdf', 'svg', 'png'].
            Default: ['pdf', 'svg', 'png'].
        dpi: raster format resolution; recommend 300 (standard) / 600 (IEEE).
        size_inches: (width, height) inches; forces fig.set_size_inches().
        grayscale_preview: generate _grayscale.png for colorblind check.
        tight: use bbox_inches='tight' (trim whitespace).
        pad_inches: padding in tight mode.
        transparent: transparent background.

    Returns:
        List of actually saved file paths.
    """
    if formats is None:
        formats = ("pdf", "svg", "png")
    if isinstance(formats, str):
        formats = [formats]
    formats = [f.lower().lstrip(".") for f in formats]
    unknown = [f for f in formats if f not in SUPPORTED_FORMATS]
    if unknown:
        raise ValueError(f"Unsupported formats: {unknown}. "
                         f"Supported: {sorted(SUPPORTED_FORMATS)}")

    if size_inches is not None:
        if len(size_inches) != 2:
            raise ValueError("size_inches must be (width, height)")
        fig.set_size_inches(*size_inches)

    # Force TrueType font embedding (fonttype 42); many journals reject Type-3 PDF
    plt.rcParams["pdf.fonttype"] = 42
    plt.rcParams["ps.fonttype"] = 42
    plt.rcParams["svg.fonttype"] = "none"

    saved: list[str] = []
    for fmt in formats:
        if fmt in {"jpg", "jpeg"}:
            print(f"[figure-export] WARNING: skipping {fmt} -- "
                  "JPEG is lossy and unsuitable for line/text figures.",
                  file=sys.stderr)
            continue
        path = f"{basename}.{fmt}"
        _ensure_parent(path)
        kwargs: dict = {
            "bbox_inches": "tight" if tight else None,
            "pad_inches": pad_inches,
            "transparent": transparent,
        }
        if fmt in RASTER_FORMATS:
            kwargs["dpi"] = dpi
        fig.savefig(path, **kwargs)
        saved.append(path)
        print(f"[figure-export] wrote {path}")

    if grayscale_preview:
        gray_path = _grayscale_from(fig, basename, dpi=dpi)
        if gray_path:
            saved.append(gray_path)
    return saved


def _grayscale_from(fig, basename: str, dpi: int) -> str | None:
    """Export grayscale preview for colorblind safety check."""
    try:
        from PIL import Image
    except ImportError:
        print("[figure-export] Pillow not available; "
              "grayscale preview skipped.", file=sys.stderr)
        return None

    png_path = f"{basename}.png"
    _ensure_parent(png_path)
    fig.savefig(png_path, dpi=dpi, bbox_inches="tight")

    gray_path = f"{basename}_grayscale.png"
    Image.open(png_path).convert("L").save(gray_path)
    print(f"[figure-export] wrote {gray_path} (grayscale preview)")
    return gray_path


def execute(
    action: str,
    params: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute figure export action."""
    params = params or {}
    metadata = {
        "resource": "local-figure-export",
    }
    try:
        if action == "figure-export.export":
            fig = params.get("fig")
            if fig is None:
                return {
                    "status": "plugin_error",
                    "output": None,
                    "error": "Missing required parameter: fig (matplotlib Figure object)",
                    "metadata": metadata,
                }
            basename = params.get("basename")
            if basename is None:
                return {
                    "status": "plugin_error",
                    "output": None,
                    "error": "Missing required parameter: basename",
                    "metadata": metadata,
                }
            formats = params.get("formats")
            dpi = params.get("dpi", 300)
            size_inches = params.get("size_inches")
            if size_inches and isinstance(size_inches, (list, tuple)):
                size_inches = tuple(size_inches)
            grayscale_preview = params.get("grayscale_preview", False)
            tight = params.get("tight", True)
            pad_inches = params.get("pad_inches", 0.05)
            transparent = params.get("transparent", False)

            paths = export_figure(
                fig,
                basename=basename,
                formats=formats,
                dpi=dpi,
                size_inches=size_inches,
                grayscale_preview=grayscale_preview,
                tight=tight,
                pad_inches=pad_inches,
                transparent=transparent,
            )
            return {
                "status": "success",
                "output": {"paths": paths},
                "metadata": metadata,
            }
        else:
            return {
                "status": "plugin_error",
                "output": None,
                "error": f"Unsupported figure-export action: {action}",
                "metadata": metadata,
            }
    except Exception as exc:
        return {
            "status": "plugin_error",
            "output": None,
            "error": f"Figure export error: {exc}",
            "metadata": metadata,
        }
