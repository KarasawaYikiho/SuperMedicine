"""STARD 诊断准确性规范检查清单"""

from __future__ import annotations

from .checklist_base import ChecklistItemBase, DeclarativeChecklist

# Backward Compatibility Alias
STARDItem = ChecklistItemBase


class STARDChecklist(DeclarativeChecklist):
    """STARD 2015 检查清单"""

    NAME = "STARD"
    VERSION = "2015"
    ITEMS = (
        ChecklistItemBase(
            1,
            "标题",
            "诊断准确性",
            "标题中表明是诊断准确性研究",
            ["诊断准确性", "diagnostic accuracy", "sensitivity", "specificity"],
        ),
        ChecklistItemBase(
            2,
            "摘要",
            "结构化摘要",
            "提供结构化摘要",
            ["目的", "方法", "结果", "结论"],
        ),
        ChecklistItemBase(3, "引言", "科学背景", "描述科学背景", ["背景", "科学依据"]),
        ChecklistItemBase(4, "引言", "目的", "明确陈述目的", ["目的", "objective"]),
        ChecklistItemBase(
            5,
            "方法",
            "研究设计",
            "描述研究设计",
            ["研究设计", "study design", "前瞻性", "回顾性"],
        ),
        ChecklistItemBase(
            6,
            "方法",
            "参与者",
            "描述参与者",
            ["参与者", "participants", "纳入标准", "排除标准"],
        ),
        ChecklistItemBase(
            7,
            "方法",
            "索引试验",
            "描述索引试验",
            ["索引试验", "index test", "待评估试验"],
        ),
        ChecklistItemBase(
            8,
            "方法",
            "参考标准",
            "描述参考标准",
            ["参考标准", "reference standard", "金标准"],
        ),
        ChecklistItemBase(
            9, "方法", "流程和时序", "描述流程和时序", ["流程", "timing"]
        ),
        ChecklistItemBase(10, "方法", "盲法", "描述盲法", ["盲法", "blinding"]),
        ChecklistItemBase(
            11, "方法", "样本量", "描述样本量", ["样本量", "sample size"]
        ),
        ChecklistItemBase(
            12, "方法", "缺失数据", "描述缺失数据处理", ["缺失数据", "missing data"]
        ),
        ChecklistItemBase(
            13, "方法", "统计方法", "描述统计方法", ["统计方法", "统计分析"]
        ),
        ChecklistItemBase(
            14, "结果", "参与者流程", "报告参与者流程", ["流程图", "参与者流程"]
        ),
        ChecklistItemBase(
            15, "结果", "基线特征", "报告基线特征", ["基线特征", "demographics"]
        ),
        ChecklistItemBase(16, "结果", "索引试验结果", "报告索引试验结果", ["试验结果"]),
        ChecklistItemBase(
            17, "结果", "参考标准结果", "报告参考标准结果", ["参考标准结果"]
        ),
        ChecklistItemBase(
            18,
            "结果",
            "2x2 列联表",
            "报告 2x2 列联表",
            ["2x2", "列联表", "contingency", "TP", "FP", "FN", "TN"],
        ),
        ChecklistItemBase(
            19,
            "结果",
            "诊断准确性",
            "报告诊断准确性指标",
            ["敏感度", "sensitivity", "特异度", "specificity", "PPV", "NPV"],
        ),
        ChecklistItemBase(
            20,
            "结果",
            "置信区间",
            "报告置信区间",
            ["置信区间", "confidence interval", "95%CI"],
        ),
        ChecklistItemBase(
            21, "结果", "亚组分析", "报告亚组分析", ["亚组分析", "subgroup"]
        ),
        ChecklistItemBase(
            22, "结果", "不确定结果", "报告不确定结果", ["不确定", "indeterminate"]
        ),
        ChecklistItemBase(
            23, "讨论", "主要发现", "总结主要发现", ["主要发现", "main findings"]
        ),
        ChecklistItemBase(24, "讨论", "局限性", "讨论局限性", ["局限性", "limitation"]),
        ChecklistItemBase(
            25,
            "讨论",
            "临床应用",
            "讨论临床应用",
            ["临床应用", "clinical application"],
        ),
        ChecklistItemBase(26, "其他", "注册", "提供注册信息", ["注册", "registration"]),
        ChecklistItemBase(27, "其他", "资助", "提供资助信息", ["资助", "funding"]),
    )
