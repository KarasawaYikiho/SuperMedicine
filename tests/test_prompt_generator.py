from __future__ import annotations

from permission.prompt_generator import PromptGenerator

class TestPromptGenerator:
    def test_generate_prefix(self):
        gen = PromptGenerator()
        prompt = gen.generate_prefix("a", "retrieval", ["rag.query"], ["tool.execute"])
        assert "a" in prompt and "retrieval" in prompt and "rag.query" in prompt and "tool.execute" in prompt
    def test_generate_rejection_templates(self):
        templates = PromptGenerator().generate_rejection_templates("r")
        assert "code_execution" in templates and "privilege_escalation" in templates

    def test_prompt_generator_is_context_generation_only(self):
        gen = PromptGenerator()
        assert not hasattr(gen, "check")
        assert not hasattr(gen, "authorize")
        assert not hasattr(gen, "enforce")
