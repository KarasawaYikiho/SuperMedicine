# Contributing to SuperMedicine

Thank you for your interest in contributing! This document outlines the process and guidelines.

## Development Environment

```bash
# Clone and set up
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
pip install -e ".[dev]"
```

Requirements: Python >= 3.10, Git

## Code Style

We use **ruff** for linting and formatting. Run the local quality gate documented
in [README.md](README.md#local-quality-gate-and-release-checklist) before
submitting changes.

```bash
# Optional local cleanup/formatting aid
ruff check --fix .
```

Guidelines:
- All new code must have type annotations (`from __future__ import annotations`)
- Use `logging.getLogger(__name__)` instead of `print()`
- Follow existing code patterns in the module you are modifying
- Maximum line length: 120 characters (E501 is ignored)

### New file naming

For future non-Python files and directories, prefer independent-word initial capitalization: each separate word should start with an uppercase letter while preserving clear word boundaries (for example, `ReleaseNotes.md`, `UserGuide.md`, or `ExampleAssets/`).

Python import compatibility takes priority over this style rule. Do **not** rename Python modules, packages, tests, plugin manifests, or files that are part of an existing public API only to satisfy capitalization preferences. Python paths must continue to support package discovery, pytest discovery, plugin loading, and stable imports.

Examples:
- Keep package and module paths import-safe, such as `supermedicine/`, `tests/test_kernel.py`, and any existing snake_case module names.
- Keep pytest-compatible test names such as `test_*.py`; do not change them to capitalized names if that would affect discovery.
- Keep plugin manifests, entry-point targets, and documented import paths stable unless a migration explicitly updates all consumers.
- When adding a new Python module or package, choose the name that is safest for imports and tooling first; use the capitalization convention only when it does not affect compatibility.

## Testing

All changes must include tests and pass the existing test suite:

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_kernel.py -v

# With coverage
pytest tests/ --cov=. --cov-report=term
```

Rules:
- New features require tests
- Bug fixes require regression tests
- The full regression suite must pass before submitting a PR
- Use `tmp_path` fixture for temporary file tests

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes with clear, atomic commits
4. Run the local quality gate documented in [README.md](README.md#local-quality-gate-and-release-checklist)
5. Review repository/upload hygiene using the README release checklist before staging files
6. Push and open a Pull Request against `master`
7. PR description should explain what and why

## Commit Convention

We follow conventional commits:

```
feat: add new feature
fix: fix a bug
docs: documentation changes
test: add or update tests
refactor: code restructuring
style: formatting and linting
chore: maintenance tasks
ci: CI/CD changes
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full system design.

## Questions?

Open an issue on GitHub.
