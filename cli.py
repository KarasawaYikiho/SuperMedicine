#!/usr/bin/env python3
"""SuperMedicine CLI 入口"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from core.kernel import Kernel
from agents.orchestrator import Orchestrator
from agents.base_agent import BaseAgent
from permission.engine import PermissionEngine
from typing import Any


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
        print(f"项目已初始化: {config_dir}")

    def status(self) -> None:
        """显示项目状态"""
        print("SuperMedicine v0.1.0")
        print("=" * 40)

        # 检查配置
        config_dir = Path.cwd() / ".supermedicine"
        if config_dir.exists():
            print("[OK] 项目配置已初始化")
        else:
            print("[FAIL] 项目配置未初始化 (运行 'supermedicine init')")

        # 检查插件
        plugins_dir = Path(__file__).parent / "plugins"
        if plugins_dir.exists():
            plugin_count = len(list(plugins_dir.rglob("plugin.yaml")))
            print(f"[OK] 发现 {plugin_count} 个插件")

        # 检查测试
        tests_dir = Path(__file__).parent / "tests"
        if tests_dir.exists():
            test_count = len(list(tests_dir.glob("test_*.py")))
            print(f"[OK] 发现 {test_count} 个测试模块")

    def test(self) -> None:
        """运行测试"""
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-v"],
            cwd=Path(__file__).parent,
        )
        sys.exit(result.returncode)

    def run(self, task: str) -> None:
        """执行任务"""
        print(f"执行任务: {task}")
        print("注意: 完整的任务执行需要配置 RAG Provider 和 LLM")
        print("当前为 Beta 版本，仅支持基础功能演示")


def main():
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

    args = parser.parse_args()
    cli = CLI()

    if args.command == "init":
        cli.init(Path(args.dir))
    elif args.command == "status":
        cli.status()
    elif args.command == "test":
        cli.test()
    elif args.command == "run":
        cli.run(args.task)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
