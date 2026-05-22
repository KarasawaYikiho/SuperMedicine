import pytest
from plugins.standards.medical_writing.prisma import PRISMAChecklist


class TestPRISMAChecklist:
    def test_checklist_loaded(self):
        checklist = PRISMAChecklist()
        assert checklist.name == "PRISMA"
        assert len(checklist.items) == 27

    def test_check_with_good_text(self):
        checklist = PRISMAChecklist()
        text = """
        这是一项系统综述和meta分析。
        目的：评估某干预措施的效果。
        背景：基于现有理论依据，本研究旨在评估干预效果。
        方法：
        - 纳入标准：符合PICOS标准的随机对照试验
        - 检索PubMed、Cochrane等数据库
        - 采用检索策略进行文献筛选
        - 数据提取采用双人独立提取
        - 偏倚风险评估采用Cochrane风险评估工具
        - 效应量采用RR和OR
        - 合成方法：采用随机效应模型进行meta分析
        - 异质性评估：I²统计量和Q检验
        - 证据质量：采用GRADE评级
        结果：
        - PRISMA流程图展示筛选流程
        - 报告研究特征和基线特征
        - 森林图展示合并效应
        - 亚组分析和敏感性分析结果
        - 漏斗图评估发表偏倚
        讨论：
        - 证据总结：主要发现支持该干预有效
        - 局限性：纳入研究数量有限
        结论：该干预措施有效。
        注册：PROSPERO CRD42024000000
        """
        result = checklist.check(text)
        assert result["total_items"] == 27
        assert result["found_items"] > 5

    def test_check_empty_text(self):
        checklist = PRISMAChecklist()
        result = checklist.check("")
        assert result["found_items"] == 0
