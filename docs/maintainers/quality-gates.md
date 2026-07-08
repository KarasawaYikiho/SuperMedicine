# Quality Gates

Use the smallest gate that proves the change, then run broader checks before
release or risky refactors.

## Documentation Gate

```powershell
python scripts\maintainers\check_markdown_links.py docs
python -m pytest tests/test_maintainer_markdown_links.py -q
```

## Repository Hygiene and Release Docs

```powershell
python -m pytest tests/test_repo_hygiene.py tests/test_release.py -q
```

## Python Gate

```powershell
python -m pip install -e ".[dev]"
python -m ruff check --select=E,F,W --ignore=E501 .
python -m pytest tests/ -v
```

## Optional Web Gate

```powershell
python -m pip install -e ".[dev,web]"
python -m pytest tests/test_web_self_evolution.py -q
```

## Optional OpenTUI Gate

```powershell
npm ci
npm run opentui:smoke
```

Python subprocess-mock tests do not prove the JavaScript runtime can launch.
Keep at least one real OpenTUI smoke check when changing TUI release behavior.

## Packaging Gate

Build into a temp directory, install into a fresh environment, and run
`supermedicine --help` plus minimal imports before release claims.

Generated wheels, build output, caches, and payload stages should stay outside
the tracked checkout or under ignored paths.
