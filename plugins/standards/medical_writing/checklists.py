"""医学写作规范检查清单 — CONSORT 和 STROBE"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .checklist_base import ChecklistBase, ChecklistItemBase


@dataclass
class ChecklistItem(ChecklistItemBase):
    """检查清单条目（扩展基类，增加 Required 字段）"""
    required: bool = True


class Checklist(ChecklistBase):
    """规范检查清单（继承 ChecklistBase）"""

    def __init__(self, name: str, version: str, items: list[ChecklistItem]):
        # 从 ChecklistItem 中提取关键词填充到基类的 Keywords 字段
        base_items = []
        for item in items:
            base_items.append(ChecklistItemBase(
                id=item.id,
                section=item.section,
                item=item.item,
                description=item.description,
                keywords=[item.item, item.section],  # 从 Item 和 Section 生成关键词
            ))
        super().__init__(name=name, version=version, items=base_items)
        # 保存原始 ChecklistItem 列表用于计算 required_missing
        self._raw_items = items

    def check(self, text: str) -> dict[str, Any]:
        """检查文本是否符合规范（重写以添加 required_missing 字段）"""
        result = super().check(text)

        # 计算 Required_Missing（原 Checklists.Py 独有逻辑）
        required_missing = []
        for i, detail in enumerate(result["details"]):
            if i < len(self._raw_items) and self._raw_items[i].required and not detail["found"]:
                required_missing.append(detail)
        result["required_missing"] = required_missing

        return result


def get_consort_checklist() -> Checklist:
    """获取 CONSORT 检查清单"""
    return Checklist(
        name="CONSORT",
        version="2010",
        items=[
            ChecklistItem("1a", "标题", "随机对照试验", "标题中应包含'随机'一词"),
            ChecklistItem("1b", "摘要", "结构化摘要", "摘要应采用结构化格式"),
            ChecklistItem("2a", "引言", "科学背景", "描述科学背景和理论依据"),
            ChecklistItem("2b", "引言", "目的", "明确陈述目的和假设"),
            ChecklistItem("3a", "方法", "试验设计", "描述试验设计"),
            ChecklistItem("4a", "方法", "受试者", "描述受试者的纳入和排除标准"),
            ChecklistItem("5", "方法", "干预", "详细描述各组的干预措施"),
            ChecklistItem("6a", "方法", "结局指标", "明确定义主要和次要结局指标"),
            ChecklistItem("6b", "方法", "样本量", "解释样本量的确定方法"),
            ChecklistItem("7a", "方法", "随机化", "描述随机化方法"),
            ChecklistItem("7b", "方法", "分配隐藏", "描述分配隐藏机制"),
            ChecklistItem("8", "方法", "实施", "描述谁生成随机分配序列"),
            ChecklistItem("9", "方法", "盲法", "描述盲法实施情况"),
            ChecklistItem("10", "方法", "统计方法", "描述统计分析方法"),
            ChecklistItem("11a", "结果", "受试者流程", "描述每个阶段的受试者流程"),
            ChecklistItem("12a", "结果", "招募", "报告招募期和随访时间"),
            ChecklistItem("13a", "结果", "基线数据", "报告各组的基线人口学和临床特征"),
            ChecklistItem("14a", "结果", "分析人数", "报告每个分析中纳入的人数"),
            ChecklistItem("15", "结果", "结局和估计", "报告主要和次要结局的结果"),
            ChecklistItem("16", "结果", "辅助分析", "报告其他分析结果"),
            ChecklistItem("17", "讨论", "危害", "报告各组的不良事件"),
            ChecklistItem("18", "讨论", "局限性", "讨论试验的局限性"),
            ChecklistItem("19", "讨论", "推广性", "讨论试验结果的推广性"),
        ],
    )


def get_strobe_checklist() -> Checklist:
    """获取 STROBE 检查清单"""
    return Checklist(
        name="STROBE",
        version="2007",
        items=[
            ChecklistItem("1", "标题", "研究类型", "标题中指明研究设计"),
            ChecklistItem("2", "摘要", "结构化摘要", "提供结构化摘要"),
            ChecklistItem("3", "引言", "背景", "解释科学背景和理论依据"),
            ChecklistItem("4", "引言", "目的", "明确陈述目的"),
            ChecklistItem("5", "方法", "研究设计", "描述研究设计的关键要素"),
            ChecklistItem("6", "方法", "研究场所", "描述研究场所"),
            ChecklistItem("7", "方法", "参与者", "描述参与者的选择标准"),
            ChecklistItem("8", "方法", "变量", "明确定义所有结局和预测变量"),
            ChecklistItem("9", "方法", "数据来源", "描述数据来源和测量方法"),
            ChecklistItem("10", "方法", "偏倚", "描述解决潜在偏倚的方法"),
            ChecklistItem("11", "方法", "研究规模", "解释研究规模的确定方法"),
            ChecklistItem("12", "方法", "定量变量", "描述定量变量的处理方法"),
            ChecklistItem("13", "方法", "统计方法", "描述统计分析方法"),
            ChecklistItem("14a", "结果", "参与者", "报告每个阶段的参与者人数"),
            ChecklistItem("15", "结果", "描述性数据", "报告描述性数据"),
            ChecklistItem("16", "结果", "主要结果", "报告主要结果"),
            ChecklistItem("17", "结果", "其他分析", "报告其他分析"),
            ChecklistItem("18", "讨论", "主要发现", "总结主要发现"),
            ChecklistItem("19", "讨论", "局限性", "讨论局限性"),
            ChecklistItem("20", "讨论", "推广性", "讨论推广性"),
            ChecklistItem("21", "讨论", "解读", "解释结果"),
            ChecklistItem("22", "其他", "资助", "提供资助来源"),
        ],
    )
