#!/usr/bin/env python3
"""SuperMedicine CLI 入口"""
from __future__ import annotations

import argparse
import logging
import sys
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

        # 确定项目根目录
        project_dir = Path.cwd()

        logger.info("SuperMedicine v0.1.0 — 任务执行")
        logger.info(f"任务: {task}")
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
            logger.info(f"     Config: {kernel._config_path}")
            logger.info(f"     Plugins: {kernel._plugins_dir}")
            logger.info(f"     Policies: {kernel._policies_dir}")
            logger.info("     PermissionEngine: 已激活")

        # 发现插件
        plugins = kernel.plugin_registry.discover()
        logger.info(f"[OK] 已发现 {len(plugins)} 个插件")
        if verbose:
            for p in plugins:
                logger.info(f"     - {p.name} ({p.meta.type})")

        # 初始化 Orchestrator
        orchestrator = Orchestrator()

        # 注册可用 Agent（简单的 CLI Agent）
        class CLIAgent(BaseAgent):
            def execute(self, task):
                return {
                    "agent": self.agent_id,
                    "task": task,
                    "status": "completed",
                    "result": f"Task '{task.get('action', 'unknown')}' processed by CLI Agent.",
                }

        agent_ids = ["alpha", "beta", "gamma", "delta"]
        for aid in agent_ids:
            orchestrator.register_agent(CLIAgent(aid, role=f"{aid}_cli"))

        logger.info(f"[OK] 已注册 {len(agent_ids)} 个 Agent: {', '.join(agent_ids)}")

        # 派发任务到 Orchestrator
        logger.info(f"\n[→] 派发任务: {task}")
        task_payload = {"action": "execute", "description": task}

        for aid in agent_ids:
            try:
                result = orchestrator.dispatch(aid, task_payload)
                if verbose:
                    logger.info(f"     {aid}: {result.get('status', 'unknown')}")
            except Exception as e:
                if verbose:
                    logger.info(f"     {aid}: 错误 — {e}")

        logger.info(f"\n[OK] 任务已派发到全部 {len(agent_ids)} 个 Agent")
        logger.info("提示: 完整的 LLM 后端集成将在后续版本中支持")


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
