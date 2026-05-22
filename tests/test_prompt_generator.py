from permission.prompt_generator import PromptGenerator

class TestPromptGenerator:
    def test_generate_prefix(self):
        gen = PromptGenerator()
        prompt = gen.generate_prefix("a", "retrieval", ["rag.query"], ["tool.execute"])
        assert "a" in prompt and "retrieval" in prompt and "rag.query" in prompt and "tool.execute" in prompt
    def test_generate_rejection_templates(self):
        templates = PromptGenerator().generate_rejection_templates("r")
        assert "code_execution" in templates and "privilege_escalation" in templates
