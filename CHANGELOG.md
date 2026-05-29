# Changelog

All notable changes to SuperMedicine will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Release notes intentionally preserve public labels, package metadata labels, and
verification evidence exactly as recorded. Installation and architecture details
are summarized here only when they affect a release; see [README.md](README.md),
[INSTALL.md](INSTALL.md), and [ARCHITECTURE.md](ARCHITECTURE.md) for current user
guidance.

## [Beta0.3.6] - 2026-05-29

### Added
- 自定义 LLM Provider 名称支持（不再限制为 openai/anthropic）
- API Format 自动推断（根据 provider 名称）
- Dashboard Token 消耗统计
- TUI 自定义暗色主题

### Changed
- 移除 provider 白名单限制
- 默认配置模板改为通用格式
- Python package metadata uses fallback version `0.3.6b0`.

## [Beta0.3.5] — Release-Ready

### Added
- Formal optional R/rpy2 backend support for `r-survival` Kaplan-Meier,
  log-rank, and Cox PH actions, with structured unavailable responses when rpy2,
  local R, or the R `survival` package is missing.
- Documentation now states the core independent + platform add-on model:
  standalone Python CLI/Kernel is the default supported path, OpenCode is an
  optional add-on without a native subagent runtime bridge unless an orchestrator
  is injected, and Claude Code is a minimal optional add-on without native skill
  or subagent support.
- **Full interactive TUI rewrite** with Textual framework: sidebar navigation,
  7 views (Chat, Dashboard, Workspace, Paper, Experience, Tool, Dialog History),
  keyboard shortcuts (1-7 for view switch, q to quit, ? for help), CSS
  stylesheet, and Chinese UI throughout. Backend controllers unchanged.
- **PATH guidance** in Install.py, README.md, and INSTALL.md: after `pip install
  -e .`, users are informed how to add the Python Scripts directory to PATH for
  global `supermedicine` command access.
- `requirements.txt` synced with `pyproject.toml` core dependencies (added
  `rich>=13.7,<15` and `textual>=0.79,<2`).

### Release Readiness
- Set the GitHub/release-ready label to `Beta0.3.5` without creating a tag,
  release, publish, or upload.
- Audited Python packaging metadata for the same label; packaging validation
  rejects `Beta0.3.5` because `project.version` must be PEP 440, so Python
  metadata uses fallback version `0.3.5b0`.
- Final platform-integration audit summary records standalone core independence,
  OpenCode optional add-on status without native runtime subagent-bridge claims,
  and Claude Code minimal optional add-on status without native skill/subagent
  claims.
- Latest cited local verification set: `ruff` pass; `mypy` pass with 132 source
  files; `pytest` 432 passed, 3 skipped; build pass; installed wheel smoke pass.

## [0.1.0-beta] — 2026-05-22

### Release Readiness
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
