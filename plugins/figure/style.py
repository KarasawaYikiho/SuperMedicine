"""Figure style configuration plugin.

Publication-grade matplotlib / seaborn style configuration.
Supports nature / ieee / science / general journal presets,
CJK auto-detection (lang='zh'/'en') with fallback fonts.
SciencePlots optional -- used if installed, otherwise builtin presets.
"""

from __future__ import annotations

import warnings
from typing import Any

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt


# Journal presets: figsize in inches, matching single-column nominal width
JOURNAL_PRESETS = {
    "nature": {
        "figure.figsize": (3.5, 2.625),
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 7,
        "axes.labelsize": 8,
        "axes.titlesize": 8,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
        "lines.linewidth": 1.0,
        "lines.markersize": 4,
        "axes.linewidth": 0.6,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.minor.width": 0.4,
        "ytick.minor.width": 0.4,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
    },
    "science": {
        "figure.figsize": (3.5, 2.625),
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 7,
        "axes.labelsize": 7,
        "axes.titlesize": 8,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 6,
        "lines.linewidth": 1.0,
        "lines.markersize": 4,
        "axes.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
    },
    "ieee": {
        "figure.figsize": (3.5, 2.5),
        "figure.dpi": 150,
        "savefig.dpi": 600,
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
        "font.size": 8,
        "axes.labelsize": 8,
        "axes.titlesize": 9,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
        "lines.linewidth": 1.0,
        "lines.markersize": 4,
        "axes.linewidth": 0.7,
        "axes.grid": False,
        "axes.spines.top": True,
        "axes.spines.right": True,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
    },
    "general": {
        "figure.figsize": (5.0, 3.5),
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 9,
        "axes.labelsize": 10,
        "axes.titlesize": 11,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "lines.linewidth": 1.2,
        "lines.markersize": 5,
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
    },
}

# CJK font priority list (by availability + journal acceptance)
CJK_FONT_PRIORITY = [
    "Noto Sans CJK SC",
    "Noto Sans SC",
    "Source Han Sans SC",
    "Source Han Sans CN",
    "SimHei",
    "Microsoft YaHei",
    "PingFang SC",
    "Heiti SC",
    "WenQuanYi Zen Hei",
    "Arial Unicode MS",
]

CJK_SERIF_PRIORITY = [
    "Noto Serif CJK SC",
    "Noto Serif SC",
    "Source Han Serif SC",
    "Source Han Serif CN",
    "SimSun",
    "STSong",
    "Songti SC",
]

CJK_INSTALL_HINT = """\
No CJK fonts found. Please install one of the Noto CJK fonts:

  Linux:    sudo apt install fonts-noto-cjk    # Debian/Ubuntu
            sudo dnf install google-noto-sans-cjk-fonts  # Fedora/RHEL
  macOS:    brew install --cask font-noto-sans-cjk-sc
            or download: https://github.com/notofonts/noto-cjk/releases
  Windows:  download https://github.com/notofonts/noto-cjk/releases
            extract, right-click .ttf/.otf -> "Install for all users"

Or list currently installed CJK fonts:
  python -c "from plugins.tools.figure_style.runner import list_cjk_fonts; print(list_cjk_fonts())"
"""


def _available_fonts() -> set[str]:
    """Return set of all font names indexed by matplotlib."""
    return {f.name for f in fm.fontManager.ttflist}


def list_cjk_fonts() -> list[str]:
    """Return available CJK fonts on the system (sorted by priority)."""
    available = _available_fonts()
    hits = []
    for f in CJK_FONT_PRIORITY + CJK_SERIF_PRIORITY:
        if f in available and f not in hits:
            hits.append(f)
    for f in available:
        lower = f.lower()
        if any(k in lower for k in ("cjk", "han", "songti", "yahei", "simhei", "simsun")):
            if f not in hits:
                hits.append(f)
    return hits


def configure_chinese_fonts(serif_for_zh: bool = False) -> str:
    """
    Auto-detect and configure CJK fonts; fix minus sign rendering.

    Args:
        serif_for_zh: prefer serif CJK fonts (Song-style) for Chinese journals.
    Returns:
        Name of the chosen CJK font.
    Raises:
        RuntimeError: no recognized CJK font found.
    """
    available = _available_fonts()
    priority = CJK_SERIF_PRIORITY + CJK_FONT_PRIORITY if serif_for_zh else CJK_FONT_PRIORITY

    chosen = None
    for f in priority:
        if f in available:
            chosen = f
            break

    if chosen is None:
        for f in available:
            lower = f.lower()
            if any(k in lower for k in ("cjk", "han", "song", "hei", "yahei", "kaiti")):
                chosen = f
                break

    if chosen is None:
        raise RuntimeError(CJK_INSTALL_HINT)

    plt.rcParams["font.family"] = ["sans-serif"] if not serif_for_zh else ["serif"]
    if serif_for_zh:
        plt.rcParams["font.serif"] = [chosen, "Times New Roman", "Times", "DejaVu Serif"]
    else:
        plt.rcParams["font.sans-serif"] = [chosen, "Arial", "Helvetica", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    return chosen


def _try_sciencplots(journal: str) -> bool:
    """If SciencePlots is installed, apply its style stack; otherwise return False."""
    try:
        import scienceplots  # noqa: F401
    except ImportError:
        return False

    stack = ["science"]
    if journal == "nature":
        stack.append("nature")
    elif journal == "ieee":
        stack.append("ieee")
    stack.append("no-latex")
    try:
        plt.style.use(stack)
        return True
    except OSError as e:
        warnings.warn(f"SciencePlots style stack failed: {e}; fallback to builtin.")
        return False


def setup_style(
    journal: str = "general",
    lang: str = "en",
    use_sciplots: bool = True,
    serif_for_zh: bool = False,
    constrained_layout: bool = True,
) -> dict:
    """
    Apply publication-grade style preset.

    Args:
        journal: 'nature' | 'science' | 'ieee' | 'general'
        lang: 'en' | 'zh' -- Chinese mode auto-configures CJK fonts
        use_sciplots: try SciencePlots first; fallback to builtin presets
        serif_for_zh: use serif CJK font for Chinese journals
        constrained_layout: enable constrained_layout by default
    Returns:
        dict with keys: journal / lang / sciplots_used / cjk_font / constrained_layout
    """
    if journal not in JOURNAL_PRESETS:
        raise ValueError(f"Unknown journal preset: {journal}. "
                         f"Choose from {sorted(JOURNAL_PRESETS)}")

    sciplots_used = False
    if use_sciplots:
        sciplots_used = _try_sciencplots(journal)

    plt.rcParams.update(JOURNAL_PRESETS[journal])
    plt.rcParams["figure.constrained_layout.use"] = constrained_layout
    plt.rcParams["axes.unicode_minus"] = False

    cjk_font = None
    if lang == "zh":
        cjk_font = configure_chinese_fonts(serif_for_zh=serif_for_zh)
    elif lang != "en":
        raise ValueError(f"lang must be 'en' or 'zh', got {lang!r}")

    return {
        "journal": journal,
        "lang": lang,
        "sciplots_used": sciplots_used,
        "cjk_font": cjk_font,
        "constrained_layout": constrained_layout,
    }


def execute(
    action: str,
    params: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute figure style action."""
    params = params or {}
    metadata = {
        "resource": "local-figure-style",
    }
    try:
        if action == "figure-style.setup":
            journal = params.get("journal", "general")
            lang = params.get("lang", "en")
            use_sciplots = params.get("use_sciplots", True)
            serif_for_zh = params.get("serif_for_zh", False)
            constrained_layout = params.get("constrained_layout", True)
            info = setup_style(
                journal=journal,
                lang=lang,
                use_sciplots=use_sciplots,
                serif_for_zh=serif_for_zh,
                constrained_layout=constrained_layout,
            )
            return {
                "status": "success",
                "output": info,
                "metadata": metadata,
            }
        elif action == "figure-style.list-fonts":
            fonts = list_cjk_fonts()
            return {
                "status": "success",
                "output": {"cjk_fonts": fonts, "hint": CJK_INSTALL_HINT if not fonts else ""},
                "metadata": metadata,
            }
        else:
            return {
                "status": "plugin_error",
                "output": None,
                "error": f"Unsupported figure-style action: {action}",
                "metadata": metadata,
            }
    except Exception as exc:
        return {
            "status": "plugin_error",
            "output": None,
            "error": f"Figure style error: {exc}",
            "metadata": metadata,
        }
