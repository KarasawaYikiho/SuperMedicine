# SuperMedicine

![Version](https://img.shields.io/badge/version-0.1.0--beta-blue)

Modular medical research Agent framework with RAG and Harness.

## Features

- **Modular Architecture** — Microkernel + multi-Agent orchestration with plugin system
- **P0 Permission Engine** — Dual-layer (code + prompt) permission constraints with one-vote veto
- **Plugin Ecosystem** — RAG retrieval, Harness monitoring, Python/R analysis tools, medical writing standards
- **Cross-Platform** — Compatible with Claude Code, OpenCode, and standalone CLI
- **Medical Standards** — CONSORT, STROBE, PRISMA, STARD reporting checklists; AMA/Vancouver citation formats

## Quick Start

```bash
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine
pip install -e ".[dev]"
python install.py --init
```

## CLI Usage

```bash
python cli.py init      # Initialize project
python cli.py status    # Show project status
python cli.py test      # Run all tests
python cli.py run TASK  # Execute a task (beta)
```

## Architecture

```
supermedicine/
├── core/           # Microkernel, event bus, plugin registry
├── permission/     # P0 priority — policy, audit, engine, prompt constraints
├── agents/         # State machine, checkpoint, orchestrator, base agent
├── plugins/
│   ├── rag/        # RAG retrieval interface + local TF-IDF provider
│   ├── harness/    # Testing, monitoring, quality assessment
│   ├── tools/      # Python stats + R survival analysis
│   └── standards/  # Medical writing checklists + citation formatters
├── adapters/       # Platform adapters (Claude Code, OpenCode)
├── cli.py          # CLI entry point
└── install.json    # Agent-readable installation manifest
```

## Running Tests

```bash
pytest tests/ -v     # 76 tests covering all modules
python cli.py test   # Same via CLI
```

## License

MIT License — see [LICENSE](LICENSE) for details.
