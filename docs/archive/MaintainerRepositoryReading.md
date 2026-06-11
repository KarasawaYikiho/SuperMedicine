# Maintainer Repository Reading Report

This maintainer-facing report records the line-by-line repository reading pass requested from the `Architecture/ExecutionRoadmap.md` inventory. It is curated documentation, not raw scratch notes. Generated/cache/build/binary/runtime/local-only artifacts remain excluded as listed in the roadmap.

## Current Execution Boundary: Repository Cleanup and Installer Follow-up

- Online Git / `.gitignore` cleanup means repository visibility and ignore rules may be adjusted so only necessary source, project documentation, CI, packaging, maintainer, security, and test artifacts are uploaded. It does not authorize deleting tracked source, tests, CI workflows, release documentation, maintainer reports, or security records. User decision for this cleanup round explicitly makes `REQUIREMENTS_TRACEABILITY.md` local-only and forbidden from upload while preserving the local file.
- Local-only files remain ignored rather than uploaded: runtime `.supermedicine/` state except the canonical default policy, workspaces, caches, temp directories, build/package outputs, binary/release artifacts, logs, secrets, platform-local assistant config, and uncurated scratch/audit/private analysis files.
- Physical deletion permission option A is limited to clearly regenerable local junk only, such as bytecode caches, pytest/ruff/mypy/coverage caches, temporary package/build staging directories, local temp files, local logs, local release zips, or equivalent ignored generated artifacts. Any deletion candidate that could contain user data, maintainer evidence, CI inputs, tests, source behavior, configuration intent, release notes, install records needed for uninstall, or unclear ownership requires explicit user confirmation before removal.
- CI tests and test assets must remain uploaded when they are part of tracked verification. `.github/workflows/ci.yml`, `tests/`, smoke checks, installer/uninstaller regression coverage, and maintainer verification references are protected from cleanup deletion or ignore-rule demotion.
- Installer follow-up must preserve the requested behavior boundary: detect an existing installation and offer safe choices to uninstall the old version or update/overwrite the version through the installer flow. Existing install records, manifests, user data, shortcuts, and residual cleanup candidates must be handled through explicit installer/uninstaller logic and confirmations, not by ad hoc repository cleanup.
- Ask the user only for unsafe or unclear items: ambiguous untracked files, possible user data, private notes that might need promotion, non-regenerable artifacts, externally owned files, or anything outside the repository cleanup boundary. Do not ask before removing only clearly regenerable ignored junk when the user has selected option A.
- This boundary records intent only for the current cleanup/installer round. It does not authorize commits, pushes, broad renames, code behavior changes, test deletion, CI removal, or destructive filesystem operations outside the clearly regenerable local-junk category.

## Reading Coverage Summary

- Inventory source: `Architecture/ExecutionRoadmap.md` -> `## Maintainer Repository Reading Inventory`.
- Included tracked files read line by line: 241.
- Supplemental intended untracked files read line by line: 0.
- Missing included files: none.
- Python files: 183; tests: 69; non-Python/declarative docs/config/scripts: 58.
- Self-evolution files are now covered as tracked repository inputs: `core/self_evolution.py`, `tests/test_self_evolution.py`, and `tests/test_self_evolution_cli.py`.
- Exclusions respected: caches, build/dist/egg-info, runtime `.supermedicine/`, binary/release artifacts, ignored scratch docs (including `EXTERNAL_PROJECT_ANALYSIS.md` and `failure_inventory.md`), and raw/private transient notes are not treated as source inputs.

## Steps 2-4 Read-Only Inventory and Classification Findings

- Tracked/untracked/ignored inventory summary: tracked repository inputs are the protected source, project documentation, maintainer/security records, packaging metadata, adapter/plugin manifests, tests, and CI workflow files already represented in the reading inventory; untracked items must be classified before upload or deletion; ignored items remain local-only unless explicitly promoted by maintainer decision. `REQUIREMENTS_TRACEABILITY.md` is now explicitly local-only/forbidden from upload by user decision.
- Keep online/tracked categories: application and plugin source, adapters/agents/skills, installer/uninstaller code and packaging metadata, `.github/workflows/ci.yml`, `tests/`, smoke/regression assets, curated architecture/maintainer docs, release/install/security documentation other than the local-only traceability file, and canonical policy files required to run or verify the project.
- Local-only ignored categories: runtime `.supermedicine/` state except canonical defaults, workspaces, caches, bytecode, build/package staging, coverage/type-check/lint caches, logs, temp directories, virtual environments, local secrets, platform-local assistant config, release binaries/zips, and uncurated scratch/audit/private notes.
- Safe-delete regenerable candidates: only clearly generated local junk is eligible for deletion under the cleanup boundary, such as `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`, `.coverage`/coverage output, build/dist/egg-info staging, temporary package artifacts, local logs, local temp files, and locally regenerated release archives or executables. Do not delete files as part of this documentation update.
- High-risk/ask-user categories: any ambiguous untracked file, possible user data, private note that may need promotion, install/uninstall record, manifest, workspace content, environment/secret file, fixture-like binary/archive, non-regenerable artifact, external-owner file, source/test/CI input, release evidence, or unclear cleanup candidate requires explicit user confirmation before removal or ignore-rule demotion.
- `.gitignore` policy follow-up: broad generated-output protections remain for build/package artifacts, logs, zips, executables, runtime state, platform-local assistant config, caches, temp files, virtual environments, and environment secrets. The former broad `Docs/` ignore is intentionally not used because Windows case-insensitive matching can hide curated lowercase `docs/`; local-only documentation scratch is handled by specific scratch/audit/private-note patterns instead. `.env.*` and `.envrc` are ignored while sample/template env files are explicitly allowed, common virtual/tool environments (`.venv/`, `venv/`, `env/`, `.tox/`, `.nox/`) are ignored, and `tests/fixtures/**/*.zip` plus `tests/fixtures/**/*.exe` are allowed so future CI fixture archives/binaries are not hidden by release-output rules. Protected trackable inputs include `.github/workflows/**`, `tests/**`, installer sources/config, root authoritative `FUNCTION_MAP.md`, `Architecture/**`, curated root docs, and `.supermedicine/policies/default.yaml`; `/REQUIREMENTS_TRACEABILITY.md` is explicitly ignored/local-only.
- CI/test/doc protection: cleanup must not delete, hide, or demote tracked tests, smoke checks, CI workflows, documentation, architecture/maintainer reports, security files, or release/install docs. CI and test assets are protected verification inputs even when they look like generated or fixture data. `REQUIREMENTS_TRACEABILITY.md` is a special user-directed exception: preserve the local file but keep it out of the Git index/upload path.

## Final Cleanup Decisions: FunctionMap, docs/, and Traceability

- Authoritative FunctionMap location: root `FUNCTION_MAP.md`. It is the curated maintainer explanatory file and remains trackable. Case-conflicting `FunctionMap.md` and duplicate `docs/function-map.md` / `docs/FunctionMap.md` copies should not be used.
- The untracked `docs/function-map.md` duplicate was reviewed against the root map. The root file contains the maintainer-curated repository map, security/review notes, and static-analysis appendix; the untracked docs copy was a raw/generated duplicate-style copy and was removed to avoid split authority and case/path confusion.
- User-authorized `docs/` cleanup option A was applied only to non-FunctionMap untracked docs artifacts under `docs/` (`external-project-analysis.md` and `security-hardening-checklist.md`) plus the duplicate local FunctionMap copy after preserving the authoritative root map.
- `REQUIREMENTS_TRACEABILITY.md` must remain as a local file only. It is removed from the Git index when present and protected by the exact `/REQUIREMENTS_TRACEABILITY.md` ignore rule so it is forbidden from upload while not being physically deleted.

## Module and Flow Analysis

### CLI / install / packaging
Cli.py, install.py, Install.py, Uninstall.py, installer/*, pyproject/setup/manifest/requirements/install.json expose user entry points, packaging metadata, release executable helpers, and uninstall cleanup. Flow: console command -> Cli dispatch -> core services/plugins; install helpers manage package/runtime setup.

### Core kernel / config / lifecycle
core/kernel.py, config_center.py, session_manager.py, event_bus.py, serialization/time/token/log modules coordinate runtime state, events, configuration, safe serialization, token accounting, and reporting.

### Permissions / safety
permission/* plus core/path_safety.py, operation_guard.py, redaction.py enforce access modes, policy loading, audit recording, path containment, operation risk classification, and secret redaction before tool/runtime side effects.

### Plugin registry and plugins
core/plugin_registry.py discovers plugin.yaml metadata and Plugin subclasses. BasePlugin provides plugin contracts. RAG, harness, standards, and tools plugins expose domain capabilities through the registry.

### Medical writing/citation equivalents
Medical writing and citation plugins plus OpenCode skill docs are the SuperMedicine-native Citation-Check-Skill/Nature-style anchors. They implement checklist and citation formatting surfaces; no tracked Nature-Skill/PaperSpine/Citation-Check-Skill package is present.

### Paper import
core/paper_import/* models imported papers, validation errors, enrichment, and importer flow. CLI/TUI tests cover importing, metadata handling, and workspace integration.

### RAG/local knowledge
plugins/rag/* defines provider interface, local provider, PubMed provider, plugin wrapper, and provider documentation. Flow is permissioned query -> provider -> structured evidence list.

### LLM management
core/llm_client.py, llm_manager.py, llm_providers/* handle provider configuration, OpenRouter/custom providers, client creation, errors, and token tracking without exposing secrets.

### Adapters / skills / agents
adapters/base_adapter.py plus opencode/claude/standalone implement permissioned tool, skill, and subagent contracts. OpenCode agent/skill Markdown files and plugin.json are declarative platform anchors.

### CLI/TUI/workspace/experience
Cli.py, core/workspace*.py, core/experience.py, core/tui/* provide workspace creation/selection, paper and experience screens, dialog history, permissions UI, LLM UI, and Chinese workbench flows.

### Self-evolution
Self-evolution is implemented by tracked `core/self_evolution.py` with coverage in `tests/test_self_evolution.py` and `tests/test_self_evolution_cli.py`. The flow is user intent plus optional confirmed experience source -> deterministic preview plan/artifacts -> explicit confirmation and permission/audit authorization -> sandbox/conservative/full write handling for whitelisted Markdown/Python/R generated artifacts.

### Tests and CI
tests/* and .github/workflows/ci.yml cover unit/integration/regression/release hygiene across adapters, core, plugins, TUI, install/uninstall, paper import, LLM, permissions, and workspace paths.

## Target Integration Candidate Findings

- Nature-Skill: no tracked implementation/package by that name exists; closest maintainable anchors are medical writing standards, citation standards, OpenCode skill docs, and agent role docs. Future work should be clean-room and SuperMedicine-native.
- PaperSpine: no tracked PaperSpine package/workflow exists; closest anchors are `core/paper_import/*`, workspace/TUI paper screens, RAG providers, medical writing, and citation plugins.
- Citation-Check-Skill: no tracked file by that name exists; closest anchors are `plugins/standards/medical_citation/*`, medical writing checklist plugins, and `adapters/opencode/skills/medical-citation.md`.
- Medical writing: implemented as plugin/checklist modules and reference checklists; maintenance risk is guideline drift and incomplete manuscript-structure coverage.
- Paper import: implemented under `core/paper_import/*` with CLI/TUI/workspace tests; maintenance risk is provider/schema variability and file/path safety.
- Citation checking: implemented as formatting/validation helpers for AMA/Vancouver style; maintenance risk is reference parsing edge cases and changing style guidance.
- RAG/local knowledge: implemented under `plugins/rag/*`; maintenance risk is permissioned filesystem/network access and result schema drift.
- LLM management: implemented under `core/llm*`; maintenance risk is provider API/config drift and secret redaction.
- Plugin registration: `core/plugin_registry.py`, `plugins/base_plugin.py`, plugin YAML files, and adapter metadata define discovery contracts; maintenance risk is dynamic loading drift.
- Permissions: `permission/*`, path safety, operation guard, and adapter checks enforce governance; maintenance risk is bypass through new tools/callbacks.
- CLI/TUI: `Cli.py` and `core/tui/*` provide command and Chinese workbench surfaces; maintenance risk is callback/state drift not visible in static maps.
- Install/uninstall: top-level and installer modules cover setup/removal/release support; maintenance risk is host-specific filesystem/PATH behavior.
- Test coverage: broad tests exist for core/plugin/adapter/TUI/import/permission/install paths, and tracked self-evolution tests cover service safety and CLI surfaces for preview, confirmation, permission modes, path rejection, and help regression.

## Per-File Reading Inventory

### `.github/workflows/ci.yml`
- Lines read: 432.
- Purpose: YAML configuration or plugin manifest.
- Key responsibilities: declared sections/keys: name: CI, on:, push:, branches: [master, main], pull_request:
- Public interfaces: Plugin/policy keys consumed by registry or permission tooling.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `.gitignore`
- Lines read: 85.
- Purpose: Repository source component.
- Key responsibilities: Declarative content/no Python callables.
- Public interfaces: No function-level public interface; file is declarative/package metadata.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `ARCHITECTURE.md`
- Lines read: 225.
- Purpose: Maintainer/user documentation for ARCHITECTURE.
- Key responsibilities: declared sections/keys: # SuperMedicine Architecture, ## Overview, ## Layer 1: Microkernel (`core/`), ## Layer 2: Permission System (`permission/`), ## Layer 3: Agent Orchestration (`agents/`)
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `Architecture/ExecutionRoadmap.md`
- Lines read: 625.
- Purpose: Maintainer/user documentation for ExecutionRoadmap.
- Key responsibilities: declared sections/keys: # Execution Roadmap, ## Current Architecture, ## Completed Roadmap Flow, ## Project Rule: Planning vs Push Gate, ## Release-Candidate State
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `Architecture/MaintainerRepositoryReading.md`
- Lines read: 2726.
- Purpose: Maintainer/user documentation for MaintainerRepositoryReading.
- Key responsibilities: declared sections/keys: # Maintainer Repository Reading Report, ## Reading Coverage Summary, ## Module and Flow Analysis, ## Target Integration Candidate Findings, ## Per-File Reading Inventory
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `Architecture/OptimizationAudit.md`
- Lines read: 184.
- Purpose: Maintainer/user documentation for OptimizationAudit.
- Key responsibilities: declared sections/keys: # Optimization Audit Report — Step 1, ## Branch / Remote / Status Summary, ## Categorized Modified / Untracked Files, ### Modified Tracked Documentation / Metadata Files, ### Modified Tracked Application / Plugin Files
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `Architecture/PhaseImplementationPlan.md`
- Lines read: 250.
- Purpose: Maintainer/user documentation for PhaseImplementationPlan.
- Key responsibilities: declared sections/keys: # Phase Implementation Baseline, ## Purpose and Scope, ## Actual Repository Layout, ## CLI Commands and Run Flags, ## Kernel and Execution Baseline
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `Architecture/PlatformIntegrationAudit.md`
- Lines read: 416.
- Purpose: Maintainer/user documentation for PlatformIntegrationAudit.
- Key responsibilities: declared sections/keys: # Platform Integration Audit, ## 1. Core Standalone Boundary, ## 2. Optional Platform Add-On Boundary, ## 3. OpenCode Support Findings, ## 4. Claude Code Support Completeness Findings
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `Architecture/RepositoryOptimizationAudit.md`
- Lines read: 167.
- Purpose: Maintainer/user documentation for RepositoryOptimizationAudit.
- Key responsibilities: declared sections/keys: # Repository Optimization Audit, ## Audit Pass Summary, ## Hard No-Go Semantic Preservation Boundaries, ## Naming/Rename Decision (Conservative — No Renames), ## Duplicate Reduction Decision
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `Architecture/WorkspaceTuiRagGuide.md`
- Lines read: 324.
- Purpose: Maintainer/user documentation for WorkspaceTuiRagGuide.
- Key responsibilities: declared sections/keys: # Workspace, TUI, Paper Import, and Experience Guide, ## Workspaces, ## CLI and Chinese TUI, ### Current TUI Structure Audit and Execution Boundary, ### OpenCode-aligned TUI Experience Principles for This Round
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `CHANGELOG.md`
- Lines read: 135.
- Purpose: Maintainer/user documentation for CHANGELOG.
- Key responsibilities: declared sections/keys: # Changelog, ## [Beta0.4.2] - 2026-06-07, ## [Beta0.4.1] - 2026-05-31, ### Added, ### Changed, ### Fixed
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `CONTRIBUTING.md`
- Lines read: 103.
- Purpose: Maintainer/user documentation for CONTRIBUTING.
- Key responsibilities: declared sections/keys: # Contributing to SuperMedicine, ## Development Environment, # Windows:, # Linux/macOS:, Requirements: Python >= 3.10 and Git.
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `Cli.py`
- Lines read: 2620.
- Purpose: Top-level command compatibility entry point.
- Key responsibilities: classes: _RedactingFormatter, CLI; callables: _configure_stdio_errors, _log_json, _configure_cli_logging, _load_release_exe_to_desktop, _workspace_info_to_dict, _as_experience_scope, _as_optional_experience_scope, _as_export_format; constants: PERMISSION_RISK_NOTICE, _EXPERIENCE_SCOPE_CHOICES, _EXPORT_FORMAT_CHOICES
- Public interfaces: CLI, main, format, formatException, __init__, init, status, test, run, workspace_init, workspace_list, workspace_show
- Internal dependencies: argparse, core, installer, json, logging, pathlib, permission, plugins, shutil, subprocess, sys, time.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: console I/O; filesystem I/O or mutation; possible network call; subprocess execution.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `FUNCTION_MAP.md`
- Lines read: 19786.
- Purpose: Maintainer/user documentation for FUNCTION MAP.
- Key responsibilities: declared sections/keys: # Function Map / Repository Callable Inventory, ## Security and Review Notes, ## Static/Dynamic Analysis Limitations, ## Summary, ## Callable Inventory by Source File
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `INSTALL.md`
- Lines read: 544.
- Purpose: Maintainer/user documentation for INSTALL.
- Key responsibilities: declared sections/keys: # SuperMedicine Installation Guide, ## Prerequisites, ## Quick Install, Zip: `install.py`, `Install.py`, the Python packages, documentation/config, ## Step-by-Step Setup
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: filesystem permissions and PATH/venv layout vary by host.
- Maintenance risks: keep synchronized with callers and documentation.

### `Install.py`
- Lines read: 24.
- Purpose: Top-level command compatibility entry point.
- Key responsibilities: Declarative content/no Python callables.
- Public interfaces: No function-level public interface; file is declarative/package metadata.
- Internal dependencies: installer.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: filesystem permissions and PATH/venv layout vary by host.
- Maintenance risks: keep synchronized with callers and documentation.

### `LICENSE`
- Lines read: 21.
- Purpose: Repository source component.
- Key responsibilities: Declarative content/no Python callables.
- Public interfaces: No function-level public interface; file is declarative/package metadata.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `MANIFEST.in`
- Lines read: 20.
- Purpose: Packaging manifest include rules.
- Key responsibilities: Declarative content/no Python callables.
- Public interfaces: No function-level public interface; file is declarative/package metadata.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `README.md`
- Lines read: 519.
- Purpose: Maintainer/user documentation for README.
- Key responsibilities: declared sections/keys: # SuperMedicine, ## 中文简介, ## Feature Summary, ## Installation, Requirements:
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `SECURITY.md`
- Lines read: 185.
- Purpose: Maintainer/user documentation for SECURITY.
- Key responsibilities: declared sections/keys: # Security Policy, ## Security Model, guidance:, ## Permission Configuration, role: "analyst"
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `SECURITY_HARDENING_CHECKLIST.md`
- Lines read: 104.
- Purpose: Maintainer/user documentation for SECURITY HARDENING CHECKLIST.
- Key responsibilities: declared sections/keys: # SuperMedicine Security Hardening Checklist, ## Scope, ## Secret and Log Filtering, ## Permission and Full-Access Mode Wording, ## Function Map Hygiene
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `Uninstall.py`
- Lines read: 631.
- Purpose: Top-level command compatibility entry point.
- Key responsibilities: classes: RemovalCandidate, Residual; callables: _redact_text, _redact_data, _safe_display, _is_within, _load_install_record, _load_install_manifest, _iter_string_values, _iter_recorded_paths; constants: PROJECT_MARKER, INSTALL_RECORD, INSTALL_MANIFEST, SENSITIVE_KEY_PARTS
- Public interfaces: RemovalCandidate, Residual, collect_removal_candidates, uninstall, main
- Internal dependencies: argparse, core, dataclasses, json, logging, os, pathlib, shutil, subprocess, sys, typing, winreg.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: console I/O; filesystem I/O or mutation; possible network call; subprocess execution.
- Configuration assumptions: filesystem permissions and PATH/venv layout vary by host.
- Maintenance risks: keep synchronized with callers and documentation.

### `adapters/__init__.py`
- Lines read: 143.
- Purpose: Lazy platform adapter discovery for SuperMedicine.
- Key responsibilities: classes: AdapterRegistration; callables: list_adapter_registrations, get_adapter_registration, default_adapter_registration, __getattr__, as_dict; constants: ADAPTER_REGISTRY
- Public interfaces: AdapterRegistration, list_adapter_registrations, get_adapter_registration, default_adapter_registration, as_dict
- Internal dependencies: adapters, dataclasses, importlib, types, typing.
- Data flow: platform tool/skill/task request -> adapter permission/sandbox checks -> local handler/runtime response.
- Side effects: possible network call.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: security boundary; avoid privilege/tool-call drift.

### `adapters/base_adapter.py`
- Lines read: 441.
- Purpose: 平台适配器基类
- Key responsibilities: classes: BaseAdapter; callables: __init__, platform_name, tool_call, skill_load, subagent_dispatch, _tool_bash, _normalize_command, _execute_permissioned_tool_call; constants: DEFAULT_TIMEOUT_SECONDS, MAX_TIMEOUT_SECONDS, PERMISSION_GATED_TOOLS, FILESYSTEM_TOOLS
- Public interfaces: BaseAdapter, __init__, platform_name, tool_call, skill_load, subagent_dispatch
- Internal dependencies: abc, core, pathlib, permission, re, shlex, subprocess, typing.
- Data flow: platform tool/skill/task request -> adapter permission/sandbox checks -> local handler/runtime response.
- Side effects: filesystem I/O or mutation; possible network call; subprocess execution.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: security boundary; avoid privilege/tool-call drift.

### `adapters/claude_code/SKILL.md`
- Lines read: 235.
- Purpose: Maintainer/user documentation for SKILL.
- Key responsibilities: declared sections/keys: name: supermedicine, description: SuperMedicine is the single user-facing Claude Code optional-adapter surface for the modular medical resear, # SuperMedicine Claude Code Optional Adapter Skill, ## Installation Manifest Entry, ## When To Use
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: platform tool/skill/task request -> adapter permission/sandbox checks -> local handler/runtime response.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: external runtime/API configuration may be absent and must degrade safely.
- Maintenance risks: security boundary; avoid privilege/tool-call drift.

### `adapters/claude_code/__init__.py`
- Lines read: 7.
- Purpose: Optional Claude Code adapter surface.
- Key responsibilities: Declarative content/no Python callables.
- Public interfaces: No function-level public interface; file is declarative/package metadata.
- Internal dependencies: adapters.
- Data flow: platform tool/skill/task request -> adapter permission/sandbox checks -> local handler/runtime response.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: external runtime/API configuration may be absent and must degrade safely.
- Maintenance risks: security boundary; avoid privilege/tool-call drift.

### `adapters/claude_code/adapter.py`
- Lines read: 405.
- Purpose: Optional Claude Code adapter surface.
- Key responsibilities: classes: ClaudeCodeAdapter; callables: __init__, platform_name, registration, capabilities, tool_call, skill_load, subagent_dispatch, _invoke; constants: SUPPORTED_TOOLS, USER_FACING_AGENT, INTERNAL_ROLE_CONTEXTS
- Public interfaces: ClaudeCodeAdapter, __init__, platform_name, registration, capabilities, tool_call, skill_load, subagent_dispatch
- Internal dependencies: adapters, pathlib, permission, shutil, subprocess, typing.
- Data flow: platform tool/skill/task request -> adapter permission/sandbox checks -> local handler/runtime response.
- Side effects: possible network call; subprocess execution.
- Configuration assumptions: external runtime/API configuration may be absent and must degrade safely.
- Maintenance risks: security boundary; avoid privilege/tool-call drift.

### `adapters/opencode/__init__.py`
- Lines read: 7.
- Purpose: Optional OpenCode adapter/skill/agent surface.
- Key responsibilities: Declarative content/no Python callables.
- Public interfaces: No function-level public interface; file is declarative/package metadata.
- Internal dependencies: adapters.
- Data flow: platform tool/skill/task request -> adapter permission/sandbox checks -> local handler/runtime response.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: external runtime/API configuration may be absent and must degrade safely.
- Maintenance risks: security boundary; avoid privilege/tool-call drift.

### `adapters/opencode/adapter.py`
- Lines read: 306.
- Purpose: Optional OpenCode adapter/skill/agent surface.
- Key responsibilities: classes: OpenCodeAdapter; callables: __init__, platform_name, registration, capabilities, tool_call, _tool_skill, _tool_task, skill_load; constants: SUPPORTED_TOOLS, SKILL_FILES, AGENT_FILES, USER_FACING_AGENT, AI_PROVIDER_SUPPORT, AGENT_ROLE_MAP
- Public interfaces: OpenCodeAdapter, __init__, platform_name, registration, capabilities, tool_call, skill_load, subagent_dispatch
- Internal dependencies: adapters, core, pathlib, permission, typing.
- Data flow: platform tool/skill/task request -> adapter permission/sandbox checks -> local handler/runtime response.
- Side effects: event/plugin dispatch; filesystem I/O or mutation; possible network call.
- Configuration assumptions: external runtime/API configuration may be absent and must degrade safely.
- Maintenance risks: security boundary; avoid privilege/tool-call drift.

### `adapters/opencode/agents/alpha-analyst.md`
- Lines read: 62.
- Purpose: Maintainer/user documentation for alpha analyst.
- Key responsibilities: declared sections/keys: agent_id: alpha, user_facing: false, internal_role_context: true, role: 分析员 (Analyst), description: |
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: platform tool/skill/task request -> adapter permission/sandbox checks -> local handler/runtime response.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: external runtime/API configuration may be absent and must degrade safely.
- Maintenance risks: security boundary; avoid privilege/tool-call drift.

### `adapters/opencode/agents/beta-reviewer.md`
- Lines read: 62.
- Purpose: Maintainer/user documentation for beta reviewer.
- Key responsibilities: declared sections/keys: agent_id: beta, user_facing: false, internal_role_context: true, role: 审核员 (Reviewer), description: |
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: platform tool/skill/task request -> adapter permission/sandbox checks -> local handler/runtime response.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: external runtime/API configuration may be absent and must degrade safely.
- Maintenance risks: security boundary; avoid privilege/tool-call drift.

### `adapters/opencode/agents/delta-orchestrator.md`
- Lines read: 74.
- Purpose: Maintainer/user documentation for delta orchestrator.
- Key responsibilities: declared sections/keys: agent_id: delta, user_facing: false, internal_role_context: true, role: 编排员 (Orchestrator), description: |
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: platform tool/skill/task request -> adapter permission/sandbox checks -> local handler/runtime response.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: external runtime/API configuration may be absent and must degrade safely.
- Maintenance risks: security boundary; avoid privilege/tool-call drift.

### `adapters/opencode/agents/gamma-writer.md`
- Lines read: 62.
- Purpose: Maintainer/user documentation for gamma writer.
- Key responsibilities: declared sections/keys: agent_id: gamma, user_facing: false, internal_role_context: true, role: 撰写员 (Writer), description: |
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: platform tool/skill/task request -> adapter permission/sandbox checks -> local handler/runtime response.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: external runtime/API configuration may be absent and must degrade safely.
- Maintenance risks: security boundary; avoid privilege/tool-call drift.

### `adapters/opencode/agents/supermedicine.md`
- Lines read: 64.
- Purpose: Maintainer/user documentation for supermedicine.
- Key responsibilities: declared sections/keys: name: SuperMedicine, user_facing: true, agent_id: supermedicine, description: |, # SuperMedicine
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: platform tool/skill/task request -> adapter permission/sandbox checks -> local handler/runtime response.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: external runtime/API configuration may be absent and must degrade safely.
- Maintenance risks: security boundary; avoid privilege/tool-call drift.

### `adapters/opencode/plugin.json`
- Lines read: 136.
- Purpose: JSON metadata/configuration artifact.
- Key responsibilities: Declarative content/no Python callables.
- Public interfaces: JSON fields consumed by installer/adapter metadata readers.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: platform tool/skill/task request -> adapter permission/sandbox checks -> local handler/runtime response.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: external runtime/API configuration may be absent and must degrade safely.
- Maintenance risks: security boundary; avoid privilege/tool-call drift.

### `adapters/opencode/skills/harness-monitor.md`
- Lines read: 48.
- Purpose: Maintainer/user documentation for harness monitor.
- Key responsibilities: declared sections/keys: name: supermedicine-harness-monitor, description: Agent monitoring, quality assessment, and execution sandbox for medical research workflows, # Harness Monitor, ## Capabilities, ### Integration
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: platform tool/skill/task request -> adapter permission/sandbox checks -> local handler/runtime response.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: external runtime/API configuration may be absent and must degrade safely.
- Maintenance risks: security boundary; avoid privilege/tool-call drift.

### `adapters/opencode/skills/medical-citation.md`
- Lines read: 76.
- Purpose: Maintainer/user documentation for medical citation.
- Key responsibilities: declared sections/keys: name: supermedicine-medical-citation, description: Medical citation formatting — AMA and Vancouver styles, # Medical Citation, ## Supported Formats, ## Capabilities
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: platform tool/skill/task request -> adapter permission/sandbox checks -> local handler/runtime response.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: external runtime/API configuration may be absent and must degrade safely.
- Maintenance risks: security boundary; avoid privilege/tool-call drift.

### `adapters/opencode/skills/medical-writing.md`
- Lines read: 50.
- Purpose: Maintainer/user documentation for medical writing.
- Key responsibilities: declared sections/keys: name: supermedicine-medical-writing, description: Medical writing standards compliance checking — CONSORT, STROBE, PRISMA, STARD, # Medical Writing Standards, ## Supported Standards, ## Capabilities
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: platform tool/skill/task request -> adapter permission/sandbox checks -> local handler/runtime response.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: external runtime/API configuration may be absent and must degrade safely.
- Maintenance risks: security boundary; avoid privilege/tool-call drift.

### `adapters/opencode/skills/python-stats.md`
- Lines read: 47.
- Purpose: Maintainer/user documentation for python stats.
- Key responsibilities: declared sections/keys: name: supermedicine-python-stats, description: Statistical analysis tools in Python — descriptive statistics, t-test, ANOVA, linear regression, # Python Statistics, ## Capabilities, ## Usage
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: platform tool/skill/task request -> adapter permission/sandbox checks -> local handler/runtime response.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: external runtime/API configuration may be absent and must degrade safely.
- Maintenance risks: security boundary; avoid privilege/tool-call drift.

### `adapters/opencode/skills/r-survival.md`
- Lines read: 66.
- Purpose: Maintainer/user documentation for r survival.
- Key responsibilities: declared sections/keys: name: supermedicine-r-survival, description: Survival analysis tools via R — Kaplan-Meier estimation, log-rank test, Cox proportional hazards, # R Survival Analysis, ## Capabilities, ## Prerequisites
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: platform tool/skill/task request -> adapter permission/sandbox checks -> local handler/runtime response.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: external runtime/API configuration may be absent and must degrade safely.
- Maintenance risks: security boundary; avoid privilege/tool-call drift.

### `adapters/opencode/skills/rag-query.md`
- Lines read: 77.
- Purpose: Maintainer/user documentation for rag query.
- Key responsibilities: declared sections/keys: name: supermedicine-rag-query, description: RAG-based medical literature retrieval and context management for evidence-based research, # RAG Query, ## Capabilities, ## Provider
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: platform tool/skill/task request -> adapter permission/sandbox checks -> local handler/runtime response.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: external runtime/API configuration may be absent and must degrade safely.
- Maintenance risks: security boundary; avoid privilege/tool-call drift.

### `adapters/standalone/__init__.py`
- Lines read: 7.
- Purpose: Standalone 适配器 — 自包含工具调用，无需外部 AI 平台
- Key responsibilities: Declarative content/no Python callables.
- Public interfaces: No function-level public interface; file is declarative/package metadata.
- Internal dependencies: adapter.
- Data flow: platform tool/skill/task request -> adapter permission/sandbox checks -> local handler/runtime response.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: security boundary; avoid privilege/tool-call drift.

### `adapters/standalone/adapter.py`
- Lines read: 97.
- Purpose: Standalone 适配器 — 自包含实现，工具方法继承自 BaseAdapter
- Key responsibilities: classes: StandaloneAdapter; callables: __init__, platform_name, registration, tool_call, _tool_skill, _tool_task, skill_load, subagent_dispatch
- Public interfaces: StandaloneAdapter, __init__, platform_name, registration, tool_call, skill_load, subagent_dispatch
- Internal dependencies: adapters, pathlib, permission, typing.
- Data flow: platform tool/skill/task request -> adapter permission/sandbox checks -> local handler/runtime response.
- Side effects: possible network call.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: security boundary; avoid privilege/tool-call drift.

### `agents/__init__.py`
- Lines read: 16.
- Purpose: Agent orchestration/state component.
- Key responsibilities: Declarative content/no Python callables.
- Public interfaces: No function-level public interface; file is declarative/package metadata.
- Internal dependencies: agents.
- Data flow: task/state/checkpoint events -> orchestrator/state machine -> agent outputs.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `agents/base_agent.py`
- Lines read: 28.
- Purpose: Agent orchestration/state component.
- Key responsibilities: classes: BaseAgent; callables: __init__, agent_id, role, describe_state, execute
- Public interfaces: BaseAgent, __init__, agent_id, role, describe_state, execute
- Internal dependencies: abc, typing.
- Data flow: task/state/checkpoint events -> orchestrator/state machine -> agent outputs.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `agents/checkpoint.py`
- Lines read: 158.
- Purpose: Agent orchestration/state component.
- Key responsibilities: classes: CheckpointManager; callables: _is_sensitive_key, sanitize_for_checkpoint, __init__, base_dir, save, load, load_latest, get_latest_step; constants: SENSITIVE_KEYS
- Public interfaces: sanitize_for_checkpoint, CheckpointManager, __init__, base_dir, save, load, load_latest, get_latest_step, recovery_report
- Internal dependencies: core, json, pathlib, typing.
- Data flow: task/state/checkpoint events -> orchestrator/state machine -> agent outputs.
- Side effects: filesystem I/O or mutation; possible network call.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `agents/orchestrator.py`
- Lines read: 177.
- Purpose: Agent orchestration/state component.
- Key responsibilities: classes: Orchestrator; callables: __init__, checkpoint_manager, register_agent, get_agent, list_agents, describe, _next_step, _save_stage
- Public interfaces: Orchestrator, __init__, checkpoint_manager, register_agent, get_agent, list_agents, describe, dispatch, recovery_report
- Internal dependencies: base_agent, checkpoint, pathlib, state_machine, typing.
- Data flow: task/state/checkpoint events -> orchestrator/state machine -> agent outputs.
- Side effects: possible network call.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `agents/state_machine.py`
- Lines read: 108.
- Purpose: Agent orchestration/state component.
- Key responsibilities: classes: TaskState, StateMachine; callables: __init__, task_id, state, retry_count, history, transition, can_resume, snapshot; constants: PLANNING, DISPATCH, RUNNING, VERIFYING, RETRY, COMPLETED
- Public interfaces: TaskState, StateMachine, __init__, task_id, state, retry_count, history, transition, can_resume, snapshot
- Internal dependencies: core, enum, typing.
- Data flow: task/state/checkpoint events -> orchestrator/state machine -> agent outputs.
- Side effects: possible network call.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `core/__init__.py`
- Lines read: 53.
- Purpose: SuperMedicine 微内核
- Key responsibilities: callables: __getattr__, create_llm_client
- Public interfaces: create_llm_client
- Internal dependencies: core, importlib, typing.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `core/config_center.py`
- Lines read: 538.
- Purpose: 配置中心 — YAML 配置管理，支持 SM_* 环境变量覆盖
- Key responsibilities: classes: ConfigCenter; callables: _redact_llm_providers, _redact_llm_provider, _safe_runtime_slug, __init__, config_path, get, set, save
- Public interfaces: ConfigCenter, __init__, config_path, get, set, save, all, safe_all, diagnostics, diagnose_llm_config, get_llm_config, get_experiment_guide_config
- Internal dependencies: core, logging, os, pathlib, permission, typing, yaml.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: filesystem I/O or mutation; possible network call.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `core/event_bus.py`
- Lines read: 46.
- Purpose: 消息总线
- Key responsibilities: classes: Subscription, EventBus; callables: __init__, subscribe, unsubscribe, publish
- Public interfaces: Subscription, EventBus, __init__, subscribe, unsubscribe, publish
- Internal dependencies: dataclasses, logging, typing, uuid.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: possible network call.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `core/experience.py`
- Lines read: 539.
- Purpose: Experience learning storage foundation.
- Key responsibilities: classes: ExperienceError, ExperiencePrivacyError, ExperienceValidationError, ExperienceClassificationSuggestion, ExperienceRecord, ExperienceStore; callables: _new_id, _contains_key, _contains_marker_text, _reject_raw_conversation_fields, validate_confirmed_record, validate_general_experience_privacy, to_dict, to_dict; constants: EXPERIENCE_LEARNING_ENABLED_BY_DEFAULT, GENERAL_EXPERIENCE_DIRNAME, CONFIRMED_EXPERIENCE_FILENAME, _PROJECT_DETAIL_MARKERS, _RAW_CONVERSATION_MARKERS
- Public interfaces: ExperienceError, ExperiencePrivacyError, ExperienceValidationError, ExperienceClassificationSuggestion, ExperienceRecord, validate_confirmed_record, validate_general_experience_privacy, ExperienceStore, to_dict, to_dict, from_dict, __init__
- Internal dependencies: core, dataclasses, json, pathlib, tempfile, typing, uuid.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: filesystem I/O or mutation; possible network call.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `core/experiment_guide.py`
- Lines read: 632.
- Purpose: Core experiment guide state machine.
- Key responsibilities: classes: ExperimentStatus, ExperimentGuideError, KernelExecutor, CalculationResult, StepRecord, ExperimentSession; callables: _utc_now, _compact_summary, build_experiment_log_event, append_experiment_log_event, execute_task, to_dict, from_dict, to_dict; constants: MEDICAL_BOUNDARY, IN_PROGRESS, COMPLETED, ERROR
- Public interfaces: ExperimentStatus, ExperimentGuideError, build_experiment_log_event, append_experiment_log_event, KernelExecutor, CalculationResult, StepRecord, ExperimentSession, ExperimentGuide, execute_task, to_dict, from_dict
- Internal dependencies: core, dataclasses, datetime, enum, json, typing, uuid.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: possible network call.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `core/experiment_protocols.py`
- Lines read: 585.
- Purpose: Experiment protocol discovery and configuration loading.
- Key responsibilities: classes: ExperimentProtocolConfigError, ExperimentProtocolAuthoringError, ExperimentInputField, CalculationRequest, ExperimentStep, ExperimentProtocol; callables: default_experiment_config_dir, _safe_slug, _assert_safe_protocol_id, _ensure_writable_config_dir, _load_config_file, _config_paths, load_protocols, validate_experiment_config; constants: EXPERIMENT_CONFIG_DIRNAME, EXPERIMENT_CONFIG_EXTENSIONS, EXPERIMENT_CONFIG_AUTHORING_RULES, _SAFE_PROTOCOL_ID
- Public interfaces: ExperimentProtocolConfigError, ExperimentProtocolAuthoringError, default_experiment_config_dir, ExperimentInputField, CalculationRequest, ExperimentStep, ExperimentProtocol, load_protocols, validate_experiment_config, summarize_experiment_protocol, build_experiment_llm_context, draft_experiment_config_from_instruction
- Internal dependencies: dataclasses, hashlib, json, pathlib, re, typing, yaml.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: filesystem I/O or mutation; possible network call.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `core/kernel.py`
- Lines read: 800.
- Purpose: SuperMedicine 微内核 — 集成所有核心组件
- Key responsibilities: classes: Kernel; callables: __init__, config, llm_manager, event_bus, plugin_registry, session_manager, permission_engine, checkpoint_manager; constants: MEDICAL_BOUNDARY, SUPERMEDICINE_SYSTEM_PROMPT
- Public interfaces: Kernel, __init__, config, llm_manager, event_bus, plugin_registry, session_manager, permission_engine, checkpoint_manager, execute_task, emit, emit
- Internal dependencies: agents, core, json, os, pathlib, permission, typing.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: event/plugin dispatch; possible network call.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `core/llm_client.py`
- Lines read: 203.
- Purpose: LLM provider/client management component.
- Key responsibilities: classes: LLMClient, TrackedLLMClient; callables: _infer_api_format, create_llm_client, create_configured_llm_client, chat, complete, __init__, config, chat
- Public interfaces: LLMClient, TrackedLLMClient, create_llm_client, create_configured_llm_client, chat, complete, __init__, config, chat, complete
- Internal dependencies: abc, core, logging, typing.
- Data flow: provider config/messages -> client/manager dispatch -> LLM response/token accounting.
- Side effects: possible network call.
- Configuration assumptions: external runtime/API configuration may be absent and must degrade safely.
- Maintenance risks: keep synchronized with callers and documentation.

### `core/llm_manager.py`
- Lines read: 282.
- Purpose: LLM provider/client management component.
- Key responsibilities: classes: LLMConfigManager; callables: __init__, list_providers, diagnostics, add_provider, switch_provider, get_current_provider, get_provider, save_exit_state; constants: REQUIRED_FIELDS, SETUP_HINT
- Public interfaces: LLMConfigManager, __init__, list_providers, diagnostics, add_provider, switch_provider, get_current_provider, get_provider, save_exit_state, restore_startup_provider, validate_provider, create_client
- Internal dependencies: core, logging, typing.
- Data flow: provider config/messages -> client/manager dispatch -> LLM response/token accounting.
- Side effects: possible network call.
- Configuration assumptions: external runtime/API configuration may be absent and must degrade safely.
- Maintenance risks: keep synchronized with callers and documentation.

### `core/llm_providers/__init__.py`
- Lines read: 15.
- Purpose: LLM provider/client management component.
- Key responsibilities: Declarative content/no Python callables.
- Public interfaces: No function-level public interface; file is declarative/package metadata.
- Internal dependencies: core.
- Data flow: provider config/messages -> client/manager dispatch -> LLM response/token accounting.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: external runtime/API configuration may be absent and must degrade safely.
- Maintenance risks: keep synchronized with callers and documentation.

### `core/llm_providers/base.py`
- Lines read: 461.
- Purpose: LLM provider/client management component.
- Key responsibilities: classes: UnsafeProviderURL, ConfiguredLLMClient, OpenAIClient, AnthropicClient; callables: __init__, model, chat, complete, _openai_request, _openai_responses_request, _parse_openai_chat_response, _parse_openai_responses_response; constants: MAX_PROVIDER_RESPONSE_BYTES
- Public interfaces: UnsafeProviderURL, ConfiguredLLMClient, OpenAIClient, AnthropicClient, __init__, model, chat, complete, __init__, __init__
- Internal dependencies: core, json, logging, socket, typing, urllib.
- Data flow: provider config/messages -> client/manager dispatch -> LLM response/token accounting.
- Side effects: possible network call.
- Configuration assumptions: external runtime/API configuration may be absent and must degrade safely.
- Maintenance risks: keep synchronized with callers and documentation.

### `core/llm_providers/config.py`
- Lines read: 200.
- Purpose: LLM provider/client management component.
- Key responsibilities: classes: LLMProviderConfig; callables: redact_secret, sanitize_error_message, sanitized_headers, _infer_api_format, _default_api_format, _default_base_url, _default_model, _default_api_key_env; constants: _SECRET_KEYS, REQUIRED_FIELDS
- Public interfaces: redact_secret, sanitize_error_message, sanitized_headers, LLMProviderConfig, from_mapping, missing_fields, validation_error, error, safe_dict
- Internal dependencies: core, dataclasses, os, typing.
- Data flow: provider config/messages -> client/manager dispatch -> LLM response/token accounting.
- Side effects: filesystem I/O or mutation; possible network call.
- Configuration assumptions: external runtime/API configuration may be absent and must degrade safely.
- Maintenance risks: keep synchronized with callers and documentation.

### `core/llm_providers/openrouter.py`
- Lines read: 49.
- Purpose: LLM provider/client management component.
- Key responsibilities: classes: OpenRouterClient; callables: __init__, _request; constants: DEFAULT_MODEL
- Public interfaces: OpenRouterClient, __init__
- Internal dependencies: core, typing.
- Data flow: provider config/messages -> client/manager dispatch -> LLM response/token accounting.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: external runtime/API configuration may be absent and must degrade safely.
- Maintenance risks: keep synchronized with callers and documentation.

### `core/log_report.py`
- Lines read: 865.
- Purpose: Safe log report storage for CLI-facing experiment/report commands.
- Key responsibilities: classes: LogReport, LogStorageLocations, LogReportError, LogReportStore, LogReportLoggingHandler; callables: normalize_log_severity, detect_log_severity, format_log_message, _display_message, _utc_now, resolve_log_storage_locations, configure_tui_log_storage, append_tui_stream_output; constants: _SAFE_LOG_NAME, _SAFE_SESSION_ID, _LOG_TYPE, _SCHEMA_VERSION, DEFAULT_MAX_MESSAGE_LENGTH, DEFAULT_MAX_RECORDS_PER_SESSION
- Public interfaces: normalize_log_severity, detect_log_severity, format_log_message, LogReport, LogStorageLocations, LogReportError, resolve_log_storage_locations, LogReportStore, LogReportLoggingHandler, configure_tui_log_storage, append_tui_stream_output, to_dict
- Internal dependencies: builtins, core, dataclasses, datetime, json, logging, pathlib, re, sys, threading, typing, uuid.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: filesystem I/O or mutation; possible network call.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `core/operation_guard.py`
- Lines read: 163.
- Purpose: Foundation helpers for guarded dangerous operations.
- Key responsibilities: classes: DangerousOperationDenied, OperationAuditRecord, OperationAuthorization; callables: authorize_dangerous_operation, to_context
- Public interfaces: DangerousOperationDenied, OperationAuditRecord, OperationAuthorization, authorize_dangerous_operation, to_context
- Internal dependencies: core, dataclasses, pathlib, permission, typing.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `core/paper_import/__init__.py`
- Lines read: 37.
- Purpose: Paper import pipeline component.
- Key responsibilities: Declarative content/no Python callables.
- Public interfaces: No function-level public interface; file is declarative/package metadata.
- Internal dependencies: core.
- Data flow: input identifiers/files/metadata -> normalized PaperRecord/enrichment -> workspace/runtime consumers.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: external metadata/schema/provider variability.

### `core/paper_import/enrichment.py`
- Lines read: 179.
- Purpose: Paper import pipeline component.
- Key responsibilities: classes: PaperMetadataProvider, LocalMockMetadataProvider, PaperEnrichmentResult, PaperEnricher; callables: _apply_provider_fields, fetch, fetch, __init__, enrich; constants: PAPER_ENRICH_ACTION, PAPER_ENRICH_AGENT_ID
- Public interfaces: PaperMetadataProvider, LocalMockMetadataProvider, PaperEnrichmentResult, PaperEnricher, fetch, fetch, __init__, enrich
- Internal dependencies: core, dataclasses, permission, typing.
- Data flow: input identifiers/files/metadata -> normalized PaperRecord/enrichment -> workspace/runtime consumers.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: external metadata/schema/provider variability.

### `core/paper_import/errors.py`
- Lines read: 19.
- Purpose: Paper import pipeline component.
- Key responsibilities: classes: PaperImportError, UnsupportedPaperFormatError, MissingPaperSourceError, PaperMetadataError
- Public interfaces: PaperImportError, UnsupportedPaperFormatError, MissingPaperSourceError, PaperMetadataError
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: input identifiers/files/metadata -> normalized PaperRecord/enrichment -> workspace/runtime consumers.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: external metadata/schema/provider variability.

### `core/paper_import/importer.py`
- Lines read: 372.
- Purpose: Paper import pipeline component.
- Key responsibilities: classes: PaperImporter; callables: _metadata_value, _parse_datetime, _normalize_doi, _normalize_pmid, __init__, import_file, list_papers, get_paper
- Public interfaces: PaperImporter, __init__, import_file, list_papers, get_paper, update_paper_metadata, save_paper_metadata
- Internal dependencies: core, datetime, hashlib, json, pathlib, re, typing.
- Data flow: input identifiers/files/metadata -> normalized PaperRecord/enrichment -> workspace/runtime consumers.
- Side effects: filesystem I/O or mutation; possible network call.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: external metadata/schema/provider variability.

### `core/paper_import/models.py`
- Lines read: 46.
- Purpose: Paper import pipeline component.
- Key responsibilities: classes: PaperMetadata, PaperImportResult
- Public interfaces: PaperMetadata, PaperImportResult
- Internal dependencies: dataclasses, datetime, pathlib.
- Data flow: input identifiers/files/metadata -> normalized PaperRecord/enrichment -> workspace/runtime consumers.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: external metadata/schema/provider variability.

### `core/path_safety.py`
- Lines read: 227.
- Purpose: Project-root path safety helpers.
- Key responsibilities: classes: PathSafetyError, PathOutsideProjectRootError, ProtectedPathError, UnsafePathValueError, SandboxWriteScopeError, SandboxFileTypeError; callables: _path_text, _contains_unsafe_path_character, validate_path_value, resolve_project_root, _resolve_candidate, _is_relative_to, validate_path_in_project_root, is_protected_path
- Public interfaces: PathSafetyError, PathOutsideProjectRootError, ProtectedPathError, UnsafePathValueError, SandboxWriteScopeError, SandboxFileTypeError, DangerousOverwriteError, SensitiveContentError, validate_path_value, resolve_project_root, validate_path_in_project_root, is_protected_path
- Internal dependencies: core, pathlib, re, typing.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `core/plugin_registry.py`
- Lines read: 59.
- Purpose: 插件注册中心
- Key responsibilities: classes: PluginRegistry; callables: __init__, discover, diagnostics, get_meta, get, list_plugins
- Public interfaces: PluginRegistry, __init__, discover, diagnostics, get_meta, get, list_plugins
- Internal dependencies: pathlib, plugins, typing, yaml.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: filesystem I/O or mutation; possible network call.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `core/redaction.py`
- Lines read: 217.
- Purpose: Shared sensitive-value redaction utilities.
- Key responsibilities: callables: _is_sensitive_key, _redacted_or_empty, _redact_url_query, redact_path_for_display, redact_sensitive; constants: REDACTION_PLACEHOLDER, _SENSITIVE_KEY_MARKERS, _SENSITIVE_QUERY_KEYS
- Public interfaces: redact_path_for_display, redact_sensitive
- Internal dependencies: re, typing, urllib.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `core/serialization.py`
- Lines read: 26.
- Purpose: Shared serialization utilities.
- Key responsibilities: callables: json_ready
- Public interfaces: json_ready
- Internal dependencies: dataclasses, datetime, pathlib, typing.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `core/self_evolution.py`
- Lines read: 822.
- Purpose: Safe self-evolution artifact generation service.
- Key responsibilities: classes: SelfEvolutionError, SelfEvolutionValidationError, SelfEvolutionPermissionError, GeneratedArtifact, SelfEvolutionRequest, SelfEvolutionResult, SelfEvolutionService; callables: to_dict, __init__, generate, preview, confirm, _normalize_request, _build_artifacts, _finalize_artifacts, _resolve_output_file, _validate_candidate_path, _validate_extension_and_overwrite, _authorize_artifacts, _write_artifacts, _access_policy, _resolve_experience_records, _build_plan, _render_markdown, _render_tool_readme, _render_python_tool, _render_r_tool, _experience_markdown, _experience_notes, _slug_from_intent, _reject_prohibited_engineering_docs, _record_event, _audit_failure, _write_audit_event, _write_log_event, _request_summary, _event_payload, build_self_evolution_preview; constants: ARTIFACT_TYPE_WHITELIST, SELF_EVOLUTION_ACTION, SELF_EVOLUTION_LOG_SESSION_ID, ALLOWED_MARKDOWN_EXTENSIONS, ALLOWED_TOOL_EXTENSIONS, SELF_EVOLUTION_WRITABLE_ROOTS.
- Public interfaces: ARTIFACT_TYPE_WHITELIST, SELF_EVOLUTION_ACTION, SelfEvolutionError, SelfEvolutionRequest, SelfEvolutionResult, SelfEvolutionService, SelfEvolutionPermissionError, SelfEvolutionValidationError, build_self_evolution_preview, SelfEvolutionService.generate, SelfEvolutionService.preview, SelfEvolutionService.confirm.
- Internal dependencies: core.experience, core.log_report, core.operation_guard, core.path_safety, core.redaction, core.serialization, core.time_utils, dataclasses, json, pathlib, permission.access_mode, permission.audit, permission.engine, permission.policy, re, typing.
- Data flow: user intent/output request/optional confirmed experience source -> normalized SelfEvolutionRequest -> deterministic GeneratedArtifact preview content and plan -> optional permission/audit authorization -> whitelisted Markdown/Python/R artifact writes under approved generated roots; failure paths return redacted structured dictionaries and append audit/log events where available.
- Side effects: preview path may write audit/log events; confirmed path can bootstrap default policy, append audit/log records, create directories, and write generated artifact files; failures may record audit/log events while suppressing logging exceptions.
- Configuration assumptions: project root resolution is trustworthy; self-evolution writes are restricted to approved roots/extensions unless explicit conservative/full access modes are selected; full access requires explicit confirmation and risk acknowledgement; sensitive content rejection/redaction protects generated artifacts and errors.
- Maintenance risks: generated-tool safety depends on path-safety and permission contracts staying aligned; broad exception capture can hide diagnostics; whitelist/root semantics may drift from CLI copy; experience-source schema or audit/log behavior changes can break preview/confirmation flows.

### `core/session_manager.py`
- Lines read: 65.
- Purpose: 会话管理器 — UUID 会话 + TTL 超时清理
- Key responsibilities: classes: Session, SessionManager; callables: __init__, set, get, age_seconds, __init__, create, get, cleanup_expired
- Public interfaces: Session, SessionManager, __init__, set, get, age_seconds, __init__, create, get, cleanup_expired, list_active
- Internal dependencies: datetime, typing, uuid.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: possible network call.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `core/time_utils.py`
- Lines read: 15.
- Purpose: Shared UTC timestamp utilities.
- Key responsibilities: callables: utc_now, utc_now_datetime
- Public interfaces: utc_now, utc_now_datetime
- Internal dependencies: datetime.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: filesystem I/O or mutation.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `core/token_tracker.py`
- Lines read: 112.
- Purpose: Token usage tracker with JSONL persistence.
- Key responsibilities: classes: TokenRecord, TokenTracker; callables: __init__, record, summary, summary_by_provider, summary_by_model, _load, _append_to_file
- Public interfaces: TokenRecord, TokenTracker, __init__, record, summary, summary_by_provider, summary_by_model
- Internal dependencies: core, dataclasses, json, pathlib.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: filesystem I/O or mutation.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `core/tui/__init__.py`
- Lines read: 66.
- Purpose: Chinese Textual TUI component.
- Key responsibilities: callables: __getattr__; constants: _SCREEN_ALIASES
- Public interfaces: No function-level public interface; file is declarative/package metadata.
- Internal dependencies: core, importlib.
- Data flow: workspace/application state -> Textual widgets/screens -> user actions -> core service calls.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: Textual optional UI dependency available for TUI paths.
- Maintenance risks: UI callback/state drift can evade static call maps.

### `core/tui/app.py`
- Lines read: 1283.
- Purpose: Chinese Textual TUI component.
- Key responsibilities: classes: _TUILogTextSink, _TUIThreadRoutedStream, TUIStatus, NavMetadata, ShellStatusText, NavItem; callables: _capture_current_thread_tui_streams, _redact_display_secrets, _looks_like_internal_kernel_text, _strip_internal_kernel_output, apply_status_style, launch_tui, _console_safe_text, _describe_llm_status; constants: _KERNEL_OUTPUT_ASSISTANT_KEYS, _KERNEL_OUTPUT_INTERNAL_KEYS, _KERNEL_OUTPUT_INTERNAL_COMMAND_KEYS, _KERNEL_OUTPUT_INTERNAL_MARKERS, _CSS_PATH, STATUS_STYLE_CLASSES
- Public interfaces: apply_status_style, TUIStatus, NavMetadata, ShellStatusText, NavItem, MenuOption, ViewSelectMenuScreen, MainMenuScreen, PromptInput, SuperMedicineTUI, launch_tui, build_parser
- Internal dependencies: argparse, asyncio, contextlib, core, dataclasses, datetime, importlib, json, logging, pathlib, re, rich.
- Data flow: workspace/application state -> Textual widgets/screens -> user actions -> core service calls.
- Side effects: console I/O; filesystem I/O or mutation; possible network call; subprocess execution.
- Configuration assumptions: Textual optional UI dependency available for TUI paths.
- Maintenance risks: UI callback/state drift can evade static call maps.

### `core/tui/app.tcss`
- Lines read: 423.
- Purpose: Textual TUI stylesheet.
- Key responsibilities: declared sections/keys: layout: vertical;, background: $background;, color: $foreground;, background: $primary;, color: $foreground;
- Public interfaces: Textual CSS classes/IDs loaded by TUI.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: workspace/application state -> Textual widgets/screens -> user actions -> core service calls.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: Textual optional UI dependency available for TUI paths.
- Maintenance risks: UI callback/state drift can evade static call maps.

### `core/tui/dialog_history.py`
- Lines read: 161.
- Purpose: Chinese Textual TUI component.
- Key responsibilities: classes: DialogHistoryPrivacyError, DialogHistoryEvent, DialogHistoryStore; callables: _contains_prohibited_key, _contains_prohibited_marker, _reject_raw_conversation, _safe_session_id, to_dict, from_dict, workspace_manager, history_path; constants: DIALOG_HISTORY_FILENAME, RAW_CONVERSATION_FIELDS
- Public interfaces: DialogHistoryPrivacyError, DialogHistoryEvent, DialogHistoryStore, to_dict, from_dict, workspace_manager, history_path, append_event, load_events
- Internal dependencies: core, dataclasses, json, pathlib, typing, uuid.
- Data flow: workspace/application state -> Textual widgets/screens -> user actions -> core service calls.
- Side effects: filesystem I/O or mutation; possible network call.
- Configuration assumptions: Textual optional UI dependency available for TUI paths.
- Maintenance risks: UI callback/state drift can evade static call maps.

### `core/tui/i18n.py`
- Lines read: 297.
- Purpose: Chinese Textual TUI component.
- Key responsibilities: callables: t, tui_redact_sensitive
- Public interfaces: t, tui_redact_sensitive
- Internal dependencies: core, typing.
- Data flow: workspace/application state -> Textual widgets/screens -> user actions -> core service calls.
- Side effects: filesystem I/O or mutation; possible network call.
- Configuration assumptions: Textual optional UI dependency available for TUI paths.
- Maintenance risks: UI callback/state drift can evade static call maps.

### `core/tui/permissions.py`
- Lines read: 83.
- Purpose: Chinese Textual TUI component.
- Key responsibilities: classes: TUIToolActionRequest; callables: prepare_tool_action; constants: TUI_TOOL_AGENT_ID, TUI_TOOL_ACTION, HIGH_RISK_TOOLS
- Public interfaces: TUIToolActionRequest, prepare_tool_action
- Internal dependencies: dataclasses, permission, typing.
- Data flow: workspace/application state -> Textual widgets/screens -> user actions -> core service calls.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: Textual optional UI dependency available for TUI paths.
- Maintenance risks: UI callback/state drift can evade static call maps.

### `core/tui/screens/__init__.py`
- Lines read: 16.
- Purpose: Chinese Textual TUI component.
- Key responsibilities: Declarative content/no Python callables.
- Public interfaces: No function-level public interface; file is declarative/package metadata.
- Internal dependencies: core.
- Data flow: workspace/application state -> Textual widgets/screens -> user actions -> core service calls.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: Textual optional UI dependency available for TUI paths.
- Maintenance risks: UI callback/state drift can evade static call maps.

### `core/tui/screens/chat_view.py`
- Lines read: 180.
- Purpose: Chinese Textual TUI component.
- Key responsibilities: classes: ChatView; callables: _redact_sensitive_text, safe_display_text, __init__, compose, on_mount, _write_separator, _write_block, add_user_message
- Public interfaces: safe_display_text, ChatView, __init__, compose, on_mount, add_user_message, add_system_message, add_assistant_message, begin_assistant_message, append_assistant_delta, add_error_message, add_status_message
- Internal dependencies: core, html, pathlib, re, rich, textual, typing.
- Data flow: workspace/application state -> Textual widgets/screens -> user actions -> core service calls.
- Side effects: filesystem I/O or mutation.
- Configuration assumptions: Textual optional UI dependency available for TUI paths.
- Maintenance risks: UI callback/state drift can evade static call maps.

### `core/tui/screens/dashboard.py`
- Lines read: 219.
- Purpose: Chinese Textual TUI component.
- Key responsibilities: classes: DashboardOverviewController, DashboardView; callables: collect_dashboard_context, _safe_workspace_infos, _count_plugins, _count_core_modules, _safe_token_stats, _safe_llm_status, _recent_workspace_hint, _package_version
- Public interfaces: collect_dashboard_context, DashboardOverviewController, DashboardView, __init__, context, overview_rows, advice_text, __init__, compose, on_mount
- Internal dependencies: core, importlib, pathlib, textual, typing.
- Data flow: workspace/application state -> Textual widgets/screens -> user actions -> core service calls.
- Side effects: possible network call.
- Configuration assumptions: Textual optional UI dependency available for TUI paths.
- Maintenance risks: UI callback/state drift can evade static call maps.

### `core/tui/screens/dialog_screen.py`
- Lines read: 128.
- Purpose: Chinese Textual TUI component.
- Key responsibilities: classes: DialogView; callables: __init__, compose, on_mount, _get_workspace_controller, _load_workspaces, _get_selected_workspace, _load_dialog_history, _set_status
- Public interfaces: DialogView, __init__, compose, on_mount, on_select_changed, on_button_pressed
- Internal dependencies: core, pathlib, textual, typing.
- Data flow: workspace/application state -> Textual widgets/screens -> user actions -> core service calls.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: Textual optional UI dependency available for TUI paths.
- Maintenance risks: UI callback/state drift can evade static call maps.

### `core/tui/screens/experience.py`
- Lines read: 135.
- Purpose: Chinese Textual TUI component.
- Key responsibilities: classes: ExperienceScreenController; callables: store, suggest_classification, confirm_suggestion, list_experiences, edit_experience, delete_experience, export_experiences, _record_payload
- Public interfaces: ExperienceScreenController, store, suggest_classification, confirm_suggestion, list_experiences, edit_experience, delete_experience, export_experiences
- Internal dependencies: core, dataclasses, pathlib, typing.
- Data flow: workspace/application state -> Textual widgets/screens -> user actions -> core service calls.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: Textual optional UI dependency available for TUI paths.
- Maintenance risks: UI callback/state drift can evade static call maps.

### `core/tui/screens/experience_screen.py`
- Lines read: 310.
- Purpose: Chinese Textual TUI component.
- Key responsibilities: classes: ExperienceView; callables: __init__, compose, on_mount, _get_experience_controller, _get_workspace_controller, _load_workspaces, _get_selected_workspace, _load_experiences
- Public interfaces: ExperienceView, __init__, compose, on_mount, on_select_changed, on_button_pressed
- Internal dependencies: core, pathlib, textual, typing.
- Data flow: workspace/application state -> Textual widgets/screens -> user actions -> core service calls.
- Side effects: possible network call.
- Configuration assumptions: Textual optional UI dependency available for TUI paths.
- Maintenance risks: UI callback/state drift can evade static call maps.

### `core/tui/screens/experiment_screen.py`
- Lines read: 427.
- Purpose: Chinese Textual TUI component.
- Key responsibilities: classes: ExperimentGuideView; callables: __init__, compose, on_mount, on_show, refresh_session_view, on_button_pressed, _refresh_protocol_table, _switch_to_next_protocol
- Public interfaces: ExperimentGuideView, __init__, compose, on_mount, on_show, refresh_session_view, on_button_pressed
- Internal dependencies: core, json, pathlib, permission, textual, typing.
- Data flow: workspace/application state -> Textual widgets/screens -> user actions -> core service calls.
- Side effects: possible network call.
- Configuration assumptions: Textual optional UI dependency available for TUI paths.
- Maintenance risks: UI callback/state drift can evade static call maps.

### `core/tui/screens/llm_screen.py`
- Lines read: 231.
- Purpose: Chinese Textual TUI component.
- Key responsibilities: classes: LLMScreenController, LLMView; callables: __init__, list_providers, current_provider, readiness, add_provider, switch_provider, save_exit_state, __init__
- Public interfaces: LLMScreenController, LLMView, __init__, list_providers, current_provider, readiness, add_provider, switch_provider, save_exit_state, __init__, compose, controller
- Internal dependencies: core, pathlib, textual, typing.
- Data flow: workspace/application state -> Textual widgets/screens -> user actions -> core service calls.
- Side effects: possible network call.
- Configuration assumptions: Textual optional UI dependency available for TUI paths; external runtime/API configuration may be absent and must degrade safely.
- Maintenance risks: UI callback/state drift can evade static call maps.

### `core/tui/screens/log_screen.py`
- Lines read: 395.
- Purpose: Chinese Textual TUI component.
- Key responsibilities: classes: LogReportView; callables: __init__, compose, store, on_mount, on_unmount, on_button_pressed, on_data_table_row_highlighted, _refresh_from_timer; constants: _SUMMARY_LIMIT, _DETAIL_LINE_LIMIT, _REFRESH_INTERVAL_SECONDS, _SEVERITY_STYLES
- Public interfaces: LogReportView, __init__, compose, store, on_mount, on_unmount, on_button_pressed, on_data_table_row_highlighted, refresh_logs
- Internal dependencies: core, pathlib, rich, textual, typing.
- Data flow: workspace/application state -> Textual widgets/screens -> user actions -> core service calls.
- Side effects: filesystem I/O or mutation; possible network call.
- Configuration assumptions: Textual optional UI dependency available for TUI paths.
- Maintenance risks: UI callback/state drift can evade static call maps.

### `core/tui/screens/paper_screen.py`
- Lines read: 235.
- Purpose: Chinese Textual TUI component.
- Key responsibilities: classes: PaperView; callables: __init__, compose, on_mount, _get_paper_controller, _get_workspace_controller, _load_workspaces, _get_selected_workspace, _load_papers
- Public interfaces: PaperView, __init__, compose, on_mount, on_select_changed, on_button_pressed
- Internal dependencies: core, pathlib, textual, typing.
- Data flow: workspace/application state -> Textual widgets/screens -> user actions -> core service calls.
- Side effects: possible network call.
- Configuration assumptions: Textual optional UI dependency available for TUI paths.
- Maintenance risks: UI callback/state drift can evade static call maps.

### `core/tui/screens/papers.py`
- Lines read: 139.
- Purpose: Chinese Textual TUI component.
- Key responsibilities: classes: PaperScreenController; callables: importer, root, import_paper, list_papers, show_paper, edit_metadata, enrich_metadata, _import_payload
- Public interfaces: PaperScreenController, importer, root, import_paper, list_papers, show_paper, edit_metadata, enrich_metadata
- Internal dependencies: core, dataclasses, pathlib, permission, typing.
- Data flow: workspace/application state -> Textual widgets/screens -> user actions -> core service calls.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: Textual optional UI dependency available for TUI paths.
- Maintenance risks: UI callback/state drift can evade static call maps.

### `core/tui/screens/permission_screen.py`
- Lines read: 223.
- Purpose: Chinese Textual TUI component.
- Key responsibilities: classes: PermissionScreenController, PermissionView; callables: __init__, current_config, set_mode, authorize_directory, revoke_directory, access_decision, __init__, controller; constants: PERMISSION_RISK_NOTICE
- Public interfaces: PermissionScreenController, PermissionView, __init__, current_config, set_mode, authorize_directory, revoke_directory, access_decision, __init__, controller, compose, on_mount
- Internal dependencies: core, pathlib, permission, textual, typing.
- Data flow: workspace/application state -> Textual widgets/screens -> user actions -> core service calls.
- Side effects: possible network call.
- Configuration assumptions: Textual optional UI dependency available for TUI paths.
- Maintenance risks: UI callback/state drift can evade static call maps.

### `core/tui/screens/tool_screen.py`
- Lines read: 565.
- Purpose: Chinese Textual TUI component.
- Key responsibilities: classes: ToolView; callables: __init__, compose, on_mount, focus_default, _get_workspace_controller, _load_workspaces, _get_selected_workspace, _get_workspace_path
- Public interfaces: ToolView, __init__, compose, on_mount, focus_default, on_select_changed, on_button_pressed
- Internal dependencies: core, pathlib, permission, textual, typing.
- Data flow: workspace/application state -> Textual widgets/screens -> user actions -> core service calls.
- Side effects: filesystem I/O or mutation; possible network call.
- Configuration assumptions: Textual optional UI dependency available for TUI paths.
- Maintenance risks: UI callback/state drift can evade static call maps.

### `core/tui/screens/workspace_screen.py`
- Lines read: 227.
- Purpose: Chinese Textual TUI component.
- Key responsibilities: classes: WorkspaceView; callables: __init__, compose, on_mount, focus_default, on_key, on_input_submitted, _get_controller, _load_workspaces
- Public interfaces: WorkspaceView, __init__, compose, on_mount, focus_default, on_key, on_input_submitted, on_button_pressed, on_data_table_row_selected
- Internal dependencies: core, pathlib, textual, typing.
- Data flow: workspace/application state -> Textual widgets/screens -> user actions -> core service calls.
- Side effects: possible network call.
- Configuration assumptions: Textual optional UI dependency available for TUI paths.
- Maintenance risks: UI callback/state drift can evade static call maps.

### `core/tui/screens/workspaces.py`
- Lines read: 167.
- Purpose: Chinese Textual TUI component.
- Key responsibilities: classes: WorkspaceScreenController; callables: workspace_label, workspace_manager, root, list_workspaces, create_workspace, select_workspace, recent_workspace, delete_workspace; constants: WORKSPACE_DELETE_ACTION, TUI_AGENT_ID
- Public interfaces: workspace_label, WorkspaceScreenController, workspace_manager, root, list_workspaces, create_workspace, select_workspace, recent_workspace, delete_workspace
- Internal dependencies: core, dataclasses, pathlib, permission, shutil, typing.
- Data flow: workspace/application state -> Textual widgets/screens -> user actions -> core service calls.
- Side effects: filesystem I/O or mutation.
- Configuration assumptions: Textual optional UI dependency available for TUI paths.
- Maintenance risks: UI callback/state drift can evade static call maps.

### `core/tui/state.py`
- Lines read: 109.
- Purpose: Chinese Textual TUI component.
- Key responsibilities: classes: TUIState; callables: save_recent_workspace, load_recent_workspace, list_workspaces, workspace_manager, save_recent_workspace, load_recent_workspace, list_workspaces, create_workspace
- Public interfaces: TUIState, save_recent_workspace, load_recent_workspace, list_workspaces, workspace_manager, save_recent_workspace, load_recent_workspace, list_workspaces, create_workspace, select_workspace, workspace_payloads
- Internal dependencies: core, dataclasses, pathlib, typing.
- Data flow: workspace/application state -> Textual widgets/screens -> user actions -> core service calls.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: Textual optional UI dependency available for TUI paths.
- Maintenance risks: UI callback/state drift can evade static call maps.

### `core/workspace.py`
- Lines read: 342.
- Purpose: Workspace identity and storage layout primitives.
- Key responsibilities: classes: WorkspaceError, InvalidWorkspaceId, WorkspaceNotFoundError, WorkspaceMetadata, WorkspaceInfo, WorkspaceManager; callables: validate_workspace_id, workspace_path, initialize_workspace, list_workspaces, get_workspace, save_recent_selection, load_recent_selection, to_dict; constants: WORKSPACES_DIR, WORKSPACE_METADATA_FILE, WORKSPACE_METADATA_VERSION, SESSION_STATE_FILE, _SLUG_RE
- Public interfaces: WorkspaceError, InvalidWorkspaceId, WorkspaceNotFoundError, WorkspaceMetadata, WorkspaceInfo, validate_workspace_id, WorkspaceManager, workspace_path, initialize_workspace, list_workspaces, get_workspace, save_recent_selection
- Internal dependencies: core, dataclasses, pathlib, re, typing, yaml.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: filesystem I/O or mutation; possible network call.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `core/workspace_tools.py`
- Lines read: 1007.
- Purpose: Workspace-local modular Python/R research tool support.
- Key responsibilities: classes: WorkspaceToolError, InvalidToolId, InvalidToolLanguage, ToolNotFoundError, ToolManifestError, ToolCandidateError; callables: _read_limited_text, _safe_load_manifest, _load_candidate_metadata, build_tool_authoring_llm_context, validate_tool_id, validate_language, _manifest_text, _slug_from_name; constants: TOOLS_DIR, MANIFEST_FILE, TOOL_SOURCE_ROOT, PYTHON_TOOL_STORAGE, R_TOOL_STORAGE, _TOOL_ID_RE
- Public interfaces: WorkspaceToolError, InvalidToolId, InvalidToolLanguage, ToolNotFoundError, ToolManifestError, ToolCandidateError, build_tool_authoring_llm_context, validate_tool_id, validate_language, ToolManifest, ToolInvocationPlan, ToolImportCandidate
- Internal dependencies: core, dataclasses, pathlib, permission, re, shutil, typing, yaml.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: filesystem I/O or mutation; possible network call.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `install.json`
- Lines read: 101.
- Purpose: JSON metadata/configuration artifact.
- Key responsibilities: Declarative content/no Python callables.
- Public interfaces: JSON fields consumed by installer/adapter metadata readers.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: filesystem permissions and PATH/venv layout vary by host.
- Maintenance risks: keep synchronized with callers and documentation.

### `install.py`
- Lines read: 24.
- Purpose: Top-level command compatibility entry point.
- Key responsibilities: Declarative content/no Python callables.
- Public interfaces: No function-level public interface; file is declarative/package metadata.
- Internal dependencies: installer.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: filesystem permissions and PATH/venv layout vary by host.
- Maintenance risks: keep synchronized with callers and documentation.

### `installer/__init__.py`
- Lines read: 27.
- Purpose: Install/uninstall/release support component.
- Key responsibilities: Declarative content/no Python callables.
- Public interfaces: No function-level public interface; file is declarative/package metadata.
- Internal dependencies: installer.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: filesystem permissions and PATH/venv layout vary by host.
- Maintenance risks: keep synchronized with callers and documentation.

### `installer/entrypoint.py`
- Lines read: 1036.
- Purpose: Install/uninstall/release support component.
- Key responsibilities: callables: _configure_stdio_errors, _default_config_text, _deep_merge_missing, _load_config, _write_config, _normalize_provider, _optional_string, _provider_api_format; constants: INSTALLER_TITLE, INSTALLER_RULE, PROVIDER_ENV_NAMES, INSTALL_ENV_NAMES
- Public interfaces: write_llm_config, detect_platform, init_config, main
- Internal dependencies: argparse, core, getpass, importlib, logging, os, pathlib, permission, shutil, sys, typing, urllib.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: console I/O; filesystem I/O or mutation; possible network call.
- Configuration assumptions: filesystem permissions and PATH/venv layout vary by host.
- Maintenance risks: keep synchronized with callers and documentation.

### `installer/exe_release.py`
- Lines read: 405.
- Purpose: Install/uninstall/release support component.
- Key responsibilities: classes: ExeReleaseError; callables: resolve_desktop_dir, resolve_exe_path, _release_root, bundled_release_payload_root, resolve_release_payload_root, validate_release_payload_root, _is_payload_excluded, iter_release_payload_files; constants: DEFAULT_TARGET_FILENAME, DEFAULT_INSTALLER_FILENAME, DEFAULT_RELEASE_PAYLOAD_DIRNAME, DEFAULT_EXE_SEARCH_RELATIVE_PATHS, RELEASE_PAYLOAD_REQUIRED_PATHS, _PAYLOAD_EXCLUDED_DIR_NAMES
- Public interfaces: ExeReleaseError, resolve_desktop_dir, resolve_exe_path, bundled_release_payload_root, resolve_release_payload_root, validate_release_payload_root, iter_release_payload_files, release_payload_to_directory, normalize_target_filename, release_exe_to_desktop
- Internal dependencies: logging, os, pathlib, shutil, sys, typing.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: filesystem I/O or mutation.
- Configuration assumptions: filesystem permissions and PATH/venv layout vary by host.
- Maintenance risks: keep synchronized with callers and documentation.

### `permission/__init__.py`
- Lines read: 32.
- Purpose: Permission/governance policy component.
- Key responsibilities: Declarative content/no Python callables.
- Public interfaces: No function-level public interface; file is declarative/package metadata.
- Internal dependencies: permission.
- Data flow: agent/action/resource context -> policy/mode evaluation -> allow/deny/audit decision.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: security boundary; avoid privilege/tool-call drift.

### `permission/access_mode.py`
- Lines read: 424.
- Purpose: Permission/governance policy component.
- Key responsibilities: classes: AccessMode, FileAccessOperation, AccessDecisionStatus, AccessModeError, FullAccessConfirmationRequired, UnsupportedAccessMode; callables: normalize_access_mode, normalize_file_operation, insufficient_permission_helper, allowed, requires_prompt, __init__, conservative, sandbox; constants: CONSERVATIVE, SANDBOX, FULL, READ, WRITE, DELETE
- Public interfaces: AccessMode, FileAccessOperation, AccessDecisionStatus, AccessModeError, FullAccessConfirmationRequired, UnsupportedAccessMode, AccessDecision, AccessModePolicy, normalize_access_mode, normalize_file_operation, insufficient_permission_helper, allowed
- Internal dependencies: dataclasses, enum, pathlib, typing.
- Data flow: agent/action/resource context -> policy/mode evaluation -> allow/deny/audit decision.
- Side effects: filesystem I/O or mutation.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: security boundary; avoid privilege/tool-call drift.

### `permission/audit.py`
- Lines read: 84.
- Purpose: Permission/governance policy component.
- Key responsibilities: classes: AuditLogger; callables: restrict_file_permissions, __init__, for_project, storage_path, _restrict_log_permissions, log, opener
- Public interfaces: restrict_file_permissions, AuditLogger, __init__, for_project, storage_path, log, opener
- Internal dependencies: core, datetime, json, logging, os, pathlib, uuid.
- Data flow: agent/action/resource context -> policy/mode evaluation -> allow/deny/audit decision.
- Side effects: filesystem I/O or mutation.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: security boundary; avoid privilege/tool-call drift.

### `permission/default_policy.yaml`
- Lines read: 218.
- Purpose: YAML configuration or plugin manifest.
- Key responsibilities: declared sections/keys: # SuperMedicine 默认权限策略, # 每个 Agent 按角色授予合理权限, # 插件执行必须经由 Kernel -> PermissionEngine 的 execute/action 策略路径。, # 实验指导器当前仅授权本地 experiment-wb 确定性插件动作；未知实验插件/action 默认拒绝。, role: "analyst"
- Public interfaces: Plugin/policy keys consumed by registry or permission tooling.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: agent/action/resource context -> policy/mode evaluation -> allow/deny/audit decision.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: security boundary; avoid privilege/tool-call drift.

### `permission/engine.py`
- Lines read: 212.
- Purpose: Permission/governance policy component.
- Key responsibilities: classes: PermissionPolicyLoadError, PermissionEngine; callables: __init__, default_policy_path, _load_policies, check; constants: DEFAULT_POLICY_FILENAME
- Public interfaces: PermissionPolicyLoadError, PermissionEngine, __init__, default_policy_path, check
- Internal dependencies: audit, pathlib, policy, typing, yaml.
- Data flow: agent/action/resource context -> policy/mode evaluation -> allow/deny/audit decision.
- Side effects: filesystem I/O or mutation; possible network call.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: security boundary; avoid privilege/tool-call drift.

### `permission/policy.py`
- Lines read: 171.
- Purpose: Permission/governance policy component.
- Key responsibilities: classes: PermissionResult, PermissionRule, HardLimits, PermissionPolicy; callables: default_policy_path, _bundled_default_policy_text, ensure_default_policy, matches, _scope_matches, _has_wildcard, _looks_like_path, _normalize_path_scope; constants: DEFAULT_POLICY_RELATIVE_PATH, BUNDLED_DEFAULT_POLICY_RESOURCE, ALLOWED, DENIED
- Public interfaces: default_policy_path, ensure_default_policy, PermissionResult, PermissionRule, HardLimits, PermissionPolicy, matches, items, from_dict, from_dict, check
- Internal dependencies: dataclasses, enum, fnmatch, importlib, os, pathlib, shutil, typing.
- Data flow: agent/action/resource context -> policy/mode evaluation -> allow/deny/audit decision.
- Side effects: filesystem I/O or mutation; possible network call.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: security boundary; avoid privilege/tool-call drift.

### `permission/prompt_generator.py`
- Lines read: 43.
- Purpose: Permission/governance policy component.
- Key responsibilities: classes: PromptGenerator; callables: generate_prefix, generate_rejection_templates; constants: SELF_EVOLUTION_GUIDANCE
- Public interfaces: PromptGenerator, generate_prefix, generate_rejection_templates
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: agent/action/resource context -> policy/mode evaluation -> allow/deny/audit decision.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: security boundary; avoid privilege/tool-call drift.

### `plugins/__init__.py`
- Lines read: 7.
- Purpose: SuperMedicine 插件系统
- Key responsibilities: Declarative content/no Python callables.
- Public interfaces: No function-level public interface; file is declarative/package metadata.
- Internal dependencies: plugins.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `plugins/base_plugin.py`
- Lines read: 243.
- Purpose: 插件基类与最小执行契约。
- Key responsibilities: classes: PluginMeta, BasePlugin; callables: plugin_result, from_dict, __init__, meta, name, execute, health_check, _direct_execution_denied; constants: PLUGIN_CONTRACT_VERSION
- Public interfaces: plugin_result, PluginMeta, BasePlugin, from_dict, __init__, meta, name, execute, health_check
- Internal dependencies: core, dataclasses, importlib, inspect, os, pathlib, typing.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: filesystem I/O or mutation; possible network call.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `plugins/experiments/cell_culture_basic.yaml`
- Lines read: 49.
- Purpose: YAML configuration or plugin manifest.
- Key responsibilities: declared sections/keys: protocol_id: cell_culture_basic, title: 细胞培养基础流程, description: 细胞复苏、传代、处理与观察记录的基础实验指导配置示例。, version: "1.0", metadata:
- Public interfaces: Plugin/policy keys consumed by registry or permission tooling.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `plugins/experiments/western_blot_basic.yaml`
- Lines read: 84.
- Purpose: YAML configuration or plugin manifest.
- Key responsibilities: declared sections/keys: protocol_id: western_blot_basic, title: Western Blot 基础流程, description: Western Blot 实验指导骨架，用于逐步记录样本、转膜、封闭、孵育、显影与分析信息。, version: "1.0", metadata:
- Public interfaces: Plugin/policy keys consumed by registry or permission tooling.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `plugins/harness/__init__.py`
- Lines read: 8.
- Purpose: 测试评估与 Agent 监控
- Key responsibilities: Declarative content/no Python callables.
- Public interfaces: No function-level public interface; file is declarative/package metadata.
- Internal dependencies: plugins.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `plugins/harness/checkpoint_verifier.py`
- Lines read: 130.
- Purpose: 检查点验证器 — 验证检查点完整性和可恢复性
- Key responsibilities: classes: CheckpointVerifier; callables: __init__, verify, verify_all
- Public interfaces: CheckpointVerifier, __init__, verify, verify_all
- Internal dependencies: json, pathlib, typing.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: filesystem I/O or mutation; possible network call.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `plugins/harness/main.py`
- Lines read: 201.
- Purpose: Executable entrypoint for the harness-core manifest plugin.
- Key responsibilities: callables: execute, _execute_checkpoint, _execute_checkpoint_all, _execute_permission_audit, _execute_denied_actions, _execute_anomaly, _execute_performance, _execute_failure_patterns; constants: PLUGIN_NAME
- Public interfaces: execute
- Internal dependencies: pathlib, plugins, typing.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: possible network call.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `plugins/harness/monitor.py`
- Lines read: 249.
- Purpose: Agent 行为监控
- Key responsibilities: classes: AgentMonitor, AgentPerformanceMonitor; callables: _jsonl_warning, _read_jsonl_objects, __init__, warnings, get_permission_audit, get_denied_actions, detect_anomalies, __init__
- Public interfaces: AgentMonitor, AgentPerformanceMonitor, __init__, warnings, get_permission_audit, get_denied_actions, detect_anomalies, __init__, warnings, record, get_stats, detect_failure_patterns
- Internal dependencies: datetime, json, pathlib, typing.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: filesystem I/O or mutation; possible network call.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `plugins/harness/plugin.yaml`
- Lines read: 21.
- Purpose: YAML configuration or plugin manifest.
- Key responsibilities: declared sections/keys: name: "harness-core", version: "0.1.0", type: "harness", language: "python", entry: "main.py"
- Public interfaces: Plugin/policy keys consumed by registry or permission tooling.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `plugins/rag/__init__.py`
- Lines read: 32.
- Purpose: RAG/local knowledge retrieval plugin component.
- Key responsibilities: Declarative content/no Python callables.
- Public interfaces: No function-level public interface; file is declarative/package metadata.
- Internal dependencies: plugins.
- Data flow: query/config -> provider selection -> local/PubMed retrieval -> ranked document/result dictionaries.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: external metadata/schema/provider variability.

### `plugins/rag/interface.py`
- Lines read: 190.
- Purpose: RAG/local knowledge retrieval plugin component.
- Key responsibilities: classes: RAGProviderConfig, RAGProviderError, RAGConfigurationError, RAGConnectionError, RAGQueryTimeoutError, RAGResourceError; callables: make_rag_result, resource_metadata, __init__, to_dict, connect, query, store_context, retrieve_context
- Public interfaces: RAGProviderConfig, RAGProviderError, RAGConfigurationError, RAGConnectionError, RAGQueryTimeoutError, RAGResourceError, make_rag_result, RAGProvider, EmptyRAGProvider, resource_metadata, __init__, to_dict
- Internal dependencies: core, dataclasses, typing.
- Data flow: query/config -> provider selection -> local/PubMed retrieval -> ranked document/result dictionaries.
- Side effects: possible network call.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: external metadata/schema/provider variability.

### `plugins/rag/local_provider.py`
- Lines read: 363.
- Purpose: RAG/local knowledge retrieval plugin component.
- Key responsibilities: classes: LocalRAGProvider, MockExternalVectorStoreProvider; callables: __init__, _load_index, _save_index, add_document, query, store_context, retrieve_context, _context_file_for_key; constants: _SAFE_CONTEXT_KEY
- Public interfaces: LocalRAGProvider, MockExternalVectorStoreProvider, __init__, add_document, query, store_context, retrieve_context, __init__, connect, query, store_context, retrieve_context
- Internal dependencies: collections, interface, json, math, pathlib, re, typing.
- Data flow: query/config -> provider selection -> local/PubMed retrieval -> ranked document/result dictionaries.
- Side effects: filesystem I/O or mutation; possible network call.
- Configuration assumptions: local knowledge files stay inside permitted workspace paths.
- Maintenance risks: external metadata/schema/provider variability.

### `plugins/rag/main.py`
- Lines read: 274.
- Purpose: RAG/local knowledge retrieval plugin component.
- Key responsibilities: callables: execute, _execute_query, _execute_context_store, _execute_context_retrieve, _base_metadata, _storage_dir, _seed_local_documents, _provider_config; constants: PLUGIN_NAME
- Public interfaces: execute
- Internal dependencies: pathlib, plugins, tempfile, typing.
- Data flow: query/config -> provider selection -> local/PubMed retrieval -> ranked document/result dictionaries.
- Side effects: possible network call.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: external metadata/schema/provider variability.

### `plugins/rag/plugin.yaml`
- Lines read: 19.
- Purpose: YAML configuration or plugin manifest.
- Key responsibilities: declared sections/keys: name: "rag-interface", version: "0.1.0", type: "rag", language: "python", entry: "main.py"
- Public interfaces: Plugin/policy keys consumed by registry or permission tooling.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: query/config -> provider selection -> local/PubMed retrieval -> ranked document/result dictionaries.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: external metadata/schema/provider variability.

### `plugins/rag/pubmed_provider.py`
- Lines read: 420.
- Purpose: RAG/local knowledge retrieval plugin component.
- Key responsibilities: classes: PubmedRAGProvider; callables: __init__, connect, query, _search, _fetch, _parse_articles, _parse_article, _get_json; constants: BASE_URL, MAX_RESPONSE_BYTES
- Public interfaces: PubmedRAGProvider, __init__, connect, query, store_context, retrieve_context
- Internal dependencies: interface, json, permission, typing, urllib, xml.
- Data flow: query/config -> provider selection -> local/PubMed retrieval -> ranked document/result dictionaries.
- Side effects: possible network call.
- Configuration assumptions: network access and PubMed API availability are optional/permissioned.
- Maintenance risks: external metadata/schema/provider variability.

### `plugins/rag/references/provider-interface.md`
- Lines read: 29.
- Purpose: Maintainer/user documentation for provider interface.
- Key responsibilities: declared sections/keys: # RAG Provider 实现规范, ## 接口要求, ### query(query: str, scope: str) -> dict, ### store_context(key: str, value: Any) -> None, ### retrieve_context(key: str) -> Any | None
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: query/config -> provider selection -> local/PubMed retrieval -> ranked document/result dictionaries.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: external metadata/schema/provider variability.

### `plugins/standards/__init__.py`
- Lines read: 3.
- Purpose: SuperMedicine standards plugins.
- Key responsibilities: Declarative content/no Python callables.
- Public interfaces: No function-level public interface; file is declarative/package metadata.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `plugins/standards/medical_citation/__init__.py`
- Lines read: 8.
- Purpose: Medical citation formatting/checking plugin component.
- Key responsibilities: Declarative content/no Python callables.
- Public interfaces: No function-level public interface; file is declarative/package metadata.
- Internal dependencies: ama_format, vancouver_format.
- Data flow: citation/reference inputs -> normalization/format validation -> structured citation output/issues.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: medical standards can change; keep checklists/format rules current.

### `plugins/standards/medical_citation/ama_format.py`
- Lines read: 17.
- Purpose: Medical citation formatting/checking plugin component.
- Key responsibilities: classes: AMAFormatter; callables: format_journal, format_book
- Public interfaces: AMAFormatter, format_journal, format_book
- Internal dependencies: utils.
- Data flow: citation/reference inputs -> normalization/format validation -> structured citation output/issues.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: medical standards can change; keep checklists/format rules current.

### `plugins/standards/medical_citation/main.py`
- Lines read: 299.
- Purpose: Medical citation formatting/checking plugin component.
- Key responsibilities: callables: execute, _execute_citation, _base_metadata, _sources_from_params, _source_from_dict, _reference_from_source_dict, _journal_from_dict, _book_from_dict; constants: PLUGIN_NAME, MEDICAL_BOUNDARY
- Public interfaces: execute
- Internal dependencies: plugins, typing.
- Data flow: citation/reference inputs -> normalization/format validation -> structured citation output/issues.
- Side effects: possible network call.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: medical standards can change; keep checklists/format rules current.

### `plugins/standards/medical_citation/plugin.yaml`
- Lines read: 12.
- Purpose: YAML configuration or plugin manifest.
- Key responsibilities: declared sections/keys: name: "medical-citation", version: "0.1.0", type: "standard", language: "python", entry: "main.py"
- Public interfaces: Plugin/policy keys consumed by registry or permission tooling.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: citation/reference inputs -> normalization/format validation -> structured citation output/issues.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: medical standards can change; keep checklists/format rules current.

### `plugins/standards/medical_citation/utils.py`
- Lines read: 212.
- Purpose: Medical citation formatting/checking plugin component.
- Key responsibilities: classes: JournalArticle, Book, CitationSource, CitationValidationResult; callables: validate_source_id, citation_state_from_validation, citation_provenance_from_source, format_authors, format_journal_base, format_book_base; constants: LOW_CONFIDENCE_THRESHOLD
- Public interfaces: JournalArticle, Book, CitationSource, CitationValidationResult, validate_source_id, citation_state_from_validation, citation_provenance_from_source, format_authors, format_journal_base, format_book_base
- Internal dependencies: dataclasses.
- Data flow: citation/reference inputs -> normalization/format validation -> structured citation output/issues.
- Side effects: possible network call.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: medical standards can change; keep checklists/format rules current.

### `plugins/standards/medical_citation/vancouver_format.py`
- Lines read: 18.
- Purpose: Medical citation formatting/checking plugin component.
- Key responsibilities: classes: VancouverFormatter; callables: format_journal, format_book
- Public interfaces: VancouverFormatter, format_journal, format_book
- Internal dependencies: utils.
- Data flow: citation/reference inputs -> normalization/format validation -> structured citation output/issues.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: medical standards can change; keep checklists/format rules current.

### `plugins/standards/medical_writing/__init__.py`
- Lines read: 23.
- Purpose: Medical writing guideline/checklist plugin component.
- Key responsibilities: Declarative content/no Python callables.
- Public interfaces: No function-level public interface; file is declarative/package metadata.
- Internal dependencies: checklists, prisma, stard.
- Data flow: manuscript/checklist inputs -> standard-specific checks -> compliance report/items.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: medical standards can change; keep checklists/format rules current.

### `plugins/standards/medical_writing/checklist_base.py`
- Lines read: 259.
- Purpose: Medical writing guideline/checklist plugin component.
- Key responsibilities: classes: ChecklistItemBase, MedicalClaim, ChecklistBase; callables: _infer_claim_type, _split_claim_sentences, annotate_medical_claims, _citation_issue_type, _claim_audit_summary, enforce_medical_accuracy, __init__, check; constants: HUMAN_REVIEW_MESSAGE, MEDICAL_FACT_KEYWORDS
- Public interfaces: ChecklistItemBase, MedicalClaim, annotate_medical_claims, enforce_medical_accuracy, ChecklistBase, __init__, check
- Internal dependencies: dataclasses, plugins, typing.
- Data flow: manuscript/checklist inputs -> standard-specific checks -> compliance report/items.
- Side effects: filesystem I/O or mutation; possible network call.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: medical standards can change; keep checklists/format rules current.

### `plugins/standards/medical_writing/checklists.py`
- Lines read: 125.
- Purpose: Medical writing guideline/checklist plugin component.
- Key responsibilities: classes: ChecklistItem, Checklist; callables: get_consort_checklist, get_strobe_checklist, __init__, check
- Public interfaces: ChecklistItem, Checklist, get_consort_checklist, get_strobe_checklist, __init__, check
- Internal dependencies: checklist_base, dataclasses, plugins, typing.
- Data flow: manuscript/checklist inputs -> standard-specific checks -> compliance report/items.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: medical standards can change; keep checklists/format rules current.

### `plugins/standards/medical_writing/main.py`
- Lines read: 288.
- Purpose: Medical writing guideline/checklist plugin component.
- Key responsibilities: callables: execute, _checklist_for_action, _base_metadata, _required_text, _claims_from_params, _optional_claim_str, _optional_claim_str, _optional_claim_str; constants: PLUGIN_NAME, MEDICAL_BOUNDARY
- Public interfaces: execute
- Internal dependencies: checklist_base, checklists, plugins, prisma, stard, typing.
- Data flow: manuscript/checklist inputs -> standard-specific checks -> compliance report/items.
- Side effects: possible network call.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: medical standards can change; keep checklists/format rules current.

### `plugins/standards/medical_writing/plugin.yaml`
- Lines read: 22.
- Purpose: YAML configuration or plugin manifest.
- Key responsibilities: declared sections/keys: name: "medical-writing", version: "0.1.0", type: "standard", language: "python", entry: "main.py"
- Public interfaces: Plugin/policy keys consumed by registry or permission tooling.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: manuscript/checklist inputs -> standard-specific checks -> compliance report/items.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: medical standards can change; keep checklists/format rules current.

### `plugins/standards/medical_writing/prisma.py`
- Lines read: 165.
- Purpose: Medical writing guideline/checklist plugin component.
- Key responsibilities: classes: PRISMAChecklist; callables: __init__, _init_items
- Public interfaces: PRISMAChecklist, __init__
- Internal dependencies: checklist_base.
- Data flow: manuscript/checklist inputs -> standard-specific checks -> compliance report/items.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: medical standards can change; keep checklists/format rules current.

### `plugins/standards/medical_writing/references/consort-checklist.md`
- Lines read: 64.
- Purpose: Maintainer/user documentation for consort checklist.
- Key responsibilities: declared sections/keys: # CONSORT 2010 Checklist, ## Checklist Items, ## Reference, ## Usage, checklist = get_consort_checklist()
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: manuscript/checklist inputs -> standard-specific checks -> compliance report/items.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: medical standards can change; keep checklists/format rules current.

### `plugins/standards/medical_writing/references/prisma-checklist.md`
- Lines read: 60.
- Purpose: Maintainer/user documentation for prisma checklist.
- Key responsibilities: declared sections/keys: # PRISMA 2020 Checklist, ## Checklist Items, ## References
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: manuscript/checklist inputs -> standard-specific checks -> compliance report/items.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: medical standards can change; keep checklists/format rules current.

### `plugins/standards/medical_writing/references/stard-checklist.md`
- Lines read: 49.
- Purpose: Maintainer/user documentation for stard checklist.
- Key responsibilities: declared sections/keys: # STARD 2015 Checklist, ## Checklist Items, ## References
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: manuscript/checklist inputs -> standard-specific checks -> compliance report/items.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: medical standards can change; keep checklists/format rules current.

### `plugins/standards/medical_writing/references/strobe-checklist.md`
- Lines read: 51.
- Purpose: Maintainer/user documentation for strobe checklist.
- Key responsibilities: declared sections/keys: # STROBE 2007 Checklist, ## Checklist Items, ## References
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: manuscript/checklist inputs -> standard-specific checks -> compliance report/items.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: medical standards can change; keep checklists/format rules current.

### `plugins/standards/medical_writing/stard.py`
- Lines read: 135.
- Purpose: Medical writing guideline/checklist plugin component.
- Key responsibilities: classes: STARDChecklist; callables: __init__, _init_items
- Public interfaces: STARDChecklist, __init__
- Internal dependencies: checklist_base.
- Data flow: manuscript/checklist inputs -> standard-specific checks -> compliance report/items.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: medical standards can change; keep checklists/format rules current.

### `plugins/tools/__init__.py`
- Lines read: 3.
- Purpose: Scientific/statistical tool plugin component.
- Key responsibilities: Declarative content/no Python callables.
- Public interfaces: No function-level public interface; file is declarative/package metadata.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: tool parameters/data -> plugin runner/statistical adapter -> structured analysis result.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `plugins/tools/_common.py`
- Lines read: 93.
- Purpose: Scientific/statistical tool plugin component.
- Key responsibilities: callables: param_or_default, as_float_list, as_float_groups, normal_cdf, required_str
- Public interfaces: param_or_default, as_float_list, as_float_groups, normal_cdf, required_str
- Internal dependencies: math, typing.
- Data flow: tool parameters/data -> plugin runner/statistical adapter -> structured analysis result.
- Side effects: possible network call.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `plugins/tools/experiment_wb/__init__.py`
- Lines read: 7.
- Purpose: Scientific/statistical tool plugin component.
- Key responsibilities: Declarative content/no Python callables.
- Public interfaces: No function-level public interface; file is declarative/package metadata.
- Internal dependencies: main.
- Data flow: tool parameters/data -> plugin runner/statistical adapter -> structured analysis result.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `plugins/tools/experiment_wb/main.py`
- Lines read: 319.
- Purpose: Scientific/statistical tool plugin component.
- Key responsibilities: callables: normalize_loading, antibody_dilution, execute, _base_metadata, _required_samples, _positive_float, _optional_positive_float, _optional_str; constants: PLUGIN_NAME, MEDICAL_BOUNDARY
- Public interfaces: normalize_loading, antibody_dilution, execute
- Internal dependencies: plugins, typing.
- Data flow: tool parameters/data -> plugin runner/statistical adapter -> structured analysis result.
- Side effects: possible network call.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `plugins/tools/experiment_wb/plugin.yaml`
- Lines read: 13.
- Purpose: YAML configuration or plugin manifest.
- Key responsibilities: declared sections/keys: name: "experiment-wb", version: "0.1.0", type: "tool", language: "python", description: "Western Blot 实验确定性计算工具"
- Public interfaces: Plugin/policy keys consumed by registry or permission tooling.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: tool parameters/data -> plugin runner/statistical adapter -> structured analysis result.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `plugins/tools/python_data_analysis/README.md`
- Lines read: 17.
- Purpose: Maintainer/user documentation for README.
- Key responsibilities: declared sections/keys: # Python Data Analysis Workspace Tool, ## Safety Boundary
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: tool parameters/data -> plugin runner/statistical adapter -> structured analysis result.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `plugins/tools/python_data_analysis/runner.py`
- Lines read: 330.
- Purpose: Scientific/statistical tool plugin component.
- Key responsibilities: callables: _sample_rows, _read_rows, _is_missing, _float, _numeric_columns, _mean, _variance, _normal_cdf; constants: MISSING, OPTIONAL_PACKAGES
- Public interfaces: descriptive, missing, scale, correlation, linear_regression, logistic_regression, pca, kmeans, hierarchical, time_series, t_test, chi_square
- Internal dependencies: argparse, csv, importlib, json, math, pathlib, statistics, sys, typing.
- Data flow: tool parameters/data -> plugin runner/statistical adapter -> structured analysis result.
- Side effects: console I/O; filesystem I/O or mutation; possible network call; subprocess execution.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `plugins/tools/python_data_analysis/tool.yaml`
- Lines read: 25.
- Purpose: YAML configuration or plugin manifest.
- Key responsibilities: declared sections/keys: id: "python-data-analysis", language: "python", name: "Python mainstream data analysis algorithms", description: "Lightweight Python data-analysis toolkit covering descriptive statistics, missing-value summaries, scaling, entrypoint: "runner.py"
- Public interfaces: Plugin/policy keys consumed by registry or permission tooling.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: tool parameters/data -> plugin runner/statistical adapter -> structured analysis result.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `plugins/tools/python_stats/__init__.py`
- Lines read: 7.
- Purpose: Scientific/statistical tool plugin component.
- Key responsibilities: Declarative content/no Python callables.
- Public interfaces: No function-level public interface; file is declarative/package metadata.
- Internal dependencies: main.
- Data flow: tool parameters/data -> plugin runner/statistical adapter -> structured analysis result.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `plugins/tools/python_stats/main.py`
- Lines read: 287.
- Purpose: Scientific/statistical tool plugin component.
- Key responsibilities: callables: descriptive, ttest, anova, regression, execute, _f_cdf; constants: MEDICAL_BOUNDARY, STATISTICS_BOUNDARY
- Public interfaces: descriptive, ttest, anova, regression, execute
- Internal dependencies: math, plugins, typing.
- Data flow: tool parameters/data -> plugin runner/statistical adapter -> structured analysis result.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `plugins/tools/python_stats/plugin.yaml`
- Lines read: 18.
- Purpose: YAML configuration or plugin manifest.
- Key responsibilities: declared sections/keys: name: "python-stats", version: "0.1.0", type: "tool", language: "python", description: "Python 统计分析工具集"
- Public interfaces: Plugin/policy keys consumed by registry or permission tooling.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: tool parameters/data -> plugin runner/statistical adapter -> structured analysis result.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `plugins/tools/r_data_analysis/README.md`
- Lines read: 14.
- Purpose: Maintainer/user documentation for README.
- Key responsibilities: declared sections/keys: # R Data Analysis Workspace Tool, ## Safety Boundary
- Public interfaces: Human-facing Markdown content; headings and checklists are the public interface.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: tool parameters/data -> plugin runner/statistical adapter -> structured analysis result.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: requires local R/rpy2/survival availability when executed.
- Maintenance risks: keep synchronized with callers and documentation.

### `plugins/tools/r_data_analysis/runner.R`
- Lines read: 172.
- Purpose: R tool runner/template script.
- Key responsibilities: Declarative content/no Python callables.
- Public interfaces: Command-line R script contract.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: tool parameters/data -> plugin runner/statistical adapter -> structured analysis result.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: requires local R/rpy2/survival availability when executed.
- Maintenance risks: keep synchronized with callers and documentation.

### `plugins/tools/r_data_analysis/tool.yaml`
- Lines read: 25.
- Purpose: YAML configuration or plugin manifest.
- Key responsibilities: declared sections/keys: id: "r-data-analysis", language: "r", name: "R mainstream data analysis algorithms", description: "Base-R data-analysis toolkit covering descriptive statistics, missing-value summaries, scaling, correlatio, entrypoint: "runner.R"
- Public interfaces: Plugin/policy keys consumed by registry or permission tooling.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: tool parameters/data -> plugin runner/statistical adapter -> structured analysis result.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: requires local R/rpy2/survival availability when executed.
- Maintenance risks: keep synchronized with callers and documentation.

### `plugins/tools/r_survival/__init__.py`
- Lines read: 9.
- Purpose: Scientific/statistical tool plugin component.
- Key responsibilities: Declarative content/no Python callables.
- Public interfaces: No function-level public interface; file is declarative/package metadata.
- Internal dependencies: cox_model, kaplan_meier, logrank.
- Data flow: tool parameters/data -> plugin runner/statistical adapter -> structured analysis result.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: requires local R/rpy2/survival availability when executed.
- Maintenance risks: keep synchronized with callers and documentation.

### `plugins/tools/r_survival/cox_model.py`
- Lines read: 161.
- Purpose: Scientific/statistical tool plugin component.
- Key responsibilities: classes: CoxResult; callables: cox_ph, _exp_dot
- Public interfaces: CoxResult, cox_ph
- Internal dependencies: dataclasses, math, plugins.
- Data flow: tool parameters/data -> plugin runner/statistical adapter -> structured analysis result.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: requires local R/rpy2/survival availability when executed.
- Maintenance risks: keep synchronized with callers and documentation.

### `plugins/tools/r_survival/kaplan_meier.py`
- Lines read: 123.
- Purpose: Scientific/statistical tool plugin component.
- Key responsibilities: classes: KMSurvivalPoint, KMResult; callables: kaplan_meier
- Public interfaces: KMSurvivalPoint, KMResult, kaplan_meier
- Internal dependencies: dataclasses, math.
- Data flow: tool parameters/data -> plugin runner/statistical adapter -> structured analysis result.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: requires local R/rpy2/survival availability when executed.
- Maintenance risks: keep synchronized with callers and documentation.

### `plugins/tools/r_survival/logrank.py`
- Lines read: 117.
- Purpose: Scientific/statistical tool plugin component.
- Key responsibilities: classes: LogRankResult; callables: logrank_test, _chi2_cdf
- Public interfaces: LogRankResult, logrank_test
- Internal dependencies: dataclasses, kaplan_meier, math.
- Data flow: tool parameters/data -> plugin runner/statistical adapter -> structured analysis result.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: requires local R/rpy2/survival availability when executed.
- Maintenance risks: keep synchronized with callers and documentation.

### `plugins/tools/r_survival/main.py`
- Lines read: 580.
- Purpose: Scientific/statistical tool plugin component.
- Key responsibilities: callables: _optional_int, _r_backend_imports, _r_backend_status, km_tool, logrank_tool, cox_tool, km_tool_r, logrank_tool_r; constants: MEDICAL_BOUNDARY, STATISTICS_BOUNDARY, R_BACKEND_REQUEST_VALUES, PYTHON_BACKEND_REQUEST_VALUES
- Public interfaces: km_tool, logrank_tool, cox_tool, km_tool_r, logrank_tool_r, cox_tool_r, execute
- Internal dependencies: cox_model, functools, kaplan_meier, logging, logrank, plugins, rpy2, typing.
- Data flow: tool parameters/data -> plugin runner/statistical adapter -> structured analysis result.
- Side effects: possible network call.
- Configuration assumptions: requires local R/rpy2/survival availability when executed.
- Maintenance risks: keep synchronized with callers and documentation.

### `plugins/tools/r_survival/plugin.yaml`
- Lines read: 15.
- Purpose: YAML configuration or plugin manifest.
- Key responsibilities: declared sections/keys: name: "r-survival", version: "0.1.0", type: "tool", language: "python", description: "R 生存分析工具集（Python 模拟）"
- Public interfaces: Plugin/policy keys consumed by registry or permission tooling.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: tool parameters/data -> plugin runner/statistical adapter -> structured analysis result.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: requires local R/rpy2/survival availability when executed.
- Maintenance risks: keep synchronized with callers and documentation.

### `plugins/tools/r_template/__init__.py`
- Lines read: 1.
- Purpose: Scientific/statistical tool plugin component.
- Key responsibilities: Declarative content/no Python callables.
- Public interfaces: No function-level public interface; file is declarative/package metadata.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: tool parameters/data -> plugin runner/statistical adapter -> structured analysis result.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: requires local R/rpy2/survival availability when executed.
- Maintenance risks: keep synchronized with callers and documentation.

### `plugins/tools/r_template/runner.R`
- Lines read: 4.
- Purpose: R tool runner/template script.
- Key responsibilities: Declarative content/no Python callables.
- Public interfaces: Command-line R script contract.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: tool parameters/data -> plugin runner/statistical adapter -> structured analysis result.
- Side effects: none apparent from static/line reading.
- Configuration assumptions: requires local R/rpy2/survival availability when executed.
- Maintenance risks: keep synchronized with callers and documentation.

### `plugins/tools/r_template/tool.yaml`
- Lines read: 17.
- Purpose: YAML configuration or plugin manifest.
- Key responsibilities: declared sections/keys: id: "r-template", name: "r-template", version: "0.1.0", language: "r", description: "R 数据分析工具模板"
- Public interfaces: Plugin/policy keys consumed by registry or permission tooling.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: tool parameters/data -> plugin runner/statistical adapter -> structured analysis result.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: requires local R/rpy2/survival availability when executed.
- Maintenance risks: keep synchronized with callers and documentation.

### `pyproject.toml`
- Lines read: 106.
- Purpose: Python package/build configuration.
- Key responsibilities: declared sections/keys: requires = ["setuptools>=68.0", "wheel"], build-backend = "setuptools.build_meta", name = "supermedicine", version = "0.4.2b0", description = "Modular Medical Research Agent with RAG and Harness"
- Public interfaces: No function-level public interface; file is declarative/package metadata.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `requirements.txt`
- Lines read: 3.
- Purpose: Pinned/runtime dependency list.
- Key responsibilities: Declarative content/no Python callables.
- Public interfaces: No function-level public interface; file is declarative/package metadata.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: no runtime side effects when read as documentation/config.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `setup.py`
- Lines read: 321.
- Purpose: Repository source component.
- Key responsibilities: classes: build_py, sdist, bdist_wheel; callables: _repo_root, _lowercase_install_bytes, _uppercase_install_bytes, _install_payloads, _write_case_distinct_installs, _remove_stale_distribution_members, _supports_case_distinct_names, _ensure_zip_members; constants: LOWERCASE_INSTALL_NAME, UPPERCASE_INSTALL_NAME, LOWERCASE_INSTALL_BYTES, UPPERCASE_INSTALL_BYTES, STALE_DISTRIBUTION_MEMBERS
- Public interfaces: build_py, sdist, run, make_distribution, bdist_wheel, run
- Internal dependencies: base64, hashlib, io, pathlib, setuptools, subprocess, tarfile, wheel, zipfile.
- Data flow: loaded/read by packaging, CLI, docs, registry, or maintainer workflows as appropriate.
- Side effects: filesystem I/O or mutation; subprocess execution.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: keep synchronized with callers and documentation.

### `tests/__init__.py`
- Lines read: 3.
- Purpose: Test coverage for tests/  init   behavior.
- Key responsibilities: Declarative content/no Python callables.
- Public interfaces: No function-level public interface; file is declarative/package metadata.
- Internal dependencies: none beyond file format/runtime loader.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/conftest.py`
- Lines read: 83.
- Purpose: Test coverage for tests/conftest behavior.
- Key responsibilities: callables: block_real_network, sample_config_yaml, sample_policy_dir, sample_plugin_dir, empty_audit_log, _blocked_urlopen
- Public interfaces: block_real_network, sample_config_yaml, sample_policy_dir, sample_plugin_dir, empty_audit_log
- Internal dependencies: pathlib, pytest, urllib, yaml.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_audit.py`
- Lines read: 179.
- Purpose: Test coverage for audit behavior.
- Key responsibilities: classes: TestAuditLogger; callables: test_log_entry_creation, test_multiple_entries, test_audit_log_redacts_secret_values, test_audit_log_redacts_experiment_plugin_resource_and_reason, test_audit_log_redacts_headers_cookies_password_and_private_key, test_new_audit_log_is_owner_only_when_platform_supports_modes, test_chmod_failure_emits_redacted_warning, test_audit_context_is_redacted_for_permission_boundaries
- Public interfaces: TestAuditLogger, test_log_entry_creation, test_multiple_entries, test_audit_log_redacts_secret_values, test_audit_log_redacts_experiment_plugin_resource_and_reason, test_audit_log_redacts_headers_cookies_password_and_private_key, test_new_audit_log_is_owner_only_when_platform_supports_modes, test_chmod_failure_emits_redacted_warning, test_audit_context_is_redacted_for_permission_boundaries, fail_chmod
- Internal dependencies: json, permission, stat.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_backward_compatibility.py`
- Lines read: 477.
- Purpose: Test coverage for backward compatibility behavior.
- Key responsibilities: classes: FakeRegistry, FakeCheckpointManager, FakeKernel; callables: _copy_default_policy, _write_policy, _init_args, test_cli_help_preserves_legacy_commands_and_run_flags, test_core_cli_kernel_imports_do_not_load_platform_adapters, test_cli_help_and_init_do_not_require_platform_runtime_or_config, test_cli_help_documents_workspace_tui_paper_and_experience_boundaries, test_cli_run_without_workspace_preserves_params_identity_and_ignores_tui_recent_state; constants: REPO_ROOT
- Public interfaces: test_cli_help_preserves_legacy_commands_and_run_flags, test_core_cli_kernel_imports_do_not_load_platform_adapters, test_cli_help_and_init_do_not_require_platform_runtime_or_config, test_cli_help_documents_workspace_tui_paper_and_experience_boundaries, test_cli_run_without_workspace_preserves_params_identity_and_ignores_tui_recent_state, test_plugin_manifest_names_and_action_ids_are_unchanged, test_permission_engine_denies_unknown_agents_and_preserves_hard_limits, test_kernel_execute_task_result_shape_and_permission_gate_are_stable, test_rag_actions_and_result_contract_are_unchanged, test_adapter_gated_tools_remain_bash_write_edit, test_legacy_openrouter_factory_still_uses_openai_compatible_defaults, test_paper_and_experience_paths_do_not_read_tui_recent_workspace_state
- Internal dependencies: Cli, adapters, core, importlib, pathlib, permission, plugins, pytest, sys, yaml.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; possible network call; subprocess execution; test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_checkpoint.py`
- Lines read: 98.
- Purpose: Test coverage for checkpoint behavior.
- Key responsibilities: classes: TestCheckpointManager; callables: test_save_checkpoint, test_load_checkpoint, test_get_latest_step, test_load_nonexistent_returns_none, test_checkpoint_includes_agent_state_timestamp_and_summaries, test_failure_checkpoint_and_not_recoverable_report, test_recoverable_report_for_running_checkpoint, test_checkpoint_redacts_sensitive_values
- Public interfaces: TestCheckpointManager, test_save_checkpoint, test_load_checkpoint, test_get_latest_step, test_load_nonexistent_returns_none, test_checkpoint_includes_agent_state_timestamp_and_summaries, test_failure_checkpoint_and_not_recoverable_report, test_recoverable_report_for_running_checkpoint, test_checkpoint_redacts_sensitive_values
- Internal dependencies: agents.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_checkpoint_verifier.py`
- Lines read: 106.
- Purpose: Test coverage for checkpoint verifier behavior.
- Key responsibilities: classes: TestCheckpointVerifier; callables: test_verify_missing_task, test_verify_complete_checkpoint, test_verify_incomplete_checkpoint, test_verify_structural_complete_distinct_from_final_state_success, test_verify_malformed_status_is_warning_not_crash, test_verify_all
- Public interfaces: TestCheckpointVerifier, test_verify_missing_task, test_verify_complete_checkpoint, test_verify_incomplete_checkpoint, test_verify_structural_complete_distinct_from_final_state_success, test_verify_malformed_status_is_warning_not_crash, test_verify_all
- Internal dependencies: json, plugins.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_claude_code_adapter.py`
- Lines read: 359.
- Purpose: Test coverage for claude code adapter behavior.
- Key responsibilities: classes: TestClaudeCodeAdapter; callables: _write_policy, test_is_base_adapter, test_explicit_optional_import_degrades_without_claude_runtime, test_platform_name_and_registration, test_capabilities_available_with_mock_runtime, test_capabilities_do_not_expose_environment_api_keys, test_runtime_unavailable_returns_structured_state, test_invoke_available_mock_path; constants: FORBIDDEN_PLATFORM_AGENT_NAMES
- Public interfaces: TestClaudeCodeAdapter, test_is_base_adapter, test_explicit_optional_import_degrades_without_claude_runtime, test_platform_name_and_registration, test_capabilities_available_with_mock_runtime, test_capabilities_do_not_expose_environment_api_keys, test_runtime_unavailable_returns_structured_state, test_invoke_available_mock_path, test_invoke_timeout_returns_structured_timeout, test_invoke_redacts_secret_like_prompt_and_runtime_error, test_permission_denied_before_invoke, test_permission_denied_before_runtime_subprocess
- Internal dependencies: adapters, importlib, pathlib, subprocess, sys.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; test-time temp files/mocks may be used.
- Configuration assumptions: external runtime/API configuration may be absent and must degrade safely.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_config_center.py`
- Lines read: 380.
- Purpose: Test coverage for config center behavior.
- Key responsibilities: classes: TestConfigCenter; callables: test_get_set, test_experiment_guide_and_log_report_defaults_when_config_missing, test_default_sections_merge_user_config_with_safe_defaults, test_save_and_reload, test_env_override, test_init_with_existing_file, test_get_llm_provider_config, test_get_llm_provider_config_has_no_implicit_openai_default
- Public interfaces: TestConfigCenter, test_get_set, test_experiment_guide_and_log_report_defaults_when_config_missing, test_default_sections_merge_user_config_with_safe_defaults, test_save_and_reload, test_env_override, test_init_with_existing_file, test_get_llm_provider_config, test_get_llm_provider_config_has_no_implicit_openai_default, test_llm_provider_helpers_persist_multiple_providers_and_last_provider, test_ensure_llm_config_preserves_list_style_providers, test_manual_file_provider_addition_and_switch_is_normalized_and_secret_safe
- Internal dependencies: core, permission, pytest, yaml.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; possible network call; test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_custom_provider.py`
- Lines read: 126.
- Purpose: Test coverage for custom provider behavior.
- Key responsibilities: classes: TestCustomOpenAIFormatProvider, TestCustomAnthropicFormatProvider, TestProviderNameInferredFormat, TestCustomProviderNoWhitelistError, TestEnvVarGeneratedForCustomProvider; callables: _write_config, test_custom_openai_format_provider, test_custom_anthropic_format_provider, test_provider_name_inferred_format, test_custom_provider_no_whitelist_error, test_env_var_generated_for_custom_provider
- Public interfaces: TestCustomOpenAIFormatProvider, TestCustomAnthropicFormatProvider, TestProviderNameInferredFormat, TestCustomProviderNoWhitelistError, TestEnvVarGeneratedForCustomProvider, test_custom_openai_format_provider, test_custom_anthropic_format_provider, test_provider_name_inferred_format, test_custom_provider_no_whitelist_error, test_env_var_generated_for_custom_provider
- Internal dependencies: core, yaml.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_event_bus.py`
- Lines read: 46.
- Purpose: Test coverage for event bus behavior.
- Key responsibilities: classes: TestEventBus; callables: test_subscribe_and_publish, test_multiple_subscribers, test_unsubscribe, test_handler_exception_isolation, good_handler, bad_handler
- Public interfaces: TestEventBus, test_subscribe_and_publish, test_multiple_subscribers, test_unsubscribe, test_handler_exception_isolation, good_handler, bad_handler
- Internal dependencies: core.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: event/plugin dispatch; test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_experience_cli.py`
- Lines read: 318.
- Purpose: Test coverage for experience cli behavior.
- Key responsibilities: callables: _prepare_workspace, test_suggested_classification_does_not_persist, test_confirm_writes_to_user_chosen_scope_overriding_suggestion, test_cli_view_list_and_get_workspace_record, test_cli_edit_workspace_record, test_cli_delete_workspace_record_requires_matching_confirmation, test_export_workspace_records_as_json_and_markdown, test_general_export_is_cross_workspace_and_rejects_project_details
- Public interfaces: test_suggested_classification_does_not_persist, test_confirm_writes_to_user_chosen_scope_overriding_suggestion, test_cli_view_list_and_get_workspace_record, test_cli_edit_workspace_record, test_cli_delete_workspace_record_requires_matching_confirmation, test_export_workspace_records_as_json_and_markdown, test_general_export_is_cross_workspace_and_rejects_project_details, test_workspace_export_excludes_other_workspace_records, test_raw_conversation_and_project_markers_rejected, test_cli_experience_commands_require_explicit_workspace, test_cli_experience_does_not_read_tui_recent_state
- Internal dependencies: Cli, core, json, pytest.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_experience_storage.py`
- Lines read: 251.
- Purpose: Test coverage for experience storage behavior.
- Key responsibilities: callables: _store, test_experience_learning_enabled_by_default_constant, test_raw_conversation_field_rejected_and_not_persisted, test_raw_conversation_stored_true_rejected, test_unconfirmed_summary_is_not_persisted, test_general_method_experience_writes_to_tempdir_layer, test_project_details_write_to_workspace_local_experience_path, test_workspace_a_cannot_list_workspace_b_local_memory
- Public interfaces: test_experience_learning_enabled_by_default_constant, test_raw_conversation_field_rejected_and_not_persisted, test_raw_conversation_stored_true_rejected, test_unconfirmed_summary_is_not_persisted, test_general_method_experience_writes_to_tempdir_layer, test_project_details_write_to_workspace_local_experience_path, test_workspace_a_cannot_list_workspace_b_local_memory, test_general_layer_can_be_listed_from_different_workspaces, test_external_method_suggestion_stays_non_persisted_until_confirmed, test_external_project_detail_suggestion_remains_workspace_local, test_project_detail_markers_rejected_from_general_layer
- Internal dependencies: core, pathlib, pytest, unittest.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_experiment_cli.py`
- Lines read: 193.
- Purpose: Test coverage for experiment cli behavior.
- Key responsibilities: callables: test_experiment_start_persists_session_and_show_returns_current_step, test_experiment_submit_advances_step_and_records_submitted_data, test_experiment_submit_with_calculate_returns_wb_calculation_output, test_experiment_submit_calculate_rejects_step_without_supported_calculation, test_log_write_list_show_create_redacted_reports, test_experiment_submit_invalid_json_exits_with_argparse_error, test_log_write_empty_message_exits_with_argparse_error, test_experiment_submit_wrong_step_exits_with_argparse_error
- Public interfaces: test_experiment_start_persists_session_and_show_returns_current_step, test_experiment_submit_advances_step_and_records_submitted_data, test_experiment_submit_with_calculate_returns_wb_calculation_output, test_experiment_submit_calculate_rejects_step_without_supported_calculation, test_log_write_list_show_create_redacted_reports, test_experiment_submit_invalid_json_exits_with_argparse_error, test_log_write_empty_message_exits_with_argparse_error, test_experiment_submit_wrong_step_exits_with_argparse_error
- Internal dependencies: Cli, json, pytest.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_experiment_guide.py`
- Lines read: 373.
- Purpose: Test coverage for experiment guide behavior.
- Key responsibilities: callables: _kernel_with_real_plugins, test_builtin_wb_protocol_is_available, test_experiment_config_loader_scans_unified_directory_and_alias_switches, test_experiment_llm_context_reflects_selected_protocol_switch, test_create_experiment_session_and_read_current_step, test_submit_user_data_records_input_output_and_advances, test_advance_requires_completed_current_step, test_experiment_completes_after_last_step
- Public interfaces: test_builtin_wb_protocol_is_available, test_experiment_config_loader_scans_unified_directory_and_alias_switches, test_experiment_llm_context_reflects_selected_protocol_switch, test_create_experiment_session_and_read_current_step, test_submit_user_data_records_input_output_and_advances, test_advance_requires_completed_current_step, test_experiment_completes_after_last_step, test_illegal_step_input_sets_error_state, test_missing_required_input_sets_error_state, test_recover_from_error_and_continue, test_session_state_round_trip_restores_progress_and_records, test_build_experiment_log_event_redacts_and_bounds_sensitive_payloads
- Internal dependencies: core, json, permission, pytest, shutil, yaml.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_experiment_log_integration.py`
- Lines read: 145.
- Purpose: Test coverage for experiment log integration behavior.
- Key responsibilities: callables: _message, _submit_payload, test_complete_wb_cli_flow_writes_structured_session_log
- Public interfaces: test_complete_wb_cli_flow_writes_structured_session_log
- Internal dependencies: Cli, json, typing.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; possible network call; test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_experiment_wb_plugin.py`
- Lines read: 117.
- Purpose: Test coverage for experiment wb plugin behavior.
- Key responsibilities: callables: _plugin, test_experiment_wb_plugin_is_discovered_with_actions, test_normalize_loading_returns_deterministic_wb_volumes, test_antibody_dilution_returns_deterministic_reagent_volumes, test_experiment_wb_invalid_input_is_structured_plugin_error, test_experiment_wb_missing_input_is_structured_plugin_error, test_experiment_wb_unknown_action_is_rejected_without_calculation_output
- Public interfaces: test_experiment_wb_plugin_is_discovered_with_actions, test_normalize_loading_returns_deterministic_wb_volumes, test_antibody_dilution_returns_deterministic_reagent_volumes, test_experiment_wb_invalid_input_is_structured_plugin_error, test_experiment_wb_missing_input_is_structured_plugin_error, test_experiment_wb_unknown_action_is_rejected_without_calculation_output
- Internal dependencies: core.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: possible network call; test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_installer_entrypoint.py`
- Lines read: 450.
- Purpose: Test coverage for installer entrypoint behavior.
- Key responsibilities: callables: _has_exact_child_name, _git_tracks_exact_path, _read_exact_lowercase_install_source, _supports_case_distinct_names, _cp1252_stdio_env, _write_minimal_import_stubs, _copy_install_entrypoint_without_installer_package, _copy_cli_entrypoint_without_installer_package; constants: REPO_ROOT
- Public interfaces: test_lowercase_install_py_entrypoint_is_present_for_case_sensitive_platforms, test_lowercase_install_help_works_when_optional_installer_package_is_absent, test_install_help_works_when_optional_installer_package_is_absent, test_init_entry_path_does_not_require_optional_exe_release_module, test_release_exe_missing_optional_module_reports_actionable_error, test_cli_help_works_when_optional_installer_package_is_absent, test_cli_init_without_release_exe_does_not_require_optional_installer_package, test_cli_release_exe_missing_optional_module_reports_actionable_error, test_install_defaults_to_interactive_question_answer_when_args_are_absent, test_python_install_py_bare_interactive_flow_creates_config_without_optional_installer_package, fake_input, fake_getpass
- Internal dependencies: installer, os, pathlib, pytest, subprocess, sys, textwrap.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; subprocess execution; test-time temp files/mocks may be used.
- Configuration assumptions: filesystem permissions and PATH/venv layout vary by host.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_installer_exe_release.py`
- Lines read: 382.
- Purpose: Test coverage for installer exe release behavior.
- Key responsibilities: callables: _llm_args, test_exe_desktop_release_uses_supplied_desktop_directory_and_dry_run, test_exe_desktop_release_copies_to_supplied_desktop_directory, test_exe_desktop_release_missing_source_has_deterministic_error, test_exe_desktop_release_skips_existing_target_by_default, test_exe_desktop_release_overwrites_existing_target_when_requested, test_exe_desktop_release_logs_copy_errors, test_exe_desktop_release_rejects_unsafe_target_filename; constants: REPO_ROOT
- Public interfaces: test_exe_desktop_release_uses_supplied_desktop_directory_and_dry_run, test_exe_desktop_release_copies_to_supplied_desktop_directory, test_exe_desktop_release_missing_source_has_deterministic_error, test_exe_desktop_release_skips_existing_target_by_default, test_exe_desktop_release_overwrites_existing_target_when_requested, test_exe_desktop_release_logs_copy_errors, test_exe_desktop_release_rejects_unsafe_target_filename, test_exe_desktop_release_normalizes_target_filename_suffix, test_release_payload_to_directory_copies_unified_layout, test_release_payload_to_directory_dry_run_does_not_create_target, test_release_payload_to_directory_rejects_incomplete_layout, test_install_help_documents_unified_install_and_desktop_release
- Internal dependencies: importlib, json, logging, pathlib, pytest, shutil.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; test-time temp files/mocks may be used.
- Configuration assumptions: filesystem permissions and PATH/venv layout vary by host.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_integration.py`
- Lines read: 1024.
- Purpose: Test coverage for integration behavior.
- Key responsibilities: classes: MockAgent, TestIntegration, FakeRegistry, FakeCheckpointManager, FakeKernel; callables: _llm_kwargs, __init__, execute, test_install_init_creates_canonical_default_policy_without_overwrite, test_install_init_is_core_only_and_does_not_detect_platforms, test_default_policy_falls_back_to_packaged_resource_when_source_tree_missing, test_cli_init_and_install_init_create_same_default_policy, test_install_init_writes_openai_llm_config_with_secret_redaction
- Public interfaces: MockAgent, TestIntegration, __init__, execute, test_install_init_creates_canonical_default_policy_without_overwrite, test_install_init_is_core_only_and_does_not_detect_platforms, test_default_policy_falls_back_to_packaged_resource_when_source_tree_missing, test_cli_init_and_install_init_create_same_default_policy, test_install_init_writes_openai_llm_config_with_secret_redaction, test_install_init_requires_complete_llm_config, test_first_install_requires_complete_llm_setup_and_does_not_write_partial_config, test_provider_added_by_manual_config_file_is_used_without_home_or_network
- Internal dependencies: Cli, agents, core, installer, json, pathlib, permission, plugins, pytest, shutil, typing, yaml.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: event/plugin dispatch; filesystem I/O or mutation; possible network call; subprocess execution; test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_kernel.py`
- Lines read: 215.
- Purpose: Test coverage for kernel behavior.
- Key responsibilities: classes: TestKernel, ExplodingClient, CapturingClient; callables: _create_kernel, test_init, test_config, test_plugin_registry, test_event_bus, test_kernel_permission_engine_is_runtime_gate_not_prompt_generator, test_llm_chat_provider_exception_returns_structured_error_and_checkpoint, test_llm_chat_injects_supermedicine_system_prompt_before_user_message
- Public interfaces: TestKernel, test_init, test_config, test_plugin_registry, test_event_bus, test_kernel_permission_engine_is_runtime_gate_not_prompt_generator, test_llm_chat_provider_exception_returns_structured_error_and_checkpoint, test_llm_chat_injects_supermedicine_system_prompt_before_user_message, test_llm_chat_system_prompt_preserves_permission_generator_boundary, test_llm_chat_context_injects_selected_experiment_permission_and_tools, ExplodingClient, CapturingClient
- Internal dependencies: core, permission, shutil, yaml.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; possible network call; test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_llm_client.py`
- Lines read: 420.
- Purpose: Test coverage for llm client behavior.
- Key responsibilities: classes: TestOpenRouterClient, TestLLMFactory, TestTrackedLLMClientDiagnostics, TestUnifiedProviderConfig, FakeClient, FakeTracker; callables: test_init_defaults, test_init_custom_model, test_complete_without_api_key, test_chat_mock_response, test_complete_mock_response, test_create_openrouter, test_create_openai, test_create_anthropic
- Public interfaces: TestOpenRouterClient, TestLLMFactory, TestTrackedLLMClientDiagnostics, TestUnifiedProviderConfig, test_init_defaults, test_init_custom_model, test_complete_without_api_key, test_chat_mock_response, test_complete_mock_response, test_create_openrouter, test_create_openai, test_create_anthropic
- Internal dependencies: core, json, unittest, yaml.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; test-time temp files/mocks may be used.
- Configuration assumptions: external runtime/API configuration may be absent and must degrade safely.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_llm_manager.py`
- Lines read: 262.
- Purpose: Test coverage for llm manager behavior.
- Key responsibilities: callables: _write_config, test_manager_adds_lists_and_redacts_providers, test_cli_add_switch_and_list_are_secret_safe_and_persist_current, test_switch_provider_persists_current_and_last_provider, test_startup_restores_last_provider_before_install_default, test_startup_uses_install_default_when_no_last_provider, test_kernel_exposes_manager_and_restores_last_provider, test_incomplete_provider_returns_structured_secret_safe_error
- Public interfaces: test_manager_adds_lists_and_redacts_providers, test_cli_add_switch_and_list_are_secret_safe_and_persist_current, test_switch_provider_persists_current_and_last_provider, test_startup_restores_last_provider_before_install_default, test_startup_uses_install_default_when_no_last_provider, test_kernel_exposes_manager_and_restores_last_provider, test_incomplete_provider_returns_structured_secret_safe_error, test_list_style_providers_survive_startup_and_can_switch_and_create_client, test_create_client_uses_restored_last_provider_not_install_default, test_create_client_after_switch_uses_new_current_provider, test_create_client_without_llm_config_returns_actionable_secret_safe_error
- Internal dependencies: Cli, core, permission, shutil, yaml.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; test-time temp files/mocks may be used.
- Configuration assumptions: external runtime/API configuration may be absent and must degrade safely.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_local_rag.py`
- Lines read: 406.
- Purpose: Test coverage for local rag behavior.
- Key responsibilities: classes: TestLocalRAGProvider, TestPubmedRAGProvider, TestMockExternalVectorStoreProvider, OversizedResponse; callables: _pubmed_engine_for, test_add_and_query, test_empty_query, test_context_store_retrieve, test_context_key_rejects_path_traversal, test_context_key_retrieve_rejects_path_traversal, test_context_not_found, test_query_empty_result_on_failure
- Public interfaces: TestLocalRAGProvider, TestPubmedRAGProvider, TestMockExternalVectorStoreProvider, test_add_and_query, test_empty_query, test_context_store_retrieve, test_context_key_rejects_path_traversal, test_context_key_retrieve_rejects_path_traversal, test_context_not_found, test_query_empty_result_on_failure, test_query_with_mock_results, test_context_store_retrieve
- Internal dependencies: json, pathlib, permission, plugins, pytest, tempfile, unittest, yaml.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; test-time temp files/mocks may be used.
- Configuration assumptions: local knowledge files stay inside permitted workspace paths.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_log_report.py`
- Lines read: 431.
- Purpose: Test coverage for log report behavior.
- Key responsibilities: callables: test_log_directory_is_created_and_isolated_log_is_redacted, test_session_writes_append_to_one_redacted_log, test_log_report_redacts_request_headers_body_url_query_and_private_key, test_log_report_keeps_business_fields_while_redacting_error_payload, test_list_show_and_summary_return_redacted_records, test_show_rejects_unsafe_file_names, test_write_rejects_empty_messages, test_append_rejects_empty_messages
- Public interfaces: test_log_directory_is_created_and_isolated_log_is_redacted, test_session_writes_append_to_one_redacted_log, test_log_report_redacts_request_headers_body_url_query_and_private_key, test_log_report_keeps_business_fields_while_redacting_error_payload, test_list_show_and_summary_return_redacted_records, test_show_rejects_unsafe_file_names, test_write_rejects_empty_messages, test_append_rejects_empty_messages, test_format_log_message_adds_representative_labels_without_duplicates, test_list_and_summary_display_severity_labels_but_raw_records_stay_unprefixed, test_structured_json_record_message_remains_json_decodable, test_session_ids_are_isolated_and_path_safe
- Internal dependencies: core, io, json, logging, pytest, sys.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_medical_citation.py`
- Lines read: 201.
- Purpose: Test coverage for medical citation behavior.
- Key responsibilities: classes: TestAMAFormatter, TestVancouverFormatter, TestCitationAccuracy, TestMedicalCitationPluginEntry; callables: test_journal_article, test_book, test_journal_article, test_formatter_models_are_shared, test_missing_source_id_is_error_and_does_not_generate_citation, test_unknown_source_id_is_error, test_low_confidence_source_is_warning, test_citation_source_provenance_defaults_are_stable
- Public interfaces: TestAMAFormatter, TestVancouverFormatter, TestCitationAccuracy, TestMedicalCitationPluginEntry, test_journal_article, test_book, test_journal_article, test_formatter_models_are_shared, test_missing_source_id_is_error_and_does_not_generate_citation, test_unknown_source_id_is_error, test_low_confidence_source_is_warning, test_citation_source_provenance_defaults_are_stable
- Internal dependencies: plugins.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_medical_writing.py`
- Lines read: 219.
- Purpose: Test coverage for medical writing behavior.
- Key responsibilities: classes: TestConsortChecklist, TestStrobeChecklist, TestMedicalWritingPluginSafetyMetadata; callables: test_checklist_loaded, test_check_with_consort_text, test_check_empty_text, test_medical_claims_are_classified_and_review_message_present, test_missing_citation_for_medical_fact_returns_error_without_fabrication, test_invalid_source_returns_error, test_low_confidence_source_returns_observable_warning, test_claim_ledger_provenance_and_audit_summary_are_reported
- Public interfaces: TestConsortChecklist, TestStrobeChecklist, TestMedicalWritingPluginSafetyMetadata, test_checklist_loaded, test_check_with_consort_text, test_check_empty_text, test_medical_claims_are_classified_and_review_message_present, test_missing_citation_for_medical_fact_returns_error_without_fabrication, test_invalid_source_returns_error, test_low_confidence_source_returns_observable_warning, test_claim_ledger_provenance_and_audit_summary_are_reported, test_claim_audit_summary_blocks_missing_required_source
- Internal dependencies: plugins.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_monitor.py`
- Lines read: 202.
- Purpose: Test coverage for monitor behavior.
- Key responsibilities: classes: TestAgentMonitor, TestAgentPerformanceMonitor; callables: test_init, test_get_permission_audit_empty, test_get_permission_audit_with_entries, test_get_permission_audit_skips_malformed_jsonl_with_warnings, test_get_denied_actions, test_detect_anomalies_high_frequency, test_record_and_stats, test_get_stats_skips_malformed_and_invalid_jsonl_with_warnings
- Public interfaces: TestAgentMonitor, TestAgentPerformanceMonitor, test_init, test_get_permission_audit_empty, test_get_permission_audit_with_entries, test_get_permission_audit_skips_malformed_jsonl_with_warnings, test_get_denied_actions, test_detect_anomalies_high_frequency, test_record_and_stats, test_get_stats_skips_malformed_and_invalid_jsonl_with_warnings, test_detect_failure_patterns
- Internal dependencies: json, pathlib, plugins.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_opencode_adapter.py`
- Lines read: 728.
- Purpose: Test coverage for opencode adapter behavior.
- Key responsibilities: classes: TestAdapterImport, TestToolCall, TestSkillLoad, TestSubagentDispatch, TestPluginJson, TestSkillsExist; callables: adapter, _adapter_with_policy, permissive_adapter, test_adapter_import, test_explicit_optional_import_degrades_without_orchestrator, test_platform_name, test_capabilities_report_optional_degraded_boundary, test_capabilities_do_not_expose_environment_api_keys; constants: FORBIDDEN_PLATFORM_AGENT_NAMES
- Public interfaces: adapter, permissive_adapter, TestAdapterImport, TestToolCall, TestSkillLoad, TestSubagentDispatch, TestPluginJson, TestSkillsExist, TestAgentsExist, DummyEchoAgent, TestOpenCodeRealDispatch, test_adapter_import
- Internal dependencies: adapters, agents, importlib, json, pathlib, permission, pytest, sys, tempfile, yaml.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; test-time temp files/mocks may be used.
- Configuration assumptions: external runtime/API configuration may be absent and must degrade safely.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_operation_guard.py`
- Lines read: 98.
- Purpose: Test coverage for operation guard behavior.
- Key responsibilities: classes: RecordingPermissionEngine; callables: test_permission_engine_called_before_authorizing_dangerous_operation, test_allowed_decision_writes_guard_audit_event, test_denied_decision_writes_guard_audit_event_and_raises, __init__, check
- Public interfaces: RecordingPermissionEngine, test_permission_engine_called_before_authorizing_dangerous_operation, test_allowed_decision_writes_guard_audit_event, test_denied_decision_writes_guard_audit_event_and_raises, __init__, check
- Internal dependencies: core, json, permission, pytest, typing.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_orchestrator.py`
- Lines read: 62.
- Purpose: Test coverage for orchestrator behavior.
- Key responsibilities: classes: DummyAgent, FailingAgent, TestOrchestrator; callables: __init__, execute, execute, test_register_and_list, test_dispatch, test_dispatch_unknown_raises, test_dispatch_records_stage_checkpoints, test_failure_checkpoint_is_not_recoverable
- Public interfaces: DummyAgent, FailingAgent, TestOrchestrator, __init__, execute, execute, test_register_and_list, test_dispatch, test_dispatch_unknown_raises, test_dispatch_records_stage_checkpoints, test_failure_checkpoint_is_not_recoverable
- Internal dependencies: agents, pytest, typing.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: event/plugin dispatch; test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_paper_cli.py`
- Lines read: 354.
- Purpose: Test coverage for paper cli behavior.
- Key responsibilities: classes: CountingProvider, FakeRegistry, FakeCheckpointManager, FakeKernel; callables: _copy_default_policy, _write_delta_policy, _audit_entries, test_paper_import_cli_requires_explicit_workspace, test_paper_import_cli_copies_file_and_writes_metadata, test_paper_list_show_edit_use_explicit_workspace, test_enrichment_does_not_call_provider_without_confirm_and_audits_skip, test_enrichment_permission_deny_prevents_provider_call_and_audits_denial; constants: REPO_ROOT
- Public interfaces: CountingProvider, test_paper_import_cli_requires_explicit_workspace, test_paper_import_cli_copies_file_and_writes_metadata, test_paper_list_show_edit_use_explicit_workspace, test_enrichment_does_not_call_provider_without_confirm_and_audits_skip, test_enrichment_permission_deny_prevents_provider_call_and_audits_denial, test_cli_enrichment_allow_uses_mocked_provider_and_updates_metadata, test_denied_enrichment_does_not_corrupt_import, test_old_cli_commands_and_run_flags_still_present, __init__, fetch, FakeRegistry
- Internal dependencies: Cli, core, hashlib, json, pathlib, permission, pytest, yaml.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_paper_import_core.py`
- Lines read: 333.
- Purpose: Test coverage for paper import core behavior.
- Key responsibilities: callables: _source_bytes, _paper_storage_state, test_import_supports_expected_extensions_and_preserves_source, test_import_writes_metadata_json_and_import_log_jsonl, test_import_duplicate_sha256_reuses_existing_original_metadata_and_logs_attempt, test_import_duplicate_doi_reuses_existing_metadata_without_copying_new_original, test_import_duplicate_pmid_reuses_existing_metadata_without_copying_new_original, test_import_rejects_unsupported_extension_without_partial_writes; constants: SUPPORTED_EXTENSIONS
- Public interfaces: test_import_supports_expected_extensions_and_preserves_source, test_import_writes_metadata_json_and_import_log_jsonl, test_import_duplicate_sha256_reuses_existing_original_metadata_and_logs_attempt, test_import_duplicate_doi_reuses_existing_metadata_without_copying_new_original, test_import_duplicate_pmid_reuses_existing_metadata_without_copying_new_original, test_import_rejects_unsupported_extension_without_partial_writes, test_import_rejects_missing_source_without_partial_writes, test_import_propagates_missing_workspace_without_creating_workspace_or_partial_writes
- Internal dependencies: core, hashlib, json, pytest.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_path_safety.py`
- Lines read: 125.
- Purpose: Test coverage for path safety behavior.
- Key responsibilities: callables: test_resolve_project_root_returns_canonical_path, test_path_inside_project_root_is_accepted, test_parent_traversal_outside_project_root_is_rejected, test_absolute_path_outside_project_root_is_rejected, test_symlink_target_outside_project_root_is_rejected, test_protected_directories_are_rejected_for_destructive_operations, test_project_root_is_rejected_for_destructive_operations, test_control_character_path_value_is_rejected_before_resolution
- Public interfaces: test_resolve_project_root_returns_canonical_path, test_path_inside_project_root_is_accepted, test_parent_traversal_outside_project_root_is_rejected, test_absolute_path_outside_project_root_is_rejected, test_symlink_target_outside_project_root_is_rejected, test_protected_directories_are_rejected_for_destructive_operations, test_project_root_is_rejected_for_destructive_operations, test_control_character_path_value_is_rejected_before_resolution, test_sandbox_write_path_allows_generated_markdown_and_python, test_sandbox_write_path_rejects_traversal_scope_type_and_overwrite, test_generated_content_with_secret_like_values_is_rejected
- Internal dependencies: core, os, pytest.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_permission_engine.py`
- Lines read: 365.
- Purpose: Test coverage for permission engine behavior.
- Key responsibilities: classes: TestPermissionEngine, TestPermissionEngineWithPolicies; callables: _make_engine, test_check_allowed, test_check_denied, test_check_unknown_agent, test_audit_log_written, test_load_default_policy, test_default_policies_exist, test_hard_limits_enforced; constants: PROJECT_ROOT
- Public interfaces: TestPermissionEngine, TestPermissionEngineWithPolicies, test_check_allowed, test_check_denied, test_check_unknown_agent, test_audit_log_written, test_load_default_policy, test_default_policies_exist, test_hard_limits_enforced, test_hard_limits_no_context, test_external_api_hard_limit_denies_before_allow_rule, test_default_policy_allows_declared_experiment_wb_local_actions
- Internal dependencies: pathlib, permission, yaml.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_permission_modes.py`
- Lines read: 99.
- Purpose: Test coverage for permission modes behavior.
- Key responsibilities: callables: test_cli_permission_mode_requires_confirmation_and_persists_runtime_policy, test_cli_permission_authorize_and_revoke_external_directory_updates_policy, test_sandbox_mode_limits_writes_to_generated_safe_file_types, test_sandbox_mode_rejects_external_paths_even_when_alias_used
- Public interfaces: test_cli_permission_mode_requires_confirmation_and_persists_runtime_policy, test_cli_permission_authorize_and_revoke_external_directory_updates_policy, test_sandbox_mode_limits_writes_to_generated_safe_file_types, test_sandbox_mode_rejects_external_paths_even_when_alias_used
- Internal dependencies: Cli, core, permission, pytest.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_plugin_registry.py`
- Lines read: 374.
- Purpose: Test coverage for plugin registry behavior.
- Key responsibilities: classes: TestAdapterDiscoveryRegistry, TestPluginRegistry; callables: test_top_level_adapters_import_exposes_static_metadata_without_platform_imports, test_adapter_registry_distinguishes_core_and_optional_boundaries, _create_plugin, test_discover, test_load_meta, test_get_plugin, test_unknown_returns_none, test_bad_manifest_is_skipped_without_blocking_other_plugins
- Public interfaces: TestAdapterDiscoveryRegistry, TestPluginRegistry, test_top_level_adapters_import_exposes_static_metadata_without_platform_imports, test_adapter_registry_distinguishes_core_and_optional_boundaries, test_discover, test_load_meta, test_get_plugin, test_unknown_returns_none, test_bad_manifest_is_skipped_without_blocking_other_plugins, test_python_entry_execute_success, test_direct_plugin_execution_requires_permission_proof_outside_dev_test, test_python_entry_missing_execute_returns_plugin_error
- Internal dependencies: adapters, core, plugins, sys, yaml.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; possible network call; test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_policy.py`
- Lines read: 120.
- Purpose: Test coverage for policy behavior.
- Key responsibilities: classes: TestPermissionPolicy; callables: test_path_scope_matches_resolved_same_file_representation, test_resolved_path_scope_matches_raw_same_file_representation, test_path_scope_does_not_match_different_normalized_file, test_load_policy_from_dict, test_check_allowed_action, test_check_denied_action, test_check_undeclared_action_denied, test_denied_overrides_allowed
- Public interfaces: test_path_scope_matches_resolved_same_file_representation, test_resolved_path_scope_matches_raw_same_file_representation, test_path_scope_does_not_match_different_normalized_file, TestPermissionPolicy, test_load_policy_from_dict, test_check_allowed_action, test_check_denied_action, test_check_undeclared_action_denied, test_denied_overrides_allowed
- Internal dependencies: permission.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_prisma.py`
- Lines read: 47.
- Purpose: Test coverage for prisma behavior.
- Key responsibilities: classes: TestPRISMAChecklist; callables: test_checklist_loaded, test_check_with_good_text, test_check_empty_text
- Public interfaces: TestPRISMAChecklist, test_checklist_loaded, test_check_with_good_text, test_check_empty_text
- Internal dependencies: plugins.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_prompt_generator.py`
- Lines read: 58.
- Purpose: Test coverage for prompt generator behavior.
- Key responsibilities: classes: TestPromptGenerator; callables: test_generate_prefix, test_generate_rejection_templates, test_prompt_generator_is_context_generation_only, test_generate_prefix_injects_self_evolution_guidance
- Public interfaces: TestPromptGenerator, test_generate_prefix, test_generate_rejection_templates, test_prompt_generator_is_context_generation_only, test_generate_prefix_injects_self_evolution_guidance
- Internal dependencies: permission.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_python_stats.py`
- Lines read: 110.
- Purpose: Test coverage for python stats behavior.
- Key responsibilities: classes: TestDescriptive, TestTtest, TestAnova, TestRegression, TestPythonStatsContract; callables: assert_prototype_contract, test_basic, test_empty, test_different_groups, test_same_groups, test_three_groups, test_linear, test_descriptive_execute_contract_is_deterministic_prototype
- Public interfaces: assert_prototype_contract, TestDescriptive, TestTtest, TestAnova, TestRegression, TestPythonStatsContract, test_basic, test_empty, test_different_groups, test_same_groups, test_three_groups, test_linear
- Internal dependencies: plugins.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_r_survival.py`
- Lines read: 206.
- Purpose: Test coverage for r survival behavior.
- Key responsibilities: classes: TestKaplanMeier, TestLogRank, TestCoxPH, TestRSurvivalContract; callables: assert_prototype_contract, test_basic, test_all_events, test_all_censored, test_median_survival, test_different_groups, test_same_groups, test_basic; constants: TOY_TIMES, TOY_EVENTS
- Public interfaces: assert_prototype_contract, TestKaplanMeier, TestLogRank, TestCoxPH, TestRSurvivalContract, test_basic, test_all_events, test_all_censored, test_median_survival, test_different_groups, test_same_groups, test_basic
- Internal dependencies: plugins.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: test-time temp files/mocks may be used.
- Configuration assumptions: requires local R/rpy2/survival availability when executed.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_redaction.py`
- Lines read: 182.
- Purpose: Test coverage for redaction behavior.
- Key responsibilities: callables: test_redact_sensitive_covers_headers_cloud_keys_private_keys_and_query_values, test_redact_sensitive_redacts_json_strings_without_persisting_original_values, test_redact_sensitive_preserves_pretty_json_layout_while_redacting_values, test_redact_sensitive_redacts_plain_auth_keys_in_structured_and_json_text, test_cli_redacting_formatter_redacts_json_and_error_report_messages, test_cli_redacting_formatter_redacts_exception_log_arguments_and_headers, test_cli_formatter_and_tui_kernel_format_redact_plain_auth_fields
- Public interfaces: test_redact_sensitive_covers_headers_cloud_keys_private_keys_and_query_values, test_redact_sensitive_redacts_json_strings_without_persisting_original_values, test_redact_sensitive_preserves_pretty_json_layout_while_redacting_values, test_redact_sensitive_redacts_plain_auth_keys_in_structured_and_json_text, test_cli_redacting_formatter_redacts_json_and_error_report_messages, test_cli_redacting_formatter_redacts_exception_log_arguments_and_headers, test_cli_formatter_and_tui_kernel_format_redact_plain_auth_fields
- Internal dependencies: Cli, core, json, logging.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_regression_baseline.py`
- Lines read: 494.
- Purpose: Test coverage for regression baseline behavior.
- Key responsibilities: classes: FakeResponse, FakeInput, FakeEvent, FakeChat, EscapeKey, DigitKey; callables: test_llm_client_must_really_call_configured_provider_or_return_explicit_failure, test_llm_client_missing_configuration_is_explicit_failure_not_success, test_tui_visible_logging_does_not_show_llm_client_creation_noise, test_tui_input_submission_clears_input_without_raw_terminal_echo_or_screen_clear, test_tui_interactive_launch_does_not_print_status_before_alternate_screen, test_tui_prompt_digits_are_plain_input_and_do_not_switch_views, test_tui_prompt_filters_terminal_control_sequences_but_preserves_pasted_digits, test_tui_prompt_swallow_digits_while_terminal_sequence_is_incomplete
- Public interfaces: test_llm_client_must_really_call_configured_provider_or_return_explicit_failure, test_llm_client_missing_configuration_is_explicit_failure_not_success, test_tui_visible_logging_does_not_show_llm_client_creation_noise, test_tui_input_submission_clears_input_without_raw_terminal_echo_or_screen_clear, test_tui_interactive_launch_does_not_print_status_before_alternate_screen, test_tui_prompt_digits_are_plain_input_and_do_not_switch_views, test_tui_prompt_filters_terminal_control_sequences_but_preserves_pasted_digits, test_tui_prompt_swallow_digits_while_terminal_sequence_is_incomplete, test_tui_prompt_key_filter_uses_textual_character_attribute_shape, test_tui_prompt_backspace_keeps_text_editing_behavior, test_tui_digits_do_not_open_or_navigate_view_menu, test_tui_prompt_backspace_control_bytes_are_not_classified_as_shortcuts
- Internal dependencies: Uninstall, asyncio, core, installer, json, pathlib, pytest, textual, typing, yaml.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; subprocess execution; test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_release_smoke.py`
- Lines read: 422.
- Purpose: Test coverage for release smoke behavior.
- Key responsibilities: callables: _extract_bash_pyinstaller_command, _token_value, _looks_absolute_or_resolved_for_ci_shell, _relative_source_is_staged_under_specpath, _cp1252_stdio_env, _has_exact_child_name, _supports_case_distinct_names, _copy_release_tree; constants: REPO_ROOT, RELEASE_DIR_NAME, CRITICAL_RELEASE_PATHS, CRITICAL_IMPORTS, INSTALLER_EXE_RELEASE_PATHS, INSTALLER_EXE_NAME
- Public interfaces: test_extracted_release_directory_installer_entrypoint_smoke, test_ci_release_artifacts_include_installer_usable_exe_or_dist_path, test_ci_release_artifacts_include_standalone_installer_exe_and_shared_payload, test_ci_standalone_installer_pyinstaller_payload_path_matches_specpath_contract, test_ci_packaging_smoke_installs_runtime_dependencies_before_installer_entrypoints, test_release_docs_describe_ci_artifact_layout_and_install_py_roles
- Internal dependencies: os, pathlib, re, shlex, shutil, subprocess, sys.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; subprocess execution; test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_repo_hygiene.py`
- Lines read: 849.
- Purpose: Test coverage for repo hygiene behavior.
- Key responsibilities: callables: _read_pyproject, _tracked_files, _active_gitignore_patterns, _normalized_parts, _top_level_entry_from_yaml, _setuptools_py_modules, _tracked_python_files, test_python_sources_do_not_import_legacy_uppercase_install_module_outside_compatibility_tests; constants: REPO_ROOT, FORBIDDEN_PLATFORM_AGENT_NAMES, COMMIT_ELIGIBLE_MAINTAINER_DOC_EXAMPLES, LOCAL_ONLY_ENGINEERING_ARTIFACT_PATTERNS
- Public interfaces: test_python_sources_do_not_import_legacy_uppercase_install_module_outside_compatibility_tests, test_tracked_files_do_not_include_forbidden_or_generated_artifacts, test_supermedicine_runtime_bootstrap_copies_are_local_only, test_gitignore_excludes_runtime_and_external_platform_config_artifacts, test_gitignore_allows_curated_maintainer_repository_docs, test_gitignore_keeps_temporary_engineering_artifacts_local_only, test_install_manifest_keeps_external_platform_config_out_of_core_product_paths, test_install_manifest_platform_entries_point_to_existing_adapter_files, test_install_manifest_declares_single_user_facing_platform_agent, test_release_label_and_package_version_stay_in_sync, test_release_zip_archive_name_uses_display_format_without_source_suffix, test_release_zip_layout_includes_installer_package_for_install_entrypoint
- Internal dependencies: adapters, ast, importlib, json, pathlib, re, subprocess, tomllib.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; possible network call; subprocess execution; test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_self_evolution.py`
- Lines read: 223.
- Purpose: Test coverage for self-evolution service behavior.
- Key responsibilities: classes: RecordingPermissionEngine; callables: __init__, check, _service, test_preview_markdown_returns_plan_without_writing, test_confirmed_markdown_writes_allowed_file_and_bootstraps_policy, test_python_tool_preview_and_confirmed_creation_use_safe_output_validation, test_experience_source_is_included_in_generated_artifact, test_illegal_paths_and_extensions_are_rejected, test_overwrite_conflict_is_rejected_without_overwrite_flag, test_insufficient_permission_returns_clear_failure, test_full_access_confirmed_write_requires_risk_acknowledgement, test_sensitive_content_is_rejected_before_preview_artifact_is_returned, test_empty_input_and_unknown_artifact_type_fail_clearly.
- Public interfaces: RecordingPermissionEngine, _service, test_preview_markdown_returns_plan_without_writing, test_confirmed_markdown_writes_allowed_file_and_bootstraps_policy, test_python_tool_preview_and_confirmed_creation_use_safe_output_validation, test_experience_source_is_included_in_generated_artifact, test_illegal_paths_and_extensions_are_rejected, test_overwrite_conflict_is_rejected_without_overwrite_flag, test_insufficient_permission_returns_clear_failure, test_full_access_confirmed_write_requires_risk_acknowledgement, test_sensitive_content_is_rejected_before_preview_artifact_is_returned, test_empty_input_and_unknown_artifact_type_fail_clearly.
- Internal dependencies: core.experience, core.self_evolution, core.workspace, pathlib, permission.policy, typing.
- Data flow: pytest constructs temporary project/workspace state -> invokes SelfEvolutionService preview/confirm paths with sample intents, artifact types, paths, experience records, and permission-engine fakes -> asserts returned dictionaries, generated content, policy bootstrap, file existence/non-existence, and clear failure errors.
- Side effects: test-time temp directories/files are created and mutated; confirmed service paths may create `.supermedicine` policy/audit/log artifacts and generated Markdown/Python/README files under tmp_path; permission-engine fake records authorization calls.
- Configuration assumptions: service accepts tmp_path as project root; sandbox generated roots and allowed extensions match service constants; temporary filesystem supports creation/removal and path resolution; sensitive-content patterns catch representative token strings.
- Maintenance risks: tests can become stale if service result schema, path safety wording, generated content, policy bootstrap location, or full-access confirmation semantics change; fake permission engine only covers check-call behavior, not full real-policy integration.

### `tests/test_self_evolution_cli.py`
- Lines read: 206.
- Purpose: Test coverage for self-evolution CLI behavior.
- Key responsibilities: callables: _cli_json, test_self_evolve_preview_does_not_write_and_reports_files, test_self_evolve_confirmed_write_creates_allowed_file_and_reports_audit, test_self_evolve_sandbox_rejects_out_of_scope_path, test_self_evolve_full_access_notice_is_visible_and_requires_confirmation_flags, test_self_evolve_full_access_confirmation_flags_are_reported, test_self_evolve_full_access_requires_risk_acknowledgement, test_self_evolve_help_does_not_regress_existing_commands.
- Public interfaces: _cli_json, test_self_evolve_preview_does_not_write_and_reports_files, test_self_evolve_confirmed_write_creates_allowed_file_and_reports_audit, test_self_evolve_sandbox_rejects_out_of_scope_path, test_self_evolve_full_access_notice_is_visible_and_requires_confirmation_flags, test_self_evolve_full_access_confirmation_flags_are_reported, test_self_evolve_full_access_requires_risk_acknowledgement, test_self_evolve_help_does_not_regress_existing_commands.
- Internal dependencies: Cli, json, pathlib, pytest.
- Data flow: pytest changes cwd to tmp_path -> invokes `Cli.main` with `self-evolve` and help argument lists -> captures JSON from stdout/stderr -> asserts preview/confirmation flags, target paths, file operation summaries, audit-log metadata, full-access notice fields, next-step guidance, and help command coverage.
- Side effects: test-time cwd changes and temp filesystem writes; confirmed CLI calls can create generated files and `.supermedicine/policies/audit.jsonl`; help checks raise and catch SystemExit.
- Configuration assumptions: CLI emits parseable JSON for self-evolve paths; sandbox mode is the default permission mode; full-access writes require both `--confirm-full-access` and `--acknowledge-risk`; command help includes existing top-level/run options.
- Maintenance risks: CLI output schema/copy, stream selection, help formatting, or flag names may change; assertions couple to path resolution and audit-log location; monkeypatched cwd requires CLI/project-root behavior to remain cwd-based.

### `tests/test_session_manager.py`
- Lines read: 107.
- Purpose: Test coverage for session manager behavior.
- Key responsibilities: classes: TestSession, TestSessionManager, TestSessionTTL; callables: test_session_set_get, test_session_default_value, test_create, test_get_existing, test_get_nonexistent, test_multiple_sessions_isolation, test_ttl_cleanup_expired, test_ttl_list_active
- Public interfaces: TestSession, TestSessionManager, TestSessionTTL, test_session_set_get, test_session_default_value, test_create, test_get_existing, test_get_nonexistent, test_multiple_sessions_isolation, test_ttl_cleanup_expired, test_ttl_list_active, test_no_ttl_default
- Internal dependencies: core, datetime.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: possible network call; test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_standalone_adapter.py`
- Lines read: 276.
- Purpose: Test coverage for standalone adapter behavior.
- Key responsibilities: classes: TestStandaloneAdapter; callables: _adapter_with_policy, permissive_adapter, test_is_base_adapter, test_platform_name, test_registration_marks_standalone_as_core_default, test_explicit_standalone_import_does_not_load_optional_platform_adapters, test_tool_call_bash, test_tool_call_read_write
- Public interfaces: permissive_adapter, TestStandaloneAdapter, test_is_base_adapter, test_platform_name, test_registration_marks_standalone_as_core_default, test_explicit_standalone_import_does_not_load_optional_platform_adapters, test_tool_call_bash, test_tool_call_read_write, test_write_and_edit_fail_closed_when_permission_engine_unavailable, test_tool_call_glob, test_tool_call_unsupported, test_denied_edit_returns_before_file_mutation
- Internal dependencies: adapters, builtins, importlib, pathlib, permission, pytest, sys, tempfile, yaml.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_stard.py`
- Lines read: 27.
- Purpose: Test coverage for stard behavior.
- Key responsibilities: classes: TestSTARDChecklist; callables: test_checklist_loaded, test_check_with_good_text, test_check_empty_text
- Public interfaces: TestSTARDChecklist, test_checklist_loaded, test_check_with_good_text, test_check_empty_text
- Internal dependencies: plugins.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_state_machine.py`
- Lines read: 81.
- Purpose: Test coverage for state machine behavior.
- Key responsibilities: classes: TestStateMachine; callables: test_initial_state, test_transition_planning_to_dispatch, test_transition_dispatch_to_running, test_transition_running_to_verifying, test_transition_verifying_to_completed, test_transition_verifying_to_retry, test_invalid_transition_raises, test_retry_increments_counter
- Public interfaces: TestStateMachine, test_initial_state, test_transition_planning_to_dispatch, test_transition_dispatch_to_running, test_transition_running_to_verifying, test_transition_verifying_to_completed, test_transition_verifying_to_retry, test_invalid_transition_raises, test_retry_increments_counter, test_max_retries_exceeded, test_history_has_explicit_status_and_timestamp, test_snapshot_reports_recoverability
- Internal dependencies: agents, pytest.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_token_tracker.py`
- Lines read: 68.
- Purpose: Test coverage for token tracker behavior.
- Key responsibilities: classes: TestTokenTracker; callables: test_token_tracker_records_usage, test_token_tracker_persists_across_instances, test_token_tracker_groups_by_provider, test_token_tracker_empty_state, test_token_tracker_summary_by_model
- Public interfaces: TestTokenTracker, test_token_tracker_records_usage, test_token_tracker_persists_across_instances, test_token_tracker_groups_by_provider, test_token_tracker_empty_state, test_token_tracker_summary_by_model
- Internal dependencies: core, pathlib.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_tui_chat_view.py`
- Lines read: 199.
- Purpose: Test coverage for tui chat view behavior.
- Key responsibilities: classes: CapturingRichLog, CapturingChatView, FakeChat, FakeKernel; callables: test_chat_messages_are_escaped_redacted_and_stably_prefixed, test_chat_status_message_uses_status_prefix_and_escaping, test_chat_empty_success_and_error_copy_stays_localized_and_secret_safe, test_kernel_result_format_handles_success_error_empty_and_non_dict_outputs, test_kernel_result_format_redacts_secret_strings_and_keeps_stable_chinese_headings, test_run_kernel_task_emits_running_completion_and_formatted_messages, test_chat_streaming_methods_keep_assistant_turn_and_append_safe_deltas, test_safe_display_text_escapes_markup_and_redacts_secrets
- Public interfaces: CapturingRichLog, CapturingChatView, test_chat_messages_are_escaped_redacted_and_stably_prefixed, test_chat_status_message_uses_status_prefix_and_escaping, test_chat_empty_success_and_error_copy_stays_localized_and_secret_safe, test_kernel_result_format_handles_success_error_empty_and_non_dict_outputs, test_kernel_result_format_redacts_secret_strings_and_keeps_stable_chinese_headings, test_run_kernel_task_emits_running_completion_and_formatted_messages, test_chat_streaming_methods_keep_assistant_turn_and_append_safe_deltas, test_safe_display_text_escapes_markup_and_redacts_secrets, __init__, write
- Internal dependencies: asyncio, core.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: subprocess execution; test-time temp files/mocks may be used.
- Configuration assumptions: Textual optional UI dependency available for TUI paths.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_tui_dashboard.py`
- Lines read: 162.
- Purpose: Test coverage for tui dashboard behavior.
- Key responsibilities: callables: test_dashboard_context_for_uninitialized_project_is_chinese_and_stable, test_dashboard_context_for_initialized_project_with_workspace_and_ready_llm_redacts_secret, test_dashboard_context_reports_initialized_project_without_workspace_or_provider, test_dashboard_context_collects_counts_recent_hint_and_ready_advice_without_network, test_dashboard_context_reports_incomplete_llm_without_api_key_leak
- Public interfaces: test_dashboard_context_for_uninitialized_project_is_chinese_and_stable, test_dashboard_context_for_initialized_project_with_workspace_and_ready_llm_redacts_secret, test_dashboard_context_reports_initialized_project_without_workspace_or_provider, test_dashboard_context_collects_counts_recent_hint_and_ready_advice_without_network, test_dashboard_context_reports_incomplete_llm_without_api_key_leak
- Internal dependencies: core, yaml.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; test-time temp files/mocks may be used.
- Configuration assumptions: Textual optional UI dependency available for TUI paths.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_tui_dialog_history.py`
- Lines read: 60.
- Purpose: Test coverage for tui dialog history behavior.
- Key responsibilities: callables: test_dialog_history_appends_and_loads_summary_events_only, test_dialog_history_rejects_raw_conversation_fields, test_dialog_history_rejects_raw_conversation_on_reload
- Public interfaces: test_dialog_history_appends_and_loads_summary_events_only, test_dialog_history_rejects_raw_conversation_fields, test_dialog_history_rejects_raw_conversation_on_reload
- Internal dependencies: core, json, pytest.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; test-time temp files/mocks may be used.
- Configuration assumptions: Textual optional UI dependency available for TUI paths.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_tui_entrypoint.py`
- Lines read: 413.
- Purpose: Test coverage for tui entrypoint behavior.
- Key responsibilities: callables: test_tui_help_is_registered, test_cli_init_help_documents_optional_desktop_exe_release, test_chinese_labels_available, test_tui_dry_run_returns_chinese_status, test_tui_startup_metadata_covers_all_primary_views_and_shortcuts, test_tui_theme_layout_and_status_text_are_testable_without_terminal, test_tui_dry_run_prints_modern_status_without_secrets, test_tui_dry_run_status_and_output_use_chinese_copy_and_no_llm_secret
- Public interfaces: test_tui_help_is_registered, test_cli_init_help_documents_optional_desktop_exe_release, test_chinese_labels_available, test_tui_dry_run_returns_chinese_status, test_tui_startup_metadata_covers_all_primary_views_and_shortcuts, test_tui_theme_layout_and_status_text_are_testable_without_terminal, test_tui_dry_run_prints_modern_status_without_secrets, test_tui_dry_run_status_and_output_use_chinese_copy_and_no_llm_secret, test_cli_tui_dry_run_entrypoint, test_tui_dry_run_restores_last_exit_provider_without_secret_leak, test_tui_view_title_and_status_text_are_test_friendly, test_tui_help_text_documents_actual_bindings_and_state_meanings
- Internal dependencies: Cli, asyncio, core, pathlib, pytest, re, textual, typing, yaml.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; subprocess execution; test-time temp files/mocks may be used.
- Configuration assumptions: Textual optional UI dependency available for TUI paths.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_tui_experience_screens.py`
- Lines read: 125.
- Purpose: Test coverage for tui experience screens behavior.
- Key responsibilities: callables: test_experience_screen_suggest_requires_later_confirmation, test_experience_screen_empty_state_and_confirmation_copy_are_chinese, test_experience_screen_confirm_then_list_edit_export, test_experience_screen_delete_requires_exact_confirmation, test_experience_delete_copy_describes_exact_irreversible_confirmation, test_experience_view_sets_deterministic_non_empty_reload_status, test_experience_view_empty_success_error_copy_and_secret_redaction_are_explicit
- Public interfaces: test_experience_screen_suggest_requires_later_confirmation, test_experience_screen_empty_state_and_confirmation_copy_are_chinese, test_experience_screen_confirm_then_list_edit_export, test_experience_screen_delete_requires_exact_confirmation, test_experience_delete_copy_describes_exact_irreversible_confirmation, test_experience_view_sets_deterministic_non_empty_reload_status, test_experience_view_empty_success_error_copy_and_secret_redaction_are_explicit
- Internal dependencies: core, inspect, pytest.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: test-time temp files/mocks may be used.
- Configuration assumptions: Textual optional UI dependency available for TUI paths.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_tui_experiment_screen.py`
- Lines read: 158.
- Purpose: Test coverage for tui experiment screen behavior.
- Key responsibilities: callables: _static_text, test_tui_explicit_switch_opens_experiment_screen_and_preserves_prompt_focus, test_experiment_screen_accepts_input_calculates_advances_and_saves_redacted_log, test_experiment_screen_reports_missing_required_input, test_experiment_screen_initial_empty_copy_and_safe_layout_are_visible, scenario, scenario, scenario
- Public interfaces: test_tui_explicit_switch_opens_experiment_screen_and_preserves_prompt_focus, test_experiment_screen_accepts_input_calculates_advances_and_saves_redacted_log, test_experiment_screen_reports_missing_required_input, test_experiment_screen_initial_empty_copy_and_safe_layout_are_visible, scenario, scenario, scenario, scenario
- Internal dependencies: asyncio, core, textual.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; subprocess execution; test-time temp files/mocks may be used.
- Configuration assumptions: Textual optional UI dependency available for TUI paths.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_tui_invalid_table_actions.py`
- Lines read: 165.
- Purpose: Test coverage for tui invalid table actions behavior.
- Key responsibilities: callables: _static_text, _assert_red_error_with_reason, test_tool_run_on_empty_table_shows_red_error_without_exiting_tui, test_tool_screen_scans_candidates_without_tool_id_input, test_paper_enrich_on_empty_table_shows_red_error_without_exiting_tui, test_log_show_on_empty_table_shows_red_error_without_exiting_tui, test_experience_delete_on_empty_table_shows_red_error_without_exiting_tui, scenario
- Public interfaces: test_tool_run_on_empty_table_shows_red_error_without_exiting_tui, test_tool_screen_scans_candidates_without_tool_id_input, test_paper_enrich_on_empty_table_shows_red_error_without_exiting_tui, test_log_show_on_empty_table_shows_red_error_without_exiting_tui, test_experience_delete_on_empty_table_shows_red_error_without_exiting_tui, scenario, scenario, scenario, scenario, scenario
- Internal dependencies: asyncio, core, textual, yaml.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; subprocess execution; test-time temp files/mocks may be used.
- Configuration assumptions: Textual optional UI dependency available for TUI paths.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_tui_llm_screen.py`
- Lines read: 211.
- Purpose: Test coverage for tui llm screen behavior.
- Key responsibilities: callables: test_tui_controller_adds_switches_and_redacts_provider, test_tui_controller_restores_previous_exit_provider_on_startup, test_tui_controller_ignores_missing_last_provider_and_keeps_valid_current, test_tui_controller_save_exit_state_persists_current_provider_for_restore, test_tui_controller_error_messages_do_not_expose_api_key, test_tui_controller_readiness_message_redacts_api_key, test_llm_view_declares_secret_safe_inputs_empty_state_and_error_redaction, test_background_llm_transport_diagnostics_are_not_formatted_as_chat_content
- Public interfaces: test_tui_controller_adds_switches_and_redacts_provider, test_tui_controller_restores_previous_exit_provider_on_startup, test_tui_controller_ignores_missing_last_provider_and_keeps_valid_current, test_tui_controller_save_exit_state_persists_current_provider_for_restore, test_tui_controller_error_messages_do_not_expose_api_key, test_tui_controller_readiness_message_redacts_api_key, test_llm_view_declares_secret_safe_inputs_empty_state_and_error_redaction, test_background_llm_transport_diagnostics_are_not_formatted_as_chat_content
- Internal dependencies: core, inspect, yaml.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; test-time temp files/mocks may be used.
- Configuration assumptions: Textual optional UI dependency available for TUI paths; external runtime/API configuration may be absent and must degrade safely.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_tui_log_screen.py`
- Lines read: 226.
- Purpose: Test coverage for tui log screen behavior.
- Key responsibilities: callables: _static_text, test_tui_explicit_switch_opens_log_screen_and_global_shortcuts_remain, test_log_screen_writes_lists_and_shows_redacted_report, test_log_screen_empty_message_sets_status_without_creating_report, test_log_screen_initial_empty_copy_and_safe_layout_are_visible, test_log_screen_severity_text_uses_distinct_styles, test_log_screen_empty_and_refreshed_status_include_zero_statistics, test_log_screen_populated_table_and_detail_statistics_match_selected_entry
- Public interfaces: test_tui_explicit_switch_opens_log_screen_and_global_shortcuts_remain, test_log_screen_writes_lists_and_shows_redacted_report, test_log_screen_empty_message_sets_status_without_creating_report, test_log_screen_initial_empty_copy_and_safe_layout_are_visible, test_log_screen_severity_text_uses_distinct_styles, test_log_screen_empty_and_refreshed_status_include_zero_statistics, test_log_screen_populated_table_and_detail_statistics_match_selected_entry, test_log_screen_severity_label_uses_explicit_mapping_for_each_level, scenario, scenario, scenario, scenario
- Internal dependencies: asyncio, core, textual.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; subprocess execution; test-time temp files/mocks may be used.
- Configuration assumptions: Textual optional UI dependency available for TUI paths.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_tui_paper_screens.py`
- Lines read: 121.
- Purpose: Test coverage for tui paper screens behavior.
- Key responsibilities: callables: _policy, test_paper_screen_import_is_copy_only_and_lists_metadata, test_paper_screen_empty_state_and_select_workspace_copy_are_chinese, test_paper_screen_edit_metadata, test_paper_screen_enrichment_requires_explicit_confirmation, test_paper_enrichment_copy_warns_about_network_and_confirmation, test_paper_enrichment_confirmation_skips_without_network_policy_or_api, test_paper_view_sets_deterministic_non_empty_reload_status
- Public interfaces: test_paper_screen_import_is_copy_only_and_lists_metadata, test_paper_screen_empty_state_and_select_workspace_copy_are_chinese, test_paper_screen_edit_metadata, test_paper_screen_enrichment_requires_explicit_confirmation, test_paper_enrichment_copy_warns_about_network_and_confirmation, test_paper_enrichment_confirmation_skips_without_network_policy_or_api, test_paper_view_sets_deterministic_non_empty_reload_status, test_paper_view_empty_success_error_copy_and_secret_redaction_are_explicit
- Internal dependencies: core, inspect.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; test-time temp files/mocks may be used.
- Configuration assumptions: Textual optional UI dependency available for TUI paths.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_tui_permissions.py`
- Lines read: 105.
- Purpose: Test coverage for tui permissions behavior.
- Key responsibilities: classes: FakePermissionEngine; callables: test_high_risk_action_refuses_unconfirmed_request_without_permission_call, test_high_risk_action_requires_permission_engine_allow, test_low_risk_action_still_uses_permission_engine_but_not_confirmation_gate, test_permission_screen_controller_requires_full_confirmation_and_updates_policy, __init__, check
- Public interfaces: FakePermissionEngine, test_high_risk_action_refuses_unconfirmed_request_without_permission_call, test_high_risk_action_requires_permission_engine_allow, test_low_risk_action_still_uses_permission_engine_but_not_confirmation_gate, test_permission_screen_controller_requires_full_confirmation_and_updates_policy, __init__, check
- Internal dependencies: core, permission, pytest, typing.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; test-time temp files/mocks may be used.
- Configuration assumptions: Textual optional UI dependency available for TUI paths.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_tui_state.py`
- Lines read: 225.
- Purpose: Test coverage for tui state behavior.
- Key responsibilities: classes: FakeRegistry, FakeCheckpointManager, FakeKernel; callables: test_recent_workspace_selection_saved_and_loaded_from_workspace_session_state, test_tui_state_facade_uses_workspace_session_only, test_recent_workspace_state_is_scoped_per_workspace_and_not_global_cli_state, test_tui_state_does_not_affect_cli_workspace_requirement, test_llm_startup_restore_is_separate_from_tui_workspace_session_state, test_tui_shell_status_object_exposes_workspace_plugin_llm_version_and_task_state, test_tui_navigation_metadata_preserves_numeric_shortcuts_and_chinese_titles, discover
- Public interfaces: test_recent_workspace_selection_saved_and_loaded_from_workspace_session_state, test_tui_state_facade_uses_workspace_session_only, test_recent_workspace_state_is_scoped_per_workspace_and_not_global_cli_state, test_tui_state_does_not_affect_cli_workspace_requirement, test_llm_startup_restore_is_separate_from_tui_workspace_session_state, test_tui_shell_status_object_exposes_workspace_plugin_llm_version_and_task_state, test_tui_navigation_metadata_preserves_numeric_shortcuts_and_chinese_titles, FakeRegistry, FakeCheckpointManager, FakeKernel, discover, __init__
- Internal dependencies: Cli, core, yaml.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; subprocess execution; test-time temp files/mocks may be used.
- Configuration assumptions: Textual optional UI dependency available for TUI paths.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_tui_workspace_screens.py`
- Lines read: 265.
- Purpose: Test coverage for tui workspace screens behavior.
- Key responsibilities: classes: FakeStatus, FakeApp, TestWorkspaceView; callables: _allow_delete_policy, test_workspace_screen_create_select_and_recent_state, test_workspace_screen_create_rejects_duplicate_and_invalid_ids, test_workspace_screen_create_does_not_enter_kernel_or_llm, test_workspace_screen_empty_state_is_chinese_and_non_destructive, test_workspace_screen_delete_requires_exact_confirmation, test_workspace_screen_hard_delete_uses_policy_and_removes_workspace, test_workspace_view_delete_does_not_auto_confirm_source
- Public interfaces: test_workspace_screen_create_select_and_recent_state, test_workspace_screen_create_rejects_duplicate_and_invalid_ids, test_workspace_screen_create_does_not_enter_kernel_or_llm, test_workspace_screen_empty_state_is_chinese_and_non_destructive, test_workspace_screen_delete_requires_exact_confirmation, test_workspace_screen_hard_delete_uses_policy_and_removes_workspace, test_workspace_view_delete_does_not_auto_confirm_source, test_workspace_delete_copy_describes_exact_irreversible_confirmation, test_workspace_manual_create_entry_copy_is_visible_and_keyboard_mouse_friendly, test_workspace_view_supports_enter_shortcut_and_keeps_focus_after_create, test_workspace_view_manual_create_is_visible_and_usable_in_running_tui, test_workspace_manual_create_is_visible_to_already_mounted_dialog_page
- Internal dependencies: asyncio, core, inspect, pytest, textual.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; subprocess execution; test-time temp files/mocks may be used.
- Configuration assumptions: Textual optional UI dependency available for TUI paths.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_uninstall.py`
- Lines read: 257.
- Purpose: Test coverage for uninstall behavior.
- Key responsibilities: callables: test_dry_run_does_not_delete_project_owned_files, test_force_removes_owned_runtime_artifacts_but_not_unrecorded_platform_dirs, test_uninstall_does_not_remove_user_owned_files_or_repo_root, test_recorded_and_explicit_targets_are_removed_only_inside_project, test_nested_platform_install_records_are_removed_but_unrecorded_home_like_dirs_survive, test_invalid_install_record_is_ignored_safely, test_uninstall_logs_are_secret_redacted, test_collect_candidates_defines_project_owned_rules
- Public interfaces: test_dry_run_does_not_delete_project_owned_files, test_force_removes_owned_runtime_artifacts_but_not_unrecorded_platform_dirs, test_uninstall_does_not_remove_user_owned_files_or_repo_root, test_recorded_and_explicit_targets_are_removed_only_inside_project, test_nested_platform_install_records_are_removed_but_unrecorded_home_like_dirs_survive, test_invalid_install_record_is_ignored_safely, test_uninstall_logs_are_secret_redacted, test_collect_candidates_defines_project_owned_rules, test_uninstall_removes_recorded_binary_shortcut_config_cache_log_temp_and_user_data_by_default, test_uninstall_manifest_ownership_keys_cover_recorded_exe_and_shortcut_artifacts, test_uninstall_can_preserve_recorded_user_data_explicitly, test_uninstall_reports_residuals_and_repair_suggestions_when_delete_fails
- Internal dependencies: Uninstall, json, logging, yaml.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; test-time temp files/mocks may be used.
- Configuration assumptions: filesystem permissions and PATH/venv layout vary by host.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_workspace.py`
- Lines read: 149.
- Purpose: Test coverage for workspace behavior.
- Key responsibilities: callables: test_valid_workspace_slug_is_accepted, test_invalid_workspace_slug_is_rejected, test_initialize_workspace_creates_expected_layout_only_under_workspaces, test_workspace_metadata_is_stored_and_reloaded, test_workspace_symlink_target_inside_project_is_accepted, test_workspace_symlink_target_outside_project_is_rejected, test_recent_selection_state_is_stored_only_in_workspace_session_path, test_no_implicit_cli_or_global_state_is_created
- Public interfaces: test_valid_workspace_slug_is_accepted, test_invalid_workspace_slug_is_rejected, test_initialize_workspace_creates_expected_layout_only_under_workspaces, test_workspace_metadata_is_stored_and_reloaded, test_workspace_symlink_target_inside_project_is_accepted, test_workspace_symlink_target_outside_project_is_rejected, test_recent_selection_state_is_stored_only_in_workspace_session_path, test_no_implicit_cli_or_global_state_is_created, test_workspace_manager_create_is_direct_without_kernel_or_llm_import, guarded_import
- Internal dependencies: core, os, pytest, yaml.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_workspace_cli.py`
- Lines read: 233.
- Purpose: Test coverage for workspace cli behavior.
- Key responsibilities: classes: FakeRegistry, FakeCheckpointManager, FakeKernel, FakeRegistry, FakeCheckpointManager, FakeKernel; callables: _copy_default_policy, test_workspace_init_list_show_use_explicit_workspace, test_workspace_init_does_not_enter_kernel_or_llm, test_workspace_subcommands_require_explicit_workspace, test_workspace_delete_rejects_confirmation_mismatch_and_audits, test_workspace_delete_hard_deletes_after_permission_approval, test_workspace_delete_denied_by_policy_keeps_workspace_and_audits, test_run_without_workspace_preserves_legacy_params; constants: REPO_ROOT
- Public interfaces: test_workspace_init_list_show_use_explicit_workspace, test_workspace_init_does_not_enter_kernel_or_llm, test_workspace_subcommands_require_explicit_workspace, test_workspace_delete_rejects_confirmation_mismatch_and_audits, test_workspace_delete_hard_deletes_after_permission_approval, test_workspace_delete_denied_by_policy_keeps_workspace_and_audits, test_run_without_workspace_preserves_legacy_params, test_run_with_workspace_adds_explicit_workspace_context, guarded_import, FakeRegistry, FakeCheckpointManager, FakeKernel
- Internal dependencies: Cli, core, json, pathlib, permission, pytest, yaml.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; subprocess execution; test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

### `tests/test_workspace_tools.py`
- Lines read: 566.
- Purpose: Test coverage for workspace tools behavior.
- Key responsibilities: classes: RecordingPermissionEngine, FakeRegistry, FakeCheckpointManager, FakeKernel; callables: _copy_default_policy, test_language_validation_accepts_supported_languages, test_language_validation_rejects_invalid_languages, test_tool_id_validation_accepts_safe_slugs, test_tool_id_validation_rejects_traversal_and_unsafe_ids, test_tool_init_creates_python_and_r_directories_under_workspace, test_builtin_templates_can_be_scaffolded_and_loaded, test_manifest_schema_requires_expected_fields_and_validates_identity; constants: REPO_ROOT
- Public interfaces: RecordingPermissionEngine, test_language_validation_accepts_supported_languages, test_language_validation_rejects_invalid_languages, test_tool_id_validation_accepts_safe_slugs, test_tool_id_validation_rejects_traversal_and_unsafe_ids, test_tool_init_creates_python_and_r_directories_under_workspace, test_builtin_templates_can_be_scaffolded_and_loaded, test_manifest_schema_requires_expected_fields_and_validates_identity, test_workspace_tool_manifest_size_is_bounded, test_tool_authoring_context_matches_manifest_and_scanner_contract, test_list_discovers_tools_grouped_by_language, test_scan_import_candidates_lists_python_and_r_with_metadata_fallback
- Internal dependencies: Cli, core, json, pathlib, permission, pytest, typing, yaml.
- Data flow: pytest imports target modules, creates fixtures/mocks, asserts behavior and regressions.
- Side effects: filesystem I/O or mutation; subprocess execution; test-time temp files/mocks may be used.
- Configuration assumptions: standard project/runtime assumptions only.
- Maintenance risks: coverage can become stale if target behavior changes.

## Questions / Unknowns

- No tracked Nature-Skill, PaperSpine, or Citation-Check-Skill implementation files are present; future requirements for those targets must define clean-room behavior before implementation. Self-evolution files are present locally and mapped above as supplemental intended untracked source/test coverage.
- Static AST and line-reading cannot prove runtime behavior of Textual callbacks, plugin dynamic imports, external CLIs, network providers, or optional R/LLM runtimes; tests and permission reviews remain required before release.
- External medical style/checklist authority updates are not automatically synchronized; maintainers should periodically review AMA/Vancouver/PRISMA/STARD/STROBE/CONSORT references.
