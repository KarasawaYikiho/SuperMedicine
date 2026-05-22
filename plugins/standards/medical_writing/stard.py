"""STARD 诊断准确性规范检查清单"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class STARDItem:
    """STARD 检查条目"""
    id: int
    section: str
    item: str
    description: str
    keywords: list[str] = field(default_factory=list)


class STARDChecklist:
    """STARD 2015 检查清单"""

    def __init__(self):
        self.name = "STARD"
        self.version = "2015"
        self.items = self._init_items()

    def _init_items(self) -> list[STARDItem]:
        return [
            STARDItem(1, "标题", "诊断准确性", "标题中表明是诊断准确性研究", ["诊断准确性", "diagnostic accuracy", "sensitivity", "specificity"]),
            STARDItem(2, "摘要", "结构化摘要", "提供结构化摘要", ["目的", "方法", "结果", "结论"]),
            STARDItem(3, "引言", "科学背景", "描述科学背景", ["背景", "科学依据"]),
            STARDItem(4, "引言", "目的", "明确陈述目的", ["目的", "objective"]),
            STARDItem(5, "方法", "研究设计", "描述研究设计", ["研究设计", "study design", "前瞻性", "回顾性"]),
            STARDItem(6, "方法", "参与者", "描述参与者", ["参与者", "participants", "纳入标准", "排除标准"]),
            STARDItem(7, "方法", "索引试验", "描述索引试验", ["索引试验", "index test", "待评估试验"]),
            STARDItem(8, "方法", "参考标准", "描述参考标准", ["参考标准", "reference standard", "金标准"]),
            STARDItem(9, "方法", "流程和时序", "描述流程和时序", ["流程", "timing"]),
            STARDItem(10, "方法", "盲法", "描述盲法", ["盲法", "blinding"]),
            STARDItem(11, "方法", "样本量", "描述样本量", ["样本量", "sample size"]),
            STARDItem(12, "方法", "缺失数据", "描述缺失数据处理", ["缺失数据", "missing data"]),
            STARDItem(13, "方法", "统计方法", "描述统计方法", ["统计方法", "统计分析"]),
            STARDItem(14, "结果", "参与者流程", "报告参与者流程", ["流程图", "参与者流程"]),
            STARDItem(15, "结果", "基线特征", "报告基线特征", ["基线特征", "demographics"]),
            STARDItem(16, "结果", "索引试验结果", "报告索引试验结果", ["试验结果"]),
            STARDItem(17, "结果", "参考标准结果", "报告参考标准结果", ["参考标准结果"]),
            STARDItem(18, "结果", "2x2 列联表", "报告 2x2 列联表", ["2x2", "列联表", "contingency", "TP", "FP", "FN", "TN"]),
            STARDItem(19, "结果", "诊断准确性", "报告诊断准确性指标", ["敏感度", "sensitivity", "特异度", "specificity", "PPV", "NPV"]),
            STARDItem(20, "结果", "置信区间", "报告置信区间", ["置信区间", "confidence interval", "95%CI"]),
            STARDItem(21, "结果", "亚组分析", "报告亚组分析", ["亚组分析", "subgroup"]),
            STARDItem(22, "结果", "不确定结果", "报告不确定结果", ["不确定", "indeterminate"]),
            STARDItem(23, "讨论", "主要发现", "总结主要发现", ["主要发现", "main findings"]),
            STARDItem(24, "讨论", "局限性", "讨论局限性", ["局限性", "limitation"]),
            STARDItem(25, "讨论", "临床应用", "讨论临床应用", ["临床应用", "clinical application"]),
            STARDItem(26, "其他", "注册", "提供注册信息", ["注册", "registration"]),
            STARDItem(27, "其他", "资助", "提供资助信息", ["资助", "funding"]),
        ]

    def check(self, text: str) -> dict[str, Any]:
        """检查文本是否符合 STARD 规范"""
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
            "standard": "STARD",
            "version": "2015",
            "total_items": total,
            "found_items": found,
            "compliance_rate": round(found / total * 100, 1) if total > 0 else 0,
            "details": results,
        }
