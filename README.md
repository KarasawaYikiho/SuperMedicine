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

### Virtual Environment (Recommended)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e .
```

### PATH Configuration

After `pip install -e .`, the `supermedicine` command is installed as a Python
console script. If the command is not found, add the Python Scripts directory to
your PATH:

| System | Path to add |
|--------|-------------|
| **Windows** | `%APPDATA%\Python\Python<version>\Scripts` |
| **macOS** | `~/.local/bin` |
| **Linux** | `~/.local/bin` |

Restart your terminal and verify with `supermedicine --help`. Alternatively, use
`python Cli.py` as a direct substitute for `supermedicine` throughout this guide.

### Optional Dependencies

For R survival analysis tools: `pip install -e ".[r]"` then install the R
`survival` package. Use `backend="r"` in action parameters; without it, the
plugin uses the pure-Python fallback.

For development tools (mypy, pytest, pytest-cov, ruff): `pip install -e ".[dev]"`.

---

## Quick Start

```bash
# Clone and install
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine
pip install -e .
export OPENAI_API_KEY=<OPENAI_API_KEY>
python Install.py --init --provider openai --base-url https://api.openai.com/v1 --model gpt-4o-mini

# Check status
supermedicine status

# Create a workspace
supermedicine workspace init --workspace my-research --name "My Research"

# Run a task
supermedicine run "summarize local context" --workspace my-research

# Launch the interactive TUI
supermedicine tui
```

---

## LLM Provider Configuration

SuperMedicine supports direct OpenAI-compatible and Anthropic-compatible LLM
configuration through the standalone Python core. OpenCode and Claude Code are
optional platform surfaces; they are not required.

### Supported Formats

| Provider | API Format | Default BaseURL | Default Key Env | Default Model |
|----------|------------|-----------------|-----------------|---------------|
| `openai` | OpenAI Chat Completions | `https://api.openai.com/v1` | `OPENAI_API_KEY` | `gpt-4o-mini` |
| `anthropic` | Anthropic Messages | `https://api.anthropic.com/v1` | `ANTHROPIC_API_KEY` | `claude-3-5-sonnet-latest` |

Custom endpoints are supported with `--base-url` or `SM_LLM_BASE_URL`.

### Custom Providers

SuperMedicine accepts **any provider name**. The `api_format` field determines
which HTTP client is used, not the provider name itself:

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
```

Provider names containing `anthropic` or `claude` auto-infer the Anthropic API
format; all others default to OpenAI chat-completions. Override with
`--api-format` or `api_format` in `.supermedicine/config.yaml`.

### First-Run Requirement

LLM-backed tasks require one complete provider (`base_url`, `api_key` or
`api_key_env`, and `model`). If none is configured, runtime paths return a
structured setup error. See [INSTALL.md](INSTALL.md) for runtime validation
details and programmatic client creation examples.

### Configure By Editing The File

Edit `.supermedicine/config.yaml` after initialization. Prefer `api_key_env` for
real credentials so file edits stay secret-free:

```yaml
llm:
  provider: openai
  last_provider: openai
  providers:
    openai:
      provider: openai
      api_format: openai
      base_url: https://api.openai.com/v1
      api_key_env: OPENAI_API_KEY
      model: gpt-4o-mini
    anthropic:
      provider: anthropic
      api_format: anthropic
      base_url: https://api.anthropic.com/v1
      api_key_env: ANTHROPIC_API_KEY
      model: claude-3-5-sonnet-latest
```

Set the referenced key in your shell (`export OPENAI_API_KEY=<key>` on
macOS/Linux, `$env:OPENAI_API_KEY = "<key>"` on Windows PowerShell).

### Configure With The CLI

```bash
# Initialize with a provider (installer resolves key variable when --api-key omitted)
export OPENAI_API_KEY=<OPENAI_API_KEY>
python Install.py --init --provider openai \
  --base-url https://api.openai.com/v1 \
  --model gpt-4o-mini

# Add and switch providers after initialization
supermedicine llm add openai \
  --api-format openai \
  --base-url https://api.openai.com/v1 \
  --api-key-env OPENAI_API_KEY \
  --model gpt-4o-mini \
  --set-current
supermedicine llm add anthropic \
  --api-format anthropic \
  --base-url https://api.anthropic.com/v1 \
  --api-key-env ANTHROPIC_API_KEY \
  --model claude-3-5-sonnet-latest

# Review and switch
supermedicine llm list
supermedicine llm show openai
supermedicine llm switch anthropic
```

Use `--api-key-env` for real keys; `--api-key` may persist plaintext in local
YAML.

### Configure In The TUI

Launch with `supermedicine tui` and open **LLM 管理** from the sidebar. Fill
provider name, BaseURL, model, and API key, then click **添加 Provider** to
save. Select a provider and click **切换 Provider** to make it current.

### Switching And Startup Restore

`supermedicine llm switch <provider>` validates the target and persists it as
both `llm.provider` and `llm.last_provider`. On startup, SuperMedicine restores
`llm.last_provider` when it still exists; otherwise falls back to the
install-time provider. The TUI also saves the current provider on exit.

```bash
supermedicine llm list       # current_provider, last_provider, providers; redacted
supermedicine llm show       # current/restored provider; redacted
supermedicine llm switch openai
```

### Environment Variables And Secret Safety

For shell-only configuration during initialization:

```bash
export SM_LLM_PROVIDER=anthropic
export SM_LLM_BASE_URL=https://api.anthropic.com/v1
export SM_LLM_MODEL=claude-3-5-sonnet-latest
export ANTHROPIC_API_KEY=<ANTHROPIC_API_KEY>
python Install.py --init
```

`SM_LLM_API_KEY` is a generic override but may be written to local config.
Prefer provider-specific env vars or `api_key_env` for real credentials.

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
`edit`, `glob`, `grep`, `skill`, `task`.

| Capability | Status |
|------------|--------|
| Tool mapping (8 tools) | Implemented |
| Permission-gated high-risk operations | Implemented |
| Skill document loading | Provided for OpenCode use |
| Native subagent runtime | Not implemented without injected orchestrator |
| Capability reporting | Implemented |

### Claude Code Add-On

The Claude Code adapter (`adapters/claude_code/`) provides capability reporting,
runtime status checking, and permission-checked `claude --print` invocation.

| Capability | Status |
|------------|--------|
| `claude.capabilities` | Implemented |
| `claude.runtime_status` | Implemented |
| `claude.invoke` (when `claude` on PATH) | Implemented, permission-checked |
| Native skill loading / subagent dispatch | Not implemented |
| Missing `claude` runtime | Adapter unavailable, not core failure |

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
│   └── llm_providers/    # OpenAI/Anthropic provider config and HTTP clients
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
| **CLI command not found** | Add Python Scripts to PATH (see [PATH Configuration](#path-configuration)), or use `python Cli.py` directly |

For R survival backend setup, TUI launch issues, and additional troubleshooting,
see [INSTALL.md](INSTALL.md).

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
