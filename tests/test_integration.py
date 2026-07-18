"""集成测试 — 端到端科研流程"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import yaml
import pytest

from cli_entry import CLI
from cli import _resolve_run_params
from installer.entrypoint import (
    DEFAULT_CONFIG,
    init_config,
    main as install_main,
    write_llm_config,
)
from core.kernel import Kernel
from agents.orchestrator import Orchestrator
from agents.roles import BaseAgent
from agents.state_machine import StateMachine, TaskState
from agents.checkpoint import CheckpointManager
from permission.engine import PermissionEngine
from permission.policy import PermissionResult, default_policy_path
from plugins.tools.python_stats.main import descriptive, ttest, regression
from plugins.standards.medical_writing.checklists import get_consort_checklist
from typing import Any


def _llm_kwargs(provider: str = "openai") -> dict[str, str]:
    return {
        "provider": provider,
        "base_url": f"https://{provider}.local.test/v1",
        "api_key": f"{provider}-test-secret",
        "model": f"{provider}-test-model",
    }


class MockAgent(BaseAgent):
    """测试用 Agent"""

    def __init__(self, agent_id: str, role: str):
        super().__init__(agent_id, role)
        self.executed: list[dict[str, Any]] = []

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        self.executed.append(task)
        return {"status": "success", "agent": self.agent_id, "task": task}


class TestIntegration:
    """端到端集成测试"""

    def test_install_init_creates_canonical_default_policy_without_overwrite(
        self, tmp_path
    ):
        """Install.py --init 应创建核心默认策略，并在重复初始化时保留用户策略。"""
        expected_policy = PermissionEngine.default_policy_path().read_text(
            encoding="utf-8"
        )

        init_config(tmp_path, **_llm_kwargs())

        target_policy = default_policy_path(tmp_path)
        assert target_policy.exists()
        assert target_policy.read_text(encoding="utf-8") == expected_policy

        custom_policy = "# user customized policy\n"
        target_policy.write_text(custom_policy, encoding="utf-8")
        init_config(tmp_path, **_llm_kwargs("anthropic"))

        assert target_policy.read_text(encoding="utf-8") == custom_policy

    @pytest.mark.core
    def test_install_init_is_core_only_and_does_not_detect_platforms(
        self, tmp_path, monkeypatch
    ):
        """核心初始化不得探测 OpenCode/Claude Code 平台目录。"""
        from pathlib import Path as PathClass

        original_joinpath = PathClass.joinpath

        def reject_platform_probe(self, *other):
            joined = "/".join(str(part) for part in other)
            if ".claude" in joined or "opencode" in joined:
                raise AssertionError(
                    "init_config must not probe platform config directories"
                )
            return original_joinpath(self, *other)

        monkeypatch.setattr(PathClass, "joinpath", reject_platform_probe)

        init_config(tmp_path, **_llm_kwargs())

        assert (tmp_path / ".supermedicine" / "config.yaml").exists()
        assert default_policy_path(tmp_path).exists()

    def test_default_policy_falls_back_to_packaged_resource_when_source_tree_missing(
        self, tmp_path
    ):
        """安装后的包缺少源码树 .supermedicine 时，应从包资源创建同一默认策略。"""
        expected_policy = PermissionEngine.default_policy_path().read_text(
            encoding="utf-8"
        )
        installed_like_root = tmp_path / "site-packages"
        project_dir = tmp_path / "project"
        installed_like_root.mkdir()
        project_dir.mkdir()

        from permission.policy import ensure_default_policy

        created_policy = ensure_default_policy(project_dir, installed_like_root)

        assert created_policy == default_policy_path(project_dir)
        assert created_policy.read_text(encoding="utf-8") == expected_policy

    def test_cli_init_and_install_init_create_same_default_policy(self, tmp_path):
        """CLI init 与 Install.py --init 应生成同一份 canonical 默认策略。"""
        cli_project = tmp_path / "cli" / "nonexistent-project"
        install_project = tmp_path / "install"
        install_project.mkdir()

        CLI().init(cli_project, **_llm_kwargs())
        init_config(install_project, **_llm_kwargs())

        assert (cli_project / ".supermedicine").is_dir()
        assert default_policy_path(cli_project).read_text(
            encoding="utf-8"
        ) == default_policy_path(install_project).read_text(encoding="utf-8")

    def test_install_init_writes_openai_llm_config_with_secret_redaction(
        self, tmp_path, caplog
    ):
        secret = "sk-test-install-secret"
        caplog.set_level("INFO", logger="Install")

        init_config(
            tmp_path,
            provider="openai",
            base_url="https://openai.example.test/v1",
            api_key=secret,
            model="gpt-test-install",
        )

        config = yaml.safe_load(
            (tmp_path / ".supermedicine" / "config.yaml").read_text(encoding="utf-8")
        )
        openai = config["llm"]["providers"]["openai"]
        assert config["llm"]["provider"] == "openai"
        assert openai["base_url"] == "https://openai.example.test/v1"
        assert openai["api_key"] == secret
        assert openai["model"] == "gpt-test-install"
        assert secret not in caplog.text
        assert "<redacted>" in caplog.text

    def test_install_init_requires_complete_llm_config(self, tmp_path):
        with pytest.raises(ValueError, match="完整 LLM Provider 配置"):
            init_config(tmp_path)

    def test_first_install_requires_complete_llm_setup_and_does_not_write_partial_config(
        self, tmp_path, monkeypatch
    ):
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Path, "home", lambda: fake_home)
        monkeypatch.setattr("sys.argv", ["Install.py", "--init"])

        with pytest.raises(ValueError, match="provider, base_url, api_key, model"):
            install_main()

        assert not (tmp_path / ".supermedicine" / "config.yaml").exists()
        assert not (fake_home / ".supermedicine" / "config.yaml").exists()

    def test_provider_added_by_manual_config_file_is_used_without_home_or_network(
        self, tmp_path, monkeypatch
    ):
        secret = "sk-manual-file-secret"
        init_config(tmp_path, **_llm_kwargs("openai"))
        config_path = tmp_path / ".supermedicine" / "config.yaml"
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        config["llm"]["providers"]["file-provider"] = {
            "api_format": "openai",
            "base_url": "https://file-provider.local.test/v1",
            "api_key": secret,
            "model": "file-model",
        }
        config["llm"]["provider"] = "file-provider"
        config_path.write_text(
            yaml.safe_dump(config, sort_keys=False), encoding="utf-8"
        )

        def reject_home_access():
            raise AssertionError("manual provider path must not read real user home")

        monkeypatch.setattr(Path, "home", reject_home_access)
        policies_dir = tmp_path / ".supermedicine" / "policies"

        kernel = Kernel(
            config_path=config_path,
            plugins_dir="plugins",
            policies_dir=policies_dir,
        )
        context = kernel._llm_runtime_context()

        assert context["configured"] is True
        assert context["provider"] == "file-provider"
        assert context["config"]["api_key"] == "[REDACTED]"
        assert secret not in str(context)

    def test_install_init_default_template_keeps_api_values_empty(self):
        assert DEFAULT_CONFIG["llm"]["provider"] == ""
        assert DEFAULT_CONFIG["llm"]["providers"] == {}

    def test_install_init_writes_anthropic_llm_config(self, tmp_path):
        secret = "anthropic-test-install-secret"

        init_config(
            tmp_path,
            provider="anthropic",
            base_url="https://anthropic.example.test/v1",
            api_key=secret,
            model="claude-test-install",
        )

        config = yaml.safe_load(
            (tmp_path / ".supermedicine" / "config.yaml").read_text(encoding="utf-8")
        )
        anthropic = config["llm"]["providers"]["anthropic"]
        assert config["llm"]["provider"] == "anthropic"
        assert anthropic["base_url"] == "https://anthropic.example.test/v1"
        assert anthropic["api_key"] == secret
        assert anthropic["model"] == "claude-test-install"

    def test_install_init_accepts_custom_openai_compatible_provider(self, tmp_path):
        init_config(
            tmp_path,
            provider="custom-ai",
            base_url="https://custom.example.test/v1",
            api_key="custom-secret",
            model="custom-model",
        )

        config = yaml.safe_load(
            (tmp_path / ".supermedicine" / "config.yaml").read_text(encoding="utf-8")
        )
        custom = config["llm"]["providers"]["custom-ai"]
        assert config["llm"]["provider"] == "custom-ai"
        assert custom["api_format"] == "openai"
        assert custom["api_key_env"] == "CUSTOM-AI_API_KEY"
        assert custom["base_url"] == "https://custom.example.test/v1"
        assert custom["api_key"] == "custom-secret"
        assert custom["model"] == "custom-model"

    def test_install_cli_init_uses_environment_llm_config(self, tmp_path, monkeypatch):
        secret = "sk-env-install-secret"
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("SM_LLM_PROVIDER", "openai")
        monkeypatch.setenv("SM_LLM_BASE_URL", "https://env.example.test/v1")
        monkeypatch.setenv("SM_LLM_API_KEY", secret)
        monkeypatch.setenv("SM_LLM_MODEL", "gpt-env-install")
        monkeypatch.setattr("sys.argv", ["Install.py", "--init"])

        install_main()

        config = yaml.safe_load(
            (tmp_path / ".supermedicine" / "config.yaml").read_text(encoding="utf-8")
        )
        assert config["llm"]["provider"] == "openai"
        assert (
            config["llm"]["providers"]["openai"]["base_url"]
            == "https://env.example.test/v1"
        )
        assert config["llm"]["providers"]["openai"]["api_key"] == secret
        assert config["llm"]["providers"]["openai"]["model"] == "gpt-env-install"

    def test_install_llm_config_merges_existing_config_without_touching_home(
        self, tmp_path, monkeypatch, caplog
    ):
        secret = "sk-test-merge-secret"
        config_dir = tmp_path / ".supermedicine"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text(
            yaml.safe_dump(
                {
                    "project_name": "legacy",
                    "custom": {"keep": True},
                    "llm": {"providers": {}},
                }
            ),
            encoding="utf-8",
        )

        def fail_home_access():
            raise AssertionError(
                "LLM config injection must not read the real user home"
            )

        monkeypatch.setattr(Path, "home", fail_home_access)
        caplog.set_level("INFO", logger="Install")

        write_llm_config(
            tmp_path,
            provider="openai",
            base_url="https://merge.local.test/v1",
            api_key=secret,
            model="gpt-merge",
        )

        config = yaml.safe_load(
            (config_dir / "config.yaml").read_text(encoding="utf-8")
        )
        assert config["project_name"] == "legacy"
        assert config["custom"] == {"keep": True}
        assert config["llm"]["provider"] == "openai"
        assert config["llm"]["providers"]["openai"]["api_key"] == secret
        assert (
            config["llm"]["providers"]["openai"]["base_url"]
            == "https://merge.local.test/v1"
        )
        assert config["llm"]["providers"]["openai"]["model"] == "gpt-merge"
        assert secret not in caplog.text
        assert "<redacted>" in caplog.text

    def test_cli_diagnose_returns_actionable_secret_safe_config_llm_and_audit_snapshot(
        self, tmp_path, monkeypatch
    ):
        secret = "sk-cli-diagnose-secret"
        env_secret = "cli-diagnose-env-api-key-value-not-real"
        init_config(
            tmp_path,
            provider="openai",
            base_url="https://diagnose.example.test/v1",
            api_key=secret,
            model="gpt-diagnose",
        )
        audit_log = tmp_path / ".supermedicine" / "policies" / "audit.jsonl"
        audit_log.write_text("", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("SM_LLM_API_KEY", env_secret)

        result = CLI().diagnose()

        assert result["ok"] is True
        assert result["stage"] == "diagnose"
        assert result["required_runtime"]["harness"]["required"] is True
        assert result["required_runtime"]["rag"]["disable_supported"] is False
        assert result["required_runtime"]["agents"]["mode"] == "single"
        assert result["config"]["exists"] is True
        assert result["config"]["load_error"] == ""
        assert result["llm"]["ok"] is True
        assert result["llm"]["provider"] == "openai"
        assert result["audit"] == {
            "path": str(audit_log),
            "exists": True,
            "writable_parent": True,
        }
        assert "--api-key-env" not in result["commands"]["init"]
        assert (
            "supermedicine init --provider <name> --base-url <url> --model <model>"
            in result["commands"]["init"]
        )
        assert "supermedicine llm switch <provider>" == result["commands"]["llm_switch"]
        assert (
            "python Uninstall.py --dry-run" == result["commands"]["uninstall_dry_run"]
        )
        assert secret not in str(result)
        assert env_secret not in str(result)
        assert result["config"]["config"]["llm-api-key"] == "[REDACTED]"
        assert result["llm"]["providers"]["openai"]["api_key"] == "[REDACTED]"

    def test_cli_diagnose_reports_unconfigured_llm_template_as_actionable_failure(
        self, tmp_path, monkeypatch
    ):
        secret = "sk-unconfigured-diagnose-secret"
        config_dir = tmp_path / ".supermedicine"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text(
            yaml.safe_dump(
                {"llm": {"provider": "", "providers": {}, "note": f"api_key={secret}"}}
            ),
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_path)

        result = CLI().diagnose()

        assert result["ok"] is False
        assert result["stage"] == "diagnose"
        assert result["config"]["exists"] is True
        assert result["config"]["load_error"] == ""
        assert result["llm"]["ok"] is False
        assert result["llm"]["stage"] == "config.llm"
        assert result["llm"]["missing"] == ["provider"]
        assert "Set llm.provider" in result["llm"]["hints"]["provider"]
        assert "api_key" in result["llm"]["hints"]
        assert "base_url" in result["llm"]["hints"]
        assert "model" in result["llm"]["hints"]
        assert (
            "supermedicine init --provider <name> --base-url <url> --model <model>"
            in result["commands"]["init"]
        )
        assert "Traceback" not in str(result)
        assert secret not in str(result)
        assert "[REDACTED]" in str(result)

    def test_init_paths_write_unicode_config_with_explicit_utf8(
        self, tmp_path, monkeypatch
    ):
        """初始化入口写入含中文的配置时不应依赖平台默认编码。"""
        original_write_text = Path.write_text

        def reject_default_encoding_for_unicode(self, data, *args, **kwargs):
            encoding = kwargs.get("encoding")
            if encoding is None and any(ord(char) > 127 for char in data):
                raise UnicodeEncodeError(
                    "charmap", data, 0, len(data), "character maps to <undefined>"
                )
            return original_write_text(self, data, *args, **kwargs)

        monkeypatch.setattr(Path, "write_text", reject_default_encoding_for_unicode)

        install_project = tmp_path / "install"
        cli_project = tmp_path / "cli"
        install_project.mkdir()
        cli_project.mkdir()

        init_config(install_project, **_llm_kwargs())
        CLI().init(cli_project, **_llm_kwargs())

        assert default_policy_path(install_project).read_text(
            encoding="utf-8"
        ) == default_policy_path(cli_project).read_text(encoding="utf-8")

    def test_cli_resolves_params_json_object(self):
        params = _resolve_run_params(
            '{"source_id":"src-1","sources":{"src-1":{"title":"T"}}}', None
        )

        assert params == {"source_id": "src-1", "sources": {"src-1": {"title": "T"}}}

    def test_cli_resolves_params_file_object(self, tmp_path):
        params_file = tmp_path / "params.json"
        params_file.write_text(
            json.dumps({"query": "hypertension", "top_k": 1}), encoding="utf-8"
        )

        params = _resolve_run_params(None, str(params_file))

        assert params == {"query": "hypertension", "top_k": 1}

    def test_cli_rejects_both_params_sources(self, tmp_path):
        params_file = tmp_path / "params.json"
        params_file.write_text("{}", encoding="utf-8")

        with pytest.raises(ValueError, match="cannot be used together"):
            _resolve_run_params("{}", str(params_file))

    def test_cli_rejects_invalid_params_json(self):
        with pytest.raises(ValueError, match="valid JSON"):
            _resolve_run_params("{not-json", None)

    def test_cli_rejects_non_object_params_json(self):
        with pytest.raises(ValueError, match="JSON object"):
            _resolve_run_params("[]", None)

    def test_cli_run_passes_structured_params_to_citation_plugin(self, monkeypatch):
        captured = {}

        class FakeRegistry:
            def discover(self):
                return []

        class FakeCheckpointManager:
            base_dir = "checkpoints"

        class FakeKernel:
            def __init__(self, *args, **kwargs):
                self._config_path = kwargs["config_path"]
                self._plugins_dir = kwargs["plugins_dir"]
                self._policies_dir = kwargs["policies_dir"]
                self.plugin_registry = FakeRegistry()
                self.checkpoint_manager = FakeCheckpointManager()

            def execute_task(self, task, plugin_name=None, action=None, params=None):
                captured.update(
                    {
                        "task": task,
                        "plugin_name": plugin_name,
                        "action": action,
                        "params": params,
                    }
                )
                return {
                    "status": "success",
                    "task": task,
                    "plugin": plugin_name,
                    "action": action,
                    "output": {},
                }

        monkeypatch.setattr("core.kernel.Kernel", FakeKernel)

        params = {
            "source_id": "src-1",
            "sources": {"src-1": {"title": "Cardiovascular Risk Factors"}},
        }
        result = CLI().run(
            "AMA citation task",
            plugin="medical-citation",
            action="standard.citation.ama",
            params=params,
        )

        assert result["status"] == "success"
        assert captured == {
            "task": "AMA citation task",
            "plugin_name": "medical-citation",
            "action": "standard.citation.ama",
            "params": params,
        }

    def test_full_workflow(self, tmp_path):
        """测试完整工作流程：初始化 → 权限检查 → 任务分派 → 检查点"""
        # 1. 初始化内核
        (tmp_path / "config.yaml").write_text(
            yaml.dump({"project": "test"}), encoding="utf-8"
        )
        (tmp_path / "plugins").mkdir()
        (tmp_path / "policies").mkdir()
        shutil.copyfile(
            PermissionEngine.default_policy_path(),
            tmp_path / "policies" / PermissionEngine.DEFAULT_POLICY_FILENAME,
        )
        kernel = Kernel(
            config_path=tmp_path / "config.yaml",
            plugins_dir="plugins",
            policies_dir=tmp_path / "policies",
        )
        assert kernel is not None

        # 2. 权限检查
        policy_data = {
            "agent_id": "analyst",
            "role": "analysis",
            "permissions": {
                "allowed": [{"action": "stats.*", "scope": "data/*"}],
                "denied": [],
            },
        }
        (tmp_path / "policies" / "analyst.yaml").write_text(
            yaml.dump(policy_data), encoding="utf-8"
        )
        engine = PermissionEngine(
            policy_dir=tmp_path / "policies",
            audit_log=tmp_path / "audit.log",
        )
        assert (
            engine.check("analyst", "stats.ttest", "data/clinical")
            == PermissionResult.ALLOWED
        )

        # 3. 任务分派
        orch = Orchestrator()
        agent = MockAgent("analyst", "analysis")
        orch.register_agent(agent)
        result = orch.dispatch(
            "analyst", {"action": "stats.ttest", "data": "data/clinical"}
        )
        assert result["status"] == "success"

        # 4. 检查点
        cp = CheckpointManager(tmp_path / "checkpoints")
        cp.save(task_id="task-001", step=1, state="completed", result=result)
        loaded = cp.load("task-001", step=1)
        assert loaded is not None
        assert loaded["state"] == "completed"

    def test_state_machine_workflow(self):
        """测试状态机工作流"""
        sm = StateMachine(task_id="task-001")
        assert sm.state == TaskState.PLANNING

        sm.transition(TaskState.DISPATCH)
        sm.transition(TaskState.RUNNING)
        sm.transition(TaskState.VERIFYING)
        sm.transition(TaskState.COMPLETED)
        assert sm.state == TaskState.COMPLETED

    def test_stats_analysis(self):
        """测试统计分析流程"""
        # 描述性统计
        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        desc = descriptive(data)
        assert desc["count"] == 10
        assert desc["mean"] == 5.5

        # t 检验
        control = [1, 2, 3, 4, 5]
        treatment = [6, 7, 8, 9, 10]
        t_result = ttest(control, treatment)
        assert t_result["p_value"] < 0.05

        # 回归
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]
        reg = regression(x, y)
        assert reg["slope"] == 2.0
        assert reg["r_squared"] == 1.0

    def test_consort_check(self):
        """测试 CONSORT 规范检查"""
        checklist = get_consort_checklist()

        good_text = """
        本研究是一项随机对照试验。
        摘要采用结构化格式。
        引言描述了科学背景和研究目的。
        方法部分详细描述了试验设计、受试者纳入标准、干预措施、结局指标。
        样本量通过功效分析确定。
        随机化采用计算机生成的随机序列。
        分配隐藏使用密封信封。
        实施由独立的统计师完成。
        采用双盲设计。
        统计方法包括 t 检验和卡方检验。
        结果报告了受试者流程、招募时间、基线数据。
        分析采用意向治疗分析。
        报告了主要结局和辅助分析。
        讨论部分描述了危害和局限性。
        研究结果具有良好的推广性。
        """
        result = checklist.check(good_text)
        assert result["compliance_rate"] > 50  # 至少 50% 符合

    def test_end_to_end_analysis(self, tmp_path):
        """端到端分析流程"""
        # 1. 创建数据
        control_data = [1.2, 1.5, 1.8, 2.0, 2.3, 2.5, 2.8, 3.0]
        treatment_data = [2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0]

        # 2. 描述性统计
        control_desc = descriptive(control_data)
        treatment_desc = descriptive(treatment_data)
        assert control_desc["count"] == 8
        assert treatment_desc["count"] == 8

        # 3. t 检验
        t_result = ttest(control_data, treatment_data)
        assert t_result["p_value"] < 0.05

        # 4. 保存结果
        cp = CheckpointManager(tmp_path / "results")
        cp.save(
            task_id="analysis-001",
            step=1,
            state="completed",
            result={
                "control": control_desc,
                "treatment": treatment_desc,
                "ttest": t_result,
            },
        )

        # 5. 验证保存
        loaded = cp.load("analysis-001", step=1)
        assert loaded is not None
        assert loaded["result"]["ttest"]["p_value"] < 0.05

    def test_kernel_execute_task_success_with_medical_boundary(self):
        kernel = Kernel()
        result = kernel.execute_task("smoke medical task")
        assert result["status"] == "success"
        assert result["plugin"] == "python-stats"
        assert result["action"] == "stats.descriptive"
        assert result["output"]["count"] == 5
        assert result["error"] is None
        assert "contract_version" in result["metadata"]
        assert "not production/clinical medical advice" in result["medical_boundary"]
        assert (
            "no production-grade statistical guarantee" in result["statistics_boundary"]
        )

    def test_kernel_runtime_llm_context_uses_restored_provider_without_secret_leak(
        self, tmp_path
    ):
        config_path = tmp_path / "config.yaml"
        secret = "sk-anthropic-runtime-secret"
        config_path.write_text(
            yaml.safe_dump(
                {
                    "llm": {
                        "provider": "openai",
                        "last_provider": "anthropic",
                        "providers": {
                            "openai": {
                                "api_format": "openai",
                                "base_url": "https://openai.test/v1",
                                "api_key": "sk-openai",
                                "model": "gpt-test",
                            },
                            "anthropic": {
                                "api_format": "anthropic",
                                "base_url": "https://anthropic.test/v1",
                                "api_key": secret,
                                "model": "claude-test",
                            },
                        },
                    }
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        policies_dir = tmp_path / "policies"
        policies_dir.mkdir()
        shutil.copyfile(
            PermissionEngine.default_policy_path(),
            policies_dir / PermissionEngine.DEFAULT_POLICY_FILENAME,
        )

        kernel = Kernel(
            config_path=config_path,
            plugins_dir="plugins",
            policies_dir=policies_dir,
        )
        context = kernel._llm_runtime_context()

        assert context["configured"] is True
        assert context["provider"] == "anthropic"
        assert context["config"]["api_key"] == "[REDACTED]"
        assert secret not in str(context)

    def test_kernel_execute_task_permission_denied(self, tmp_path):
        (tmp_path / "config.yaml").write_text(
            yaml.dump({"project": "test"}), encoding="utf-8"
        )
        policies = tmp_path / "policies"
        policies.mkdir()
        (policies / PermissionEngine.DEFAULT_POLICY_FILENAME).write_text(
            yaml.dump(
                {
                    "agent_id": "alpha",
                    "role": "restricted",
                    "permissions": {
                        "allowed": [],
                        "denied": [{"action": "execute", "scope": "*"}],
                    },
                }
            ),
            encoding="utf-8",
        )
        kernel = Kernel(
            config_path=tmp_path / "config.yaml",
            plugins_dir="plugins",
            policies_dir=policies,
        )
        result = kernel.execute_task("smoke medical task")
        assert result["status"] == "denied"
        assert result["output"] is None
        assert result["error"] == "Permission denied by canonical policy chain."
        assert result["reason"] == "Permission denied by canonical policy chain."

    def test_kernel_execute_task_missing_plugin(self):
        kernel = Kernel()
        result = kernel.execute_task(
            "smoke medical task",
            plugin_name="missing-plugin",
            action="stats.descriptive",
        )
        assert result["status"] == "missing_plugin"
        assert result["plugin"] == "missing-plugin"
        assert result["output"] is None
        assert result["error"] == "Plugin not found: missing-plugin"

    def test_kernel_execute_task_plugin_error(self):
        kernel = Kernel()
        result = kernel.execute_task(
            "smoke medical task",
            plugin_name="python-stats",
            action="stats.unsupported",
        )
        assert result["status"] == "plugin_error"
        assert "Unsupported python-stats action" in result["error"]
        assert result["output"] is None
        assert "medical_boundary" in result["metadata"]

    def test_kernel_execute_task_survival_plugin_path(self):
        kernel = Kernel()
        result = kernel.execute_task("medical survival task")
        assert result["status"] == "success"
        assert result["plugin"] == "r-survival"
        assert result["action"] == "r.survival.km"
        assert "total_subjects" in result["output"]
        assert "not production/clinical medical advice" in result["medical_boundary"]

    def test_kernel_execute_task_invalid_plugin_input_is_structured_error(self):
        kernel = Kernel()
        result = kernel.execute_task(
            "smoke medical task",
            plugin_name="python-stats",
            action="stats.descriptive",
            params={"data": ["not-a-number"]},
        )
        assert result["status"] == "plugin_error"
        assert result["output"] is None
        assert "Invalid python-stats input" in result["error"]

    def test_kernel_executes_rag_interface_manifest_plugin_without_external_service(
        self, tmp_path
    ):
        (tmp_path / "config.yaml").write_text(
            yaml.dump({"project": "test"}), encoding="utf-8"
        )
        policies = tmp_path / "policies"
        policies.mkdir()
        shutil.copyfile(
            PermissionEngine.default_policy_path(),
            policies / PermissionEngine.DEFAULT_POLICY_FILENAME,
        )
        kernel = Kernel(
            config_path=tmp_path / "config.yaml",
            plugins_dir="plugins",
            policies_dir=policies,
        )

        result = kernel.execute_task(
            "rag retrieval task",
            params={
                "query": "hypertension cardiovascular",
                "top_k": 1,
                "storage_dir": str(tmp_path / "rag"),
                "documents": [
                    {
                        "id": "doc-1",
                        "title": "Hypertension review",
                        "source": "kernel-local-rag",
                        "text": "hypertension diabetes cardiovascular risk",
                    }
                ],
            },
        )

        assert result["status"] == "success"
        assert result["plugin"] == "rag-interface"
        assert result["action"] == "rag.query"
        assert result["output"]["items"][0]["source"] == "kernel-local-rag"
        assert result["output"]["errors"] == []

    def test_rag_pubmed_manifest_denies_without_permission_context_before_http(self):
        from plugins.rag.main import execute

        result = execute(
            "rag.query", {"provider": "pubmed", "query": "hypertension", "top_k": 1}
        )

        assert result["status"] == "plugin_error"
        assert result["output"]["status"] == "denied"
        assert result["output"]["errors"][0]["code"] == "permission_engine_required"

    def test_rag_pubmed_manifest_denies_without_agent_identity_before_http(
        self, tmp_path
    ):
        from plugins.rag.main import execute

        policies = tmp_path / "policies"
        policies.mkdir()
        (policies / PermissionEngine.DEFAULT_POLICY_FILENAME).write_text(
            yaml.dump(
                {
                    "agent_id": "alpha",
                    "role": "rag-test",
                    "permissions": {
                        "allowed": [
                            {
                                "action": "rag.external.query",
                                "scope": "https://eutils.ncbi.nlm.nih.gov/*",
                            }
                        ],
                        "denied": [],
                        "hard_limits": {"network_access": True, "external_api": True},
                    },
                }
            ),
            encoding="utf-8",
        )
        engine = PermissionEngine(policies, tmp_path / "audit.jsonl")

        result = execute(
            "rag.query",
            {"provider": "pubmed", "query": "hypertension", "top_k": 1},
            {"permission_engine": engine},
        )

        assert result["status"] == "plugin_error"
        assert result["output"]["status"] == "denied"
        assert result["output"]["errors"][0]["code"] == "agent_identity_required"

    def test_kernel_rag_interface_invalid_input_is_structured_plugin_error(self):
        kernel = Kernel()
        result = kernel.execute_task(
            "rag retrieval task",
            plugin_name="rag-interface",
            action="rag.query",
            params={"query": ""},
        )
        assert result["status"] == "plugin_error"
        assert result["output"] is None
        assert "Invalid rag-interface input" in result["error"]

    def test_kernel_executes_harness_core_manifest_plugin(self, tmp_path):
        checkpoint_step = tmp_path / "checkpoints" / "task-1" / "step-1"
        checkpoint_step.mkdir(parents=True)
        (checkpoint_step / "status.json").write_text(
            json.dumps({"state": "completed"}), encoding="utf-8"
        )
        (tmp_path / "config.yaml").write_text(
            yaml.dump({"project": "test"}), encoding="utf-8"
        )
        policies = tmp_path / "policies"
        policies.mkdir()
        shutil.copyfile(
            PermissionEngine.default_policy_path(),
            policies / PermissionEngine.DEFAULT_POLICY_FILENAME,
        )
        kernel = Kernel(
            config_path=tmp_path / "config.yaml",
            plugins_dir="plugins",
            policies_dir=policies,
        )

        result = kernel.execute_task(
            "harness checkpoint task",
            params={
                "checkpoint_dir": str(tmp_path / "checkpoints"),
                "task_id": "task-1",
            },
        )

        assert result["status"] == "success"
        assert result["plugin"] == "harness-core"
        assert result["action"] == "harness.integration.checkpoint"
        assert result["output"]["complete"] is True

    def test_kernel_harness_core_invalid_input_is_structured_plugin_error(self):
        kernel = Kernel()
        result = kernel.execute_task(
            "harness checkpoint task",
            plugin_name="harness-core",
            action="harness.integration.checkpoint",
            params={"task_id": "task-1"},
        )

        assert result["status"] == "plugin_error"
        assert result["output"] is None
        assert "Invalid harness-core input" in result["error"]

    def test_kernel_executes_medical_citation_manifest_plugin(self):
        kernel = Kernel()
        result = kernel.execute_task(
            "AMA citation task",
            params={
                "source_id": "src-1",
                "sources": {
                    "src-1": {
                        "reference_type": "journal",
                        "authors": ["John Smith", "Jane Doe"],
                        "title": "Cardiovascular Risk Factors",
                        "journal": "JAMA",
                        "year": 2024,
                        "volume": "331",
                        "issue": "5",
                        "pages": "401-410",
                        "doi": "10.1001/jama.2024.1234",
                    }
                },
            },
        )

        assert result["status"] == "success"
        assert result["plugin"] == "medical-citation"
        assert result["action"] == "standard.citation.ama"
        assert "Smith J" in result["output"]["citation"]

    def test_kernel_medical_citation_invalid_input_is_structured_plugin_error(self):
        kernel = Kernel()
        result = kernel.execute_task(
            "AMA citation task",
            plugin_name="medical-citation",
            action="standard.citation.ama",
            params={"source_id": "missing", "sources": {}},
        )

        assert result["status"] == "plugin_error"
        assert result["output"] is None
        assert "Invalid medical-citation input" in result["error"]

    def test_kernel_records_checkpoint_for_plugin_error(self, tmp_path):
        (tmp_path / "config.yaml").write_text(
            yaml.dump({"project": "test"}), encoding="utf-8"
        )
        policies = tmp_path / "policies"
        policies.mkdir()
        shutil.copyfile(
            PermissionEngine.default_policy_path(),
            policies / PermissionEngine.DEFAULT_POLICY_FILENAME,
        )
        kernel = Kernel(
            config_path=tmp_path / "config.yaml",
            plugins_dir="plugins",
            policies_dir=policies,
        )
        result = kernel.execute_task(
            "smoke medical task",
            plugin_name="python-stats",
            action="stats.descriptive",
            params={"data": ["not-a-number"], "api_key": "secret"},
        )
        assert result["status"] == "plugin_error"
        task_dirs = list((tmp_path / "checkpoints").iterdir())
        assert task_dirs
        latest = CheckpointManager(tmp_path / "checkpoints").load_latest(
            task_dirs[0].name
        )
        assert latest["state"] == "failed"
        assert latest["recoverable"] is False
        assert latest["not_recoverable_reason"] == "Plugin returned an error status."
