"""Figure compliance audit plugin.

Pre-submission figure compliance audit.
Checks: format (vector vs raster vs forbidden JPEG), pixel size/DPI,
vector PDF font embedding type (must be TrueType/Type 42).
Non-destructive -- read-only, does not modify original files.
"""

from __future__ import annotations

import io
import logging
import os
import sys
import warnings
from typing import Any

import matplotlib.text as mtext

JPEG_FORMATS = {"jpg", "jpeg"}
VECTOR_FORMATS = {"pdf", "svg", "eps"}
RASTER_OK_FORMATS = {"png", "tiff", "tif"}

# Severity ordering
SEVERITY = {"INFO": 0, "WARN": 1, "FAIL": 2}


def _ext(path: str) -> str:
    return os.path.splitext(path)[1].lower().lstrip(".")


def _check_raster(
    path: str, ext: str, min_dpi: int, target_inches: tuple[float, float] | None
) -> tuple[list, dict]:
    """Raster (PNG/TIFF/JPEG) compliance check."""
    issues: list[tuple[str, str]] = []
    info: dict[str, Any] = {"category": "raster", "ext": ext}

    if ext in JPEG_FORMATS:
        issues.append(
            (
                "FAIL",
                "JPEG is lossy and unsuitable for line/text data figures. "
                "Use PDF/SVG (vector) or PNG/TIFF (raster) instead.",
            )
        )

    try:
        from PIL import Image
    except ImportError:
        issues.append(
            (
                "INFO",
                "Pillow not installed, skipping pixel/DPI check: "
                "pip install Pillow to enable.",
            )
        )
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
        issues.append(
            (
                "WARN",
                "File has no embedded DPI metadata. Journals often calculate "
                "final size from DPI; use fig.savefig(dpi=300) explicitly.",
            )
        )
    else:
        if isinstance(dpi, tuple):
            if len(dpi) == 0:
                issues.append(
                    (
                        "WARN",
                        "DPI metadata is an empty tuple; cannot determine resolution. "
                        "Re-export with fig.savefig(dpi=300) explicitly.",
                    )
                )
                return issues, info
            dx = dpi[0]
        else:
            dx = dpi
        dx_rounded = round(float(dx))
        if dx_rounded < min_dpi:
            issues.append(
                (
                    "FAIL",
                    f"DPI = {dx_rounded} is below required {min_dpi}. "
                    "Re-export with savefig(dpi=...).",
                )
            )
        if target_inches is not None:
            tw, th = target_inches
            actual_w_in = info["size_px"][0] / float(dx)
            actual_h_in = info["size_px"][1] / float(dx)
            tol = 0.1
            if abs(actual_w_in - tw) > tol or abs(actual_h_in - th) > tol:
                issues.append(
                    (
                        "WARN",
                        f"Actual size approx {actual_w_in:.2f}x{actual_h_in:.2f} in, "
                        f"target {tw}x{th} in. Set figsize=({tw}, {th}) in code; "
                        "do not rescale in Word/LaTeX.",
                    )
                )
    return issues, info


def _check_pdf_fonts(path: str) -> list[tuple[str, str]]:
    """Check PDF font embedding -- many journals reject Type 3 (CFF outlines)."""
    issues: list[tuple[str, str]] = []
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # type: ignore[assignment]  # noqa: F401
        except ImportError:
            issues.append(
                (
                    "INFO",
                    "pypdf / PyPDF2 not installed, skipping font embedding check. "
                    "pip install pypdf to enable.",
                )
            )
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
                    embedded = any(
                        k in descriptor
                        for k in ("/FontFile", "/FontFile2", "/FontFile3")
                    )
                else:
                    embedded = False
                if "Type3" in subtype:
                    bad_fonts.append(f"{base} ({subtype})")
                elif not embedded and "Type1" not in subtype:
                    not_embedded.append(base)
        except Exception:
            continue
    if bad_fonts:
        issues.append(
            (
                "FAIL",
                f"PDF contains Type 3 fonts: {', '.join(set(bad_fonts))[:200]}. "
                "Type 3 fonts blur when zoomed; many journals reject them. "
                "Set rcParams['pdf.fonttype'] = 42 and re-export.",
            )
        )
    if not_embedded:
        issues.append(
            (
                "WARN",
                f"PDF fonts possibly not embedded: {', '.join(set(not_embedded))[:200]}. "
                "May render as substitute fonts on other machines.",
            )
        )
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
        issues.append(
            (
                "WARN",
                "SVG contains base64-embedded bitmaps -- loses vector advantage. "
                "Check if imshow or image overlay was used accidentally.",
            )
        )
    return issues


def check_figure(
    path: str, min_dpi: int = 300, target_inches: tuple[float, float] | None = None
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


def execute_check(
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

            issues, info = check_figure(
                path, min_dpi=min_dpi, target_inches=target_inches
            )
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


"""Figure visual QA plugin.

Post-render "programmatic self-check" + "render preview" -- the machine layer
of the self-check loop.

Division of labor:
- **Program (this script)** catches deterministic issues: missing glyphs,
  text clipping, tick label overlap.
- **AI visual review** (see references/visual_review.md) catches perceptual
  issues: legend-over-data, label alignment, color/grayscale separability.

Together they form the complete "render -> program check + AI review -> fix"
feedback loop.

Core capabilities:
- `render_preview(fig_or_path, out_png, dpi)` -- render a medium-res PNG for
  AI visual review via Read tool.
- `audit_layout(fig)` -- returns [(severity, msg), ...]:
  * Missing glyphs (FAIL): intercepts both warnings and logging channels.
  * Text clipping (WARN): Text window_extent exceeds canvas bounds.
  * Tick overlap (WARN): adjacent tick label bounding boxes intersect.
"""


# Windows GBK terminal: force UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        pass

SEVERITY = {"INFO": 0, "WARN": 1, "FAIL": 2}
_GLYPH_MARKERS = ("missing from", "Glyph", "findfont")


def _ensure_parent(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


class _GlyphLogHandler(logging.Handler):
    """Intercept matplotlib logger records about missing glyphs / fonts."""

    def __init__(self):
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record):
        msg = record.getMessage()
        if any(m in msg for m in _GLYPH_MARKERS):
            self.messages.append(msg)


def _draw_and_collect_glyph_warnings(fig) -> list[str]:
    """
    Render a figure once, collecting glyph warnings from both warnings and
    logging channels. This ensures the renderer is ready for subsequent
    window_extent measurements.
    """
    handler = _GlyphLogHandler()
    mpl_logger = logging.getLogger("matplotlib")
    prev_level = mpl_logger.level
    mpl_logger.setLevel(logging.WARNING)
    mpl_logger.addHandler(handler)

    collected: list[str] = []
    try:
        with warnings.catch_warnings(record=True) as wlist:
            warnings.simplefilter("always")
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=100)
            buf.close()
        for w in wlist:
            s = str(w.message)
            if any(m in s for m in _GLYPH_MARKERS):
                collected.append(s)
    finally:
        mpl_logger.removeHandler(handler)
        mpl_logger.setLevel(prev_level)

    collected.extend(handler.messages)
    seen, uniq = set(), []
    for m in collected:
        if m not in seen:
            seen.add(m)
            uniq.append(m)
    return uniq


def _visible_texts(fig) -> list:
    out = []
    for t in fig.findobj(mtext.Text):
        try:
            if t.get_visible() and t.get_text().strip():
                out.append(t)
        except Exception:
            continue
    return out


def audit_layout(
    fig, clip_tol_px: float = 2.0, overlap_tol_px: float = 1.0
) -> list[tuple[str, str]]:
    """
    Audit a matplotlib Figure for layout issues. Returns [(severity, msg), ...].

    Checks:
        1. Missing glyphs (FAIL) -- CJK/special chars font not found.
        2. Text clipping (WARN) -- title/axis labels exceed canvas.
        3. Tick label overlap (WARN) -- adjacent tick bounding boxes intersect.
    """
    issues: list[tuple[str, str]] = []

    # 1. Missing glyphs (also triggers a render to ready the renderer)
    glyph_msgs = _draw_and_collect_glyph_warnings(fig)
    if glyph_msgs:
        sample = " | ".join(glyph_msgs[:3])
        issues.append(
            (
                "FAIL",
                f"Missing glyphs detected, output will have boxes/garbled text: {sample[:240]}. "
                "For Chinese figures, run setup_style(lang='zh') to configure CJK fonts; "
                "for minus sign boxes, confirm axes.unicode_minus=False.",
            )
        )

    try:
        renderer = fig.canvas.get_renderer()
    except Exception:
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()

    W = float(fig.bbox.width)
    H = float(fig.bbox.height)

    # 2. Text clipping (skip tick labels -- handled by constrained_layout and tick overlap check)
    tick_ids = set()
    for ax in fig.axes:
        for tl in (
            *ax.get_xticklabels(),
            *ax.get_xticklabels(minor=True),
            *ax.get_yticklabels(),
            *ax.get_yticklabels(minor=True),
        ):
            tick_ids.add(id(tl))

    clipped: list[str] = []
    for t in _visible_texts(fig):
        if id(t) in tick_ids:
            continue
        try:
            bb = t.get_window_extent(renderer)
        except Exception:
            continue
        if (
            bb.x0 < -clip_tol_px
            or bb.y0 < -clip_tol_px
            or bb.x1 > W + clip_tol_px
            or bb.y1 > H + clip_tol_px
        ):
            txt = t.get_text().strip().replace("\n", " ")
            if txt:
                clipped.append(txt[:24])
    if clipped:
        uniq = list(dict.fromkeys(clipped))[:6]
        issues.append(
            (
                "WARN",
                f"Text may exceed canvas and be clipped: {uniq}. "
                "Run finalize_figure(fig) or export with bbox_inches='tight'; "
                "shorten long titles/labels or wrap.",
            )
        )

    # 3. Tick label overlap
    overlap_axes = 0
    for ax in fig.axes:
        if ax.get_subplotspec() is None:
            continue
        if _ticklabels_overlap(
            ax.get_xticklabels(), renderer, axis="x", tol=overlap_tol_px
        ):
            overlap_axes += 1
            continue
        if _ticklabels_overlap(
            ax.get_yticklabels(), renderer, axis="y", tol=overlap_tol_px
        ):
            overlap_axes += 1
    if overlap_axes:
        issues.append(
            (
                "WARN",
                f"{overlap_axes} subplot(s) have overlapping tick labels. "
                "X-axis: ax.tick_params(axis='x', rotation=30) or reduce tick count; "
                "Y-axis: increase subplot height or reduce tick count.",
            )
        )

    return issues


def _ticklabels_overlap(labels, renderer, axis: str, tol: float) -> bool:
    """Check if adjacent tick label bounding boxes intersect."""
    boxes = []
    for label in labels:
        try:
            if label.get_visible() and label.get_text().strip():
                boxes.append(label.get_window_extent(renderer))
        except Exception:
            continue
    if len(boxes) < 2:
        return False
    if axis == "x":
        boxes.sort(key=lambda b: b.x0)
        return any(a.x1 - b.x0 > tol for a, b in zip(boxes, boxes[1:]))
    else:
        boxes.sort(key=lambda b: b.y0)
        return any(a.y1 - b.y0 > tol for a, b in zip(boxes, boxes[1:]))


def render_preview(fig_or_path, out_png: str = "_preview.png", dpi: int = 150) -> str:
    """
    Render a PNG preview for AI visual review.

    Args:
        fig_or_path: matplotlib Figure object, or an image file path.
        out_png: output PNG path.
        dpi: preview resolution, default 150.

    Returns:
        PNG path readable by the Read tool.
    """
    if hasattr(fig_or_path, "savefig"):
        _ensure_parent(out_png)
        fig_or_path.savefig(out_png, dpi=dpi, bbox_inches="tight")
        return out_png

    path = str(fig_or_path)
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    if ext in {"png", "tif", "tiff", "jpg", "jpeg", "bmp"}:
        return path
    if ext == "pdf":
        try:
            import fitz  # PyMuPDF, optional
        except ImportError as e:
            raise RuntimeError(
                "Rendering PDF preview requires PyMuPDF (pip install pymupdf). "
                "Recommended: pass matplotlib Figure object directly to render_preview "
                "before export to complete the review loop."
            ) from e
        doc = fitz.open(path)
        pix = doc[0].get_pixmap(dpi=dpi)
        _ensure_parent(out_png)
        pix.save(out_png)
        doc.close()
        return out_png
    raise RuntimeError(
        f"Cannot generate preview from .{ext}; pass Figure object or bitmap."
    )


def format_audit_report(issues: list[tuple[str, str]]) -> dict:
    """Format audit_layout result as structured report."""
    if not issues:
        verdict = "PASS"
    else:
        max_sev = max(SEVERITY[s] for s, _ in issues)
        verdict = {2: "FAIL", 1: "WARN", 0: "INFO"}[max_sev]
    return {
        "verdict": verdict,
        "issues": [{"severity": s, "message": m} for s, m in issues],
    }


def execute_qa(
    action: str,
    params: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute figure QA action."""
    params = params or {}
    metadata = {
        "resource": "local-figure-qa",
    }
    try:
        if action == "figure-qa.audit":
            fig = params.get("fig")
            if fig is None:
                return {
                    "status": "plugin_error",
                    "output": None,
                    "error": "Missing required parameter: fig",
                    "metadata": metadata,
                }
            issues = audit_layout(fig)
            report = format_audit_report(issues)
            return {
                "status": "success",
                "output": report,
                "metadata": metadata,
            }
        elif action == "figure-qa.preview":
            fig_or_path = params.get("fig")
            if fig_or_path is None:
                return {
                    "status": "plugin_error",
                    "output": None,
                    "error": "Missing required parameter: fig",
                    "metadata": metadata,
                }
            out_png = params.get("out_png", "_preview.png")
            dpi = params.get("dpi", 150)
            preview_path = render_preview(fig_or_path, out_png=out_png, dpi=dpi)
            return {
                "status": "success",
                "output": {"preview_path": preview_path},
                "metadata": metadata,
            }
        else:
            return {
                "status": "plugin_error",
                "output": None,
                "error": f"Unsupported figure-qa action: {action}",
                "metadata": metadata,
            }
    except Exception as exc:
        return {
            "status": "plugin_error",
            "output": None,
            "error": f"Figure QA error: {exc}",
            "metadata": metadata,
        }
