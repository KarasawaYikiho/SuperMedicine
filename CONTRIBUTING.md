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

We use **ruff** for linting and formatting:

```bash
ruff check --select=E,F,W --ignore=E501 .
ruff check --fix .
```

Guidelines:
- All new code must have type annotations (`from __future__ import annotations`)
- Use `logging.getLogger(__name__)` instead of `print()`
- Follow existing code patterns in the module you are modifying
- Maximum line length: 120 characters (E501 is ignored)

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
- All 137 tests must pass before submitting a PR
- Use `tmp_path` fixture for temporary file tests

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes with clear, atomic commits
4. Ensure all tests pass: `pytest tests/ -v`
5. Ensure lint passes: `ruff check --select=E,F,W --ignore=E501 .`
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
