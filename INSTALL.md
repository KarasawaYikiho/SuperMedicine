# SuperMedicine 安装指南

## 快速安装

```bash
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine
pip install -e ".[dev]"
python install.py --init
```

## Agent 自动安装

Agent 可以读取 `install.json` 自动完成安装。

## 平台适配

### Claude Code
将 `adapters/claude-code/` 目录复制到 `~/.claude/skills/supermedicine/`

### OpenCode
将 `adapters/opencode/plugin.json` 复制到 OpenCode 插件目录
