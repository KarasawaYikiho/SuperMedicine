# SuperMedicine

![Version](https://img.shields.io/badge/version-0.1.0--beta-blue)

Modular medical research agent framework with RAG, plugin execution, and
permission-gated orchestration.

## Features

- **Modular Architecture** — Microkernel + multi-Agent orchestration with plugin system
- **P0 Permission Engine** — Dual-layer (code + prompt) permission constraints with one-vote veto
- **Plugin Ecosystem** — RAG retrieval, Harness monitoring, prototype Python/R statistics interfaces, medical writing standards
- **Cross-Platform** — OpenCode and standalone adapters, plus a minimal permission-checked Claude Code adapter with real local CLI invocation when `claude` is available
- **Medical Standards** — CONSORT, STROBE, PRISMA, STARD reporting checklists; AMA/Vancouver citation formatting constraints

## Medical statistics boundary

The current `python-stats` and `r-survival` plugins are interface/prototype test
paths only. They provide stable input/output contracts and deterministic smoke
fixtures for development tests, but SuperMedicine does not promise
production-grade, clinical-grade, regulatory-grade, or decision-support
statistical accuracy. Outputs require qualified expert review before any
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

- Confirm permission policies and audit behavior still enforce one-vote vetoes.
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
