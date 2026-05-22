import pytest
from plugins.standards.medical_writing.checklists import get_consort_checklist, get_strobe_checklist


class TestConsortChecklist:
    def test_checklist_loaded(self):
        checklist = get_consort_checklist()
        assert checklist.name == "CONSORT"
        assert len(checklist.items) > 0

    def test_check_with_consort_text(self):
        checklist = get_consort_checklist()
        text = "本研究是一项随机对照试验，采用结构化摘要，描述了科学背景和目的"
        result = checklist.check(text)
        assert result["standard"] == "CONSORT"
        assert result["total_items"] > 0
        assert result["found_items"] > 0

    def test_check_empty_text(self):
        checklist = get_consort_checklist()
        result = checklist.check("")
        assert result["found_items"] == 0


class TestStrobeChecklist:
    def test_checklist_loaded(self):
        checklist = get_strobe_checklist()
        assert checklist.name == "STROBE"
        assert len(checklist.items) > 0

    def test_check_with_strobe_text(self):
        checklist = get_strobe_checklist()
        text = "这是一项队列研究，描述了研究设计和参与者选择标准"
        result = checklist.check(text)
        assert result["standard"] == "STROBE"
        assert result["total_items"] > 0
