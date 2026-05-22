"""规范检查清单基类"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChecklistItemBase:
    """检查条目基类"""
    id: int | str
    section: str
    item: str
    description: str
    keywords: list[str] = field(default_factory=list)


class ChecklistBase:
    """规范检查清单基类"""
    
    def __init__(self, name: str, version: str, items: list[ChecklistItemBase]):
        self.name = name
        self.version = version
        self.items = items
    
    def check(self, text: str) -> dict[str, Any]:
        """检查文本是否符合规范"""
        results = []
        text_lower = text.lower()

        for item in self.items:
            found = any(kw.lower() in text_lower for kw in item.keywords)
            results.append({
                "item_id": item.id,
                "section": item.section,
                "item": item.item,
                "found": found,
            })

        total = len(results)
        found = sum(1 for r in results if r["found"])

        return {
            "standard": self.name,
            "version": self.version,
            "total_items": total,
            "found_items": found,
            "compliance_rate": round(found / total * 100, 1) if total > 0 else 0,
            "details": results,
        }
