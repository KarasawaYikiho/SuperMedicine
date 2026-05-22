"""引用格式化工具函数"""
from __future__ import annotations


def format_authors(authors: list[str], max_authors: int = 6) -> str:
    """
    格式化作者列表
    
    Args:
        authors: 作者列表，每个元素为 "名 姓" 格式
        max_authors: 最大作者数量，超过则使用 "et al"
    
    Returns:
        格式化后的作者字符串
    """
    formatted = []
    for author in authors:
        parts = author.split()
        if len(parts) >= 2:
            last = parts[-1]
            initials = "".join(p[0].upper() for p in parts[:-1])
            formatted.append(f"{last} {initials}")
        else:
            formatted.append(author)

    if len(formatted) <= max_authors:
        return ", ".join(formatted)
    else:
        return ", ".join(formatted[:max_authors]) + ", et al"
