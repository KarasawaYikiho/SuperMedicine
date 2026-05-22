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
python install.py --init
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
python install.py --init
```

This creates the `.supermedicine/` directory with configuration and plugin settings.

### 4. Install Optional R Support

```bash
pip install -e ".[r]"
```

Required for Kaplan-Meier, log-rank test, and Cox proportional hazards analysis.

## Verify Installation

Run the status command to check everything is working:

```bash
python cli.py status
```

Expected output shows:
- SuperMedicine version
- Configuration initialized status
- Number of discovered plugins
- Number of test modules

Run the test suite:

```bash
python cli.py test
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
Install R >= 4.3 and the rpy2 package:
```bash
pip install rpy2
```

### CLI command not found
Ensure you are in the SuperMedicine directory:
```bash
cd SuperMedicine
python cli.py status
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
