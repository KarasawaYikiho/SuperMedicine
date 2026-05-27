# SuperMedicine

![Version](https://img.shields.io/badge/version-Beta0.2.1-blue)

Release-ready label: `Beta0.2.1`. Python package metadata uses `0.2.1b0`
because PEP 440 packaging validation rejects `Beta0.2.1` as a Python project
version. No tag, release, publish, or upload has been created by this release
readiness update.

Independent Python medical research agent framework with RAG, plugin execution,
and permission-gated orchestration. SuperMedicine runs as a standalone Python
package by default; OpenCode, Claude Code, and similar assistant platforms are
optional add-on adapters around the core, not core runtime requirements.

## Features

- **Modular Architecture** — Microkernel + multi-Agent orchestration with plugin system
- **P0 Permission Engine** — Code-layer runtime permission constraints with prompt-context safety guidance
- **Plugin Ecosystem** — RAG retrieval, Harness monitoring, prototype Python/R statistics interfaces, medical writing standards
- **Core standalone by default** — install and run the Python CLI/kernel without OpenCode, Claude Code, or any assistant-platform runtime
- **Optional platform add-ons** — OpenCode adapter content and a minimal Claude Code CLI adapter are available for platform-specific workflows, with documented limits
- **Medical Standards** — CONSORT, STROBE, PRISMA, STARD reporting checklists; AMA/Vancouver citation formatting constraints

## Core independent + platform add-on model

SuperMedicine's supported default model is **core independent + platform
add-ons**:

- **Core independent runtime** — `Cli.py`, `core/**`, `permission/**`,
  `agents/**`, and `plugins/**` provide the Python CLI, Kernel, permission
  engine, in-process orchestration concepts, RAG, harness, prototype statistics,
  and medical writing/citation helpers. This path does not require OpenCode,
  Claude Code, `claude`, or platform configuration directories.
- **OpenCode optional add-on** — `adapters/opencode/**` provides an OpenCode
  adapter surface, plugin metadata, skill documents, and agent role documents.
  It supports the implemented adapter tool mapping and permission-gated
  high-risk operations, but it does **not** launch a native OpenCode subagent
  runtime by itself when no SuperMedicine orchestrator is injected.
- **Claude Code minimal optional add-on** — `adapters/claude_code/**` provides
  capability reporting, runtime probing, and permission-checked
  `claude --print` invocation when a local `claude` command is available. It
  does **not** implement native Claude Code skill loading or native Claude Code
  subagent dispatch.

### Installation completeness model

`install.json` is the agent-readable installation manifest. It declares the
standalone Python core as the default product path and lists OpenCode and Claude
Code only as optional add-ons under `adapters/`. The platform entries point to
real repository files and intentionally expose exactly one user-facing platform
agent/surface: `SuperMedicine`.

- OpenCode entry: `adapters/opencode/plugin.json`, with `adapter.py`, six skill
  documents, one user-facing `agents/supermedicine.md` file, and four
  non-user-facing internal role context documents.
- Claude Code entry: `adapters/claude_code/SKILL.md`, with
  `adapters/claude_code/adapter.py` providing capability reporting, runtime
  status, and permission-checked `claude.invoke` only.
- α/β/γ/δ are internal SuperMedicine role contexts/capabilities, not separate
  OpenCode or Claude Code user-facing Agents.
- Missing platform runtimes are adapter degraded/unavailable states, not core
  SuperMedicine installation failures.

## Medical statistics boundary

The current `python-stats` and `r-survival` plugins provide stable input/output
contracts and deterministic smoke fixtures for development tests, but
SuperMedicine does not promise production-grade, clinical-grade,
regulatory-grade, or decision-support statistical accuracy. `r-survival` uses a
pure-Python fallback by default and formally supports an optional R/rpy2 backend
for Kaplan-Meier, log-rank, and Cox PH actions when local R and the R `survival`
package are available. Outputs require qualified expert review before any
research, regulatory, or clinical use.

## RAG external database/vector index integration

RAG supports a stable provider contract for local retrieval, PubMed retrieval,
and external database/vector-index backends. External providers use explicit
configuration (`endpoint`, `index_name`, optional `namespace`, `api_key_env`, and
`timeout_seconds`) and must reference secrets through environment variable names
rather than hardcoding credentials. A deterministic mock external vector-store
backend is included so development and tests do not require a live service.

## Safety and resource controls

Adapter calls, RAG external resources, and plugin execution paths use the
canonical permission policy where they cross execution or external-resource
boundaries. Claude Code adapter invocations expose structured timeout,
unavailable, and runtime errors with timeout metadata. RAG providers expose
configuration, connection, timeout, and resource errors without dereferencing or
printing secret values; secret references should use environment variable names.
Plugin execution through `Kernel` carries resource/security metadata and remains
permission-gated. The canonical default policy path is
`.supermedicine/policies/default.yaml`.

## Repository and upload hygiene

Only necessary project files should be committed or uploaded. Do not include
`Docs/`, `Superpower`, `superpower`, external skill packages, or non-essential
documentation artifacts in Git uploads for this repository.

This documentation update does not create a tag, release, publish, package
upload, paper upload, or external artifact upload.

## Quick Start

Standalone core install and initialization:

```bash
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine
pip install -e .
```

> **注意**: `pip install -e .` 会安装 `supermedicine` 命令行工具。
> 如果安装后 `supermedicine` 命令不可用，请将 Python Scripts 目录添加到 PATH：
> - **Windows**: `%APPDATA%\Python\Python<版本>\Scripts`（例如 `C:\Users\<用户名>\AppData\Roaming\Python\Python314\Scripts`）
> - **Linux/macOS**: `~/.local/bin`
>
> 或者始终使用 `python Cli.py` 代替 `supermedicine` 命令。

```bash
python Install.py --init
python Cli.py status
python Cli.py run "summarize local context"
```

Use `pip install -e ".[dev]"` only when you need development/test/lint tooling.
Use `pip install -e ".[r]"` only when you need the optional R/rpy2 survival
backend and have local R plus the R `survival` package available.

## CLI Usage

```bash
python Cli.py init      # Initialize project
python Cli.py status    # Show project status
python Cli.py test      # Run all tests
python Cli.py run TASK  # Execute a task through the initialized Kernel and plugins
```

No-platform example using only the Python core:

```bash
python Install.py --init
python Cli.py run "Find locally available RAG and writing capabilities"
supermedicine workspace init --workspace literature-review --name "Literature Review"
supermedicine run "summarize workspace notes" --workspace literature-review
```

Workspace-aware commands are explicit by design. Workspaces live under
`workspaces/<id>`, where `<id>` is a lowercase slug made from letters, digits,
and hyphens. CLI commands never infer the last TUI workspace; every
workspace-scoped CLI action requires `--workspace <id>`.

```bash
supermedicine workspace init --workspace hypertension-review --name "Hypertension Review"
supermedicine run "summarize local context" --workspace hypertension-review
supermedicine paper import ./paper.pdf --workspace hypertension-review --title "Trial paper"
supermedicine experience suggest --workspace hypertension-review --summary "Keep extraction prompts short"
supermedicine tui  # launches the Chinese TUI workbench
```

### Workspaces, papers, TUI, and experience learning

- **Workspace layout** — `supermedicine workspace init --workspace <slug>`
  creates `workspaces/<slug>` with workspace-local `.supermedicine/`, paper,
  notes, output, checkpoint, session, and local RAG directories.
- **Explicit CLI workspace use** — `run`, `paper`, and `experience` CLI paths
  require or accept an explicit `--workspace`; they do not read TUI recent-state
  files or silently select a workspace.
- **Chinese TUI** — `supermedicine tui` starts the Chinese-language terminal UI.
  TUI recent selection is workspace/session state and does not alter CLI defaults.
- **Workspace deletion** — `supermedicine workspace delete --workspace <slug>
  --confirm <slug>` is a hard delete. The confirmation must exactly match the
  workspace id, the path must pass destructive-path guards, PermissionEngine must
  authorize `workspace.delete`, and audit records are written for cancellation,
  denial, and deletion outcomes.
- **Paper import** — imports are copy-only: the source file is read and copied to
  the workspace, never moved or uploaded. Supported local formats are PDF, TeX,
  BibTeX/RIS, TXT, and Markdown (`.pdf`, `.tex`, `.bib`, `.ris`, `.txt`, `.md`).
  Imported papers are deduplicated by SHA-256 and by normalized DOI/PMID when
  supplied. Metadata such as title, authors, DOI, PMID, notes, and tags remains
  editable after import.
- **Paper metadata enrichment** — online or external metadata enrichment requires
  explicit `--confirm-enrich`, a PermissionEngine check with network and
  external-API hard-limit context, and audit logging. There is no silent network
  access during ordinary import.
- **Experience learning** — experience learning is enabled by default, but raw
  conversations are not stored. Only user-confirmed summaries/experience records
  are persisted. General method experience is stored in the OS temp directory
  method layer; project-specific details remain workspace-local. Users can
  suggest, add, list, view, edit, delete, and export experience records.

See [Architecture/WorkspaceTuiRagGuide.md](Architecture/WorkspaceTuiRagGuide.md)
for the detailed workspace/TUI/RAG usage guide.

## Architecture

```
supermedicine/
├── core/           # Microkernel, event bus, plugin registry
├── permission/     # P0 priority — policy, audit, engine, prompt constraints
├── agents/         # State machine, checkpoint, orchestrator, base agent
├── plugins/
│   ├── rag/        # RAG retrieval interface + local/mock external providers
│   ├── harness/    # Testing, monitoring, quality assessment
│   ├── tools/      # Python stats + R survival analysis
│   └── standards/  # Medical writing checklists + citation formatters
├── adapters/       # Optional platform add-ons (OpenCode, minimal Claude Code, standalone facade)
├── Cli.py          # CLI entry point
└── install.json    # Agent-readable installation manifest
```

### Capability matrix

| Capability | Standalone Python core | OpenCode add-on | Claude Code add-on |
|------------|------------------------|-----------------|--------------------|
| Install/init without assistant platform | Supported default | Not required | Not required |
| CLI `init` / `status` / `run` via Kernel | Supported | Can wrap/adapt core workflows | Can invoke only through minimal adapter path |
| PermissionEngine runtime checks | Supported | Used for high-risk adapter operations | Used before Claude adapter tool execution |
| Plugin discovery/execution | Supported through Kernel | Metadata/adapter integration content | Not native plugin runtime |
| RAG/harness/medical standards/prototype stats | Supported as Python plugins | Skill docs and role context available | Conceptual skill documentation only |
| Native platform tool calls | Not required | Implemented adapter mapping for declared tools | `claude.capabilities`, `claude.runtime_status`, `claude.invoke` |
| Native platform subagent runtime bridge | Not applicable | Not implemented unless an orchestrator is injected; local metadata fallback only | Not implemented; `subagent_dispatch` reports unavailable |
| Native platform skill loading | Not applicable | Skill documents are provided for OpenCode add-on use | Not implemented; `skill_load` returns contract metadata only |
| Platform runtime requirement | Python >= 3.10 plus package deps | Optional OpenCode environment/configuration | Optional local `claude` CLI only for `claude.invoke` |

### Runtime requirements

- **Required for core**: Python >= 3.10, `pip`, package dependencies declared in
  `pyproject.toml` (`pyyaml`, `rich`, `textual`), and local filesystem access for
  `.supermedicine/` plus optional workspaces.
- **Optional for development**: `.[dev]` dependencies for tests/lint/local release
  checks.
- **Optional for R survival backend**: `.[r]`, local R, and the R `survival`
  package. The default survival path remains deterministic pure Python unless
  `backend="r"` is requested.
- **Optional for OpenCode add-on**: OpenCode configuration/plugin placement as
  appropriate for the user's OpenCode installation. Core install/run does not
  need OpenCode.
- **Optional for Claude Code add-on**: a local `claude` command on PATH is needed
  only for `claude.invoke`; missing runtime is reported as adapter unavailable,
  not as a core failure.

### Optional platform add-on configuration/status

- **OpenCode**: copy or reference `adapters/opencode/plugin.json` and the
  associated `adapters/opencode/skills/*.md` and `adapters/opencode/agents/*.md`
  from an OpenCode setup when you want OpenCode-specific metadata. The adapter
  declares mappings for `bash`, `read`, `write`, `edit`, `glob`, `grep`, `skill`,
  and `task`; high-risk execution/mutation paths remain permission-gated. Current
  status: implemented adapter surface and metadata, but no standalone native
  OpenCode subagent runtime bridge without an injected SuperMedicine
  orchestrator.
- **Claude Code**: optional minimal adapter only. It can report capabilities,
  check runtime status, and call `claude --print` through `claude.invoke` when
  available and permitted. Current status: no native Claude Code skills, no
  native Claude Code subagents, and unavailable/timeout/runtime errors are
  structured and redacted.

## Running Tests

```bash
pytest tests/ -v     # Run the test suite
python Cli.py test   # Same via CLI
```

## Local quality gate and release checklist

Run the same lightweight checks expected by CI before opening a PR or uploading
release files:

```bash
pip install -e ".[dev]"
ruff check --select=E,F,W --ignore=E501 .
python -m pip wheel . --no-deps --wheel-dir .pytest-tmp/wheel-smoke
pytest tests/ -v
```

Release readiness review:

- Treat `Beta0.2.1` as the GitHub/release-ready label. Python packaging
  metadata intentionally uses the PEP 440 fallback `0.2.1b0`.

- Confirm permission policies and audit behavior still enforce runtime vetoes through `PermissionEngine.check()`.
- Exercise the CLI `init`, `status`, `test`, and `run` paths in an initialized workspace.
- Confirm plugin discovery and execution remain permission-gated.
- Confirm Claude Code adapter paths report capabilities, runtime status, timeout,
  unavailable, and runtime errors without exposing secrets.
- Confirm RAG local/mock-external behavior, external configuration boundaries,
  timeout/resource errors, and secret environment-variable references.
- Confirm prototype medical statistics paths remain interface/test contracts only;
  do not claim clinical-grade, regulatory-grade, production-grade, or
  decision-support accuracy.
- Confirm medical writing and citation helpers only provide checklist/formatting
  constraints and require qualified human review of content and references.
- Confirm checkpoint and orchestration recovery paths behave as documented.
- Review security/privacy boundaries for external resources, audit logs, and
  redaction of sensitive values.
- Git upload hygiene: stage only necessary project files. Do not upload `Docs/`,
  `Superpower`, `superpower`, external skill packages, non-essential docs, build
  outputs, distribution artifacts, `*.egg-info`, `__pycache__`, `.pytest_cache`,
  `.pytest-tmp`, runtime checkpoints, or secret-bearing local configuration.

## License

MIT License — see [LICENSE](LICENSE) for details.
