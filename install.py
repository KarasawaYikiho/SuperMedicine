#!/usr/bin/env python3
"""SuperMedicine 安装脚本"""
import argparse
from pathlib import Path

def detect_platform() -> str:
    if Path.home().joinpath(".claude").exists(): return "claude-code"
    if Path.home().joinpath(".config", "opencode").exists(): return "opencode"
    return "standalone"

def init_config(project_dir: Path) -> None:
    config_dir = project_dir / ".supermedicine"
    config_dir.mkdir(exist_ok=True)
    config_file = config_dir / "config.yaml"
    if not config_file.exists():
        config_file.write_text("# SuperMedicine 配置\nproject_name: supermedicine\nversion: 0.1.0\n")
    (config_dir / "agents").mkdir(exist_ok=True)
    (config_dir / "plugins").mkdir(exist_ok=True)
    print(f"Configuration initialized at {config_dir}")

def main():
    parser = argparse.ArgumentParser(description="SuperMedicine installer")
    parser.add_argument("--detect", action="store_true", help="Detect platform")
    parser.add_argument("--init", action="store_true", help="Initialize config")
    args = parser.parse_args()
    if args.detect: print(f"Detected platform: {detect_platform()}"); return
    if args.init: init_config(Path.cwd()); return
    parser.print_help()

if __name__ == "__main__": main()
