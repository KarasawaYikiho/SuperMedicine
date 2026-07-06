# Quality Gates

This page documents the intended local and CI checks for human maintainers.
Commands that create caches or build outputs should write outside the repository
when possible.

## Local Scratch Root

For local Codex-assisted work in this checkout, prefer:

```text
D:\GIT\CodexTem\SuperMedicine
```

Use that location for temporary wheels, pytest basetemp directories, browser
artifacts, generated reports, and other scratch outputs when a tool supports an
output directory.

## Baseline Local Gate

```powershell
python -m pip install -e ".[dev]"
python -m ruff check --select=E,F,W --ignore=E501 .
python -m mypy . --cache-dir D:\GIT\CodexTem\SuperMedicine\mypy-cache
python -m pytest tests/ -v --tb=short --override-ini addopts= -p no:cacheprovider --basetemp D:\GIT\CodexTem\SuperMedicine\pytest
python -m pip wheel . --no-deps --wheel-dir D:\GIT\CodexTem\SuperMedicine\wheelhouse
```

Remove temporary output under `D:\GIT\CodexTem\SuperMedicine` after inspection
if it is no longer useful.

## Documentation Gate

```powershell
python scripts\maintainers\check_markdown_links.py docs\maintainers
python -m pytest tests/test_maintainer_markdown_links.py -q --override-ini addopts= -p no:cacheprovider --basetemp D:\GIT\CodexTem\SuperMedicine\pytest-maintainer-docs
```

The whole-tree docs check is useful during cleanup:

```powershell
python scripts\maintainers\check_markdown_links.py docs
```

Do not wire the whole-tree command into CI until existing broken links in
`docs/guides/` and `docs/archive/` are fixed or intentionally allowlisted.

## Optional Web Gate

Web tests require optional Web dependencies. CI should install the `web` extra
before claiming Web API coverage.

```powershell
python -m pip install -e ".[dev,web]"
python -m pytest tests/test_web_self_evolution.py -q --override-ini addopts= -p no:cacheprovider --basetemp D:\GIT\CodexTem\SuperMedicine\pytest-web
```

If diagnose or other Web endpoint tests are restored, include them in this gate.

## Optional OpenTUI Gate

OpenTUI checks require Node package installation and Bun-compatible runtime
availability.

```powershell
npm ci
npm run opentui:smoke
```

Python tests that mock subprocess calls do not prove the JavaScript runtime can
launch. Keep one real runtime smoke check in CI when OpenTUI is a supported user
surface.

## Packaging Gate

Building a wheel is weaker than installing it. A stronger packaging gate is:

1. Build wheel and sdist into a temp directory.
2. Create a fresh virtual environment.
3. Install the built artifact.
4. Run `supermedicine --help` and a minimal import check.

Keep PyInstaller work paths, wheelhouses, and payload stages under CI temp
directories where practical.

## Test Organization Rule

Prefer feature-focused test files. A large catch-all test file is acceptable only
when it is intentionally an integration suite and does not replace focused
regression tests for separate screens, routes, or command domains.
