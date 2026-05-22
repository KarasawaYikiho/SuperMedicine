"""PRISMA 系统综述规范检查清单"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PRISMAItem:
    """PRISMA 检查条目"""
    id: int
    section: str
    item: str
    description: str
    keywords: list[str] = field(default_factory=list)


class PRISMAChecklist:
    """PRISMA 2020 检查清单"""

    def __init__(self):
        self.name = "PRISMA"
        self.version = "2020"
        self.items = self._init_items()

    def _init_items(self) -> list[PRISMAItem]:
        return [
            PRISMAItem(1, "标题", "系统综述", "标题中应表明这是系统综述", ["系统综述", "systematic review", "meta分析", "meta-analysis"]),
            PRISMAItem(2, "摘要", "结构化摘要", "提供结构化摘要", ["目的", "方法", "结果", "结论"]),
            PRISMAItem(3, "引言", "理论依据", "描述理论依据", ["背景", "理论依据", "rationale"]),
            PRISMAItem(4, "引言", "目的", "明确陈述目的", ["目的", "objective", "aim"]),
            PRISMAItem(5, "方法", "纳入标准", "描述纳入标准", ["纳入标准", "inclusion criteria", "eligibility"]),
            PRISMAItem(6, "方法", "信息来源", "描述信息来源", ["数据库", "database", "PubMed", "检索"]),
            PRISMAItem(7, "方法", "检索策略", "描述检索策略", ["检索策略", "search strategy", "检索词"]),
            PRISMAItem(8, "方法", "选择过程", "描述研究选择过程", ["筛选", "screening", "选择过程"]),
            PRISMAItem(9, "方法", "数据提取", "描述数据提取方法", ["数据提取", "data extraction"]),
            PRISMAItem(10, "方法", "偏倚风险", "描述偏倚风险评估", ["偏倚风险", "risk of bias", "质量评价"]),
            PRISMAItem(11, "方法", "效应量", "描述效应量指标", ["效应量", "effect size", "RR", "OR", "HR"]),
            PRISMAItem(12, "方法", "合成方法", "描述数据合成方法", ["meta分析", "meta-analysis", "随机效应", "固定效应"]),
            PRISMAItem(13, "方法", "异质性", "描述异质性评估", ["异质性", "heterogeneity", "I²", "Q检验"]),
            PRISMAItem(14, "方法", "证据质量", "描述证据质量评估", ["GRADE", "证据质量", "certainty"]),
            PRISMAItem(15, "结果", "研究选择", "报告研究选择流程", ["PRISMA流程图", "筛选流程", "排除原因"]),
            PRISMAItem(16, "结果", "研究特征", "报告纳入研究特征", ["研究特征", "基线特征"]),
            PRISMAItem(17, "结果", "偏倚风险", "报告偏倚风险结果", ["偏倚风险", "质量评价"]),
            PRISMAItem(18, "结果", "个别结果", "报告个别研究结果", ["森林图", "forest plot"]),
            PRISMAItem(19, "结果", "合成结果", "报告合成结果", ["合并效应", "pooled effect"]),
            PRISMAItem(20, "结果", "异质性", "报告异质性结果", ["I²", "异质性"]),
            PRISMAItem(21, "结果", "亚组分析", "报告亚组分析结果", ["亚组分析", "subgroup analysis"]),
            PRISMAItem(22, "结果", "敏感性分析", "报告敏感性分析结果", ["敏感性分析", "sensitivity analysis"]),
            PRISMAItem(23, "结果", "发表偏倚", "报告发表偏倚评估", ["发表偏倚", "publication bias", "漏斗图"]),
            PRISMAItem(24, "讨论", "证据总结", "总结主要证据", ["证据总结", "主要发现"]),
            PRISMAItem(25, "讨论", "局限性", "讨论局限性", ["局限性", "limitation"]),
            PRISMAItem(26, "讨论", "结论", "给出结论", ["结论", "conclusion"]),
            PRISMAItem(27, "其他", "注册与协议", "提供注册信息", ["PROSPERO", "注册", "protocol"]),
        ]

    def check(self, text: str) -> dict[str, any]:
        """检查文本是否符合 PRISMA 规范"""
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
            "standard": "PRISMA",
            "version": "2020",
            "total_items": total,
            "found_items": found,
            "compliance_rate": round(found / total * 100, 1) if total > 0 else 0,
            "details": results,
        }
