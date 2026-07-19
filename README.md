# SuperMedicine

<p align="center"><img src="assets/logo.jpg" alt="SuperMedicine" width="360"></p>

![Version](https://img.shields.io/badge/version-Beta0.4.2-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Language:** English | [Simplified Chinese](README.zh-CN.md)

SuperMedicine is a local-first Python framework for medical research assistance.
It provides a CLI, kernel, permission engine, plugin runtime, workspace and paper
management, LLM provider configuration, local RAG utilities, writing/citation
helpers, experiment/log workflows, and a Chinese OpenTUI terminal interface.

SuperMedicine is not a clinical decision system. Treat every generated output as
research assistance that needs qualified human review.

Current release label: **Beta0.4.2**. Python package fallback version:
**0.4.2b0**.

## Mandatory Harness and RAG Runtime

Every formal CLI, TUI, Web, plugin, LLM, and optional multi-agent task enters the
same Kernel pipeline. Harness and local-first RAG are required runtime
capabilities and cannot be disabled by configuration, environment variables, or
direct plugin parameters. Missing, damaged, or unwritable required components
fail closed with structured errors.

Knowledge-generation tasks retrieve evidence before generation. An empty index
is reported as `rag.status=empty`; sources are never fabricated. Deterministic
and control actions record an explicit `skipped` reason. PubMed remains
permission-gated and degrades to local evidence when denied. Multi-agent mode
defaults to `agents.mode: single` and uses the same Harness, RAG, permission,
audit, and result envelope as single mode.

## Read First

- [Installation guide](docs/guides/INSTALL.md)
- [Architecture overview](docs/architecture/ARCHITECTURE.md)
- [Security policy](SECURITY.md)
- [Contribution guide](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

## What It Includes

| Area | Scope |
| --- | --- |
| CLI and kernel | Command dispatch, configuration, event bus, plugin routing, sessions, and permission checks. |
| Permissions | Conservative by default, with explicit full-access acknowledgement and audit logging. |
| Workspaces | Explicit `--workspace` ids for workspace, paper, tool, and experience commands. |
| LLM providers | OpenAI, Anthropic, OpenRouter, and OpenAI-compatible custom endpoints through local config or environment variables. |
| Plugins | RAG, harness checks, medical writing, citation formatting, experiment helpers, Python/R tool templates, and figure utilities. |
| TUI | Chinese OpenTUI terminal interface backed by Bun and `@opentui/core@0.4.1`. |
| Optional adapters | OpenCode and Claude Code metadata/adapter files under `adapters/`; they are not required for the standalone Python runtime. |

## Install From Source

Requirements:

- Python 3.10 or newer
- Git
- pip
- Bun and npm for the OpenTUI runtime
- R 4.3 or newer only when using optional R-backed survival tooling

```bash
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine
python -m pip install -e .
npm ci
python install.py
supermedicine status
```

The lowercase `python install.py` path is the canonical source entry. For direct
module execution and lightweight fallback initialization, use `install_entry.py`.

For development:

```bash
python -m pip install -e ".[dev]"
```

For the OpenTUI smoke check:

```bash
npm run opentui:smoke
```

## Release Package Layout

Windows release archives are expected to keep the installer, Python sources,
OpenTUI manifests, documentation, and generated executables together.

Important release files include:

- `SuperMedicineInstaller.exe`
- `dist/SuperMedicine.exe`
- `install.py`
- `install_entry.py`
- `uninstall_entry.py`
- `installer/`
- `package.json`
- `package-lock.json`
- `THIRD_PARTY_NOTICES.md`
- `docs/guides/INSTALL.md`

Do not copy only `install.py` out of a release archive. The release installer
entrypoints import sibling packages and expect the archive layout to remain
intact.

## Quick CLI Tour

```bash
supermedicine status
supermedicine diagnose
supermedicine workspace init --workspace demo --name "Demo Workspace"
supermedicine paper import ./paper.pdf --workspace demo --title "Paper Title"
supermedicine experience suggest --workspace demo --summary "Keep useful prompts short"
supermedicine tool scan --language python
supermedicine tool add --workspace demo --select 1
supermedicine experiment list
supermedicine experiment start --protocol western_blot_basic --session-id wb-demo
supermedicine log follow --session-id wb-demo --interval 1 --max-entries 20
supermedicine tui
```

CLI commands always require explicit `--workspace` when they operate on a
workspace. They do not silently reuse the TUI's recent workspace.

## Configuration

Local runtime state lives under `.supermedicine/`.

| File or variable | Purpose |
| --- | --- |
| `.supermedicine/config.yaml` | Local runtime configuration. Keep it private. |
| `.supermedicine/policies/default.yaml` | Tracked default permission policy. |
| `.supermedicine/policies/audit.jsonl` | Local permission audit log. |
| `SM_CONFIG` | Override the config file path. |
| `SM_<KEY>` | Override config keys from the environment. |
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY` | Preferred key sources for common providers. |

Prefer environment variables or private config for secrets. Shared examples must
use placeholders such as `<OPENAI_API_KEY>`.

## Permissions

SuperMedicine has two file-access modes:

| Mode | Behavior |
| --- | --- |
| `conservative` | Default. Project-local access is allowed; external writes, deletes, and execution require explicit authorization or are denied. |
| `full` | Relaxes SuperMedicine's own checks after confirmation. It uses only the current OS user/process permissions and does not bypass UAC, ACLs, or administrator requirements. |

Useful commands:

```bash
supermedicine permission status
supermedicine permission roots
supermedicine permission authorize C:\path\to\allowed-dir
supermedicine permission revoke C:\path\to\allowed-dir
supermedicine permission mode conservative
supermedicine permission mode full --confirm-full
```

## TUI

Launch the Chinese OpenTUI interface:

```bash
supermedicine tui
supermedicine tui --dry-run
npm run opentui:smoke
```

The non-dry-run path uses Bun to start `core/tui/opentui_runtime.mjs` and the
pinned `@opentui/core@0.4.1` dependency.
If Bun is not on `PATH`, set `SUPERMEDICINE_OPENTUI_JS_RUNTIME` to a
Bun-compatible executable.

Global shortcuts:

| Key | Action |
| --- | --- |
| `Tab` | Move focus forward. |
| `Shift+Tab` | Move focus backward. |
| `Enter` | Submit the focused input or confirm the selected action. |
| `M` | Open or close the menu. |
| `P` / `Ctrl+P` | Open the permission view. |
| `Esc` / `B` | Go back from the current route or menu state. |
| `Q` | Quit the TUI. |

Number keys `1-0` are not direct view-switching shortcuts; they remain normal
input when the prompt has focus.

During active chat work, the status bar shows `Chat Processing`. Only the main
prompt input is locked until the request reaches success or failure; other
screen controls remain reachable through focus navigation and the `M` menu.
Dynamic refresh is targeted by screen and action rather than a broad filesystem
watcher or polling loop.

Readable UTF-8 labels covered by the TUI documentation tests include
`选择视图`, `切换主题`, `帮助`, `最大化/还原`, `LLM 状态`, and `任务运行状态`.

## LLM Providers

Provider records require:

- provider name
- API format (`openai`, `anthropic`, or `openrouter`)
- Base URL
- model
- API key or `api_key_env`

Example:

```bash
supermedicine llm add deepseek \
  --api-format openai \
  --base-url https://api.deepseek.com/v1 \
  --api-key-env DEEPSEEK_API_KEY \
  --model deepseek-chat \
  --set-current

supermedicine llm list
supermedicine llm show deepseek
supermedicine llm switch deepseek
```

## Local Quality Gate

```bash
python -m pip install -e ".[dev]"
ruff check --select=E,F,W --ignore=E501 .
python -m pytest tests/test_repo_hygiene.py tests/test_release.py tests/test_maintainer_markdown_links.py
```

Run the broader test suite before release work:

```bash
python -m pytest tests/ -v
```

## Repository Hygiene

Tracked files should be source, tests, CI, package metadata, docs, policies, and
small assets. Do not commit build output, caches, local workspaces, logs,
credentials, generated executables, or local archives. Historical archive notes
belong in ignored `Temp/`, not in `docs/archive/`.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `No module named 'yaml'` | Run `python -m pip install -e .`. |
| `supermedicine` is not found | Add the Python Scripts directory to `PATH`, or run `python -m cli_entry`. |
| TUI does not start | Run `npm ci`, confirm Bun is on `PATH`, then run `supermedicine tui --dry-run`. |
| Missing release executable | Use a complete release archive containing `dist/SuperMedicine.exe`. |
| LLM setup fails | Provide provider, API format, Base URL, model, and key source. |

## License

MIT. See [LICENSE](LICENSE).
