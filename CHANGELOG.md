# Changelog

All notable changes to SuperMedicine will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0-beta] — 2026-05-22

### Added
- P0 dual-layer Permission Engine with code + prompt constraints and one-vote veto
- Plugin-based architecture with 6 plugins: RAG, Harness, Python Stats, R Survival, Medical Writing, Medical Citation
- Multi-Agent orchestration with state machine (7 states) and checkpoint persistence
- OpenCode platform adapter with full implementation (8 native tool mappings)
- Claude Code platform adapter (Coming Soon mode)
- CLI with init/status/test/run commands
- Medical reporting standards: CONSORT (23 items), STROBE (22 items), PRISMA (27 items), STARD (27 items)
- Citation formatting: AMA and Vancouver styles
- Statistical analysis: descriptive stats, t-test, ANOVA, linear regression (Python)
- Survival analysis: Kaplan-Meier, log-rank test, Cox PH model (Python fallback)
- TF-IDF based local RAG provider with Chinese/English tokenization
- Agent monitoring with permission audit and anomaly detection
- Environment variable configuration support (SM_* prefix)
- GitHub Actions CI with Python 3.10/3.11/3.12 matrix

### Fixed
- Claude Code adapter: replaced NotImplementedError stubs with Coming Soon responses
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
- Replaced print() with logging.getLogger() in cli.py and install.py
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
