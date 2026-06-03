# SuperMedicine Installation Guide

This guide covers installation, initialization, provider configuration, optional
R support, platform adapter notes, troubleshooting, and uninstall behavior for
SuperMedicine **Beta0.4.1**. The Python package fallback version is **0.4.1b0**.

For a shorter overview, start with [README.md](README.md). For design and
security boundaries, see [ARCHITECTURE.md](ARCHITECTURE.md) and
[SECURITY.md](SECURITY.md).

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | >= 3.10 | Required |
| Git | Any | Required for cloning |
| pip | >= 21.0 | Required for installation |
| R | >= 4.3 | Optional, for R survival backend |

OpenCode, Claude Code, and other assistant platforms are optional add-ons, not
requirements for the standalone Python core.

## Quick Install

```bash
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine
pip install -e .
export OPENAI_API_KEY=<OPENAI_API_KEY>
python Install.py --init --provider openai --base-url https://api.openai.com/v1 --model gpt-4o-mini
python Cli.py status
```

For development tooling:

```bash
pip install -e ".[dev]"
```

Installation and initialization are intentionally LLM-complete. A provider must
have `provider`, `base_url`, `model`, and an API key source (`api_key` or
`api_key_env`). If initialization fails, the installer restores the previous
`.supermedicine/` state or removes the partial directory.

## Step-by-Step Setup

### 1. Create a Virtual Environment

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
```

### 2. Clone and Install

```bash
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine
pip install -e .
```

### 3. Initialize the Project

```bash
export OPENAI_API_KEY=<OPENAI_API_KEY>
python Install.py --init --provider openai --base-url https://api.openai.com/v1 --model gpt-4o-mini
```

This creates local `.supermedicine/` configuration. It does not require or create
OpenCode or Claude Code configuration.

If you launch `Install.py` from a release archive, keep the extracted directory
intact. The fixed Beta0.4.1 release layout places `Install.py` next to the
`installer/` package, including `installer/__init__.py` and
`installer/exe_release.py`, under the extracted root. Copying only `Install.py`
out of the archive can trigger `ModuleNotFoundError: No module named 'installer'`.
In that case, re-download the fixed complete package or run the installer from a
complete source/release directory.

Alternative initialization examples:

```bash
# Anthropic format
export ANTHROPIC_API_KEY=<ANTHROPIC_API_KEY>
python Install.py --init --provider anthropic \
  --base-url https://api.anthropic.com/v1 \
  --model claude-3-5-sonnet-latest

# Custom OpenAI-compatible provider
export DEEPSEEK_API_KEY=<DEEPSEEK_API_KEY>
python Install.py --init --provider deepseek \
  --base-url https://api.deepseek.com/v1 \
  --api-format openai \
  --model deepseek-chat

# OpenRouter gateway
export OPENROUTER_API_KEY=<OPENROUTER_API_KEY>
python Install.py --init --provider openrouter

# Interactive prompt; API key input is hidden
python Install.py --init --interactive
```

Use placeholders in shared examples. Replace them only in private shells, secret
managers, CI secrets, or untracked local files.

## LLM Provider Management

Provider names are flexible. The `api_format` decides which HTTP protocol is used:

| API Format | Default Base URL | Default Key Env | Default Model |
|------------|------------------|-----------------|---------------|
| `openai` | `https://api.openai.com/v1` | `OPENAI_API_KEY` | `gpt-4o-mini` |
| `anthropic` | `https://api.anthropic.com/v1` | `ANTHROPIC_API_KEY` | `claude-3-5-sonnet-latest` |
| `openrouter` | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` | `anthropic/claude-3.5-sonnet` |

Add, inspect, and switch providers through the CLI:

```bash
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

supermedicine llm list
supermedicine llm show openai
supermedicine llm switch anthropic
```

`supermedicine llm switch <provider>` validates required fields, persists the
current provider, and records `last_provider` for startup restore.

### Manual YAML Configuration

You may edit `.supermedicine/config.yaml` directly. Prefer environment variable
references over plaintext keys:

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
```

Then set the environment variable outside the repository:

```bash
export OPENAI_API_KEY=<OPENAI_API_KEY>
```

### TUI Configuration

Run `supermedicine tui`, open **LLM 管理**, enter provider name, BaseURL, model,
API Key, and optional API format, then add or switch the provider. Key fields are
password-style and cleared after submission.

## Optional R Support

```bash
pip install -e ".[r]"
R -e "install.packages('survival', repos='https://cran.r-project.org')"
```

The R survival backend requires local R, rpy2, and the R `survival` package. If
requested R dependencies are unavailable, SuperMedicine returns a structured
`plugin_unavailable` result instead of silently using R. Without `backend="r"`,
the deterministic pure-Python fallback remains available.

## Verify Basic Installation

Use the status and diagnostic commands:

```bash
python Cli.py status
supermedicine diagnose
supermedicine llm list
```

Expected status output includes the SuperMedicine version, configuration state,
plugin discovery status, and test-module count. Diagnostic output redacts API
keys, authorization headers, key-like URL tokens, and secret-looking fields while
preserving information needed for repair.

For development environments, run the Local Quality Gate described in
[README.md](README.md#local-quality-gate).

## Global CLI Access

After `pip install -e .`, the `supermedicine` command is installed as a console
script. If it is not recognized, add the Python Scripts directory to PATH:

- Windows: `%APPDATA%\Python\Python<版本>\Scripts`
- Linux/macOS: `~/.local/bin`

You can always use `python Cli.py` as a direct substitute.

## Platform Adapters

Adapters are optional add-ons around the standalone Python framework.

| Area | Core Install Required? | Status |
|------|------------------------|--------|
| Standalone Python CLI/Kernel | Yes | Default supported path |
| OpenCode Add-on | No | Metadata, skills, agents, and tool mapping; no native external subagent runtime bridge by itself |
| Claude Code Add-on | No | Minimal capabilities/runtime/local CLI invocation adapter; no native Claude Code skill or subagent support |

OpenCode add-on content lives under `adapters/opencode/`. Claude Code add-on
content lives under `adapters/claude_code/`. These files contain metadata and
must not contain real API keys.

## Troubleshooting

### `No module named 'yaml'`

Install project dependencies:

```bash
pip install -e .
```

### `ModuleNotFoundError: No module named 'installer'`

This usually means `Install.py` was copied out of the release archive instead of
being run from the full extracted directory. The Beta0.4.1 release must keep the
complete layout with `Install.py` and the `installer/` package together at the
extracted root, including `installer/__init__.py` and `installer/exe_release.py`.
Re-download the fixed complete package or run from a complete source/release
directory. Do not try to repair this by manually copying single files out of the
archive.

### Permission denied on Windows

Run PowerShell as Administrator, or create a virtual environment with:

```bash
python -m venv .venv --without-pip
```

### CLI command not found

Use `python Cli.py` or add the Python Scripts directory to PATH, then restart the
terminal and run:

```bash
supermedicine --help
```

### Missing LLM key, endpoint, or model

Set provider-specific variables for real credentials:

```bash
export OPENAI_API_KEY=<OPENAI_API_KEY>
export ANTHROPIC_API_KEY=<ANTHROPIC_API_KEY>
export OPENROUTER_API_KEY=<OPENROUTER_API_KEY>
```

If switching fails, inspect redacted state with `supermedicine llm list` and add
missing `base_url`, `api_key_env`/`api_key`, or `model` values with
`supermedicine llm add ... --set-current`.

### Initialization fails and no `.supermedicine/` remains

This is expected when first-run LLM configuration is incomplete. Re-run init with
all required fields. If a previous config existed, failed initialization restores
it; otherwise the partial directory is removed.

### TUI launch or terminal recovery

```bash
supermedicine tui --dry-run
supermedicine tui
```

Use dry-run before launching on new terminals or after a crash. Normal exit is
`q`; if the terminal is interrupted, reopen the shell before relaunching.

## Uninstall

```bash
python Uninstall.py --dry-run
python Uninstall.py --force
python Uninstall.py --force --preserve-user-data
python Uninstall.py --target .opencode/skills/supermedicine --dry-run
```

The uninstaller removes SuperMedicine-owned local artifacts in the current
project, including `.supermedicine/`, repository-scoped adapter copies, recorded
installer targets, and explicit `--target` paths. It does not delete the source
repository or unrecorded user-owned global OpenCode/Claude Code configuration.
Use `pip uninstall supermedicine` separately if you installed the package and
want to remove it from the Python environment.

Uninstall logs redact secret-looking fields. Manually remove shell/profile
variables such as `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`, or
`SM_LLM_API_KEY` if you no longer need them.
