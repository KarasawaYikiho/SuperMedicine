#!/Usr/Bin/Env Python3
"""SuperMedicine CLI 入口"""
from __future__ import annotations

import argparse
import json
import logging
import shutil
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
        from permission.engine import PermissionEngine

        config_dir = project_dir / ".supermedicine"
        config_dir.mkdir(exist_ok=True)
        (config_dir / "config.yaml").write_text(
            "# SuperMedicine 配置\nproject_name: supermedicine\nversion: 0.1.0\n"
        )
        (config_dir / "agents").mkdir(exist_ok=True)
        (config_dir / "plugins").mkdir(exist_ok=True)
        policies_dir = config_dir / "policies"
        policies_dir.mkdir(exist_ok=True)
        target_policy = policies_dir / PermissionEngine.DEFAULT_POLICY_FILENAME
        source_policy = PermissionEngine.default_policy_path(Path(__file__).parent)
        if not target_policy.exists():
            shutil.copyfile(source_policy, target_policy)
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
            logger.info("[FAIL] 项目配置未初始化 (运行 'Supermedicine Init')")

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

    def run(self, task: str, verbose: bool = False, plugin: str | None = None, action: str | None = None) -> dict:
        """执行任务 — 真实执行用户任务与医疗插件"""
        from core.kernel import Kernel
        from permission.engine import PermissionEngine

        # 确定项目根目录
        project_dir = Path.cwd()

        logger.info("SuperMedicine v0.1.0 — 任务执行")
        logger.info("任务: %s", task)
        logger.info("=" * 50)

        # 初始化 Kernel（集成 PermissionEngine）
        policies_dir = project_dir / ".supermedicine" / "policies"
        default_policy = policies_dir / PermissionEngine.DEFAULT_POLICY_FILENAME
        if not default_policy.exists():
            raise FileNotFoundError(
                f"默认权限策略不存在: {default_policy}. 请先运行 'supermedicine init' "
                "或恢复仓库中的 .supermedicine/policies/default.yaml。"
            )

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
            logger.info("     Checkpoints: %s", kernel.checkpoint_manager.base_dir)

        # 发现插件
        plugins = kernel.plugin_registry.discover()
        logger.info("[OK] 已发现 %d 个插件", len(plugins))
        if verbose:
            for p in plugins:
                logger.info("     - %s (%s)", p.name, p.type)

        result = kernel.execute_task(task, plugin_name=plugin, action=action)
        if verbose:
            logger.info(
                "[STATE] agent=%s task=%s plugin=%s action=%s status=%s",
                result.get("agent", "alpha"),
                result.get("task", task),
                result.get("plugin"),
                result.get("action"),
                result.get("status"),
            )
        logger.info(json.dumps(result, ensure_ascii=False, indent=2))
        return result


def main():
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    parser = argparse.ArgumentParser(
        prog="supermedicine",
        description="SuperMedicine - 模块化医学科研 Agent 框架",
    )
    subparsers = parser.add_subparsers(dest="command")

    # Init 命令
    init_parser = subparsers.add_parser("init", help="初始化项目")
    init_parser.add_argument("--dir", type=str, default=".", help="项目目录")

    # Status 命令
    subparsers.add_parser("status", help="显示项目状态")

    # Test 命令
    subparsers.add_parser("test", help="运行测试")

    # Run 命令
    run_parser = subparsers.add_parser("run", help="执行任务")
    run_parser.add_argument("task", type=str, help="任务描述")
    run_parser.add_argument("--verbose", action="store_true", help="详细输出")
    run_parser.add_argument("--plugin", type=str, default=None, help="指定插件名称")
    run_parser.add_argument("--action", type=str, default=None, help="指定插件动作")

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
        cli.run(args.task, verbose=verbose, plugin=args.plugin, action=args.action)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
