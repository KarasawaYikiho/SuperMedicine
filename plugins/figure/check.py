"""Figure compliance audit plugin.

Pre-submission figure compliance audit.
Checks: format (vector vs raster vs forbidden JPEG), pixel size/DPI,
vector PDF font embedding type (must be TrueType/Type 42).
Non-destructive -- read-only, does not modify original files.
"""

from __future__ import annotations

import os
from typing import Any

JPEG_FORMATS = {"jpg", "jpeg"}
VECTOR_FORMATS = {"pdf", "svg", "eps"}
RASTER_OK_FORMATS = {"png", "tiff", "tif"}

# Severity ordering
SEVERITY = {"INFO": 0, "WARN": 1, "FAIL": 2}


def _ext(path: str) -> str:
    return os.path.splitext(path)[1].lower().lstrip(".")


def _check_raster(path: str, ext: str, min_dpi: int,
                  target_inches: tuple[float, float] | None) -> tuple[list, dict]:
    """Raster (PNG/TIFF/JPEG) compliance check."""
    issues: list[tuple[str, str]] = []
    info: dict[str, Any] = {"category": "raster", "ext": ext}

    if ext in JPEG_FORMATS:
        issues.append(("FAIL",
                       "JPEG is lossy and unsuitable for line/text data figures. "
                       "Use PDF/SVG (vector) or PNG/TIFF (raster) instead."))

    try:
        from PIL import Image
    except ImportError:
        issues.append(("INFO",
                       "Pillow not installed, skipping pixel/DPI check: "
                       "pip install Pillow to enable."))
        return issues, info

    try:
        img = Image.open(path)
        info["size_px"] = img.size  # (w, h)
        dpi = img.info.get("dpi")
        info["dpi"] = dpi
    except Exception as e:
        issues.append(("FAIL", f"Cannot read image: {e}"))
        return issues, info

    if dpi is None:
        issues.append(("WARN",
                        "File has no embedded DPI metadata. Journals often calculate "
                        "final size from DPI; use fig.savefig(dpi=300) explicitly."))
    else:
        if isinstance(dpi, tuple):
            if len(dpi) == 0:
                issues.append(("WARN",
                               "DPI metadata is an empty tuple; cannot determine resolution. "
                               "Re-export with fig.savefig(dpi=300) explicitly."))
                return issues, info
            dx = dpi[0]
        else:
            dx = dpi
        dx_rounded = round(float(dx))
        if dx_rounded < min_dpi:
            issues.append(("FAIL",
                           f"DPI = {dx_rounded} is below required {min_dpi}. "
                           "Re-export with savefig(dpi=...)."))
        if target_inches is not None:
            tw, th = target_inches
            actual_w_in = info["size_px"][0] / float(dx)
            actual_h_in = info["size_px"][1] / float(dx)
            tol = 0.1
            if abs(actual_w_in - tw) > tol or abs(actual_h_in - th) > tol:
                issues.append((
                    "WARN",
                    f"Actual size approx {actual_w_in:.2f}x{actual_h_in:.2f} in, "
                    f"target {tw}x{th} in. Set figsize=({tw}, {th}) in code; "
                    "do not rescale in Word/LaTeX."
                ))
    return issues, info


def _check_pdf_fonts(path: str) -> list[tuple[str, str]]:
    """Check PDF font embedding -- many journals reject Type 3 (CFF outlines)."""
    issues: list[tuple[str, str]] = []
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # noqa: F401
        except ImportError:
            issues.append(("INFO",
                           "pypdf / PyPDF2 not installed, skipping font embedding check. "
                           "pip install pypdf to enable."))
            return issues

    try:
        reader = PdfReader(path)
    except Exception as e:
        issues.append(("WARN", f"PDF cannot be parsed for font check: {e}"))
        return issues

    bad_fonts: list[str] = []
    not_embedded: list[str] = []
    for page in reader.pages:
        try:
            resources = page.get("/Resources")
            if not resources:
                continue
            fonts = resources.get("/Font")
            if not fonts:
                continue
            for fname, fobj in fonts.items():
                font = fobj.get_object()
                subtype = str(font.get("/Subtype", ""))
                base = str(font.get("/BaseFont", "?"))
                descriptor = font.get("/FontDescriptor")
                if descriptor:
                    descriptor = descriptor.get_object()
                    embedded = any(k in descriptor for k in
                                   ("/FontFile", "/FontFile2", "/FontFile3"))
                else:
                    embedded = False
                if "Type3" in subtype:
                    bad_fonts.append(f"{base} ({subtype})")
                elif not embedded and "Type1" not in subtype:
                    not_embedded.append(base)
        except Exception:
            continue
    if bad_fonts:
        issues.append((
            "FAIL",
            f"PDF contains Type 3 fonts: {', '.join(set(bad_fonts))[:200]}. "
            "Type 3 fonts blur when zoomed; many journals reject them. "
            "Set rcParams['pdf.fonttype'] = 42 and re-export."
        ))
    if not_embedded:
        issues.append((
            "WARN",
            f"PDF fonts possibly not embedded: {', '.join(set(not_embedded))[:200]}. "
            "May render as substitute fonts on other machines."
        ))
    return issues


def _check_svg(path: str) -> list[tuple[str, str]]:
    """SVG quick check: warn about base64-embedded bitmaps."""
    issues: list[tuple[str, str]] = []
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            head = f.read(50000)
    except Exception as e:
        issues.append(("WARN", f"SVG read failed: {e}"))
        return issues
    if "data:image/png;base64" in head or "data:image/jpeg;base64" in head:
        issues.append(("WARN",
                       "SVG contains base64-embedded bitmaps -- loses vector advantage. "
                       "Check if imshow or image overlay was used accidentally."))
    return issues


def check_figure(path: str, min_dpi: int = 300,
                 target_inches: tuple[float, float] | None = None
                 ) -> tuple[list[tuple[str, str]], dict]:
    """
    Audit a single figure file. Returns (issues, info).
    issues: [(severity, message), ...]; severity in {INFO, WARN, FAIL}
    info: metadata dict (format, pixels, DPI, etc.)
    """
    issues: list[tuple[str, str]] = []
    info: dict[str, Any] = {"path": path}

    if not os.path.exists(path):
        return [("FAIL", f"File not found: {path}")], info

    ext = _ext(path)
    info["ext"] = ext
    info["size_bytes"] = os.path.getsize(path)

    if ext in VECTOR_FORMATS:
        info["category"] = "vector"
        if ext == "pdf":
            issues.extend(_check_pdf_fonts(path))
        elif ext == "svg":
            issues.extend(_check_svg(path))
    elif ext in RASTER_OK_FORMATS or ext in JPEG_FORMATS:
        sub_issues, sub_info = _check_raster(path, ext, min_dpi, target_inches)
        issues.extend(sub_issues)
        info.update(sub_info)
    else:
        issues.append(("WARN", f"Unrecognized extension: .{ext}"))

    return issues, info


def format_report(path: str, issues: list, info: dict) -> dict:
    """Format audit result as a structured report."""
    if not issues:
        verdict = "PASS"
    else:
        max_sev = max(SEVERITY[s] for s, _ in issues)
        verdict = {2: "FAIL", 1: "WARN", 0: "INFO"}[max_sev]

    return {
        "path": path,
        "verdict": verdict,
        "category": info.get("category", "unknown"),
        "ext": info.get("ext", ""),
        "size_bytes": info.get("size_bytes", 0),
        "size_px": info.get("size_px"),
        "dpi": info.get("dpi"),
        "issues": [{"severity": s, "message": m} for s, m in issues],
    }


def execute(
    action: str,
    params: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute figure check action."""
    params = params or {}
    metadata = {
        "resource": "local-figure-check",
    }
    try:
        if action == "figure-check.audit":
            path = params.get("path")
            if path is None:
                return {
                    "status": "plugin_error",
                    "output": None,
                    "error": "Missing required parameter: path",
                    "metadata": metadata,
                }
            min_dpi = params.get("min_dpi", 300)
            target_inches = params.get("target_inches")
            if target_inches and isinstance(target_inches, (list, tuple)):
                target_inches = tuple(target_inches)

            issues, info = check_figure(path, min_dpi=min_dpi, target_inches=target_inches)
            report = format_report(path, issues, info)
            return {
                "status": "success",
                "output": report,
                "metadata": metadata,
            }
        else:
            return {
                "status": "plugin_error",
                "output": None,
                "error": f"Unsupported figure-check action: {action}",
                "metadata": metadata,
            }
    except Exception as exc:
        return {
            "status": "plugin_error",
            "output": None,
            "error": f"Figure check error: {exc}",
            "metadata": metadata,
        }
