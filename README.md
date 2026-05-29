# SuperMedicine

![Version](https://img.shields.io/badge/version-Beta0.3.6-blue)
![CI](https://github.com/KarasawaYikiho/SuperMedicine/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Independent Python medical research agent framework with RAG, plugin execution,
and permission-gated orchestration. SuperMedicine runs as a standalone Python
package by default; OpenCode, Claude Code, and similar assistant platforms are
optional add-on adapters around the core, not core runtime requirements.

**Use this README for orientation and quick-start commands.** For full setup
detail, see [INSTALL.md](INSTALL.md); for system design, see
[ARCHITECTURE.md](ARCHITECTURE.md); for security boundaries, see
[SECURITY.md](SECURITY.md).

## Feature Summary

- **Modular Architecture** — Microkernel plus multi-agent orchestration with a plugin system.
- **P0 Permission Engine** — Runtime permission constraints with prompt-context safety guidance.
- **Plugin Ecosystem** — RAG retrieval, Harness monitoring, Python/R statistics, and medical writing standards.
- **Interactive TUI** — Chinese terminal UI with sidebar navigation, LLM management, and keyboard shortcuts.
- **Workspace System** — Explicit workspace management with paper import, experience learning, and tool management.
- **Standalone Core by Default** — No OpenCode, Claude Code, or platform runtime is required.
- **Optional Platform Add-ons** — OpenCode and Claude Code adapters support platform-specific workflows.
- **Medical Standards** — CONSORT, STROBE, PRISMA, and STARD checklists plus AMA/Vancouver citation formatting.

---

## Table Of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [LLM Provider Configuration](#llm-provider-configuration)
- [CLI Reference](#cli-reference)
- [TUI (Terminal UI)](#tui-terminal-ui)
- [Platform Adapters](#platform-adapters)
- [Architecture](#architecture)
- [Running Tests](#running-tests)
- [Troubleshooting](#troubleshooting)
- [Safety And Security](#safety-and-security)
- [License](#license)

---

## Installation

### Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | >= 3.10 | Required (3.10, 3.11, 3.12, 3.13 tested) |
| Git | any | For cloning the repository |
| pip | >= 21.0 | For package installation |
| R | >= 4.3 | Optional, for survival analysis tools |

OpenCode, Claude Code, and other assistant platforms are **not** prerequisites.

### Quick Install (All Platforms)

```bash
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine
pip install -e .       # use python3 on macOS/Linux
supermedicine status   # or: python Cli.py status
```

For virtual environment setup, PATH configuration, and optional dependencies,
see [INSTALL.md](INSTALL.md).

---

## Quick Start

```bash
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine
pip install -e .
export OPENAI_API_KEY=<OPENAI_API_KEY>
python Install.py --init --provider openai --base-url https://api.openai.com/v1 --model gpt-4o-mini
supermedicine status
supermedicine tui
```

See [INSTALL.md](INSTALL.md) for detailed provider configuration, virtual
environment setup, and platform-specific instructions.

---

## LLM Provider Configuration

SuperMedicine supports multiple LLM API formats through the standalone Python
core. `openai` (Chat Completions) and `anthropic` (Messages) are wire protocols,
not vendor names — any provider can use either format. OpenRouter is also
supported as a built-in gateway provider. OpenCode and Claude Code are optional
platform surfaces; they are not required.

### Supported API Formats

| API Format | Protocol | Default BaseURL | Default Key Env | Default Model | Compatible Providers |
|------------|----------|-----------------|-----------------|---------------|---------------------|
| `openai` | OpenAI Chat Completions | `https://api.openai.com/v1` | `OPENAI_API_KEY` | `gpt-4o-mini` | OpenAI, DeepSeek, Zhipu GLM, Ollama, etc. |
| `anthropic` | Anthropic Messages | `https://api.anthropic.com/v1` | `ANTHROPIC_API_KEY` | `claude-3-5-sonnet-latest` | Anthropic |
| `openrouter` | OpenRouter Gateway (OpenAI format) | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` | `anthropic/claude-3.5-sonnet` | OpenRouter (multi-model gateway) |

Custom endpoints are supported with `--base-url` or `SM_LLM_BASE_URL`.

### Custom Providers (Any Name)

SuperMedicine accepts **any provider name**. The `api_format` field determines
which HTTP client is used, not the provider name itself. Built-in defaults exist
for `openai`, `anthropic`, and `openrouter`; all other names default to OpenAI
chat-completions format unless overridden with `--api-format`.

| Example Provider | BaseURL | API Format | Model Example |
|------------------|---------|------------|---------------|
| DeepSeek | `https://api.deepseek.com/v1` | `openai` (auto) | `deepseek-chat` |
| 智谱 GLM | `https://open.bigmodel.cn/api/paas/v4` | `openai` (auto) | `glm-4-flash` |
| Ollama (local) | `http://localhost:11434/v1` | `openai` (auto) | `llama3` |
| Any Anthropic-compatible | Custom URL | `anthropic` (explicit) | Custom model |

```bash
# DeepSeek example
python Install.py --init --provider deepseek \
  --base-url https://api.deepseek.com/v1 \
  --api-key <DEEPSEEK_API_KEY> \
  --model deepseek-chat

# 智谱 GLM example
python Install.py --init --provider zhipu \
  --base-url https://open.bigmodel.cn/api/paas/v4 \
  --api-key <ZHIPU_API_KEY> \
  --model glm-4-flash

# Local Ollama example (no API key required)
python Install.py --init --provider ollama \
  --base-url http://localhost:11434/v1 \
  --api-key ollama \
  --model llama3

# OpenRouter example (uses OPENROUTER_API_KEY by default)
export OPENROUTER_API_KEY=<OPENROUTER_API_KEY>
python Install.py --init --provider openrouter
```

Provider names containing `anthropic` or `claude` auto-infer the Anthropic API
format; all others default to OpenAI chat-completions. Override with
`--api-format` or `api_format` in `.supermedicine/config.yaml`.

### First-Run Requirement

LLM-backed tasks require one complete provider (`base_url`, `api_key` or
`api_key_env`, and `model`). See [INSTALL.md](INSTALL.md) for runtime
validation details and programmatic client creation examples.

### Configure By Editing The File

Edit `.supermedicine/config.yaml` directly; see [INSTALL.md](INSTALL.md#3b-configure-by-editing-supermedicineconfigyaml) for YAML examples.

### Configure With The CLI

Use `supermedicine llm add/switch/list`; see [INSTALL.md](INSTALL.md#3a-add-providers-after-initialization) for CLI examples.

### Configure In The TUI

Launch `supermedicine tui` and open **LLM 管理**; see [INSTALL.md](INSTALL.md#3c-configure-in-the-tui) for details.

### Switching And Startup Restore

Use `supermedicine llm switch <provider>`; see [INSTALL.md](INSTALL.md#3a-add-providers-after-initialization) for details.

### Environment Variables And Secret Safety

Use `SM_LLM_*` and provider-specific env vars; see [INSTALL.md](INSTALL.md) and [SECURITY.md](SECURITY.md) for the full list.

---

## CLI Reference

All commands are available via `supermedicine <command>` or `python Cli.py <command>`.

### Core Commands

```bash
supermedicine init --provider openai --base-url https://api.openai.com/v1 --model gpt-4o-mini
                                      # Initialize project configuration
supermedicine status                  # Show project status (version, plugins, modules)
supermedicine test                    # Run the test suite
supermedicine run TASK [--workspace]  # Execute a task through the Kernel and plugins
supermedicine run TASK --plugin NAME  # Execute via a specific plugin
supermedicine run TASK --action NAME  # Execute a specific plugin action
supermedicine run TASK --params-json '{"key": "value"}'  # Pass structured parameters
supermedicine run TASK --verbose      # Detailed output
```

### Workspace Commands

```bash
supermedicine workspace init --workspace <slug> [--name "Display Name"]
supermedicine workspace list
supermedicine workspace show --workspace <slug>
supermedicine workspace delete --workspace <slug> --confirm <slug>
```

Workspaces live under `workspaces/<id>` (lowercase slug, letters/digits/hyphens).
CLI commands never infer the last TUI workspace; every workspace-scoped action
requires `--workspace <id>`.

### Paper Commands

```bash
supermedicine paper import ./paper.pdf --workspace <slug> --title "Paper Title"
supermedicine paper import ./paper.pdf --workspace <slug> --doi "10.xxx/yyy"
supermedicine paper import ./paper.pdf --workspace <slug> --tag "oncology" --tag "RCT"
supermedicine paper list --workspace <slug>
supermedicine paper show <paper-id> --workspace <slug>
supermedicine paper edit <paper-id> --workspace <slug> --title "New Title"
supermedicine paper enrich <paper-id> --workspace <slug> --confirm-enrich
```

Paper imports are copy-only: the source file is never moved or uploaded.
Papers are deduplicated by SHA-256 and by normalized DOI/PMID.

### Experience Commands

```bash
supermedicine experience suggest --workspace <slug> --summary "Keep prompts short"
supermedicine experience add --workspace <slug> --scope workspace \
  --title "Prompt Strategy" --summary "Keep prompts short" --confirm
supermedicine experience list --workspace <slug>
supermedicine experience list --workspace <slug> --include-general
supermedicine experience view <record-id> --workspace <slug>
supermedicine experience edit <record-id> --workspace <slug> --scope workspace \
  --title "Updated Title"
supermedicine experience delete <record-id> --workspace <slug> --scope workspace \
  --confirm <record-id>
supermedicine experience export --workspace <slug> --format json
supermedicine experience export --workspace <slug> --format md --output experience.md
```

Experience learning is enabled by default. Raw conversations are **not** stored;
only user-confirmed summaries are persisted.

### Tool Commands

```bash
supermedicine tool init --workspace <slug>
supermedicine tool add --workspace <slug> --language python --tool heatmap
supermedicine tool add --workspace <slug> --language r --tool umap
supermedicine tool list --workspace <slug>
supermedicine tool list --workspace <slug> --language python
supermedicine tool show --workspace <slug> --language python --tool heatmap
supermedicine tool run --workspace <slug> --language python --tool heatmap --dry-run
supermedicine tool run --workspace <slug> --language python --tool heatmap \
  --input data.csv --output results/
```

### TUI Command

```bash
supermedicine tui              # Launch interactive TUI
supermedicine tui --dry-run    # Show TUI status without launching
```

### LLM Commands

```bash
supermedicine llm add openai --api-format openai \
  --base-url https://api.openai.com/v1 \
  --api-key-env OPENAI_API_KEY \
  --model gpt-4o-mini \
  --set-current

supermedicine llm list              # List providers; secrets are redacted
supermedicine llm show [provider]   # Show current or named provider; redacted
supermedicine llm switch anthropic  # Validate, switch, and persist default/last
```

For real credentials, prefer `--api-key-env` over `--api-key` so command history
and local YAML do not receive plaintext secrets.

---

## TUI (Terminal UI)

SuperMedicine includes a full interactive Chinese terminal UI built with
[Textual](https://textual.textualize.io/). Launch with `supermedicine tui`.

### Interface Structure

The TUI is organized as a persistent left sidebar plus a swappable main content
area and bottom status bar:

- **Sidebar** — numbered navigation entries `1` through `8` and a compact global
  shortcut hint.
- **Main area** — current view title, the selected management/workbench screen,
  and a shared input bar for chat-style commands.
- **Status bar** — workspace count and current focus on the left, plugin count,
  LLM status, and task running state in the center, and current view/version on
  the right.

### Navigation And Shortcuts

| Key | Action |
|-----|--------|
| `1` | Chat (对话) |
| `2` | Dashboard (仪表盘) |
| `3` | Workspace (工作区管理) |
| `4` | Paper (论文管理) |
| `5` | Experience (经验学习) |
| `6` | Tool (工具管理) |
| `7` | Dialog (对话历史) |
| `8` | LLM (LLM 管理) |
| `↑` / `↓` | Navigate sidebar |
| `Tab` | Move focus forward between input, buttons, lists, and tables |
| `Shift+Tab` | Move focus backward between focusable widgets |
| `Enter` | Submit the input when focused on the prompt; activate the focused button/list item elsewhere |
| `f` | Maximize/Minimize focused widget |
| `Esc` | Exit maximize mode |
| `?` | Show help |
| `q` | Quit |

### Screens

| Screen | Description |
|--------|-------------|
| **Chat** | Interactive conversation with the AI agent |
| **Dashboard** | System status, workspace count, plugin count, quick actions |
| **Workspace** | Create, select, delete workspaces; view workspace details |
| **Paper** | Import papers, view/edit metadata, run enrichment |
| **Experience** | Suggest, confirm, list, edit, delete, export experience records |
| **Tool** | Initialize tools, add templates, list, run |
| **LLM** | Add providers, switch current default, inspect redacted readiness state |
| **Dialog** | View session dialog history (read-only) |

### Status And Safety Cues

- **LLM 状态** shows provider readiness without exposing API keys.
- **任务运行状态** appears as `任务空闲` or `任务执行中` for long-running work.
- **刷新** buttons on each screen reload lists from shared backend controllers.
- **危险操作** require explicit confirmation before irreversible work proceeds.

### TUI vs CLI

- TUI recent selection is workspace/session state and does **not** alter CLI defaults.
- CLI commands always require explicit `--workspace` — they never read TUI state.
- TUI and CLI share the same backend controllers and data.
- The TUI is part of the standalone Python package; platform adapters are optional.

---

## Platform Adapters

SuperMedicine's default model is **core independent + platform add-ons**. The
standalone Python core is the default supported path; OpenCode and Claude Code
are optional adapters. See [INSTALL.md](INSTALL.md) for detailed setup steps.

### OpenCode Add-On

The OpenCode adapter (`adapters/opencode/`) provides plugin metadata, skill
documents, agent definitions, and tool mapping for `bash`, `read`, `write`,
`edit`, `glob`, `grep`, `skill`, `task`. See [INSTALL.md](INSTALL.md) for
setup details.

### Claude Code Add-On

The Claude Code adapter (`adapters/claude_code/`) provides capability reporting,
runtime status checking, and permission-checked `claude --print` invocation.
See [INSTALL.md](INSTALL.md) for setup details.

### Capability Matrix

| Capability | Standalone Core | OpenCode Add-on | Claude Code Add-on |
|------------|----------------|-----------------|-------------------|
| CLI `init`/`status`/`run` | Supported | Can wrap/adapt | Minimal adapter path |
| PermissionEngine | Supported | Used for adapter ops | Used before tool execution |
| Plugin discovery/execution | Supported | Metadata integration | Not native |
| RAG/harness/medical standards | Supported | Skill docs available | Conceptual docs only |
| Native platform tool calls | Not required | 8 tools mapped | `claude.invoke` only |
| Native subagent runtime | Not applicable | Not without orchestrator | Not implemented |

---

## Architecture

```
supermedicine/
├── core/                 # Microkernel, event bus, plugin registry, workspace
│   ├── redaction.py      # Shared sensitive-value redaction
│   ├── time_utils.py     # Shared UTC timestamp utilities
│   ├── tui/              # Interactive TUI (Textual)
│   │   ├── app.py        # Main TUI application
│   │   ├── app.tcss      # TUI stylesheet
│   │   ├── screens/      # Dashboard, Workspace, Paper, Experience, Tool, Dialog
│   │   ├── i18n.py       # Chinese labels
│   │   └── dialog_history.py
│   ├── paper_import/     # Paper import, metadata, enrichment
│   ├── workspace.py      # Workspace identity and storage
│   ├── experience.py     # Experience learning store
│   └── llm_providers/    # OpenAI/Anthropic/OpenRouter provider config and HTTP clients
├── permission/           # P0 policy, audit, engine, prompt constraints
├── agents/               # State machine, checkpoint, orchestrator, base agent
├── plugins/
│   ├── rag/              # RAG retrieval + local/mock external providers
│   ├── harness/          # Testing, monitoring, quality assessment
│   ├── tools/            # Python stats + R survival analysis
│   └── standards/        # Medical writing checklists + citation formatters
├── adapters/             # Optional platform add-ons
│   ├── opencode/         # OpenCode adapter (plugin.json, skills, agents)
│   ├── claude_code/      # Claude Code adapter (SKILL.md, adapter.py)
│   └── standalone/       # Standalone facade
├── Cli.py                # CLI entry point
├── Install.py            # Project initializer
├── install.json          # Agent-readable installation manifest
└── tests/                # Test suite (542+ tests)
```

---

## Running Tests

```bash
# Via CLI
supermedicine test

# Via pytest directly
pytest tests/ -v

# Run specific test file
pytest tests/test_workspace.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=term-missing
```

### Local Quality Gate

```bash
pip install -e ".[dev]"
ruff check --select=E,F,W --ignore=E501 .
python -m pip wheel . --no-deps --wheel-dir .pytest-tmp/wheel-smoke
pytest tests/ -v
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| **"No module named 'yaml'"** | `pip install pyyaml` |
| **"Permission denied" on Windows** | Run PowerShell as Administrator, or use `python -m venv .venv --without-pip` |
| **CLI command not found** | Add Python Scripts to PATH (see [INSTALL.md](INSTALL.md#cli-command-not-found)), or use `python Cli.py` directly |

For R survival backend setup, TUI launch issues, LLM provider troubleshooting,
and additional guidance, see [INSTALL.md](INSTALL.md#troubleshooting).

---

## Safety And Security

- **Permission Engine** — All high-risk operations (bash, write, edit) are
  permission-gated through `PermissionEngine.check()` at runtime.
- **Adapter Sandboxing** — In-project read/write/edit compatible; out-of-root
  denied; bash permission-gated.
- **RAG Security** — External providers use environment variable references for
  secrets; no hardcoded credentials.
- **LLM Secrets** — Use environment variables or local private config for API
  keys. Documentation examples use placeholders only; never commit real keys.
- **Paper Import** — Copy-only; source files are never moved or uploaded.
- **Experience Learning** — Raw conversations are not stored; only
  user-confirmed summaries are persisted.
- **Audit Logging** — All permission decisions are logged to
  `.supermedicine/policies/audit.jsonl`.

See [SECURITY.md](SECURITY.md) for the full security policy.

---

## License

MIT License — see [LICENSE](LICENSE) for details.
