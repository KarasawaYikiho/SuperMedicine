# SuperMedicine

![Version](https://img.shields.io/badge/version-Beta0.3.0-blue)
![CI](https://github.com/KarasawaYikiho/SuperMedicine/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Independent Python medical research agent framework with RAG, plugin execution,
and permission-gated orchestration. SuperMedicine runs as a standalone Python
package by default; OpenCode, Claude Code, and similar assistant platforms are
optional add-on adapters around the core, not core runtime requirements.

## Features

- **Modular Architecture** — Microkernel + multi-Agent orchestration with plugin system
- **P0 Permission Engine** — Code-layer runtime permission constraints with prompt-context safety guidance
- **Plugin Ecosystem** — RAG retrieval, Harness monitoring, Python/R statistics, medical writing standards
- **Interactive TUI** — Full Chinese terminal UI with sidebar navigation, 7 views, keyboard shortcuts
- **Workspace System** — Explicit workspace management with paper import, experience learning, tool management
- **Core standalone by default** — No OpenCode, Claude Code, or platform runtime required
- **Optional platform add-ons** — OpenCode and Claude Code adapters for platform-specific workflows
- **Medical Standards** — CONSORT, STROBE, PRISMA, STARD checklists; AMA/Vancouver citation formatting

---

## Table of Contents

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

# 3. Initialize
python Install.py --init

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

# 3. Initialize
python3 Install.py --init

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

# 3. Initialize
python3 Install.py --init

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
python Install.py --init

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

## CLI Reference

All commands are available via `supermedicine <command>` or `python Cli.py <command>`.

### Core Commands

```bash
supermedicine init [--dir .]          # Initialize project configuration
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

---

## TUI (Terminal UI)

SuperMedicine includes a full interactive Chinese terminal UI built with
[Textual](https://textual.textualize.io/).

### Launching

```bash
supermedicine tui
```

### Navigation

| Key | Action |
|-----|--------|
| `1` | Chat (对话) |
| `2` | Dashboard (仪表盘) |
| `3` | Workspace (工作区管理) |
| `4` | Paper (论文管理) |
| `5` | Experience (经验学习) |
| `6` | Tool (工具管理) |
| `7` | Dialog (对话历史) |
| `↑` / `↓` | Navigate sidebar |
| `Enter` | Send message |
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
| **Dialog** | View session dialog history (read-only) |

### TUI vs CLI

- TUI recent selection is workspace/session state and does **not** alter CLI defaults
- CLI commands always require explicit `--workspace` — they never read TUI state
- TUI and CLI share the same backend controllers and data

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

3. Without an injected SuperMedicine orchestrator, the adapter uses local
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
│   └── llm_providers/    # LLM provider integrations (OpenRouter)
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

### CLI command not found

If `supermedicine` is not recognized after `pip install -e .`:

1. **Add Scripts to PATH** (see [PATH Configuration](#path-configuration))
2. **Or use `python Cli.py` directly**:
   ```bash
   cd SuperMedicine
   python Cli.py status
   ```

### R survival tools not working

```bash
pip install -e ".[r]"
R -e "install.packages('survival', repos='https://cran.r-project.org')"
```

### TUI not launching

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

## Safety and Security

- **Permission Engine** — All high-risk operations (bash, write, edit) are
  permission-gated through `PermissionEngine.check()` at runtime.
- **Adapter Sandboxing** — In-project read/write/edit compatible; out-of-root
  denied; bash permission-gated.
- **RAG Security** — External providers use environment variable references for
  secrets; no hardcoded credentials.
- **Paper Import** — Copy-only; source files are never moved or uploaded.
- **Experience Learning** — Raw conversations are not stored; only
  user-confirmed summaries are persisted.
- **Audit Logging** — All permission decisions are logged to
  `.supermedicine/policies/audit.jsonl`.

See [SECURITY.md](SECURITY.md) for the full security policy.

---

## License

MIT License — see [LICENSE](LICENSE) for details.
