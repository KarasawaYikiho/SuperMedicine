"""LLM 客户端测试"""
from __future__ import annotations

from unittest.mock import patch

from core.llm_client import create_llm_client
from core.llm_providers.openrouter import OpenRouterClient


class TestOpenRouterClient:
    """测试 OpenRouter LLM 客户端"""

    def test_init_defaults(self):
        """测试默认初始化"""
        client = OpenRouterClient()
        assert client.model == "anthropic/claude-3.5-sonnet"

    def test_init_custom_model(self):
        """测试自定义模型"""
        client = OpenRouterClient(model="openai/gpt-4o")
        assert client.model == "openai/gpt-4o"

    def test_complete_without_api_key(self):
        """无 API Key 时返回错误"""
        client = OpenRouterClient(api_key="")
        result = client.complete("Hello")
        assert result["content"] == ""
        assert "error" in result

    def test_chat_mock_response(self):
        """模拟 API 响应"""
        client = OpenRouterClient(api_key="test-key")
        with patch.object(client, '_request', return_value={
            "content": "Hello, I am Claude.",
            "model": "anthropic/claude-3.5-sonnet",
            "usage": {"prompt_tokens": 5, "completion_tokens": 10},
        }):
            result = client.chat([{"role": "user", "content": "Hi"}])
            assert result["content"] == "Hello, I am Claude."
            assert result["model"] == "anthropic/claude-3.5-sonnet"

    def test_complete_mock_response(self):
        """模拟 complete 调用"""
        client = OpenRouterClient(api_key="test-key")
        with patch.object(client, '_request', return_value={
            "content": "Response text",
            "model": "anthropic/claude-3.5-sonnet",
            "usage": {},
        }):
            result = client.complete("Test prompt", temperature=0.5)
            assert result["content"] == "Response text"


class TestLLMFactory:
    """测试 LLM 工厂函数"""

    def test_create_openrouter(self):
        """创建 OpenRouter 客户端"""
        client = create_llm_client("openrouter", api_key="test-key", model="test-model")
        assert isinstance(client, OpenRouterClient)
        assert client.model == "test-model"

    def test_create_unsupported(self):
        """不支持的 provider 抛出 ValueError"""
        try:
            create_llm_client("unsupported")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Unsupported" in str(e)
