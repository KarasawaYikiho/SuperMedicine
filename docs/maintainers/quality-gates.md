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

## Human Maintenance Contract

```powershell
python -m scripts.maintainers.human_maintenance_snapshot --output Temp\human-maintenance-current.json
python -m pytest tests/feature_contract tests/test_core_convergence.py tests/test_application_service_boundaries.py -q
```

Compare a temporary snapshot before replacing the reviewed baseline. A baseline
update is an explicit review of Feature IDs, surfaces, signatures, file roles,
and implementation authorities; it is not a routine formatting step.

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

Run the final release commands and clean-install the built Wheel before release
claims:

```powershell
python -m pytest -q
python -m mypy core permission cli plugins agents adapters installer
python -m ruff check .
python -m build
npm run opentui:smoke
python -m pip install <wheel> --no-deps --target <clean-target>
python scripts/ci/smoke_wheel_install.py <clean-target>
```

The application EXE must pass `tui --dry-run`; GUI and Installer EXEs must pass
`--self-test`. A release publish must fail when its version tag or Release
already exists.

Generated wheels, build output, caches, and payload stages should stay outside
the tracked checkout or under ignored paths.
