# SuperMedicine Installation Guide

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | >= 3.10 | Required |
| Git | any | For cloning the repository |
| pip | >= 21.0 | For package installation |
| R | >= 4.3 | Optional, for survival analysis tools |

## Quick Install

```bash
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine
pip install -e ".[dev]"
python Install.py --init
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

### 2. Clone and Install

```bash
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine
pip install -e ".[dev]"
```

### 3. Initialize Project

```bash
python Install.py --init
```

This creates the `.supermedicine/` directory with configuration and plugin settings.

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

Run the test suite:

```bash
python Cli.py test
# or directly:
pytest tests/ -v
```

All 100 tests should pass.

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

### Claude Code
Copy the skill directory to your Claude skills folder:
```bash
cp -r adapters/claude_code/ ~/.claude/skills/supermedicine/
```

### OpenCode
The OpenCode adapter is fully implemented. Copy `adapters/opencode/plugin.json` to your OpenCode plugins directory. Configuration includes 6 skills and 4 agent definitions.

## Uninstall

```bash
pip uninstall supermedicine
rm -rf .supermedicine/
```
