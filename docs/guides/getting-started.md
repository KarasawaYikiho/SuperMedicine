# Getting Started with SuperMedicine

This guide walks you through installing, configuring, and using SuperMedicine.
For detailed installation options, see [INSTALL.md](../../INSTALL.md).

## Installation

### Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | >= 3.10 | Required |
| Git | Any | Required for cloning |
| pip | >= 21.0 | Required for installation |
| R | >= 4.3 | Optional, for R survival backend |

### Quick Install

```bash
# Clone the repository
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine

# Install in development mode
pip install -e .

# Run the interactive installer
python Install.py

# Verify installation
supermedicine status
```

The installer wizard will guide you through:
1. Setting the project path
2. Initializing `.supermedicine/` configuration
3. Configuring your LLM provider (API format, base URL, model, key)
4. Optional shortcuts and PATH setup

### Virtual Environment (Recommended)

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -e .
python Install.py
```

### Web Interface Dependencies

```bash
pip install supermedicine[web]
```

## Basic Usage

### CLI Commands

All commands work as `supermedicine <command>` after installation, or `python Cli.py <command>` from the repo root.

```bash
# Check project status
supermedicine status

# Run diagnostics
supermedicine diagnose

# List LLM providers
supermedicine llm list
```

### Working with Workspaces

```bash
# Initialize a workspace
supermedicine workspace init --workspace my-research --name "My Research"

# List workspaces
supermedicine workspace list

# Show workspace details
supermedicine workspace show --workspace my-research
```

### Managing Papers

```bash
# Import a paper
supermedicine paper import ./paper.pdf --workspace my-research --title "Paper Title"

# List papers in a workspace
supermedicine paper list --workspace my-research

# Enrich paper metadata with LLM
supermedicine paper enrich --workspace my-research --paper-id <id> --confirm-enrich
```

### Experience Learning

```bash
# Add an experience record
supermedicine experience suggest --workspace my-research --summary "Keep prompts short"

# List experiences
supermedicine experience list --workspace my-research
```

### Research Tools

```bash
# Scan for available tools
supermedicine tool scan --language python

# Add a tool to workspace
supermedicine tool add --workspace my-research --select 1

# List workspace tools
supermedicine tool list --workspace my-research
```

### Experiments

```bash
# List available experiment protocols
supermedicine experiment list

# Start an experiment
supermedicine experiment start --protocol western_blot_basic --session-id wb-demo

# Follow experiment logs
supermedicine log follow --session-id wb-demo --interval 1 --max-entries 20
```

## Configuration

### Project Structure

```
.supermedicine/
  config.yaml          # Main configuration
  policies/
    default.yaml       # Default permission policy
    audit.jsonl        # Permission audit log
  checkpoints/         # Agent checkpoints
  logs/                # Session logs
```

### Configuration File

The main config is at `.supermedicine/config.yaml`:

```yaml
llm:
  provider: openai
  base_url: https://api.openai.com/v1
  model: gpt-4o-mini
  api_key_env: OPENAI_API_KEY

permissions:
  mode: conservative  # or "full"
```

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `SM_CONFIG` | Override config file path |
| `SM_<KEY>` | Override any config key |
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `OPENROUTER_API_KEY` | OpenRouter API key |

### Adding a Custom LLM Provider

```bash
supermedicine llm add deepseek \
  --api-format openai \
  --base-url https://api.deepseek.com/v1 \
  --api-key-env DEEPSEEK_API_KEY \
  --model deepseek-chat \
  --set-current
```

## CLI Commands Reference

### Core

| Command | Description |
|---------|-------------|
| `status` | Show project status |
| `diagnose` | Run secret-safe diagnostics |
| `tui` | Launch the Chinese Textual TUI |
| `web` | Start the web interface |

### Workspace

| Command | Description |
|---------|-------------|
| `workspace init` | Create a new workspace |
| `workspace list` | List all workspaces |
| `workspace show` | Show workspace details |
| `workspace delete` | Delete a workspace |

### Papers

| Command | Description |
|---------|-------------|
| `paper import` | Import a paper |
| `paper list` | List papers |
| `paper show` | Show paper details |
| `paper edit` | Edit paper metadata |
| `paper enrich` | Enrich with LLM |

### Experience

| Command | Description |
|---------|-------------|
| `experience suggest` | Add experience record |
| `experience list` | List experiences |
| `experience view` | View experience details |
| `experience delete` | Delete an experience |

### Tools

| Command | Description |
|---------|-------------|
| `tool scan` | Scan for available tools |
| `tool add` | Add tool to workspace |
| `tool list` | List workspace tools |

### LLM

| Command | Description |
|---------|-------------|
| `llm list` | List configured providers |
| `llm show` | Show provider details |
| `llm add` | Add a new provider |
| `llm switch` | Switch active provider |

### Permissions

| Command | Description |
|---------|-------------|
| `permission status` | Show permission status |
| `permission mode` | Set permission mode |
| `permission roots` | List authorized roots |
| `permission authorize` | Authorize an external path |
| `permission revoke` | Revoke an authorized path |

### Logs

| Command | Description |
|---------|-------------|
| `log location` | Show log storage path |
| `log follow` | Follow log output |

## TUI Usage

Launch the Chinese Textual terminal interface:

```bash
supermedicine tui
supermedicine tui --dry-run  # Check readiness without starting
```

### Global Shortcuts

| Key | Action |
|-----|--------|
| `Tab` | Move focus forward |
| `Shift+Tab` | Move focus backward |
| `Enter` | Submit/confirm |
| `M` | Open main menu |
| `P` | Open permission view |
| `Esc` | Exit maximized mode |
| `Q` | Quit TUI |

### Screens

The TUI provides screens for: chat, dashboard, workspace management, paper management, experience learning, tool management, dialog history, LLM management, experiment guide, permission mode, and log reports.

## Web Interface

Start the web server:

```bash
supermedicine web
# Or directly:
python -c "from core.web.server import start_server; start_server()"
```

Access at `http://127.0.0.1:8000`. See [API Reference](../api/README.md) for endpoint details.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `No module named 'yaml'` | `pip install -e .` or `pip install pyyaml` |
| `supermedicine` command not found | Add Python Scripts to PATH or use `python Cli.py` |
| Missing LLM fields | Provide provider, base_url, model, and API key source |
| TUI launch issue | Run `supermedicine tui --dry-run` first |

See [README.md](../../README.md) for more troubleshooting details.
