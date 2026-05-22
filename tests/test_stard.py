import pytest
from plugins.standards.medical_writing.stard import STARDChecklist


class TestSTARDChecklist:
    def test_checklist_loaded(self):
        checklist = STARDChecklist()
        assert checklist.name == "STARD"
        assert len(checklist.items) == 27

    def test_check_with_good_text(self):
        checklist = STARDChecklist()
        text = """
        这是一项诊断准确性研究。
        方法：采用前瞻性研究设计，评估索引试验的敏感度和特异度。
        参考标准为金标准。
        结果：报告了2x2列联表，敏感度95%，特异度90%。
        """
        result = checklist.check(text)
        assert result["total_items"] == 27
        assert result["found_items"] > 5

    def test_check_empty_text(self):
        checklist = STARDChecklist()
        result = checklist.check("")
        assert result["found_items"] == 0
