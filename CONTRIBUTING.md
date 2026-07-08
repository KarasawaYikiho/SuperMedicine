# Contributing

This repository is a Python medical-research assistant with optional adapter and
OpenTUI surfaces. Keep changes small, testable, and honest about what is actually
implemented.

## Setup

```bash
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
npm ci
```

On Linux or macOS, activate the environment with:

```bash
source .venv/bin/activate
```

## Development Rules

- Follow the existing package boundaries: CLI behavior in `cli/`, runtime
  services in `core/`, permissions in `permission/`, plugins in `plugins/`,
  installer behavior in `installer/`, and optional platform surfaces in
  `adapters/`.
- Do not claim a capability in docs until code and tests support it.
- Do not store secrets in docs, tests, manifests, logs, screenshots, or examples.
- Keep workspace-scoped behavior explicit; commands that operate on workspaces
  should require `--workspace`.
- Keep generated files, caches, release output, local archives, and runtime state
  out of Git.
- Treat files under `adapters/**/agents/*.md`, `adapters/**/skills/*.md`, and
  `adapters/claude_code/SKILL.md` as runtime inputs, not ordinary prose.

## Quality Gate

Run targeted checks while developing, then run the relevant gate before commit:

```bash
python -m pytest tests/test_repo_hygiene.py tests/test_release.py tests/test_maintainer_markdown_links.py
ruff check --select=E,F,W --ignore=E501 .
```

For release or broad changes:

```bash
python -m pytest tests/ -v
```

The repository supports Python 3.10 through 3.13. CI installs the `dev` extra and
expects `pytest`, `ruff`, and `mypy` paths to remain usable.

## Documentation

- Keep root docs concise and current.
- Keep `README.md` and `README.zh-CN.md` aligned on release label
  `Beta0.4.2` and package fallback version `0.4.2b0`.
- Keep release-package references to `SuperMedicineInstaller.exe`,
  `dist/SuperMedicine.exe`, `@opentui/core@0.4.1`, and
  `npm run opentui:smoke` when those contracts still apply.
- Do not add new tracked archive notes under `docs/archive/`; use ignored
  `Temp/` for local archive material.
- Run the markdown link checker after doc changes:

```bash
python scripts/maintainers/check_markdown_links.py docs
```

## Pull Requests

1. Start from a clean `master`.
2. Create a focused branch.
3. Make the smallest change that handles the requirement.
4. Add or update tests when behavior changes.
5. Run the relevant quality gate.
6. Summarize what changed, why it changed, and what was verified.

## Commit Style

Use clear imperative messages. Conventional prefixes are welcome when useful:

```text
feat: add workspace import flow
fix: reject unsafe paper paths
docs: rewrite installation guide
test: cover permission mode switching
chore: clean ignored artifacts
```

## Security

Report security-sensitive issues through GitHub with enough detail to reproduce
the problem, but do not include real credentials, patient data, private endpoints,
or unredacted logs. See [SECURITY.md](SECURITY.md).
