"""医学写作规范"""
from .checklists import Checklist, ChecklistItem, get_consort_checklist, get_strobe_checklist
from .prisma import PRISMAChecklist, PRISMAItem
from .stard import STARDChecklist, STARDItem

__all__ = [
    "Checklist", "ChecklistItem", "get_consort_checklist", "get_strobe_checklist",
    "PRISMAChecklist", "PRISMAItem", "STARDChecklist", "STARDItem",
]
