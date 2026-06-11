"""Pure mapping from natural-language task text to plugin/action paths.

This module contains ``select_plugin_action``, a stateless function that
inspects a task description and returns the matching ``(plugin, action)``
tuple.  It was extracted from ``Kernel._select_plugin_action`` to make the
mapping reusable and independently testable.
"""

from __future__ import annotations


def select_plugin_action(task: str) -> tuple[str | None, str | None]:
    """基于任务文本选择当前阶段可控的真实插件路径。"""
    normalized = task.lower()
    if "survival" in normalized or "kaplan" in normalized or "生存" in normalized:
        return "r-survival", "r.survival.km"
    if "ttest" in normalized or "t-test" in normalized or "t 检验" in normalized:
        return "python-stats", "stats.ttest"
    if "anova" in normalized or "方差" in normalized:
        return "python-stats", "stats.anova"
    if "regression" in normalized or "回归" in normalized:
        return "python-stats", "stats.regression"
    if "rag" in normalized or "retrieval" in normalized or "检索" in normalized:
        return "rag-interface", "rag.query"
    if (
        "harness" in normalized
        or "checkpoint" in normalized
        or "monitor" in normalized
        or "检查点" in normalized
        or "监控" in normalized
    ):
        return "harness-core", "harness.integration.checkpoint"
    if "consort" in normalized or "随机对照" in normalized:
        return "medical-writing", "standard.consort"
    if "strobe" in normalized or "观察性" in normalized:
        return "medical-writing", "standard.strobe"
    if (
        "prisma" in normalized
        or "系统综述" in normalized
        or "meta分析" in normalized
        or "meta-analysis" in normalized
    ):
        return "medical-writing", "standard.prisma"
    if "stard" in normalized or "诊断准确性" in normalized:
        return "medical-writing", "standard.stard"
    if "vancouver" in normalized:
        return "medical-citation", "standard.citation.vancouver"
    if "ama" in normalized or "citation" in normalized or "引用" in normalized:
        return "medical-citation", "standard.citation.ama"
    if (
        "medical writing" in normalized
        or "checklist" in normalized
        or "写作规范" in normalized
        or "检查清单" in normalized
    ):
        return "medical-writing", "standard.consort"
    if "medical" in normalized or "stats" in normalized or "统计" in normalized:
        return "python-stats", "stats.descriptive"
    # Figure visualization (unified workflow)
    if any(k in normalized for k in (
        "画图", "画图表", "图表", "可视化", "figure", "plot", "chart",
        "柱状图", "散点图", "折线图", "箱线图", "热力图", "直方图",
        "bar chart", "scatter", "line chart", "box plot", "heatmap", "histogram",
        "论文图", "科研图", "期刊图", "数据图",
        "期刊样式", "nature", "science", "ieee", "中文字体", "cjk",
        "字体配置", "style setup",
        "导出图", "export figure", "pdf导出", "矢量图", "灰度预览",
        "检查图", "check figure", "合规", "dpi检查", "字体嵌入",
        "子图标签", "panel label", "对齐", "a/b/c",
        "视觉自检", "visual qa", "缺字", "裁切", "刻度重叠",
    )):
        return "figure", "figure.workflow"
    return None, None
