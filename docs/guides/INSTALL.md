# Installation Guide

This guide covers source installs, development installs, release archive layout,
OpenTUI setup, LLM provider configuration, and uninstall behavior for
SuperMedicine **Beta0.4.2**.

For a short overview, see [README.md](../../README.md). For security boundaries,
see [SECURITY.md](../../SECURITY.md).

## Requirements

| Requirement | Version | Needed for |
| --- | --- | --- |
| Python | 3.10 or newer | Core runtime |
| pip | Current enough for editable installs | Package install |
| Git | Any recent version | Source checkout |
| npm | Lockfile-compatible | OpenTUI dependency install |
| Bun | Current stable | OpenTUI runtime |
| R | 4.3 or newer | Optional R survival backend |

## Source Install

```bash
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine
python -m pip install -e .
npm ci
python install.py
supermedicine status
```

Use `python install.py` for new source checkouts. Use `python install_entry.py`
when invoking the dependency-light module entry directly.

The installer creates or updates local `.supermedicine/` state. It asks for the
target project root, optional LLM provider settings, and confirmation before
writing installer-owned files.

## Development Install

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
npm ci
```

Linux/macOS activation:

```bash
source .venv/bin/activate
```

Run a focused local gate:

```bash
python -m pytest tests/test_repo_hygiene.py tests/test_release.py tests/test_maintainer_markdown_links.py
```

## LLM Provider Setup

Provider records need a provider name, API format, Base URL, model, and key
source. Prefer environment variables for keys:

```bash
set OPENAI_API_KEY=<OPENAI_API_KEY>
```

Example custom provider:

```bash
supermedicine llm add deepseek ^
  --api-format openai ^
  --base-url https://api.deepseek.com/v1 ^
  --api-key-env DEEPSEEK_API_KEY ^
  --model deepseek-chat ^
  --set-current
```

Useful checks:

```bash
supermedicine llm list
supermedicine llm show deepseek
supermedicine diagnose
```

## OpenTUI Setup

The TUI uses Bun and the npm lockfile dependency `@opentui/core@0.4.3`.

```bash
npm ci
npm run opentui:smoke
supermedicine tui --dry-run
supermedicine tui
```

If Bun is not on `PATH`, set `SUPERMEDICINE_OPENTUI_JS_RUNTIME` to a
Bun-compatible executable.

## Release Archive Layout

Release archives must stay intact. The installer entrypoints import sibling
packages and resources.

Required release files include:

- `SuperMedicineInstaller.exe`
- `dist/SuperMedicine.exe`
- `SuperMedicineGUI.exe`
- `install.py`
- `install_entry.py`
- `uninstall_entry.py`
- `installer/`
- `core/`
- `permission/`
- `plugins/`
- `adapters/`
- `package.json`
- `package-lock.json`
- `THIRD_PARTY_NOTICES.md`
- `docs/guides/INSTALL.md`

`SuperMedicineInstaller.exe` defaults to yes for release payload extraction when
run as a frozen installer. Scripted CI paths may pass `--extract-release-to` and
`--release-payload-root` to control extraction targets.
Use `--release-exe dist/SuperMedicine.exe` only for the compatibility CLI Exe.
Use `--release-gui-exe SuperMedicineGUI.exe` for the desktop GUI; unified installs
select the GUI desktop entry by default.
Use `--exe-dry-run` when validating installer behavior without copying files.

Do not copy only `install.py` or `SuperMedicineInstaller.exe` out of the release
directory.

## What the interactive questions mean

Ordinary users should run `python install.py` with no flags from a source checkout
or run `SuperMedicineInstaller.exe` from a complete release archive. Source `python install.py` usually defaults to no for release payload extraction because
source checkouts normally do not contain `dist/SuperMedicine.exe`.
`SuperMedicineInstaller.exe` defaults to yes when it is run from a staged release payload.

Advanced automation / CI may use explicit flags such as:

```bash
python install.py --release-exe dist/SuperMedicine.exe --exe-dry-run
python install.py --release-gui-exe SuperMedicineGUI.exe --exe-dry-run
python install.py --extract-release-to C:\Temp\SuperMedicine --release-payload-root C:\Temp\SuperMedicinePayload --exe-dry-run
```

If the executable path is wrong, installer output may report:

```text
Exe source does not exist
```

## Common Commands

```bash
supermedicine status
supermedicine diagnose
supermedicine permission status
supermedicine workspace init --workspace demo --name "Demo Workspace"
supermedicine paper import ./paper.pdf --workspace demo --title "Paper Title"
supermedicine log location
```

Workspace-scoped commands require explicit `--workspace`.

## Uninstall

Dry run first:

```bash
python uninstall_entry.py --dry-run
```

Remove installer-owned local artifacts:

```bash
python uninstall_entry.py --force
```

Preserve user data when needed:

```bash
python uninstall_entry.py --force --preserve-user-data
```

The uninstaller does not remove the source repository or uninstall the Python
package by default. It targets project-owned runtime state and installer-recorded
artifacts.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `supermedicine` is not found | Add Python Scripts to `PATH`, or run commands through `python -m cli_entry`. |
| `No module named 'yaml'` | Run `python -m pip install -e .`. |
| TUI fails before launch | Run `npm ci`, confirm Bun is installed, then run `supermedicine tui --dry-run`. |
| Release installer cannot import `installer` | Use a complete extracted release archive. |
| `ModuleNotFoundError: No module named 'installer'` | You probably copied an installer entrypoint out of the archive. Run from the complete extracted release directory. |
| Missing `dist/SuperMedicine.exe` | Re-download or rebuild the complete release artifact. |
