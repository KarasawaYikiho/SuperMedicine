# SuperMedicine

![Version](https://img.shields.io/badge/version-Beta0.4.0-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

SuperMedicine is an independent Python framework for medical research assistance.
It combines a microkernel, permission-gated plugin execution, RAG utilities,
medical writing/citation helpers, workspace management, paper import, experience
learning, and a Chinese terminal UI. OpenCode and Claude Code integrations are
optional add-ons; the Python CLI and Kernel are the default supported runtime.

Public/release label: **Beta0.4.0**. Python package fallback version:
**0.4.0b0**.

For detailed setup, see [INSTALL.md](INSTALL.md). For design boundaries, see
[ARCHITECTURE.md](ARCHITECTURE.md). For security and medical-use limits, see
[SECURITY.md](SECURITY.md).

## 中文简介

SuperMedicine 是一个面向医学科研辅助的独立 Python 框架，默认通过本项目的
CLI、Kernel、插件系统和中文 TUI 运行，不依赖 OpenCode、Claude Code 或其他
助手平台。平台适配器仅作为可选扩展。

主要能力：

- 工作区管理、论文导入、经验学习和工具管理。
- RAG 检索、实验指导/日志、Python/R 统计原型接口。
- CONSORT、STROBE、PRISMA、STARD 检查表，以及 AMA/Vancouver 引文格式化。
- P0 权限引擎、审计日志和密钥脱敏诊断。
- LLM Provider 管理，支持 OpenAI 格式、Anthropic 格式、OpenRouter 以及兼容网关。

使用前请配置至少一个完整 LLM Provider（provider、base URL、model 和 API key
来源）。真实密钥应放在环境变量、私有配置或密钥管理器中，不要提交到仓库。

## Feature Summary

- **Standalone Python core** — CLI, Kernel, configuration, plugin discovery, and
  runtime execution work without platform-specific assistant runtimes.
- **Permission-gated execution** — high-risk actions pass through
  `PermissionEngine.check()` and are written to audit logs.
- **LLM provider management** — built-in defaults for OpenAI, Anthropic, and
  OpenRouter plus custom compatible providers by API format.
- **Research workspaces** — explicit workspace ids, copy-only paper import,
  user-confirmed experience records, and local tool templates.
- **Chinese TUI** — Textual-based terminal interface for chat, dashboard,
  workspace, paper, experience, tool, dialog history, LLM, experiment guide, and
  log report screens.
- **Medical research helpers** — RAG, harness monitoring, prototype statistics,
  reporting checklists, and citation formatting.

## Installation

Requirements:

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | >= 3.10 | Required |
| Git | any | Required for cloning |
| pip | >= 21.0 | Required for package install |
| R | >= 4.3 | Optional, for R survival backend |

Quick install:

```bash
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine
pip install -e .
export OPENAI_API_KEY=<OPENAI_API_KEY>
python Install.py --init --provider openai --base-url https://api.openai.com/v1 --model gpt-4o-mini
supermedicine status
```

Use `python Cli.py status` if the `supermedicine` console script is not on PATH.
For virtual environments, development dependencies, optional R support, and
platform-specific notes, see [INSTALL.md](INSTALL.md).

## LLM Provider Configuration

Initialization and LLM-backed tasks require a complete provider configuration:
`provider`, `base_url`, `model`, and either `api_key` or `api_key_env`.
SuperMedicine reports explicit setup or provider errors instead of pretending a
missing provider succeeded.

Supported API formats:

| API Format | Default Base URL | Default Key Env | Default Model |
|------------|------------------|-----------------|---------------|
| `openai` | `https://api.openai.com/v1` | `OPENAI_API_KEY` | `gpt-4o-mini` |
| `anthropic` | `https://api.anthropic.com/v1` | `ANTHROPIC_API_KEY` | `claude-3-5-sonnet-latest` |
| `openrouter` | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` | `anthropic/claude-3.5-sonnet` |

Custom providers such as DeepSeek, 智谱 GLM, local Ollama-compatible endpoints,
or private gateways can be configured with `--provider`, `--base-url`,
`--api-format`, and `--model`.

Example:

```bash
supermedicine llm add deepseek \
  --api-format openai \
  --base-url https://api.deepseek.com/v1 \
  --api-key-env DEEPSEEK_API_KEY \
  --model deepseek-chat \
  --set-current

supermedicine llm list
supermedicine llm show deepseek
supermedicine llm switch deepseek
```

Prefer `--api-key-env` for real credentials. Documentation examples use
placeholders only.

## CLI Reference

All commands can be run as `supermedicine <command>` or `python Cli.py <command>`.

```bash
supermedicine init --provider openai --base-url https://api.openai.com/v1 --model gpt-4o-mini
supermedicine status
supermedicine diagnose
supermedicine run "summarize local context" [--workspace <slug>]
supermedicine tui
```

Workspace, paper, experience, tool, experiment, log, and LLM management commands
use explicit flags and redacted output where appropriate:

```bash
supermedicine workspace init --workspace demo --name "Demo Workspace"
supermedicine paper import ./paper.pdf --workspace demo --title "Paper Title"
supermedicine experience suggest --workspace demo --summary "Keep prompts short"
supermedicine tool init --workspace demo
supermedicine experiment start --protocol wb --session-id wb-demo
supermedicine log list
supermedicine llm list
```

Workspace-scoped CLI commands do not silently reuse the TUI's recent workspace.
CLI commands always require explicit `--workspace`.

## TUI (Terminal UI)

Launch the Chinese terminal UI with:

```bash
supermedicine tui
supermedicine tui --dry-run
```

Navigation keys:

| Key | Screen |
|-----|--------|
| `1` | Chat / 对话 |
| `2` | Dashboard / 仪表盘 |
| `3` | Workspace / 工作区管理 |
| `4` | Paper / 论文管理 |
| `5` | Experience / 经验学习 |
| `6` | Tool / 工具管理 |
| `7` | Dialog / 对话历史 |
| `8` | LLM / LLM 管理 |
| `9` | Experiment Guide / 实验指导器 |
| `0` | Log Report / Log 报告 |
| `f` | Maximize/minimize the focused widget |

Use `Tab`/`Shift+Tab` for focus movement, `Enter` to submit or activate, `?` for
help, and `q` to quit. API-key fields are password-style, but ordinary chat input
is not a secret-entry control.

Status cues include workspace count and current focus on the left, plugin count,
LLM status, and task running state in the center, and current view/version on the
right. **LLM 状态** shows provider readiness without exposing API keys, and
**任务运行状态** appears as `任务空闲` or `任务执行中` for long-running work.

## Platform Adapters

Platform adapters live under `adapters/` and are optional:

| Capability | Standalone Core | OpenCode Add-on | Claude Code Add-on |
|------------|----------------|-----------------|-------------------|
| CLI init/status/run | Supported | Can wrap metadata | Minimal adapter path |
| Permission engine | Supported | Used for adapter operations | Used before tool execution |
| Plugin discovery/execution | Supported | Metadata integration | Not native |
| Native platform tool calls | Not required | Declared tool mappings | `claude.invoke` only |
| Native subagent runtime | Not applicable | Not launched by adapter alone | Not implemented |

## Architecture Overview

```text
CLI / TUI / Optional Adapters
        |
        v
Kernel: ConfigCenter + EventBus + PluginRegistry + SessionManager + PermissionEngine
        |
        +--> Agents and orchestration state machine
        +--> Plugins: RAG, harness, tools, standards
        +--> Workspace layer: papers, experience, local tool assets
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the root architecture reference.

## Diagnostics and Troubleshooting

Use `supermedicine diagnose` for secret-safe status, provider readiness, audit log
path checks, and repair suggestions.

Common fixes:

| Issue | Fix |
|-------|-----|
| `No module named 'yaml'` | Install package dependencies with `pip install -e .` or install `pyyaml`. |
| `supermedicine` command not found | Add the Python Scripts directory to PATH or use `python Cli.py`. |
| Initialization fails with missing LLM fields | Provide provider, base URL, model, and API key source. |
| LLM call fails | Treat it as a real provider/configuration error; run diagnostics and inspect redacted fields. |
| TUI launch issue | Run `supermedicine tui --dry-run`, then restart the terminal if needed. |

## Local Quality Gate

For development and release checks, use the project quality commands documented
by the maintainers. A typical local gate includes linting, packaging smoke checks,
and the test suite, for example:

```bash
pip install -e ".[dev]"
ruff check --select=E,F,W --ignore=E501 .
python -m pip wheel . --no-deps --wheel-dir .pytest-tmp/wheel-smoke
pytest tests/ -v
```

## Safety and Medical-Use Boundaries

- SuperMedicine is research-support software, not a clinical decision system.
- Plugin outputs, citations, RAG results, metadata enrichment, and prototype
  statistics require qualified human review.
- Paper import is copy-only and does not upload source files by default.
- Experience learning stores user-confirmed summaries, not raw conversations.
- Real credentials belong in environment variables, private local config, secret
  managers, or CI secrets, not committed files.

See [SECURITY.md](SECURITY.md) for the full policy.

## License

MIT License — see [LICENSE](LICENSE) for details.
