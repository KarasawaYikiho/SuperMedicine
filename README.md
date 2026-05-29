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
  - [Prerequisites](#prerequisites)
  - [Windows](#windows)
  - [macOS](#macos)
  - [Linux](#linux)
  - [Virtual Environment (Recommended)](#virtual-environment-recommended)
  - [PATH Configuration](#path-configuration)
  - [Optional: R Survival Backend](#optional-r-survival-backend)
  - [Optional: Development Tools](#optional-development-tools)
- [Quick Start](#quick-start)
- [LLM Provider Configuration](#llm-provider-configuration)
  - [Custom Providers](#custom-providers)
  - [First-Run Requirement](#first-run-requirement)
  - [Configure By Editing The File](#configure-by-editing-the-file)
  - [Configure With The CLI](#configure-with-the-cli)
  - [Configure In The TUI](#configure-in-the-tui)
  - [Switching And Startup Restore](#switching-and-startup-restore)
  - [Environment Variables And Secret Safety](#environment-variables-and-secret-safety)
- [CLI Reference](#cli-reference)
  - [Core Commands](#core-commands)
  - [Workspace Commands](#workspace-commands)
  - [Paper Commands](#paper-commands)
  - [Experience Commands](#experience-commands)
  - [Tool Commands](#tool-commands)
  - [TUI Command](#tui-command)
- [TUI (Terminal UI)](#tui-terminal-ui)
- [Platform Adapters](#platform-adapters)
  - [OpenCode Add-on](#opencode-add-on)
  - [Claude Code Add-on](#claude-code-add-on)
- [Architecture](#architecture)
- [Running Tests](#running-tests)
- [Troubleshooting](#troubleshooting)
- [Safety and Security](#safety-and-security)
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

### Windows

```powershell
# 1. Clone the repository
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine

# 2. Install
pip install -e .

# 3. Initialize with a complete LLM provider
$env:OPENAI_API_KEY = "<OPENAI_API_KEY>"
python Install.py --init --provider openai --base-url https://api.openai.com/v1 --model gpt-4o-mini

# 4. Verify
python Cli.py status
```

### macOS

```bash
# 1. Clone the repository
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine

# 2. Install
pip install -e .

# 3. Initialize with a complete LLM provider
export OPENAI_API_KEY=<OPENAI_API_KEY>
python3 Install.py --init --provider openai --base-url https://api.openai.com/v1 --model gpt-4o-mini

# 4. Verify
python3 Cli.py status
```

### Linux

```bash
# 1. Clone the repository
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine

# 2. Install
pip install -e .

# 3. Initialize with a complete LLM provider
export OPENAI_API_KEY=<OPENAI_API_KEY>
python3 Install.py --init --provider openai --base-url https://api.openai.com/v1 --model gpt-4o-mini

# 4. Verify
python3 Cli.py status
```

### Virtual Environment (Recommended)

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# Then install
pip install -e .
export OPENAI_API_KEY=<OPENAI_API_KEY>
python Install.py --init --provider openai --base-url https://api.openai.com/v1 --model gpt-4o-mini
```

To initialize with an LLM provider at the same time, pass OpenAI-compatible or
Anthropic-compatible settings. Use placeholders or fake keys in shared examples;
never commit real API keys:

```bash
# OpenAI-compatible endpoint
python Install.py --init --provider openai \
  --base-url https://api.openai.com/v1 \
  --api-key <OPENAI_API_KEY> \
  --model gpt-4o-mini

# Anthropic-compatible endpoint
python Install.py --init --provider anthropic \
  --base-url https://api.anthropic.com/v1 \
  --api-key <ANTHROPIC_API_KEY> \
  --model claude-3-5-sonnet-latest

# Custom OpenAI-compatible provider (DeepSeek, 智谱 GLM, Ollama, etc.)
python Install.py --init --provider deepseek \
  --base-url https://api.deepseek.com/v1 \
  --api-key <DEEPSEEK_API_KEY> \
  --model deepseek-chat
```

Instead of `--api-key`, prefer environment variables for private workstations:

```bash
export SM_LLM_PROVIDER=openai
export SM_LLM_BASE_URL=https://api.openai.com/v1
export SM_LLM_MODEL=gpt-4o-mini
export OPENAI_API_KEY=<OPENAI_API_KEY>
python Install.py --init
```

### PATH Configuration

After `pip install -e .`, the `supermedicine` command is installed as a Python
console script. If the command is not found, add the Python Scripts directory to
your PATH:

| System | Path to add |
|--------|-------------|
| **Windows** | `%APPDATA%\Python\Python<版本>\Scripts` (e.g., `C:\Users\YourName\AppData\Roaming\Python\Python314\Scripts`) |
| **macOS** | `~/.local/bin` |
| **Linux** | `~/.local/bin` |

After adding to PATH, restart your terminal and verify:

```bash
supermedicine --help
```

Alternatively, use `python Cli.py` as a direct substitute for `supermedicine`
throughout this guide.

### Optional: R Survival Backend

```bash
pip install -e ".[r]"
R -e "install.packages('survival', repos='https://cran.r-project.org')"
```

When available, request the R backend with `backend="r"` in r-survival action
parameters. Without `backend="r"`, the plugin uses the deterministic pure-Python
fallback.

### Optional: Development Tools

```bash
pip install -e ".[dev]"
```

Includes: mypy, pytest, pytest-cov, ruff.

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
optional platform surfaces around the same configuration model; they are not
required to use it.

### Supported Formats

| Provider | API Format | Default BaseURL | Default Key Env | Default Model |
|----------|------------|-----------------|-----------------|---------------|
| `openai` | OpenAI Chat Completions | `https://api.openai.com/v1` | `OPENAI_API_KEY` | `gpt-4o-mini` |
| `anthropic` | Anthropic Messages | `https://api.anthropic.com/v1` | `ANTHROPIC_API_KEY` | `claude-3-5-sonnet-latest` |

Custom compatible endpoints are supported with `--base-url` or
`SM_LLM_BASE_URL`. OpenAI-compatible requests post to `/chat/completions` by
default; Anthropic-compatible requests post to `/messages`.

### Custom Providers

SuperMedicine accepts **any provider name** — not just `openai` or `anthropic`.
The `api_format` field (or its auto-inferred equivalent) determines which HTTP
client is used, not the provider name itself. This means you can configure
DeepSeek, 智谱 GLM, Ollama, or any other OpenAI-compatible or
Anthropic-compatible endpoint:

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
format; all other names default to the OpenAI chat-completions format. You can
override this with an explicit `--api-format` flag or `api_format` field in
`.supermedicine/config.yaml`.

### First-Run Requirement

LLM-backed tasks require one complete provider before the runtime can create a
client. A complete provider has `base_url`, `api_key` (or `api_key_env` that
points to an environment variable), and `model`. If no provider is configured,
runtime paths return a structured setup error and tell you to configure LLM via
`Install.py --init`, `.supermedicine/config.yaml`, `supermedicine llm add/switch`,
or the TUI LLM screen. This is intentional: first installation must explicitly
choose a provider instead of silently using an unknown model.

You can configure the first provider through any of the following channels. All
examples use placeholders or environment-variable names only; replace them only
in your private shell or local config.

### Configure By Editing The File

After initialization, edit `.supermedicine/config.yaml` and adjust the `llm`
section. Prefer `api_key_env` for real credentials so future file edits can stay
secret-free:

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

Then set the referenced key in your shell, not in Git-tracked files:

```bash
export OPENAI_API_KEY=<OPENAI_API_KEY>
```

On Windows PowerShell:

```powershell
$env:OPENAI_API_KEY = "<OPENAI_API_KEY>"
```

### Configure With The CLI

You can inject a provider during initialization. The example below assumes
`OPENAI_API_KEY` is already set in your private shell; the installer resolves the
provider-specific key variable when `--api-key` is not supplied:

```bash
export OPENAI_API_KEY=<OPENAI_API_KEY>
python Install.py --init --provider openai \
  --base-url https://api.openai.com/v1 \
  --model gpt-4o-mini
```

Or add and switch providers after initialization:

```bash
# Add an OpenAI-compatible provider and make it current
supermedicine llm add openai \
  --api-format openai \
  --base-url https://api.openai.com/v1 \
  --api-key-env OPENAI_API_KEY \
  --model gpt-4o-mini \
  --set-current

# Add an Anthropic-compatible provider without switching yet
supermedicine llm add anthropic \
  --api-format anthropic \
  --base-url https://api.anthropic.com/v1 \
  --api-key-env ANTHROPIC_API_KEY \
  --model claude-3-5-sonnet-latest

# Review redacted config and switch defaults
supermedicine llm list
supermedicine llm show openai
supermedicine llm switch anthropic
```

`--api-key` exists for local throwaway setups but may persist the value in
`.supermedicine/config.yaml`; use `--api-key-env` for real keys whenever possible.

### Configure In The TUI

Launch the TUI and open **LLM 管理** from the sidebar:

```bash
supermedicine tui
```

In the LLM screen you can:

1. Fill provider name (`openai`, `anthropic`, or a compatible endpoint name),
   BaseURL, model, API key, and optional API format.
2. Click **添加 Provider** to save it. The API key input is password-style and is
   cleared after submission.
3. Select a provider from the dropdown and click **切换 Provider** to make it the
   current default.
4. Click refresh to reload the redacted provider table.

The TUI uses the same `.supermedicine/config.yaml` and `LLMConfigManager` as the
CLI, so provider changes are shared between CLI and TUI.

### Switching And Startup Restore

`supermedicine llm switch <provider>` validates the target provider, writes it as
both `llm.provider` and `llm.last_provider`, and persists the change. On startup,
SuperMedicine restores `llm.last_provider` when it still exists; otherwise it
falls back to the install-time `llm.provider`. The TUI also saves the current
provider on exit so the next launch resumes the most recently used LLM.

Use these commands to inspect runtime state without exposing secrets:

```bash
supermedicine llm list       # current_provider, last_provider, providers; redacted
supermedicine llm show       # current/restored provider; redacted
supermedicine llm switch openai
```

### Environment Variables And Secret Safety

For shell-only configuration during initialization, set provider metadata and a
provider-specific key variable:

```bash
# Environment-variable injection during initialization
export SM_LLM_PROVIDER=anthropic
export SM_LLM_BASE_URL=https://api.anthropic.com/v1
export SM_LLM_MODEL=claude-3-5-sonnet-latest
export ANTHROPIC_API_KEY=<ANTHROPIC_API_KEY>
python Install.py --init
```

Equivalent one-shot POSIX form:

```bash
SM_LLM_PROVIDER=anthropic \
SM_LLM_BASE_URL=https://api.anthropic.com/v1 \
SM_LLM_MODEL=claude-3-5-sonnet-latest \
ANTHROPIC_API_KEY=<ANTHROPIC_API_KEY> \
python Install.py --init
```

`SM_LLM_API_KEY` is supported as a generic installer-time override, but it can be
written to local config. Prefer `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or an
`api_key_env` reference in `.supermedicine/config.yaml` for real credentials.

### Configuration Sources

Configuration can also be injected in these ways, with examples using fake keys
only:

```bash
# Command-line injection during project initialization with a placeholder key
python Install.py --init --provider openai \
  --base-url https://api.openai.com/v1 \
  --api-key <OPENAI_API_KEY> \
  --model gpt-4o-mini

# Environment-variable injection during initialization
SM_LLM_PROVIDER=anthropic \
SM_LLM_BASE_URL=https://api.anthropic.com/v1 \
SM_LLM_MODEL=claude-3-5-sonnet-latest \
ANTHROPIC_API_KEY=<ANTHROPIC_API_KEY> \
python Install.py --init

# Interactive prompt; API key input is hidden
python Install.py --init --interactive
```

`Install.py --init` writes local project configuration to
`.supermedicine/config.yaml`. If an API key is supplied by `--api-key` or
`SM_LLM_API_KEY`, it can be written to that local file; do not commit that file
after adding real secrets. Prefer provider environment variables
(`OPENAI_API_KEY` or `ANTHROPIC_API_KEY`) for real credentials.

### Runtime Use And Validation

Use `python Cli.py status` or `supermedicine status` to confirm the project is
initialized. Provider validation is performed when an LLM client is used or when
you switch providers: missing BaseURL, API key, or model returns a structured
error such as `missing_api_key`; request and HTTP errors are sanitized so known
secret values are redacted.

Python callers can use the factory directly:

```python
from core.llm_client import create_llm_client

client = create_llm_client(
    "openai",
    api_key="<OPENAI_API_KEY>",
    base_url="https://api.openai.com/v1",
    model="gpt-4o-mini",
)
```

Never paste real keys into committed source, docs, tests, manifests, issue logs,
or screenshots. Use placeholders such as `<OPENAI_API_KEY>`,
`<ANTHROPIC_API_KEY>`, or `<redacted>` in examples.

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
# Create a workspace
supermedicine workspace init --workspace <slug> [--name "Display Name"]

# List all workspaces
supermedicine workspace list

# Show workspace details
supermedicine workspace show --workspace <slug>

# Hard delete (requires exact confirmation)
supermedicine workspace delete --workspace <slug> --confirm <slug>
```

Workspaces live under `workspaces/<id>`, where `<id>` is a lowercase slug
(letters, digits, hyphens). CLI commands never infer the last TUI workspace;
every workspace-scoped CLI action requires `--workspace <id>`.

### Paper Commands

```bash
# Import a paper (copy-only, supports PDF/TeX/BibTeX/RIS/TXT/MD)
supermedicine paper import ./paper.pdf --workspace <slug> --title "Paper Title"
supermedicine paper import ./paper.pdf --workspace <slug> --doi "10.xxx/yyy"
supermedicine paper import ./paper.pdf --workspace <slug> --tag "oncology" --tag "RCT"

# List papers in workspace
supermedicine paper list --workspace <slug>

# Show paper metadata
supermedicine paper show <paper-id> --workspace <slug>

# Edit paper metadata
supermedicine paper edit <paper-id> --workspace <slug> --title "New Title"

# Online metadata enrichment (requires explicit confirmation)
supermedicine paper enrich <paper-id> --workspace <slug> --confirm-enrich
```

Paper imports are copy-only: the source file is never moved or uploaded.
Papers are deduplicated by SHA-256 and by normalized DOI/PMID.

### Experience Commands

```bash
# Suggest a classification (does not persist)
supermedicine experience suggest --workspace <slug> --summary "Keep prompts short"

# Confirm and write to experience store
supermedicine experience add --workspace <slug> --scope workspace \
  --title "Prompt Strategy" --summary "Keep prompts short" --confirm

# List experience records
supermedicine experience list --workspace <slug>
supermedicine experience list --workspace <slug> --include-general

# View a specific record
supermedicine experience view <record-id> --workspace <slug>

# Edit a record
supermedicine experience edit <record-id> --workspace <slug> --scope workspace \
  --title "Updated Title"

# Delete a record (requires exact ID confirmation)
supermedicine experience delete <record-id> --workspace <slug> --scope workspace \
  --confirm <record-id>

# Export experience records
supermedicine experience export --workspace <slug> --format json
supermedicine experience export --workspace <slug> --format md --output experience.md
```

Experience learning is enabled by default. Raw conversations are **not** stored;
only user-confirmed summaries are persisted.

### Tool Commands

```bash
# Initialize tool directory in workspace
supermedicine tool init --workspace <slug>

# Add a built-in tool template (heatmap or umap)
supermedicine tool add --workspace <slug> --language python --tool heatmap
supermedicine tool add --workspace <slug> --language r --tool umap

# List tools in workspace
supermedicine tool list --workspace <slug>
supermedicine tool list --workspace <slug> --language python

# Show tool manifest
supermedicine tool show --workspace <slug> --language python --tool heatmap

# Run a tool (dry-run by default for safety)
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
[Textual](https://textual.textualize.io/).

### Launching

```bash
supermedicine tui
```

### Interface structure

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

The sidebar shortcut hint shown in the TUI mirrors these bindings: `1-8` switch
views, `Tab`/`Shift+Tab` change focus, `Enter` submits, `?` opens help, `f`
maximizes/restores the focused widget, and `q` exits.

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

- **LLM 状态** appears in the center status segment. It shows whether the current
  provider is ready and names the active provider without exposing API keys.
- **任务运行状态** also appears in the center segment as `任务空闲` or
  `任务执行中`, so long-running kernel work is visible without leaving the
  current screen.
- **刷新** buttons on Workspace, Paper, Experience, Tool, Dialog, and LLM screens
  reload their current lists from the shared backend controllers.
- **危险操作** such as workspace deletion, experience deletion, and online paper
  enrichment require explicit confirmation, exact ID input, or a dedicated
  action button before irreversible or network-touching work proceeds.

### TUI vs CLI

- TUI recent selection is workspace/session state and does **not** alter CLI defaults
- CLI commands always require explicit `--workspace` — they never read TUI state
- TUI and CLI share the same backend controllers and data
- The TUI is part of the standalone Python package; platform adapters remain
  optional surfaces and are not required for CLI or TUI operation.

---

## Platform Adapters

SuperMedicine's default model is **core independent + platform add-ons**. The
standalone Python core is the default supported path. OpenCode and Claude Code
are optional add-on adapters.

### OpenCode Add-on

The OpenCode adapter lives under `adapters/opencode/`. It provides:

- Plugin metadata (`plugin.json`)
- 6 skill documents (`skills/*.md`)
- 1 user-facing agent (`agents/supermedicine.md`)
- 4 internal role context documents (`agents/{alpha,beta,gamma,delta}-*.md`)
- Adapter tool mapping: `bash`, `read`, `write`, `edit`, `glob`, `grep`, `skill`, `task`

#### Setup

1. Copy or reference `adapters/opencode/plugin.json` and associated files
   according to your OpenCode installation.

2. The adapter maps declared tools with permission-gated high-risk operations
    (`bash`, `write`, `edit`, `task`).

3. Configure optional OpenAI/Anthropic provider metadata through `Install.py`,
   `SM_LLM_*`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or project-local
   `.supermedicine/config.yaml`; never embed real keys in OpenCode files.

4. Without an injected SuperMedicine orchestrator, the adapter uses local
    metadata/fallback behavior.

#### Capabilities

| Capability | Status |
|------------|--------|
| Tool mapping (bash, read, write, edit, glob, grep, skill, task) | Implemented |
| Permission-gated high-risk operations | Implemented |
| Skill document loading | Provided for OpenCode use |
| Native OpenCode subagent runtime | Not implemented without injected orchestrator |
| Capability reporting | Implemented |

### Claude Code Add-on

The Claude Code adapter lives under `adapters/claude_code/`. It provides:

- Capability reporting (`claude.capabilities`)
- Runtime status checking (`claude.runtime_status`)
- Permission-checked `claude --print` invocation (`claude.invoke`)

#### Setup

```bash
# Copy skill directory for local Claude Code documentation
cp -r adapters/claude_code/ ~/.claude/skills/supermedicine/
```

Claude Code adapter calls use the same SuperMedicine provider configuration
boundary as the core: OpenAI-compatible or Anthropic-compatible settings from
installer flags, `SM_LLM_*`, provider key environment variables, or local project
config. Missing `claude` on PATH is reported as optional-adapter unavailable,
not as a core failure.

#### Capabilities

| Capability | Status |
|------------|--------|
| `claude.capabilities` | Implemented |
| `claude.runtime_status` | Implemented |
| `claude.invoke` (when `claude` on PATH) | Implemented, permission-checked |
| Native Claude Code skill loading | Not implemented |
| Native Claude Code subagent dispatch | Not implemented |
| Missing `claude` runtime | Reported as adapter unavailable, not core failure |

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
└── tests/                # Test suite (432+ tests)
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

### "No module named 'yaml'"

```bash
pip install pyyaml
```

### "Permission denied" on Windows

Run PowerShell as Administrator, or use:

```bash
python -m venv .venv --without-pip
```

### CLI Command Not Found

If `supermedicine` is not recognized after `pip install -e .`:

1. **Add Scripts to PATH** (see [PATH Configuration](#path-configuration))
2. **Or use `python Cli.py` directly**:
   ```bash
   cd SuperMedicine
   python Cli.py status
   ```

### R Survival Tools Not Working

```bash
pip install -e ".[r]"
R -e "install.packages('survival', repos='https://cran.r-project.org')"
```

### TUI Not Launching

Ensure `textual` is installed:

```bash
pip install textual
```

### "Textual 未安装，无法启动交互界面"

```bash
pip install -e .
```

This installs `textual` as a core dependency.

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
