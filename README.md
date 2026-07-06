# SuperMedicine

<p align="center"><img src="assets/logo.jpg" alt="SuperMedicine" width="400"></p>

![Version](https://img.shields.io/badge/version-Beta0.4.2-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Language:** English | [简体中文](README.zh-CN.md)

SuperMedicine is an independent Python framework for medical research assistance.
It provides a standalone CLI, Kernel, permission-gated plugin execution,
workspace and paper management, local RAG utilities, medical writing/citation
helpers, LLM provider management, log reporting, multi-agent orchestration
components, and a Chinese OpenTUI-powered TUI. OpenCode and Claude Code integrations are
optional adapter surfaces; they are not required for the supported Python runtime.

Current public/release label: **Beta0.4.2**. Python package fallback version:
**0.4.2b0**.

Core references:

- [INSTALL.md](docs/guides/INSTALL.md) — installation, provider setup, release package layout,
  optional R support, and uninstall behavior.
- [ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md) — microkernel, plugin, permission, adapter,
  and repository-boundary design.
- [SECURITY.md](SECURITY.md) — security model, secret handling, medical-use limits,
  and disclosure guidance.
- [FUNCTION_MAP.md](docs/architecture/FUNCTION_MAP.md) — static callable inventory and its limits.
- [CHANGELOG.md](CHANGELOG.md) — release history.

## Project Positioning

SuperMedicine is research-support software, not a clinical decision system. It is
designed for local medical-research workflows where users keep control of
configuration, credentials, generated artifacts, paper imports, and workspace data.
Outputs from plugins, RAG, citation tools, statistics prototypes, experiment
guides, and LLM calls require qualified human review.

The default product boundary is the standalone Python CLI/Kernel/TUI. Platform
adapters under `adapters/` are add-ons around that core and must not be treated as
native OpenCode or Claude Code runtimes unless a capability is implemented and
tested.

## Feature Summary

- **Standalone Python core** — CLI, Kernel, configuration, event bus, plugin
  discovery, session state, workspace state, and runtime permission enforcement.
- **Permission-gated operations** — high-risk paths use `PermissionEngine.check()`,
  policy files under `.supermedicine/policies/`, and JSONL audit records.
- **LLM provider management** — OpenAI, Anthropic, OpenRouter, and custom
  compatible gateways selected by `api_format`, Base URL, model, and key source.
- **Research workspaces** — explicit workspace ids, copy-only paper import,
  user-confirmed experience records, workspace-local tool assets, and no implicit
  reuse of the TUI's recent workspace by CLI commands.
- **Plugin ecosystem** — RAG, harness monitoring, Python/R tool prototypes,
  experiment calculations, medical writing checklists, and AMA/Vancouver citation
  formatting.
- **Chinese TUI** — OpenTUI interface for chat, dashboard, workspace, paper,
  experience, tool, dialog history, LLM, experiment guide, permission mode, and
  log report screens.
- **Self-evolution preview** — generates Markdown/Python/R artifacts only after
  preview, explicit confirmation, path checks, permission checks, and overwrite
  controls.
- **Multi-agent components** — alpha/beta/gamma/delta roles, state machine, and
  checkpoints are present as orchestration components; external platform subagent
  runtimes are not launched by adapters alone.

## Installation

Requirements:

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | >= 3.10 | Required |
| Git | Any | Required for cloning source |
| pip | >= 21.0 | Required for package install |
| Bun | Latest stable | Required for the interactive OpenTUI runtime |
| npm | Lockfile-compatible | Required to install `@opentui/core@0.4.1` from `package-lock.json` |
| R | >= 4.3 | Optional, for the R survival backend |

Quick install from source:

```bash
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine
pip install -e .
npm ci
python Install.py
supermedicine status
```

`python Install.py` opens the ordinary interactive installer. The wizard asks for
the target project path, `.supermedicine` initialization, LLM provider details,
optional shortcut/PATH/Desktop Exe guidance, and final confirmation. If an
existing install is detected, the interactive path asks whether to update or
uninstall before changing files; update preserves `.supermedicine/config.yaml` and
user data by default.

Windows release packages may include **SuperMedicineInstaller.exe**. Run it with no
flags for the same console wizard plus release-payload extraction. A complete
release layout keeps `SuperMedicineInstaller.exe`, `dist/SuperMedicine.exe`,
`Install.py`, `installer/`, runtime packages, `package.json`, `package-lock.json`,
`THIRD_PARTY_NOTICES.md`, resources, and documentation
together. Do not copy only `Install.py` out of the archive.

Useful post-install checks:

```bash
python Cli.py status
supermedicine diagnose
supermedicine llm list
supermedicine log location
```

For virtual environments, development dependencies, optional R support, advanced
automation flags, release extraction examples, and uninstall details, see
[INSTALL.md](docs/guides/INSTALL.md).

## Quick Start

All CLI commands can be run as `supermedicine <command>` after installation or as
`python Cli.py <command>` from the repository root.

```bash
supermedicine status
supermedicine diagnose
supermedicine workspace init --workspace demo --name "Demo Workspace"
supermedicine paper import ./paper.pdf --workspace demo --title "Paper Title"
supermedicine experience suggest --workspace demo --summary "Keep prompts short"
supermedicine tool scan --language python
supermedicine tool add --workspace demo --select 1
supermedicine experiment list
supermedicine experiment start --protocol western_blot_basic --session-id wb-demo
supermedicine log follow --session-id wb-demo --interval 1 --max-entries 20
supermedicine tui
```

Workspace-scoped CLI commands require an explicit `--workspace`; they do not
silently reuse the TUI's recent workspace.
CLI commands always require explicit `--workspace`.

## Configuration

Local project state is stored under `.supermedicine/`. The main local configuration
file is `.supermedicine/config.yaml`; it may be ignored as runtime/private state and
can contain provider-specific local settings. Keep real credentials in environment
variables, private config, secret managers, or CI secrets.

Environment and configuration notes:

- `SM_CONFIG` can override the config file path.
- `SM_<KEY>` style variables can override configuration keys.
- Provider keys should use variables such as `OPENAI_API_KEY`,
  `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`, or a custom key variable referenced by
  `api_key_env`.
- The tracked default policy is `.supermedicine/policies/default.yaml`; runtime
  audit logs are written to `.supermedicine/policies/audit.jsonl`.

## Permissions

File access mode is stored in `.supermedicine/config.yaml` and is shared by CLI,
TUI, and later policy reads.

| Mode | Behavior | Risk and limits |
|------|----------|-----------------|
| `conservative` | Default. Project-local paths are allowed; project-external reads may require prompting; project-external writes, deletes, and execution are denied unless explicitly authorized. Aliases include `sandbox` and `safe`. | Recommended for daily use. Reduces accidental deletion, broad reads, and unauthorized execution. |
| `full` | Relaxes SuperMedicine's own file-access restrictions after explicit confirmation. | High risk. It uses only the current OS user/process permissions, does not silently elevate, and does not bypass UAC, administrator requirements, ACLs, or other OS controls. |

CLI entry points:

```bash
supermedicine permission status
supermedicine permission roots
supermedicine permission authorize C:\path\to\allowed-dir
supermedicine permission revoke C:\path\to\allowed-dir
supermedicine permission mode conservative
supermedicine permission mode full --confirm-full
```

In the TUI, open the permission screen from the sidebar entry `P 🛡️ 权限模式` or the
global `P` shortcut. Switching to full access requires the confirmation text
`FULL`.

## Security and Medical-Use Boundaries

- SuperMedicine is for research assistance, not diagnosis, treatment, regulatory
  approval, or clinical decision support.
- Paper import is copy-only and does not upload source files by default.
- Paper enrichment and external-resource actions require explicit confirmation and
  permission checks where implemented.
- Experience learning stores user-confirmed summaries, not raw conversations.
- Diagnostics, log reports, and LLM/provider views redact common secret carriers,
  but users must still avoid publishing raw logs, private paths, patient data,
  private endpoints, or credentials.
- Ordinary chat fields, log text, README files, issue reports, and command history
  are not safe places for API keys or patient identifiers.

See [SECURITY.md](SECURITY.md) for the full policy.

## Plugins and Research Tools

Plugins are discovered from manifests under `plugins/` and execute through the
Kernel and permission model where applicable.

| Area | Current scope |
|------|---------------|
| RAG | Local TF-IDF provider and provider-interface contracts, with structured errors and secret-safe configuration boundaries. |
| Harness | Monitoring, audit, checkpoint, and quality-assessment helpers. |
| Medical writing | CONSORT, STROBE, PRISMA, and STARD checklist helpers. |
| Medical citation | AMA and Vancouver citation formatting helpers. |
| Python/R tools | Prototype statistics, survival-analysis interfaces, and workspace-importable data-analysis tool templates. |
| Experiments | Config-driven experiment guide protocols under `plugins/experiments/`, including WB as one ordinary configuration example. |

Python/R tool authoring follows the scanned directory format
`plugins/tools/<tool-directory>/` with a `tool.yaml` manifest and `runner.py` or
`runner.R`. Users can scan and import without memorizing a tool id:

```bash
supermedicine tool scan --language python
supermedicine tool add --workspace demo --select 1
```

## TUI

Launch the Chinese OpenTUI terminal workspace with:

```bash
supermedicine tui
supermedicine tui --dry-run
npm run opentui:smoke
```

`--dry-run` prints readiness information without starting the interactive UI. The
non-dry-run path starts `core/tui/opentui_runtime.mjs` through Bun and the pinned
`@opentui/core@0.4.1` dependency. Source checkouts and extracted release packages
must run `npm ci` once from the repository/release root, and Bun must be on `PATH`
(or `SUPERMEDICINE_OPENTUI_JS_RUNTIME` must point to a Bun-compatible executable).
The TUI reads project-local `.supermedicine/`, `workspaces/`, and `plugins/` state.

Global shortcuts:

| Key | Action |
|-----|--------|
| `Tab` | Move focus forward between interactive controls. |
| `Shift+Tab` | Move focus backward between interactive controls. |
| `Enter` | Submit the focused input or confirm the selected action. |
| `M` | Toggle the OpenTUI route/menu shell. |
| `P` / `Ctrl+P` | Open the permission-mode view. |
| `Esc` / `B` | Return/back from the current route/menu state. |
| `↑↓` / `j k` | Move the selected route/action/list item where available. |
| `/` | Focus page filtering where available. |
| `[` / `]` | Scroll page content where available. |
| `Ctrl+1` ... `Ctrl+0` | Jump directly to primary OpenTUI routes. |
| `Q` | Quit the TUI. |

The OpenTUI runtime provides a shared top/footer/sidebar route shell for Chat,
Dashboard, Workspace, Paper, Experience, Tool, Dialog, LLM, Experiment, Log,
Permission, Self-evolution, and Diagnose pages. Status lines continue to show
entries such as `LLM 状态` and `任务运行状态`.
The menu route labels remain `选择视图`, `切换主题`, `帮助`, and `最大化/还原`;
the legacy mojibake compatibility markers `ѡ����ͼ`, `�л�����`, and `����`
are retained here so encoding-regression checks can detect accidental
documentation boundary drift.
Alphabetic global shortcuts are documented as uppercase-only (`M`, `P`, `Q`) so
lowercase text such as `m`, `p`, and `q` plus IME composition remain ordinary input when the prompt has focus.
Number keys `1-0` are not direct view-switching shortcuts;
they remain normal input when the prompt has focus. `Backspace`, `Ctrl+H`, and common delete control
bytes are handled by the prompt input instead of being swallowed by global
shortcuts.

During active chat work, the status bar shows `Chat Processing`. Only the main
prompt input is locked until the request reaches success or failure; secondary
screen controls remain reachable through focus navigation and the `M` menu.
Dynamic TUI refresh is intentionally targeted rather than a broad filesystem
watcher or polling loop. The code-backed inventory is workspace, log,
dashboard, tool, and dialog refresh surfaces; these refresh when entered or
switched to, when their refresh action is used, or after related operations update
their data. Other dynamic surfaces should be inventoried and fixed individually
if stale-display evidence is found.

The TUI string inventory keeps English emphasis labels such as `User`, `System`,
`Assistant`, `Error`, `Status`, and `Output` as single capitalized words while
preserving Chinese-first navigation and screen titles. This is not a full
English-only title sweep.

For TUI visual redesign work, `scripts/tui_preview_artifact.py` can generate a
text preview artifact in the user's Downloads directory by default. The workflow
records preview metadata only; it does not create an image by itself and does not
claim user approval. Any substantial visual redesign remains gated on a preview
and explicit user confirmation.

Main screens include chat, dashboard, workspace management, paper management,
experience learning, tool management, dialog history, LLM management, experiment
guide, permission mode, and log report.

## LLM Providers

Initialization and LLM-backed tasks require a complete provider configuration:
`provider`, `base_url`, `model`, and either `api_key` or `api_key_env`. Missing
fields are reported as setup/provider errors rather than treated as success.

| API format | Default Base URL | Default key env | Default model |
|------------|------------------|-----------------|---------------|
| `openai` | `https://api.openai.com/v1` | `OPENAI_API_KEY` | `gpt-4o-mini` |
| `anthropic` | `https://api.anthropic.com/v1` | `ANTHROPIC_API_KEY` | `claude-3-5-sonnet-latest` |
| `openrouter` | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` | `anthropic/claude-3.5-sonnet` |

Example custom provider:

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

Prefer `--api-key-env` for real credentials. Shared examples should use
placeholders only.

## Logs and Diagnostics

Use `supermedicine diagnose` for secret-safe configuration, provider readiness,
audit-log path checks, log-storage paths, and repair suggestions.

Log reports are stored project-locally under `.supermedicine/logs/` by default;
permission audit records are stored under `.supermedicine/policies/audit.jsonl`.

```bash
supermedicine log location
supermedicine log location --session-id wb-demo
supermedicine log follow --session-id wb-demo --interval 1 --max-entries 20
supermedicine log follow --file session-wb-demo.json --once
```

`log follow` prints redacted storage paths, refresh information, line limits, and
redacted log lines. It runs until interrupted unless `--once` or an iteration limit
is used. The TUI Log report screen provides equivalent refresh and auto-follow
behavior.

## Multi-Agent and Optional Adapters

The repository includes alpha, beta, gamma, and delta agent roles plus state-machine
and checkpoint components for orchestration inside the Python architecture.

| Capability | Standalone core | OpenCode add-on | Claude Code add-on |
|------------|-----------------|-----------------|--------------------|
| CLI init/status/run | Supported | Can wrap metadata | Minimal adapter path |
| Permission engine | Supported | Used for adapter operations | Used before tool execution |
| Plugin discovery/execution | Supported | Metadata integration | Not native |
| Native platform tool calls | Not required | Declared mappings | `claude.invoke` only |
| Native subagent runtime | Not applicable | Not launched by adapter alone | Not implemented |

Adapter metadata and skills live under `adapters/`. They must remain credential-free
and should not claim external runtime features that are not implemented.

## Testing and Local Quality Gate

For development and release checks, use the project quality commands documented by
maintainers. A typical local gate includes dependency installation, linting,
packaging smoke checks, and the test suite:

```bash
pip install -e ".[dev]"
ruff check --select=E,F,W --ignore=E501 .
python -m pip wheel . --no-deps --wheel-dir .pytest-tmp/wheel-smoke
pytest tests/ -v
```

The CLI also contains a legacy `supermedicine test` command path, but release work
should follow the maintained quality gate above and CI packaging smoke checks.

## Release and Version Information

- Public/release label: **Beta0.4.2**.
- Python package fallback version: **0.4.2b0**.
- Package metadata is defined in [pyproject.toml](pyproject.toml).
- OpenTUI runtime dependency metadata is defined in [package.json](package.json)
  and [package-lock.json](package-lock.json), pinned to `@opentui/core@0.4.1`.
- Release history is recorded in [CHANGELOG.md](CHANGELOG.md).
- GitHub Wiki publication evidence for the current debug-documentation pass is
  recorded in the architecture tracking docs as remote commit `d6a1e11`; local
  repository tests cannot prove future remote Wiki availability or content.
- The fixed Beta0.4.2 release layout keeps installer entry points, the installer
  package, runtime packages, OpenTUI npm manifests, `THIRD_PARTY_NOTICES.md`,
  documentation/templates, and `dist/SuperMedicine.exe` together.
- Generated build artifacts, runtime logs, caches, local workspaces, local config,
  and desktop Exe files should not be committed.

## Planned or Under Review

Items captured in private/debug planning notes but not represented by implemented
code, tests, tracked release documentation, or recorded external evidence are
**planned** or **under review**, not completed. Remaining external or
approval-gated items include user approval of any TUI preview, image/screenshot
preview output if specifically required, OS-level IME verification, a full
English-only TUI title sweep that would replace Chinese-first localization, a
fresh legal-safe external OpenCode comparison/alignment program, and any broad
whole-repository refactor. Future native platform runtime bridges, broader
autonomous repository maintenance, clinical validation, and any capability that
would bypass current permission or OS controls must be implemented, reviewed, and
tested before documentation can describe it as supported.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `No module named 'yaml'` | Install dependencies with `pip install -e .` or install `pyyaml`. |
| `supermedicine` command not found | Add the Python Scripts directory to PATH or use `python Cli.py`. |
| Initialization fails with missing LLM fields | Provide provider, Base URL, model, and an API key source. |
| `ModuleNotFoundError: No module named 'installer'` | Run from a complete source/release directory; do not copy only `Install.py`. |
| Missing `SuperMedicine.exe` in a release package | Re-download or regenerate the complete release package containing `dist/SuperMedicine.exe`. |
| TUI launch issue | Run `supermedicine tui --dry-run`, `npm ci`, and `npm run opentui:smoke`; confirm Bun is installed/on `PATH`. |
| Self-evolution did not write files | Preview is default; writing requires `--no-preview --confirm-write` and an allowed output root. |
| Log page does not follow newest records | Re-enable auto-follow in the TUI Log report screen or refresh the list. |

## License

MIT License — see [LICENSE](LICENSE) for details.
