# SuperMedicine

SuperMedicine is a medical-research assistant whose primary interactive
products are the Desktop GUI and OpenTUI. Both interfaces expose the stable
research workflows; CLI and Web endpoints remain supported for automation,
integration, and parity testing.

<!-- BEGIN GENERATED: release-metadata -->
Current release: **0.5.0b0**
<!-- END GENERATED: release-metadata -->

Release series: **Beta0.5.0**

中文说明：[README.zh-CN.md](README.zh-CN.md)

<a id="product"></a>
## Product

Desktop GUI and OpenTUI are the product focus. A stable user-facing capability
is complete only when it is usable and visible in both interfaces. OpenCode,
Claude Code, and Multi-Agent execution remain optional.

Stable capabilities include:

- workspace, paper, experiment, experience, and log workflows;
- local and configured-provider LLM execution;
- required local RAG retrieval and required Harness lifecycle checks;
- optional Alpha/Beta/Gamma/Delta Multi-Agent execution with checkpoints;
- canonical permission policy, audit, redaction, and path safety;
- CLI, OpenTUI, Web, Desktop, Standalone, OpenCode, and Claude Code surfaces;
- Wheel, sdist, three Windows executables, and a versioned Release ZIP.

The complete machine-readable capability inventory is
[`feature_manifest.json`](feature_manifest.json).

<a id="safety"></a>
## Safety

SuperMedicine assists research workflows; it does not provide clinical advice,
diagnosis, or treatment decisions. Review generated claims, citations,
statistics, figures, and code before use.

Harness and RAG are mandatory, enabled by default, and fail closed when their
required runtime state is missing, damaged, or unwritable. Multi-Agent is
optional: disabled runs use the single-agent path; enabled runs preserve all
four roles and checkpoint resume.

Never commit API keys, patient data, private endpoints, permission audit logs,
or user workspaces.

<a id="install"></a>
## Install

Requirements:

- Python 3.10–3.13;
- Node.js/npm for OpenTUI dependencies;
- Bun for the real OpenTUI runtime.

```bash
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine
python -m pip install -e .
python install.py
```

Ordinary users run `python install.py` with no flags, choose the installation
directory, and installation continues automatically. LLM settings are
configured later in the GUI or TUI. Advanced automation / CI can use explicit
flags and a staged release payload. Full source, release archive, `SuperMedicineInstaller.exe`,
`dist/SuperMedicine.exe`, `--extract-release-to`, `--release-exe`,
`--exe-dry-run`, and failure recovery are documented in the
[installation guide](docs/guides/INSTALL.md).

Run `python uninstall_entry.py` from the installed directory for one-command
uninstall.

OpenTUI uses `@opentui/core@0.4.3`:

```bash
npm ci
npm run opentui:smoke
```

The JavaScript runtime defaults to Bun. Advanced diagnosis may set
`SUPERMEDICINE_OPENTUI_JS_RUNTIME` to the supported runtime executable.

<a id="quickstart"></a>
## Quickstart

```bash
supermedicine --help
supermedicine init --provider openai --base-url https://api.openai.com/v1 \
  --api-key "$OPENAI_API_KEY" --model gpt-4o-mini
supermedicine workspace create demo
supermedicine run "Summarize the evidence" --workspace demo
supermedicine tui
supermedicine web
```

Provider configuration can also come from `SM_LLM_PROVIDER`,
`SM_LLM_BASE_URL`, `SM_LLM_API_KEY`, `SM_LLM_MODEL`, or
`.supermedicine/config.yaml`. Secret values are redacted from diagnostics and
logs.

Permission modes remain `strict`, `balanced`, and `permissive`; hard limits and
explicit denies still apply in every mode. Use `supermedicine permission`,
`authorize`, and `revoke` to inspect or change policy.

<a id="documentation"></a>
## Documentation

- [Documentation index](docs/README.md)
- [Installation](docs/guides/INSTALL.md)
- [Getting started](docs/guides/getting-started.md)
- [Web and desktop UI (Chinese)](docs/guides/WEB.md)
- [Architecture](docs/architecture/ARCHITECTURE.md)
- [Runtime pipeline](docs/architecture/runtime-pipeline.md)
- [Release architecture](docs/architecture/release-architecture.md)
- [Quality gates](docs/maintainers/quality-gates.md)
- [CI workflows](docs/maintainers/ci-workflows.md)
- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

For local validation:

```bash
python scripts/maintainers/check_docs.py
python scripts/maintainers/sync_release_metadata.py --check
python -m ruff check .
python -m mypy core permission cli plugins agents adapters installer
python -m pytest tests -q --tb=short
```

<a id="license"></a>
## License

SuperMedicine is released under the MIT License. Bundled dependency notices are
in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
