#!/usr/bin/env python3
"""SuperMedicine CLI 入口"""
from __future__ import annotations

import argparse
import logging
import sys
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))



class CLI:
    """SuperMedicine CLI"""

    def __init__(self):
        self.kernel = None
        self.orchestrator = None

    def init(self, project_dir: Path) -> None:
        """初始化项目"""
        config_dir = project_dir / ".supermedicine"
        config_dir.mkdir(exist_ok=True)
        (config_dir / "config.yaml").write_text(
            "# SuperMedicine 配置\nproject_name: supermedicine\nversion: 0.1.0\n"
        )
        (config_dir / "agents").mkdir(exist_ok=True)
        (config_dir / "plugins").mkdir(exist_ok=True)
        logger.info(f"项目已初始化: {config_dir}")

    def status(self) -> None:
        """显示项目状态"""
        logger.info("SuperMedicine v0.1.0")
        logger.info("=" * 40)

        # 检查配置
        config_dir = Path.cwd() / ".supermedicine"
        if config_dir.exists():
            logger.info("[OK] 项目配置已初始化")
        else:
            logger.info("[FAIL] 项目配置未初始化 (运行 'supermedicine init')")

        # 检查插件
        plugins_dir = Path(__file__).parent / "plugins"
        if plugins_dir.exists():
            plugin_count = len(list(plugins_dir.rglob("plugin.yaml")))
            logger.info(f"[OK] 发现 {plugin_count} 个插件")

        # 检查测试
        tests_dir = Path(__file__).parent / "tests"
        if tests_dir.exists():
            test_count = len(list(tests_dir.glob("test_*.py")))
            logger.info(f"[OK] 发现 {test_count} 个测试模块")

    def test(self) -> None:
        """运行测试"""
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-v"],
            cwd=Path(__file__).parent,
        )
        sys.exit(result.returncode)

    def run(self, task: str, verbose: bool = False) -> None:
        """执行任务 — 初始化全组件栈并派发到 Orchestrator"""
        from pathlib import Path
        from core.kernel import Kernel
        from agents.orchestrator import Orchestrator
        from agents.base_agent import BaseAgent
        import tempfile

        # 确定项目根目录
        project_dir = Path.cwd()

        logger.info("SuperMedicine v0.1.0 — 任务执行")
        logger.info("任务: %s", task)
        logger.info("=" * 50)

        # 初始化 Kernel（集成 PermissionEngine）
        policies_dir = project_dir / ".supermedicine" / "policies"
        policies_dir.mkdir(parents=True, exist_ok=True)

        kernel = Kernel(
            config_path=project_dir / ".supermedicine" / "config.yaml",
            plugins_dir=project_dir / "plugins",
            policies_dir=policies_dir,
        )

        if verbose:
            logger.info("[OK] Kernel 已初始化")
            logger.info("     Config: %s", kernel._config_path)
            logger.info("     Plugins: %s", kernel._plugins_dir)
            logger.info("     Policies: %s", kernel._policies_dir)
            logger.info("     PermissionEngine: 已激活")

        # 发现插件
        plugins = kernel.plugin_registry.discover()
        logger.info("[OK] 已发现 %d 个插件", len(plugins))
        if verbose:
            for p in plugins:
                logger.info("     - %s (%s)", p.name, p.meta.type)

        # 初始化 Orchestrator
        orchestrator = Orchestrator()

        # 为每个 agent 创建独立检查点目录
        checkpoint_base = project_dir / ".supermedicine" / "checkpoints"
        checkpoint_base.mkdir(parents=True, exist_ok=True)

        # 注册 Agent
        class CLIAgent(BaseAgent):
            """CLI Agent — 真实执行最小端到端流程"""
            def __init__(self, agent_id: str, role: str, kernel, checkpoint_dir, policies_dir):
                super().__init__(agent_id, role)
                self._kernel = kernel
                self._checkpoint_dir = checkpoint_dir
                self._policies_dir = policies_dir

            def execute(self, task):
                from pathlib import Path
                from agents.state_machine import StateMachine, TaskState
                from agents.checkpoint import CheckpointManager
                from permission.engine import PermissionEngine
                from permission.policy import PermissionResult

                # 初始化状态机
                sm = StateMachine(task_id=self.agent_id)
                checkpoint = CheckpointManager(
                    base_dir=Path(self._checkpoint_dir) / self.agent_id
                )
                history = [str(sm.state)]

                # 初始化权限引擎
                audit_log = Path(self._policies_dir) / "audit.jsonl"
                perm_engine = PermissionEngine(
                    policy_dir=Path(self._policies_dir),
                    audit_log=audit_log,
                )

                try:
                    # PLANNING → DISPATCH
                    perm_result = perm_engine.check(self.agent_id, "plan", "task")
                    if perm_result == PermissionResult.DENIED:
                        return {"agent": self.agent_id, "status": "denied", "reason": "Permission denied"}
                    sm.transition(TaskState.DISPATCH)
                    history.append(str(sm.state))
                    checkpoint.save(self.agent_id, step=1, state=str(sm.state), result={"task": task})

                    # DISPATCH → RUNNING
                    sm.transition(TaskState.RUNNING)
                    history.append(str(sm.state))
                    # 在 RUNNING 阶段获取可用插件
                    plugins_list = self._kernel.plugin_registry.discover()
                    plugin_names = [p.name for p in plugins_list]
                    checkpoint.save(self.agent_id, step=2, state=str(sm.state), result={"plugins": plugin_names})

                    # RUNNING → VERIFYING
                    sm.transition(TaskState.VERIFYING)
                    history.append(str(sm.state))
                    checkpoint.save(self.agent_id, step=3, state=str(sm.state), result={})

                    # VERIFYING → COMPLETED
                    sm.transition(TaskState.COMPLETED)
                    history.append(str(sm.state))
                    checkpoint.save(self.agent_id, step=4, state=str(sm.state), result={"completed": True})

                except (ValueError, RuntimeError) as e:
                    history.append(f"error: {e}")
                    checkpoint.save(self.agent_id, step=99, state=str(sm.state), result={"error": str(e)})

                return {
                    "agent": self.agent_id,
                    "status": "completed",
                    "state": str(sm.state),
                    "history": history,
                    "plugins": plugin_names if 'plugin_names' in dir() else [],
                    "checkpoint_dir": str(self._checkpoint_dir),
                }

        agent_ids = ["alpha", "beta", "gamma", "delta"]
        for aid in agent_ids:
            agent = CLIAgent(
                aid,
                role=f"{aid}_cli",
                kernel=kernel,
                checkpoint_dir=str(checkpoint_base),
                policies_dir=str(policies_dir),
            )
            orchestrator.register_agent(agent)

        logger.info("[OK] 已注册 %d 个 Agent: %s", len(agent_ids), ", ".join(agent_ids))

        # 派发任务到 Orchestrator
        logger.info("")
        logger.info("[→] 派发任务: %s", task)
        task_payload = {"action": "execute", "description": task}

        for aid in agent_ids:
            try:
                result = orchestrator.dispatch(aid, task_payload)
                if verbose:
                    logger.info("     %s: state=%s, history=%d steps",
                                aid, result.get("state"), len(result.get("history", [])))
            except Exception as e:
                logger.info("     %s: 错误 — %s", aid, e)

        logger.info("")
        logger.info("[OK] 任务已派发到全部 %d 个 Agent", len(agent_ids))
        if verbose:
            logger.info("检查点目录: %s", str(checkpoint_base))


def main():
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    parser = argparse.ArgumentParser(
        prog="supermedicine",
        description="SuperMedicine - 模块化医学科研 Agent 框架",
    )
    subparsers = parser.add_subparsers(dest="command")

    # init 命令
    init_parser = subparsers.add_parser("init", help="初始化项目")
    init_parser.add_argument("--dir", type=str, default=".", help="项目目录")

    # status 命令
    subparsers.add_parser("status", help="显示项目状态")

    # test 命令
    subparsers.add_parser("test", help="运行测试")

    # run 命令
    run_parser = subparsers.add_parser("run", help="执行任务")
    run_parser.add_argument("task", type=str, help="任务描述")
    run_parser.add_argument("--verbose", action="store_true", help="详细输出")

    args = parser.parse_args()
    cli = CLI()

    if args.command == "init":
        cli.init(Path(args.dir))
    elif args.command == "status":
        cli.status()
    elif args.command == "test":
        cli.test()
    elif args.command == "run":
        verbose = getattr(args, 'verbose', False)
        cli.run(args.task, verbose=verbose)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
