"""Figure layout tools plugin.

Solves two common figure layout problems:

1. Panel label (a/b/c) alignment -- `add_panel_labels()` anchors each label
   at each subplot's axes fraction (0,1) (top-left), then applies a uniform
   points offset. Same-column subplots share figure-x, same-row share figure-y,
   so uniform offset produces perfect horizontal and vertical alignment.

2. Title/axis clipping, legend overlap, subplot collision -- `finalize_figure()`
   enables constrained_layout (fallback to tight_layout) as a safety net.

Both are "post-hoc" tools: even if layout was neglected during plotting,
running these can rescue the layout.
"""

from __future__ import annotations

import string
import sys
from typing import Any

import matplotlib.pyplot as plt


# Windows GBK terminal: force UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        pass


# Panel label conventions by journal
PANEL_STYLES = {
    "nature": lambda s: s,                    # a  b  c
    "science": lambda s: s,                   # a  b  c
    "ieee": lambda s: f"({s})",               # (a)(b)(c)
    "paren": lambda s: f"({s})",              # (a)(b)(c)
    "upper": lambda s: s.upper(),             # A  B  C
    "upper_paren": lambda s: f"({s.upper()})",  # (A)(B)(C)
}


def _letter_sequence(n: int) -> list[str]:
    """Generate a, b, ..., z, aa, ab, ..., zz, aaa, ... label sequence."""
    letters = string.ascii_lowercase
    out: list[str] = []
    for i in range(n):
        s = ""
        x = i
        while True:
            s = letters[x % 26] + s
            x = x // 26 - 1
            if x < 0:
                break
        out.append(s)
    return out


def _data_axes(fig) -> list:
    """Get only real grid subplots, excluding colorbar / inset."""
    return [ax for ax in fig.axes if ax.get_subplotspec() is not None]


def add_panel_labels(
    fig,
    axes=None,
    labels=None,
    style: str = "nature",
    fontsize=None,
    fontweight: str = "bold",
    x_offset_pt: float = -20.0,
    y_offset_pt: float = 2.0,
    ha: str = "right",
    va: str = "bottom",
    color: str = "black",
):
    """
    Add consistently aligned a/b/c labels to multi-panel figures.

    Args:
        fig: matplotlib Figure.
        axes: axes to label; default auto-detects all grid subplots.
        labels: custom label list; default generates from style.
        style: 'nature'|'science'(a b c) | 'ieee'|'paren'((a)(b)(c)) |
            'upper'(A B C) | 'upper_paren'((A)(B)(C)).
        fontsize: label font size; default rcParams['axes.labelsize'].
        fontweight: default 'bold'.
        x_offset_pt: horizontal offset (points), negative = left of subplot.
        y_offset_pt: vertical offset (points), positive = up.
        ha, va: alignment.
        color: label color.

    Returns:
        List of placed Text/Annotation objects.
    """
    if axes is None:
        axes = _data_axes(fig)
        axes = sorted(
            axes,
            key=lambda ax: (-round(ax.get_position().y1, 3),
                            round(ax.get_position().x0, 3)),
        )
    axes = list(axes)
    n = len(axes)
    if n == 0:
        return []

    if labels is None:
        fmt = PANEL_STYLES.get(style)
        if fmt is None:
            raise ValueError(
                f"Unknown panel style: {style!r}. "
                f"Choose from {sorted(PANEL_STYLES)}"
            )
        labels = [fmt(s) for s in _letter_sequence(n)]
    elif len(labels) < n:
        raise ValueError(
            f"Provided {len(labels)} labels but {n} subplots need labeling."
        )

    if fontsize is None:
        fontsize = plt.rcParams.get("axes.labelsize", 9)

    placed = []
    for ax, lab in zip(axes, labels):
        t = ax.annotate(
            lab,
            xy=(0, 1), xycoords="axes fraction",
            xytext=(x_offset_pt, y_offset_pt), textcoords="offset points",
            fontsize=fontsize, fontweight=fontweight, color=color,
            ha=ha, va=va,
            annotation_clip=False,
        )
        placed.append(t)
    return placed


class _suppress_tight_warnings:
    """Suppress UserWarning from tight_layout in certain combinations."""

    def __enter__(self):
        import warnings
        self._cm = warnings.catch_warnings()
        self._cm.__enter__()
        warnings.simplefilter("ignore")
        return self

    def __exit__(self, *exc):
        return self._cm.__exit__(*exc)


def finalize_figure(fig, prefer: str = "constrained", verbose: bool = False) -> str:
    """
    Pre-export layout safety net: reduce title/axis clipping, legend overlap,
    subplot collision.

    Args:
        fig: matplotlib Figure.
        prefer: 'constrained' (default) | 'tight'.
        verbose: print which strategy was used.

    Returns:
        Strategy actually used: 'constrained' | 'tight' | 'none'.
    """
    used = "none"
    if prefer == "constrained":
        try:
            fig.set_layout_engine("constrained")
            fig.canvas.draw()
            used = "constrained"
        except Exception:
            used = "none"
    if used == "none":
        try:
            with _suppress_tight_warnings():
                fig.tight_layout()
            used = "tight"
        except Exception:
            used = "none"
    if verbose:
        print(f"[figure-layout] finalize_figure -> {used}")
    return used


def execute(
    action: str,
    params: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute figure layout action."""
    params = params or {}
    metadata = {
        "resource": "local-figure-layout",
    }
    try:
        if action == "figure-layout.labels":
            fig = params.get("fig")
            if fig is None:
                return {
                    "status": "plugin_error",
                    "output": None,
                    "error": "Missing required parameter: fig",
                    "metadata": metadata,
                }
            style = params.get("style", "nature")
            labels = params.get("labels")
            placed = add_panel_labels(fig, style=style, labels=labels)
            return {
                "status": "success",
                "output": {
                    "labels_placed": [t.get_text() for t in placed],
                    "count": len(placed),
                },
                "metadata": metadata,
            }
        elif action == "figure-layout.finalize":
            fig = params.get("fig")
            if fig is None:
                return {
                    "status": "plugin_error",
                    "output": None,
                    "error": "Missing required parameter: fig",
                    "metadata": metadata,
                }
            prefer = params.get("prefer", "constrained")
            used = finalize_figure(fig, prefer=prefer)
            return {
                "status": "success",
                "output": {"strategy": used},
                "metadata": metadata,
            }
        else:
            return {
                "status": "plugin_error",
                "output": None,
                "error": f"Unsupported figure-layout action: {action}",
                "metadata": metadata,
            }
    except Exception as exc:
        return {
            "status": "plugin_error",
            "output": None,
            "error": f"Figure layout error: {exc}",
            "metadata": metadata,
        }
