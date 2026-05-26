# Changelog

All notable changes to SuperMedicine will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Beta0.2.1] — release-ready, unreleased

### Added
- Formal optional R/rpy2 backend support for `r-survival` Kaplan-Meier,
  log-rank, and Cox PH actions, with structured unavailable responses when rpy2,
  local R, or the R `survival` package is missing.
- Documentation now states the core independent + platform add-on model:
  standalone Python CLI/Kernel is the default supported path, OpenCode is an
  optional add-on without a native subagent runtime bridge unless an orchestrator
  is injected, and Claude Code is a minimal optional add-on without native skill
  or subagent support.

### Release readiness
- Set the GitHub/release-ready label to `Beta0.2.1` without creating a tag,
  release, publish, or upload.
- Audited Python packaging metadata for the same label; packaging validation
  rejects `Beta0.2.1` because `project.version` must be PEP 440, so Python
  metadata uses fallback version `0.2.1b0`.
- Final platform-integration audit summary records standalone core independence,
  OpenCode optional add-on status without native runtime subagent-bridge claims,
  and Claude Code minimal optional add-on status without native skill/subagent
  claims.
- Latest cited local verification set: `ruff` pass; `mypy` pass with 126 source
  files; `pytest` 424 passed, 3 skipped; build pass; installed wheel smoke pass.

## [0.1.0-beta] — 2026-05-22

### Release readiness
- Aligned CI/local quality gate around pytest, ruff, and a dependency-light packaging smoke check.
- Documented final regression and release checklist covering permissions, CLI, plugins, Claude adapter, RAG, prototype medical statistics boundaries, medical writing/citation constraints, checkpoint/orchestration, security/privacy, and Git upload hygiene.

### Added
- P0 dual-layer Permission Engine with code + prompt constraints and one-vote veto
- Plugin-based architecture with 6 plugins: RAG, Harness, Python Stats, R Survival, Medical Writing, Medical Citation
- Multi-Agent orchestration with state machine (7 states) and checkpoint persistence
- OpenCode platform adapter integration path with 8 native tool mappings
- Minimal Claude Code platform adapter with permission-checked local CLI invocation when `claude` is available, plus structured unavailable/error responses
- CLI with init/status/test/run commands
- Medical reporting standards: CONSORT (23 items), STROBE (22 items), PRISMA (27 items), STARD (27 items)
- Citation formatting: AMA and Vancouver styles
- Prototype statistics interface contracts for descriptive stats, t-test, ANOVA, and linear regression paths
- Prototype survival-analysis interface contracts for Kaplan-Meier, log-rank test, and Cox PH paths
- TF-IDF based local RAG provider with Chinese/English tokenization
- Agent monitoring with permission audit and anomaly detection
- Environment variable configuration support (SM_* prefix)
- GitHub Actions CI with Python 3.10/3.11/3.12 matrix

### Fixed
- Claude Code adapter: replaced NotImplementedError stubs with minimal capabilities/runtime-status/local-invoke paths and structured unavailable/error responses
- BasePlugin.execute(): returns safe default instead of crashing
- Kernel: integrated PermissionEngine at initialization (P0 security layer now active)
- CLI run command: initializes full component stack instead of Beta placeholder
- EmptyRAGProvider.store_context(): actually stores data in memory
- install.json: references actual plugin names instead of nonexistent "standards-base"
- Completed __init__.py exports for all 5 top-level packages
- Filled empty __init__.py files for harness and rag packages
- State → TaskState import correction in agents/__init__.py
- Type annotations: dict[str, any] → dict[str, Any] in prisma.py and stard.py

### Changed
- Replaced print() with logging.getLogger() in Cli.py and Install.py
- Made AgentMonitor anomaly threshold configurable (was hardcoded to 100)
- Extracted duplicate author formatting code into medical_citation/utils.py
- Extracted duplicate checklist checking into medical_writing/checklist_base.py
- Checklists.py now inherits from ChecklistBase to eliminate code redundancy

## [0.1.0-alpha] — 2026-05-22

### Added
- Initial project structure with microkernel architecture
- Core modules: ConfigCenter, EventBus, PluginRegistry, SessionManager
- Permission system: policy parsing, audit logging, prompt constraint generation
- Agent system: state machine, checkpoint manager, base agent, orchestrator
- Plugin framework with BasePlugin and PluginMeta
- Platform adapter base class
- RAG plugin interface with EmptyRAGProvider
- Harness plugin skeleton
- Python statistics tools plugin
- R survival analysis tools plugin
- Medical writing standards plugins (CONSORT, STROBE, PRISMA, STARD)
- Medical citation formatting plugins (AMA, Vancouver)
- CLI entry point with init/status/test/run commands
- Agent-readable install.json manifest
- Integration tests (5 scenarios)
- 76 unit and integration tests
