"""医学引用规范"""

from __future__ import annotations

import sys

from . import ama_format as _formatters
from .ama_format import AMAFormatter, VancouverFormatter

sys.modules.setdefault(f"{__name__}.vancouver_format", _formatters)

__all__ = ["AMAFormatter", "VancouverFormatter"]
