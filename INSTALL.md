# SuperMedicine Installation Guide

This guide is the detailed installation reference. For a shorter orientation,
start with [README.md](README.md); for optional adapter design boundaries, see
[ARCHITECTURE.md](ARCHITECTURE.md#layer-5-platform-adapters-adapters).

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | >= 3.10 | Required |
| Git | any | For cloning the repository |
| pip | >= 21.0 | For package installation |
| R | >= 4.3 | Optional, for survival analysis tools |

OpenCode, Claude Code, and other assistant platforms are **not** prerequisites
for installing or running the SuperMedicine Python core. They are optional
add-on adapter environments.

## Quick Install

```bash
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine
pip install -e ".[dev]"
export OPENAI_API_KEY=<OPENAI_API_KEY>
python Install.py --init --provider openai --base-url https://api.openai.com/v1 --model gpt-4o-mini
```

If you plan to run LLM-backed tasks, configure at least one LLM provider before
the first run. SuperMedicine intentionally refuses to create an LLM client until a
provider has `base_url`, API key source, and `model`.

For a core-only user install, omit development tooling:

```bash
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine
pip install -e .
export OPENAI_API_KEY=<OPENAI_API_KEY>
python Install.py --init --provider openai --base-url https://api.openai.com/v1 --model gpt-4o-mini
python Cli.py status
python Cli.py run "summarize local context"
```

To initialize and configure an LLM provider in one command, use OpenAI-compatible
or Anthropic-compatible settings. The keys below are fake placeholders; do not
commit real keys to Git, docs, tests, manifests, or screenshots.

```bash
python Install.py --init --provider openai \
  --base-url https://api.openai.com/v1 \
  --api-key <OPENAI_API_KEY> \
  --model gpt-4o-mini

python Install.py --init --provider anthropic \
  --base-url https://api.anthropic.com/v1 \
  --api-key <ANTHROPIC_API_KEY> \
  --model claude-3-5-sonnet-latest

# Custom OpenAI-compatible providers (DeepSeek, 智谱 GLM, Ollama, etc.)
python Install.py --init --provider deepseek \
  --base-url https://api.deepseek.com/v1 \
  --api-key <DEEPSEEK_API_KEY> \
  --model deepseek-chat

python Install.py --init --provider zhipu \
  --base-url https://open.bigmodel.cn/api/paas/v4 \
  --api-key <ZHIPU_API_KEY> \
  --model glm-4-flash
```

For real workstations, prefer environment variables over typing secrets directly
on the command line. The installer resolves provider-specific key variables to
satisfy the first-run completeness check; because that can write the resolved key
to local config, keep `.supermedicine/config.yaml` private and then use
`supermedicine llm add --api-key-env` if you want the saved provider to reference
an environment variable instead of keeping plaintext local YAML:

```bash
export OPENAI_API_KEY=<OPENAI_API_KEY>
python Install.py --init --provider openai \
  --base-url https://api.openai.com/v1 \
  --model gpt-4o-mini

supermedicine llm add openai \
  --api-format openai \
  --base-url https://api.openai.com/v1 \
  --api-key-env OPENAI_API_KEY \
  --model gpt-4o-mini \
  --set-current
```

## Step-By-Step Installation

### 1. Create A Virtual Environment (Recommended)

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
```

### 2. Clone And Install The Independent Python Core

```bash
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine
pip install -e .
```

Use `pip install -e ".[dev]"` only for development, testing, linting, or local
release checks.

### 3. Initialize Project

```bash
export OPENAI_API_KEY=<OPENAI_API_KEY>
python Install.py --init --provider openai --base-url https://api.openai.com/v1 --model gpt-4o-mini
```

This creates the `.supermedicine/` directory with configuration and plugin settings.
It does not require or create OpenCode/Claude Code configuration.

Optional LLM settings can be injected during this same step. These installer
values become the initial runtime default. If no complete provider exists later,
LLM runtime paths return a structured setup hint instead of guessing a model:

```bash
# Command-line flags
python Install.py --init --provider openai \
  --base-url https://api.openai.com/v1 \
  --api-key <OPENAI_API_KEY> \
  --model gpt-4o-mini

# Custom OpenAI-compatible provider (e.g., DeepSeek)
python Install.py --init --provider deepseek \
  --base-url https://api.deepseek.com/v1 \
  --api-key <DEEPSEEK_API_KEY> \
  --model deepseek-chat

# Environment variables; provider-specific key variables are preferred for real secrets
SM_LLM_PROVIDER=anthropic \
SM_LLM_BASE_URL=https://api.anthropic.com/v1 \
SM_LLM_MODEL=claude-3-5-sonnet-latest \
ANTHROPIC_API_KEY=<ANTHROPIC_API_KEY> \
python Install.py --init

# Prompt for values; API key input is hidden
python Install.py --init --interactive
```

`--provider` accepts `openai`, `anthropic`, or a custom OpenAI-compatible
provider name. Custom provider names default to OpenAI API format and use
`SM_LLM_API_KEY` as their generic key environment variable unless you later add a
provider-specific `api_key_env` with `supermedicine llm add`. `SM_LLM_PROVIDER`,
`SM_LLM_BASE_URL`, `SM_LLM_API_KEY`, and `SM_LLM_MODEL` are installer-time
generic overrides. Provider key variables for built-ins are `OPENAI_API_KEY` and
`ANTHROPIC_API_KEY`. If `--api-key`, `SM_LLM_API_KEY`, or a provider-specific key
variable is supplied during initialization, the resolved value can be written to
local `.supermedicine/config.yaml`; keep that file private after adding real
secrets.

### 3a. Add Providers After Initialization

Use the shared LLM manager through the CLI when you want to add, inspect, or
switch providers after initialization:

```bash
# Add OpenAI-compatible provider and set it as current default
supermedicine llm add openai \
  --api-format openai \
  --base-url https://api.openai.com/v1 \
  --api-key-env OPENAI_API_KEY \
  --model gpt-4o-mini \
  --set-current

# Add Anthropic-compatible provider for later use
supermedicine llm add anthropic \
  --api-format anthropic \
  --base-url https://api.anthropic.com/v1 \
  --api-key-env ANTHROPIC_API_KEY \
  --model claude-3-5-sonnet-latest

# Add custom OpenAI-compatible provider (DeepSeek, 智谱 GLM, Ollama, etc.)
supermedicine llm add deepseek \
  --api-format openai \
  --base-url https://api.deepseek.com/v1 \
  --api-key-env DEEPSEEK_API_KEY \
  --model deepseek-chat

# Secret-safe inspection and switching
supermedicine llm list
supermedicine llm show openai
supermedicine llm switch anthropic
```

`supermedicine llm switch <provider>` validates required fields, writes the
selected provider as both `llm.provider` and `llm.last_provider`, and persists the
change. On later startup the runtime restores `last_provider` when present;
otherwise it falls back to the install-time default provider.

### 3b. Configure By Editing `.supermedicine/config.yaml`

Manual editing is also supported. Keep real secrets out of the file by using
`api_key_env`:

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

### 3c. Configure In The TUI

Run `supermedicine tui`, open **LLM 管理**, enter provider name, BaseURL, model,
API key, and optional API format, then click **添加 Provider**. The key field is
password-style and is cleared after submission. Select a provider and click
**切换 Provider** to update the same current/default provider used by the CLI. On
TUI exit, the current provider is saved as `last_provider` for automatic restore
on the next startup.

### 4. Install Optional R Support

```bash
pip install -e ".[r]"
```

This installs rpy2. You must also install local R and the R `survival` package.
When available, request the R backend with `backend="r"` in r-survival action
parameters. If rpy2, R, or `survival` is unavailable, requested R backend calls
return a structured `plugin_unavailable` result instead of silently using R.
Without `backend="r"`, the plugin keeps using the deterministic pure-Python
fallback path.

## Verify Installation

Run the status command to check everything is working:

```bash
python Cli.py status
```

### Global CLI Access

After `pip install -e .`, the `supermedicine` command is installed as a Python
console script. If the command is not found, add the Python Scripts directory to
your PATH:

- **Windows**: `%APPDATA%\Python\Python<版本>\Scripts`
  (e.g., `C:\Users\<username>\AppData\Roaming\Python\Python314\Scripts`)
- **Linux/macOS**: `~/.local/bin`

Alternatively, use `python Cli.py` as a direct substitute for the `supermedicine`
command throughout this guide.

Expected output shows:
- SuperMedicine version
- Configuration initialized status
- Number of discovered plugins
- Number of test modules

To inspect LLM configuration without exposing secrets, use code paths that call
`ConfigCenter.get_llm_provider_config(redacted=True)` or review only placeholder
values in `.supermedicine/config.yaml`. LLM client calls return structured
validation errors such as `missing_api_key`, `missing_base_url`, or
`missing_model` when required values are absent.

For development environments, run the test suite:

```bash
python Cli.py test
# or directly:
pytest tests/ -v
```

The exact test count can change as optional adapter coverage evolves.

## Troubleshooting

### "No module named 'yaml'"
```bash
pip install pyyaml
```

### "Permission denied" On Windows
Run PowerShell as Administrator, or use:
```bash
python -m venv .venv --without-pip
```

### R Survival Tools Not Working
Install R >= 4.3, the rpy2 package, and R's `survival` package:
```bash
pip install -e ".[r]"
R -e "install.packages('survival', repos='https://cran.r-project.org')"
```

### CLI Command Not Found

If `supermedicine` is not recognized after `pip install -e .`, the Python Scripts
directory may not be on PATH. Two solutions:

1. **Add Scripts to PATH** (recommended):
   - Windows: Add `%APPDATA%\Python\Python<版本>\Scripts` to your user PATH
   - Linux/macOS: Add `~/.local/bin` to your PATH

2. **Use python Cli.py directly**:
   ```bash
   cd SuperMedicine
   python Cli.py status
   ```

After adding Scripts to PATH, restart your terminal and verify:
```bash
supermedicine --help
```

### LLM Provider Missing Key Or Endpoint

Use provider-specific environment variables for real credentials:

```bash
# OpenAI-compatible
export OPENAI_API_KEY=<OPENAI_API_KEY>

# Anthropic-compatible
export ANTHROPIC_API_KEY=<ANTHROPIC_API_KEY>
```

Use `SM_LLM_BASE_URL` or `--base-url` for compatible gateways. If you supplied a
real key through `--api-key` or `SM_LLM_API_KEY`, treat `.supermedicine/config.yaml`
as local private configuration and do not commit it.

If switching fails, run `supermedicine llm list` to confirm the provider name and
redacted fields, then add missing `base_url`, `api_key_env`/`api_key`, or `model`
with `supermedicine llm add <provider> ... --set-current`.

## Platform Adapters

Platform adapters are optional add-ons around the standalone Python framework.
Do not install or configure them unless you want platform-specific integration.

| Area | Core install required? | Current status |
|------|------------------------|----------------|
| Standalone Python CLI/Kernel | Yes | Default supported path |
| OpenCode add-on | No | Adapter surface, plugin metadata, skills, and agent role documents are present; no native OpenCode subagent runtime bridge unless a SuperMedicine orchestrator is injected |
| Claude Code add-on | No | Minimal capability/runtime/local-CLI invocation adapter; no native Claude Code skill loading or native subagent dispatch |

### Claude Code
Optional minimal adapter. Copy the skill directory only if you want local Claude
Code-facing documentation/metadata:
```bash
cp -r adapters/claude_code/ ~/.claude/skills/supermedicine/
```

The Python adapter supports `claude.capabilities`, `claude.runtime_status`, and
permission-checked `claude.invoke` when `claude` is on PATH. If `claude` is not
installed, the adapter reports a structured unavailable state. It does not expose
native Claude Code subagents or native Claude Code skill loading.

Claude Code uses SuperMedicine's optional provider metadata only. Configure
OpenAI-compatible or Anthropic-compatible settings through `Install.py`,
`SM_LLM_*`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or project-local config; never
store real keys in `adapters/claude_code/SKILL.md`.

### OpenCode
Optional OpenCode add-on content lives under `adapters/opencode/`. Copy or
reference `adapters/opencode/plugin.json`, `adapters/opencode/skills/*.md`, and
`adapters/opencode/agents/*.md` according to your OpenCode installation. The
adapter maps declared tools such as `bash`, `read`, `write`, `edit`, `glob`,
`grep`, `skill`, and `task`, with high-risk mutations/execution checked by the
SuperMedicine permission model.

Current limitation: `OpenCodeAdapter.subagent_dispatch(...)` does not launch an
external native OpenCode subagent runtime by itself. Without an injected
SuperMedicine orchestrator, it uses local metadata/fallback behavior.

OpenCode add-on manifests and skills declare the same OpenAI/Anthropic provider
formats and custom BaseURL support as the core configuration model. They contain
metadata only and must not contain plaintext real API keys.

## Safety Boundaries

- Core and adapter execution paths remain subject to the runtime
  `PermissionEngine` where actions cross execution, mutation, deletion, network,
  external API, or other high-risk resource boundaries.
- The prompt-context safety layer is advisory; the runtime code-layer permission
  check is the enforcement path.
- Medical statistics, writing, and citation helpers are research-support
  interfaces only. They do not provide clinical, regulatory, decision-support, or
  production-grade guarantees, and outputs require qualified human review.

## Uninstall

```bash
python Uninstall.py --dry-run
python Uninstall.py --force
python Uninstall.py --target .opencode/skills/supermedicine --dry-run
```

The uninstaller removes only SuperMedicine-owned local artifacts inside the
current project: `.supermedicine/`, runtime artifacts, repository-scoped
`.opencode/`, `.claude/`, and `superpowers/` copies ignored by this repository,
installer-created platform target copies recorded in
`.supermedicine/install-record.json`, and explicit `--target` paths. It does not
delete the source repository itself or unrecorded user-owned global OpenCode /
Claude Code configuration. Use `pip uninstall supermedicine` separately if you
installed the Python package and want to remove that package from the Python
environment.

Uninstall logs redact secret-looking fields. If you manually created environment
variables such as `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `SM_LLM_API_KEY`,
remove them from your shell/profile separately; the project uninstaller does not
edit user shell startup files.
