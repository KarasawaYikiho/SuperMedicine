# Changelog

All notable changes to SuperMedicine are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html) for package metadata.

Public release labels and Python package versions may differ when the public label
is not PEP 440-compatible. Current public/release label: **Beta0.4.1**. Current
Python package fallback version: **0.4.1b0**.

## [Beta0.4.1] - 2026-05-31

### Changed

- Updated public/release display label to `Beta0.4.1`.
- Python package metadata uses fallback version `0.4.1b0`.
- Reworked root user-facing Markdown for release upload scope, including a
  Chinese README section and removal of stale links to excluded engineering docs.

## [Beta0.3.6] - 2026-05-29

### Added

- Custom LLM provider names are supported instead of limiting providers to a
  fixed OpenAI/Anthropic list.
- API format inference based on provider name and explicit `api_format` override.
- Dashboard token consumption reporting.
- Custom dark theme for the TUI.

### Changed

- Removed provider whitelist assumptions.
- Updated the default configuration template to a generic provider format.
- Python package metadata used fallback version `0.3.6b0`.

## [Beta0.3.5] - 2026-05-29

### Added

- Optional R/rpy2 backend support for `r-survival` Kaplan-Meier, log-rank, and
  Cox PH actions, with structured unavailable responses when local dependencies
  are missing.
- Documentation for the standalone-core plus optional-adapter model.
- Textual-based Chinese TUI with sidebar navigation, dashboard, workspace, paper,
  experience, tool, dialog history, LLM management, and keyboard shortcuts.
- PATH guidance for the `supermedicine` console command.
- Runtime dependency alignment for Rich and Textual.

### Changed

- Public/release-ready label was `Beta0.3.5`.
- Python package metadata used fallback version `0.3.5b0` because the public label
  was not PEP 440-compatible.

### Verification Evidence Recorded at the Time

- Local release checks recorded ruff, mypy, pytest, build, and wheel smoke results
  for that release state.

## [0.1.0-beta] - 2026-05-22

### Added

- P0 permission engine with runtime code checks and prompt-context guidance.
- Plugin architecture for RAG, harness, Python statistics, R survival, medical
  writing, and medical citation.
- Multi-agent orchestration with state machine and checkpoint persistence.
- OpenCode platform adapter integration path with declared tool mappings.
- Minimal Claude Code adapter with permission-checked local CLI invocation when
  available and structured unavailable/error responses otherwise.
- CLI entry point with init, status, test, and run commands.
- CONSORT, STROBE, PRISMA, and STARD reporting checklists.
- AMA and Vancouver citation formatting helpers.
- Prototype statistics and survival-analysis interfaces.
- TF-IDF local RAG provider with Chinese/English tokenization.
- Agent monitoring with permission audit and anomaly detection.
- `SM_*` environment variable configuration support.
- GitHub Actions CI for supported Python versions.

### Fixed

- Replaced Claude Code adapter stubs with minimal capabilities, runtime-status,
  and local-invoke paths.
- Made `BasePlugin.execute()` return a safe default instead of crashing.
- Integrated PermissionEngine during Kernel initialization.
- Updated CLI run command to initialize the component stack instead of a beta
  placeholder path.
- Fixed in-memory context storage for the empty RAG provider.
- Corrected install manifest plugin references and package exports.
- Cleaned up type annotations and duplicate helper logic in standards plugins.

### Changed

- Replaced direct `print()` usage with module loggers in CLI/installer paths.
- Made harness anomaly threshold configurable.
- Extracted shared author formatting and checklist-checking helpers.

## [0.1.0-alpha] - 2026-05-22

### Added

- Initial microkernel project structure.
- Core modules: ConfigCenter, EventBus, PluginRegistry, and SessionManager.
- Permission policy parsing, audit logging, and prompt constraint generation.
- Agent state machine, checkpoint manager, base agent, and orchestrator.
- Plugin framework and base adapter interface.
- Initial RAG, harness, statistics, survival, medical writing, and citation
  plugin paths.
- Initial CLI entry point and agent-readable installation manifest.
- Initial unit and integration test coverage.
