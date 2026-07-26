"""Cross-surface regression baselines that remain outside renderer tests."""

from __future__ import annotations

import json

import pytest
import yaml

from core.config_center import ConfigCenter
from core.llm_client import create_configured_llm_client
from installer.entrypoint import init_config
from uninstall_entry import uninstall


def test_llm_client_calls_the_configured_provider(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "llm": {
                    "provider": "baseline-openai",
                    "providers": {
                        "baseline-openai": {
                            "api_format": "openai",
                            "base_url": "https://llm-baseline.local.test/v1",
                            "api_key": "sk-baseline-llm-secret",
                            "model": "baseline-model",
                        }
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    captured: dict[str, object] = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(
                {
                    "model": "baseline-model",
                    "choices": [{"message": {"content": "provider response"}}],
                    "usage": {"prompt_tokens": 2, "completion_tokens": 3},
                }
            ).encode()

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data)
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    result = create_configured_llm_client(ConfigCenter(config_path)).chat(
        [{"role": "user", "content": "baseline prompt"}], max_tokens=5
    )

    assert captured["url"] == "https://llm-baseline.local.test/v1/chat/completions"
    assert result["content"] == "provider response"


def test_missing_llm_configuration_is_an_explicit_failure(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("project: no-llm\n", encoding="utf-8")

    result = create_configured_llm_client(ConfigCenter(config_path))

    assert result["ok"] is False
    assert result["error"]["code"] == "missing_provider"


def test_install_requires_complete_llm_configuration(tmp_path):
    with pytest.raises(ValueError, match="provider, base_url, api_key, model"):
        init_config(tmp_path)

    assert not (tmp_path / ".supermedicine" / "config.yaml").exists()


def test_uninstall_removes_owned_artifacts_but_preserves_user_files(tmp_path):
    created_paths = [
        ".supermedicine/config.yaml",
        "workspaces/demo/state.json",
        "platform-targets/opencode/supermedicine.json",
    ]
    for relative in created_paths:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("generated", encoding="utf-8")
    (tmp_path / ".supermedicine" / "install-record.json").write_text(
        json.dumps(
            {
                "created_paths": created_paths,
                "platform_target_paths": [created_paths[-1]],
            }
        ),
        encoding="utf-8",
    )
    user_file = tmp_path / "user-notes.md"
    user_file.write_text("keep", encoding="utf-8")

    result = uninstall(tmp_path, force=True)

    assert result["status"] == "removed"
    assert not (tmp_path / ".supermedicine").exists()
    assert not (tmp_path / "workspaces").exists()
    assert user_file.exists()
