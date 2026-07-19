"""Unified scientific figure advisor plugin.

Provides data profiling, journal style presets, multi-format export,
compliance audit, panel alignment, visual QA, and full 8-step workflow.
"""

from __future__ import annotations

import sys

from . import audit, presentation

# Preserve the historical import paths while keeping one implementation per domain.
check = audit
qa = audit
style = presentation
layout = presentation
sys.modules[f"{__name__}.check"] = audit
sys.modules[f"{__name__}.qa"] = audit
sys.modules[f"{__name__}.style"] = presentation
sys.modules[f"{__name__}.layout"] = presentation

__all__ = ["audit", "check", "layout", "presentation", "qa", "style"]
