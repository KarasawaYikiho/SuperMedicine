# Contributing to SuperMedicine

Thank you for contributing to SuperMedicine. This guide summarizes the local
development workflow for the **Beta0.4.1** codebase. User installation details
are in [INSTALL.md](INSTALL.md), and the local quality gate is in
[README.md](README.md#local-quality-gate).

## Development Environment

```bash
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
pip install -e ".[dev]"
```

Requirements: Python >= 3.10 and Git.

## Code Style

- Follow existing module patterns and public interfaces.
- Use type annotations for new Python code.
- Prefer `logging.getLogger(__name__)` over `print()` in application code.
- Use Ruff for linting and formatting; E501 line length is ignored by the local
  lint command documented in the README.
- Do not commit real API keys, private endpoints, audit logs with sensitive
  paths, or local `.supermedicine/` secrets.

Optional cleanup command:

```bash
ruff check --fix .
```

## Testing Expectations

All functional changes should include appropriate tests and pass the existing
suite before a pull request is submitted. Use the local quality gate documented
in [README.md](README.md#local-quality-gate) for the maintained test command;
targeted test or coverage variants may also be useful while developing.

Use `tmp_path` for temporary filesystem tests, keep tests deterministic, and avoid
live external provider calls unless a test is explicitly designed and gated for
that purpose.

## Documentation and Upload Scope

- Root Markdown files are the user-facing documentation intended for release
  upload.
- Do not add final-upload dependencies on excluded engineering folders such as
  `Docs/`, `docs/`, or `Architecture/`.
- If a Markdown file in an ignored directory must be published, either force-track
  it intentionally with review or provide a visible root-level alternative.
- Keep documented versions aligned: public/release label `Beta0.4.1`, Python
  package fallback version `0.4.1b0`.
- Use placeholders such as `<OPENAI_API_KEY>` in examples; never use real secrets.
- Keep external project references as design analysis unless code has been
  license-reviewed, implemented, and tested in this repository.

## File Naming

For future non-Python files and directories, prefer independent-word initial
capitalization when it does not affect tooling. Python import compatibility,
pytest discovery, plugin manifests, entry-point targets, and documented public
paths take priority over naming style.

Examples:

- Keep Python package and test paths import-safe, such as `supermedicine/` and
  `tests/test_kernel.py`.
- Keep pytest-compatible names such as `test_*.py`.
- Do not rename public plugin manifests or import paths only to satisfy a style
  preference.

## Pull Request Process

1. Fork the repository.
2. Create a feature branch.
3. Make clear, focused commits.
4. Run the local quality gate from [README.md](README.md#local-quality-gate).
5. Review repository hygiene before staging files.
6. Open a pull request against `master` with a summary of what changed and why.

## Commit Convention

Use conventional commit prefixes where practical:

```text
feat: add new feature
fix: fix a bug
refactor: code restructuring
style: formatting and linting
chore: maintenance tasks
ci: CI/CD changes
```

## Questions

Open a GitHub issue for questions, bugs, or proposed changes.
