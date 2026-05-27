#!/usr/bin/env python3
"""SuperMedicine standalone installer.

The default ``--init`` path is intentionally core-only: it creates the
``.supermedicine`` project configuration and canonical permission policy
without inspecting OpenCode, Claude Code, or any other assistant-platform
runtime/config directories. Platform discovery remains available only through
the explicit optional ``--detect`` command.
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from permission.policy import ensure_default_policy

logger = logging.getLogger(__name__)

def detect_platform() -> str:
    """Optionally detect installed assistant-platform add-ons.

    This function is not called by ``init_config`` or by module import. Keeping
    it behind the explicit CLI flag preserves standalone initialization on
    hosts with no OpenCode/Claude Code assumptions.
    """
    if Path.home().joinpath(".claude").exists():
        return "claude-code"
    if Path.home().joinpath(".config", "opencode").exists():
        return "opencode"
    return "standalone"

def init_config(project_dir: Path) -> None:
    """Initialize standalone SuperMedicine project configuration only."""
    config_dir = project_dir / ".supermedicine"
    config_dir.mkdir(exist_ok=True)
    config_file = config_dir / "config.yaml"
    if not config_file.exists():
        config_file.write_text(
            "# SuperMedicine 配置\nproject_name: supermedicine\nversion: Beta0.3.0\n",
            encoding="utf-8",
        )
    (config_dir / "agents").mkdir(exist_ok=True)
    (config_dir / "plugins").mkdir(exist_ok=True)
    ensure_default_policy(project_dir, Path(__file__).parent)
    logger.info("初始化完成。")
    logger.info("")
    logger.info("如果 'supermedicine' 命令不可用，请将以下目录添加到系统 PATH：")
    logger.info("  Windows:  %APPDATA%\\Python\\Python<版本>\\Scripts")
    logger.info("  Linux/macOS: ~/.local/bin")
    logger.info("或者使用 'python Cli.py' 代替 'supermedicine' 命令。")

def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    parser = argparse.ArgumentParser(description="SuperMedicine standalone installer")
    parser.add_argument("--detect", action="store_true", help="Optionally detect OpenCode/Claude Code add-on presence")
    parser.add_argument("--init", action="store_true", help="Initialize core SuperMedicine config only")
    args = parser.parse_args()
    if args.detect:
        logger.info("Detected platform: %s", detect_platform())
        return
    if args.init:
        init_config(Path.cwd())
        return
    parser.print_help()

if __name__ == "__main__":
    main()
