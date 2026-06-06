from __future__ import annotations

from permission.prompt_generator import PromptGenerator


class TestPromptGenerator:
    def test_generate_prefix(self):
        gen = PromptGenerator()
        prompt = gen.generate_prefix("a", "retrieval", ["rag.query"], ["tool.execute"])
        assert (
            "a" in prompt
            and "retrieval" in prompt
            and "rag.query" in prompt
            and "tool.execute" in prompt
        )

    def test_generate_rejection_templates(self):
        templates = PromptGenerator().generate_rejection_templates("r")
        assert "code_execution" in templates and "privilege_escalation" in templates

    def test_prompt_generator_is_context_generation_only(self):
        gen = PromptGenerator()
        assert not hasattr(gen, "check")
        assert not hasattr(gen, "authorize")
        assert not hasattr(gen, "enforce")

    def test_generate_prefix_injects_self_evolution_guidance(self):
        prompt = PromptGenerator().generate_prefix(
            "delta",
            "execution",
            ["self_evolution.generate"],
            ["git.push"],
        )

        required_phrases = [
            "permission mode",
            "sandbox restrictions",
            "目标路径",
            "产物类型",
            "风险等级",
            "用户显式确认",
            "敏感信息处理",
            "审计/日志要求",
            "self_evolution",
            "generated",
            "tools/generated",
            "Docs",
            "docs",
            "REQUIREMENTS_TRACEABILITY.md",
            "engineering-only files",
            "Git-submittable artifacts",
            "不可提交/不可上传 Git",
            "redaction",
            "permission engine",
            "audit logger",
        ]
        for phrase in required_phrases:
            assert phrase in prompt
