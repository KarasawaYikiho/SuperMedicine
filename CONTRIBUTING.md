# Contributing

SuperMedicine is a Python medical-research assistant with OpenTUI, Web,
Desktop, and optional adapter surfaces. Contributions must be focused,
testable, and limited to behavior the repository can demonstrate.

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

## Engineering Rules

- Follow the existing package boundaries: CLI behavior in `cli/`, runtime
  services in `core/`, permissions in `permission/`, plugins in `plugins/`,
  installer behavior in `installer/`, and optional platform surfaces in
  `adapters/`.
- Document a capability only after code and tests establish it.
- Do not store secrets in docs, tests, manifests, logs, screenshots, or examples.
- Keep workspace-scoped behavior explicit; commands that operate on workspaces
  should require `--workspace`.
- Keep generated files, caches, release output, engineering plans, local
  archives, and runtime state out of Git.
- Treat files under `adapters/**/agents/*.md`, `adapters/**/skills/*.md`, and
  `adapters/claude_code/SKILL.md` as runtime inputs, not ordinary prose.

## Validation

Run focused checks while developing and the applicable gate before commit:

```bash
python scripts/maintainers/check_docs.py
python scripts/maintainers/sync_release_metadata.py --check
python -m pytest tests/test_repository_policy.py tests/test_release.py tests/test_docs_contract.py
python -m ruff check .
```

For release work or broad changes:

```bash
python -m pytest tests/ -v
```

The repository supports Python 3.10 through 3.13. CI installs the `dev` extra and
expects `pytest`, `ruff`, and `mypy` paths to remain usable.

## Documentation Standards

- Use concise, direct language and identify the intended audience.
- Keep commands executable and terminology consistent with current interfaces.
- Keep `README.md` and `README.zh-CN.md` aligned through the generated release
  metadata block.
- Keep release-package references to `SuperMedicineInstaller.exe`,
  `dist/SuperMedicine.exe`, `@opentui/core@0.4.3`, and
  `npm run opentui:smoke` when those contracts still apply.
- Do not track plans, debug logs, task ledgers, or archive notes; use ignored
  `Temp/` for local engineering material.
- Run the markdown link checker after doc changes:

```bash
python scripts/maintainers/check_docs.py
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
