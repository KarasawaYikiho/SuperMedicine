# SuperMedicine

![Version](https://img.shields.io/badge/version-Beta0.2.0-blue)

Release-ready label: `Beta0.2.0`. Python package metadata uses `0.2.0b0`
because PEP 440 packaging validation rejects `Beta0.2.0` as a Python project
version. No tag, release, publish, or upload has been created by this release
readiness update.

Modular medical research agent framework with RAG, plugin execution, and
permission-gated orchestration.

## Features

- **Modular Architecture** — Microkernel + multi-Agent orchestration with plugin system
- **P0 Permission Engine** — Code-layer runtime permission constraints with prompt-context safety guidance
- **Plugin Ecosystem** — RAG retrieval, Harness monitoring, prototype Python/R statistics interfaces, medical writing standards
- **Cross-Platform** — OpenCode and standalone adapters, plus a minimal permission-checked Claude Code adapter with real local CLI invocation when `claude` is available
- **Medical Standards** — CONSORT, STROBE, PRISMA, STARD reporting checklists; AMA/Vancouver citation formatting constraints

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

```bash
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine
pip install -e ".[dev]"
python Install.py --init
```

## CLI Usage

```bash
python Cli.py init      # Initialize project
python Cli.py status    # Show project status
python Cli.py test      # Run all tests
python Cli.py run TASK  # Execute a task through the initialized Kernel and plugins
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
├── adapters/       # Platform adapters (minimal Claude Code, OpenCode, standalone)
├── Cli.py          # CLI entry point
└── install.json    # Agent-readable installation manifest
```

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

- Treat `Beta0.2.0` as the GitHub/release-ready label. Python packaging
  metadata intentionally uses the PEP 440 fallback `0.2.0b0`.

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
