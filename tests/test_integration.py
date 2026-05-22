"""集成测试 — 端到端科研流程"""
import yaml

from core.kernel import Kernel
from agents.orchestrator import Orchestrator
from agents.base_agent import BaseAgent
from agents.state_machine import StateMachine, TaskState
from agents.checkpoint import CheckpointManager
from permission.engine import PermissionEngine
from permission.policy import PermissionResult
from plugins.tools.python_stats.main import descriptive, ttest, regression
from plugins.standards.medical_writing.checklists import get_consort_checklist
from typing import Any


class MockAgent(BaseAgent):
    """测试用 Agent"""

    def __init__(self, agent_id: str, role: str):
        super().__init__(agent_id, role)
        self.executed = []

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        self.executed.append(task)
        return {"status": "success", "agent": self.agent_id, "task": task}


class TestIntegration:
    """端到端集成测试"""

    def test_full_workflow(self, tmp_path):
        """测试完整工作流程：初始化 → 权限检查 → 任务分派 → 检查点"""
        # 1. 初始化内核
        (tmp_path / "config.yaml").write_text(yaml.dump({"project": "test"}))
        (tmp_path / "plugins").mkdir()
        (tmp_path / "policies").mkdir()
        kernel = Kernel(
            config_path=tmp_path / "config.yaml",
            plugins_dir=tmp_path / "plugins",
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
        (tmp_path / "policies" / "analyst.yaml").write_text(yaml.dump(policy_data))
        engine = PermissionEngine(
            policy_dir=tmp_path / "policies",
            audit_log=tmp_path / "audit.log",
        )
        assert engine.check("analyst", "stats.ttest", "data/clinical") == PermissionResult.ALLOWED

        # 3. 任务分派
        orch = Orchestrator()
        agent = MockAgent("analyst", "analysis")
        orch.register_agent(agent)
        result = orch.dispatch("analyst", {"action": "stats.ttest", "data": "data/clinical"})
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
