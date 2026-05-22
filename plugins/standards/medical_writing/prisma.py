"""PRISMA 系统综述规范检查清单"""
from __future__ import annotations

from .checklist_base import ChecklistBase, ChecklistItemBase

# Backward compatibility alias
PRISMAItem = ChecklistItemBase


class PRISMAChecklist(ChecklistBase):
    """PRISMA 2020 检查清单"""

    def __init__(self):
        items = self._init_items()
        super().__init__(name="PRISMA", version="2020", items=items)

    def _init_items(self) -> list[ChecklistItemBase]:
        return [
            ChecklistItemBase(1, "标题", "系统综述", "标题中应表明这是系统综述", ["系统综述", "systematic review", "meta分析", "meta-analysis"]),
            ChecklistItemBase(2, "摘要", "结构化摘要", "提供结构化摘要", ["目的", "方法", "结果", "结论"]),
            ChecklistItemBase(3, "引言", "理论依据", "描述理论依据", ["背景", "理论依据", "rationale"]),
            ChecklistItemBase(4, "引言", "目的", "明确陈述目的", ["目的", "objective", "aim"]),
            ChecklistItemBase(5, "方法", "纳入标准", "描述纳入标准", ["纳入标准", "inclusion criteria", "eligibility"]),
            ChecklistItemBase(6, "方法", "信息来源", "描述信息来源", ["数据库", "database", "PubMed", "检索"]),
            ChecklistItemBase(7, "方法", "检索策略", "描述检索策略", ["检索策略", "search strategy", "检索词"]),
            ChecklistItemBase(8, "方法", "选择过程", "描述研究选择过程", ["筛选", "screening", "选择过程"]),
            ChecklistItemBase(9, "方法", "数据提取", "描述数据提取方法", ["数据提取", "data extraction"]),
            ChecklistItemBase(10, "方法", "偏倚风险", "描述偏倚风险评估", ["偏倚风险", "risk of bias", "质量评价"]),
            ChecklistItemBase(11, "方法", "效应量", "描述效应量指标", ["效应量", "effect size", "RR", "OR", "HR"]),
            ChecklistItemBase(12, "方法", "合成方法", "描述数据合成方法", ["meta分析", "meta-analysis", "随机效应", "固定效应"]),
            ChecklistItemBase(13, "方法", "异质性", "描述异质性评估", ["异质性", "heterogeneity", "I²", "Q检验"]),
            ChecklistItemBase(14, "方法", "证据质量", "描述证据质量评估", ["GRADE", "证据质量", "certainty"]),
            ChecklistItemBase(15, "结果", "研究选择", "报告研究选择流程", ["PRISMA流程图", "筛选流程", "排除原因"]),
            ChecklistItemBase(16, "结果", "研究特征", "报告纳入研究特征", ["研究特征", "基线特征"]),
            ChecklistItemBase(17, "结果", "偏倚风险", "报告偏倚风险结果", ["偏倚风险", "质量评价"]),
            ChecklistItemBase(18, "结果", "个别结果", "报告个别研究结果", ["森林图", "forest plot"]),
            ChecklistItemBase(19, "结果", "合成结果", "报告合成结果", ["合并效应", "pooled effect"]),
            ChecklistItemBase(20, "结果", "异质性", "报告异质性结果", ["I²", "异质性"]),
            ChecklistItemBase(21, "结果", "亚组分析", "报告亚组分析结果", ["亚组分析", "subgroup analysis"]),
            ChecklistItemBase(22, "结果", "敏感性分析", "报告敏感性分析结果", ["敏感性分析", "sensitivity analysis"]),
            ChecklistItemBase(23, "结果", "发表偏倚", "报告发表偏倚评估", ["发表偏倚", "publication bias", "漏斗图"]),
            ChecklistItemBase(24, "讨论", "证据总结", "总结主要证据", ["证据总结", "主要发现"]),
            ChecklistItemBase(25, "讨论", "局限性", "讨论局限性", ["局限性", "limitation"]),
            ChecklistItemBase(26, "讨论", "结论", "给出结论", ["结论", "conclusion"]),
            ChecklistItemBase(27, "其他", "注册与协议", "提供注册信息", ["PROSPERO", "注册", "protocol"]),
        ]
