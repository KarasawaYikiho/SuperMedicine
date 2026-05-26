# SuperMedicine Installation Guide

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
python Install.py --init
```

For a core-only user install, omit development tooling:

```bash
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine
pip install -e .
python Install.py --init
python Cli.py status
python Cli.py run "summarize local context"
```

## Step-by-Step Installation

### 1. Create a Virtual Environment (Recommended)

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
```

### 2. Clone and Install the Independent Python Core

```bash
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine
pip install -e .
```

Use `pip install -e ".[dev]"` only for development, testing, linting, or local
release checks.

### 3. Initialize Project

```bash
python Install.py --init
```

This creates the `.supermedicine/` directory with configuration and plugin settings.
It does not require or create OpenCode/Claude Code configuration.

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

Expected output shows:
- SuperMedicine version
- Configuration initialized status
- Number of discovered plugins
- Number of test modules

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

### "Permission denied" on Windows
Run PowerShell as Administrator, or use:
```bash
python -m venv .venv --without-pip
```

### R survival tools not working
Install R >= 4.3, the rpy2 package, and R's `survival` package:
```bash
pip install -e ".[r]"
R -e "install.packages('survival', repos='https://cran.r-project.org')"
```

### CLI command not found
Ensure you are in the SuperMedicine directory:
```bash
cd SuperMedicine
python Cli.py status
```
Or install in development mode:
```bash
pip install -e .
supermedicine status
```

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
pip uninstall supermedicine
rm -rf .supermedicine/
```
