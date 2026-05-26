# Repository Optimization Audit

Date: 2026-05-26

Purpose: establish the immutable baseline and protection boundaries before any repository optimization. This step is audit-only: no runtime/source behavior changes are allowed in this step except creating this document.

## 1. Current branch, remote, and working tree status

- Working directory: `D:\GIT\SuperMedicine`
- Current branch: `master`
- Tracking status: `master...origin/master`
- Remote:
  - `origin https://github.com/KarasawaYikiho/SuperMedicine.git (fetch)`
  - `origin https://github.com/KarasawaYikiho/SuperMedicine.git (push)`
- Recent baseline commit: `08ee767 feat: add workspace research tools and TUI workflows`
- Initial working tree state recorded by `git status --short --branch`:
  - Modified tracked files: 33
  - Untracked intended files: 2
  - No staged changes reported by `git diff --cached --stat`
- `git diff --stat` baseline summary: 33 files changed, 1354 insertions, 194 deletions.
- Git emitted line-ending warnings that LF will be replaced by CRLF next time Git touches many modified files. Treat line-ending normalization as non-semantic only if already project-standard and do not mix it with runtime behavior edits.

## 2. Current tracked and untracked intended changes summary

These pre-existing uncommitted changes are from earlier platform agent/model/version work that already passed final verification. Preserve them and do not discard, overwrite, or reinterpret them during optimization.

Modified tracked files at baseline:

- `.gitignore`
- `.supermedicine/config.yaml`
- `.supermedicine/policies/default.yaml`
- `ARCHITECTURE.md`
- `Architecture/ExecutionRoadmap.md`
- `Architecture/OptimizationAudit.md`
- `CHANGELOG.md`
- `Cli.py`
- `INSTALL.md`
- `Install.py`
- `README.md`
- `adapters/__init__.py`
- `adapters/claude_code/SKILL.md`
- `adapters/claude_code/adapter.py`
- `adapters/opencode/__init__.py`
- `adapters/opencode/adapter.py`
- `adapters/opencode/agents/alpha-analyst.md`
- `adapters/opencode/agents/beta-reviewer.md`
- `adapters/opencode/agents/delta-orchestrator.md`
- `adapters/opencode/agents/gamma-writer.md`
- `adapters/opencode/plugin.json`
- `adapters/standalone/adapter.py`
- `install.json`
- `permission/default_policy.yaml`
- `permission/prompt_generator.py`
- `pyproject.toml`
- `tests/test_backward_compatibility.py`
- `tests/test_claude_code_adapter.py`
- `tests/test_integration.py`
- `tests/test_opencode_adapter.py`
- `tests/test_plugin_registry.py`
- `tests/test_repo_hygiene.py`
- `tests/test_standalone_adapter.py`

Untracked intended files at baseline:

- `Architecture/PlatformIntegrationAudit.md`
- `adapters/opencode/agents/supermedicine.md`

## 3. Project structure and entry points

Tracked top-level structure includes:

- Documentation and governance: `README.md`, `INSTALL.md`, `ARCHITECTURE.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `LICENSE`, `Architecture/**`
- Python CLI and installer entry modules: `Cli.py`, `Install.py`
- Core runtime: `core/**`
- Permission engine and policies: `permission/**`, `.supermedicine/policies/default.yaml`
- Agent orchestration concepts: `agents/**`
- Optional platform adapters: `adapters/**`
- Plugin ecosystem: `plugins/**`
- Tests: `tests/**`
- Packaging/configuration: `pyproject.toml`, `requirements.txt`, `install.json`, `.github/workflows/ci.yml`, `.gitignore`

Entry points and discovery-sensitive paths:

- Package console script: `supermedicine = "Cli:main"` in `pyproject.toml`
- Setuptools modules: `py-modules = ["Cli", "Install"]`
- Setuptools package discovery: `core*`, `permission*`, `agents*`, `plugins*`, `adapters*`
- Package data: `permission/default_policy.yaml`
- Direct module entry guards observed: `Cli.py`, `Install.py`, `core/workspace_tools.py`
- TUI entry function observed: `core/tui/app.py::main`
- Pytest discovery conventions: `testpaths = ["tests"]`, `python_files = ["test_*.py"]`
- OpenCode adapter metadata and agent/skill paths under `adapters/opencode/**`
- Claude Code skill/adapter paths under `adapters/claude_code/**`

## 4. Build, test, type, lint, and packaging command inventory

Validation commands documented by repository files and CI for later steps:

- Install development environment: `python -m pip install -e ".[dev]"`
- Lint gate: `python -m ruff check --select=E,F,W --ignore=E501 .`
- Full test suite: `python -m pytest tests/ -v --tb=short --override-ini addopts= -p no:cacheprovider --basetemp <temp-dir>`
- Repository hygiene focused test: `python -m pytest tests/test_repo_hygiene.py -q --override-ini addopts= -p no:cacheprovider --basetemp <temp-dir>`
- Wheel smoke/build gate: `python -m pip wheel . --no-deps --wheel-dir <temp-wheel-dir>`
- Source distribution gate from CI release job: `python -m build --sdist --outdir dist`
- Optional documented local test command: `pytest tests/ -v`
- Optional type check mentioned in release notes: `mypy`; current CI/release gate documentation says dedicated type checking is not part of the enforced gate.
- CLI smoke commands referenced in docs/audits for later verification: `supermedicine status`, `supermedicine init`, `supermedicine run ...`, `python Install.py --init`, `python Cli.py status`.

Do not run verification in this audit step; Tester owns verification.

## 5. Generated and ignored artifacts observed

Ignored/generated artifacts observed by `git ls-files --others --ignored --exclude-standard` include:

- Python bytecode/cache directories across runtime, adapters, plugins, permission, agents, core, and tests: `__pycache__/`, `*.pyc`
- Ruff cache: `.ruff_cache/**`
- Pytest cache: `.pytest_cache/` was not listable because Git reported `warning: could not open directory '.pytest_cache/': Permission denied`
- Runtime audit log: `.supermedicine/policies/audit.jsonl`
- Runtime checkpoints: `.supermedicine/checkpoints/**`
- Local planning note: `Planning/NextSteps.md`
- Build output mirror: `build/lib/**`
- Packaging metadata: `supermedicine.egg-info/**`

Cleanup policy for later steps:

- Generated/ignored artifacts may be removed only when they are clearly ignored build/cache/runtime products and not source of truth.
- Do not remove tracked source, tests, docs, config, policies, plugin metadata, package metadata inputs, or adapter resources.
- Respect the `.pytest_cache/` permission denial; document and skip if deletion remains blocked.
- Do not clean untracked intended source/documentation files listed in section 2.

## 6. Hard no-go semantic preservation boundaries

Absolute priority: do not change existing functionality or code meaning, even for security risks or unused code. Later optimization must preserve:

- Public API behavior, function/class/module names, return shapes, exceptions, and import paths.
- CLI commands, arguments, defaults, prompts, output meanings, exit behavior, and the `supermedicine` console script entry point.
- Plugin IDs, action IDs, plugin manifests, action schemas, result schemas, and registry/discovery semantics.
- Adapter behavior and platform surfaces for OpenCode, Claude Code, and standalone adapters, including degraded/unavailable states.
- Agent IDs, role documents, skill document identity, plugin metadata, platform manifests, and install manifest semantics.
- Permission/security policy behavior, default allow/deny policy meanings, audit semantics, operation guard semantics, path safety checks, and prompt-generation safety guidance.
- Package entry points, setuptools package discovery, package data, optional extras, version meaning, and importable module names.
- Test meaning and assertions. Tests may only change if preserving intent while synchronizing purely mechanical path/name changes that have already been proven non-breaking.
- Medical/statistical output meanings, deterministic fixture behavior, R/rpy2 fallback behavior, RAG provider contracts, workspace behavior, TUI behavior, and paper/experience workflows.
- Configuration file meanings, default values, local `.supermedicine` behavior, policy file structure, and runtime artifact paths.
- Existing uncommitted platform agent/model/version changes listed in this audit.

## 7. Allowed optimization categories

Allowed only when safe and non-semantic:

- Documentation/prose/title naming cleanup, including independent word initial capitalization where it does not alter code identifiers, commands, paths, IDs, or quoted literals.
- Safe path capitalization only when every import, package/discovery reference, documentation reference, test reference, manifest reference, and platform reference is fully synchronized and the change is non-breaking on case-sensitive and case-insensitive filesystems.
- Exact duplicate prose deletion when text is semantically identical and no unique caveat, warning, or context is lost.
- Generated/ignored artifact cleanup under the cleanup policy in section 5.
- UTF-8/LF or other formatting normalization only if already project standard and strictly non-semantic; avoid touching runtime files solely for formatting during semantic-preservation work.

## 8. Python modules/tests/packages caution

Do not rename Python modules, tests, packages, package directories, or entry modules if doing so risks import/discovery, setuptools packaging, pytest discovery, adapter discovery, or external user workflows. In particular, treat these as discovery-sensitive and skip renames unless a complete non-breaking path synchronization is explicitly required and verified later:

- `Cli.py`, `Install.py`
- `core/**`, `permission/**`, `agents/**`, `plugins/**`, `adapters/**`
- `tests/test_*.py`, `tests/conftest.py`, `tests/__init__.py`
- `permission/default_policy.yaml`, plugin `plugin.yaml` files, `install.json`, `adapters/opencode/plugin.json`

If independent word capitalization would imply changing any of the above paths or identifiers, document the skip rather than forcing the rename.

## 9. Baseline notes for later optimization

- This audit file is the only intended file change in Step 1.
- Pre-existing uncommitted changes are part of the protected baseline and must survive unchanged unless a later planned step explicitly modifies them within no-go boundaries.
- Repository currently contains both tracked source/docs/config and ignored generated outputs. Later cleanup should focus only on ignored artifacts.
- File/code path renames are high risk in this Python package because import paths, setuptools discovery, pytest discovery, plugin manifests, and platform adapters all depend on stable names.

## 10. Step 2 independent-word initial capitalization naming audit

Scope: repository path-name audit only. No files or directories were renamed in this step. Generated and ignored artifacts such as `__pycache__/`, `*.pyc`, `.ruff_cache/**`, `.mypy_cache/**`, `.pytest_cache/**`, `build/lib/**`, `supermedicine.egg-info/**`, `.supermedicine/checkpoints/**`, and `.supermedicine/policies/audit.jsonl` are excluded from rename consideration because they are not source-of-truth paths.

Interpretation used for this audit:

- "Independent-word initial capitalization" means source-of-truth words would visually start with uppercase letters, for example `BaseAdapter.py` or `MedicalCitation/`, rather than `base_adapter.py` or `medical_citation/`.
- Python import/package/test discovery conventions, plugin IDs, manifests, adapter paths, CLI entry points, configuration paths, and documented user-facing paths have priority over capitalization aesthetics.
- Case-only renames are treated as risky on Windows and in Git because the current workspace is on a case-insensitive platform and because collaborators or CI may use case-sensitive filesystems.
- Conventional repository metadata names such as `.github`, `.gitignore`, `README.md`, `LICENSE`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `pyproject.toml`, and `requirements.txt` are intentionally conventional and are not recommended for capitalization-only cleanup.

### 10.1 Safe rename candidates

No low-risk source-of-truth rename candidates are recommended for Step 3.

Rationale: every non-capitalized tracked source path found is either a Python package/module/test path, a plugin/adapter/platform manifest path, a config/policy path, a conventional repository metadata path, or a static resource path under a plugin/adapter tree where code or manifests may load by literal path. The conservative outcome is to avoid behavior-affecting renames and preserve import/discovery/runtime conventions.

If Step 3 must include a capitalization rename, limit it to a separately reviewed documentation-only path outside Python packages, plugin trees, adapter trees, configuration trees, and conventional repository metadata. This audit found no such candidate that is both clearly non-conventional and clearly unreferenced.

### 10.2 Risky skipped rename mapping

The following mappings document what independent-word capitalization would imply, but they are intentionally skipped. They should not be executed unless a future plan explicitly accepts the migration risk and synchronizes every reference.

| Current path pattern | Capitalized target shape | Decision | Reference/import/config/docs/tests synchronization required | Skip reason |
| --- | --- | --- | --- | --- |
| `Cli.py` | `Cli.py` or `CLI.py` | Skip | `pyproject.toml` console script `supermedicine = "Cli:main"`, direct `python Cli.py` docs/tests, package metadata | Entry module and public workflow are discovery-sensitive; current spelling is already protected by packaging. |
| `Install.py` | `Install.py` | Skip | Direct `python Install.py` docs/tests and setuptools `py-modules` | Entry installer module is public workflow-sensitive; no rename needed. |
| `core/**` package directory | `Core/**` | Skip | All `core.*` imports, setuptools package discovery, tests, docs, generated package metadata | Python package import paths should remain lowercase; package-directory capitalization is high risk. |
| `core/config_center.py` | `core/ConfigCenter.py` | Skip | Imports, tests, docs, package metadata | Python module rename would change import path and violate common module naming convention. |
| `core/event_bus.py` | `core/EventBus.py` | Skip | Imports, tests, docs, package metadata | Python module rename would change import path. |
| `core/llm_client.py` and `core/llm_providers/**` | `core/LLMClient.py`, `core/LLMProviders/**` | Skip | Imports, tests, docs, provider discovery | Acronym/case migration is especially case-sensitive and import-sensitive. |
| `core/operation_guard.py`, `core/path_safety.py`, `core/plugin_registry.py`, `core/session_manager.py`, `core/workspace_tools.py` | `OperationGuard.py`, `PathSafety.py`, `PluginRegistry.py`, `SessionManager.py`, `WorkspaceTools.py` | Skip | Imports, tests, CLI/workspace docs | Python module import paths are behavior-sensitive. |
| `core/paper_import/**` | `core/PaperImport/**` | Skip | Imports, tests such as `test_paper_import_core.py`, paper CLI docs | Python subpackage import path and tests are discovery-sensitive. |
| `core/tui/**`, including `dialog_history.py` and `screens/**` | `core/TUI/**`, `DialogHistory.py`, `Screens/**` | Skip | TUI imports, tests, docs, entry functions | Python package/module import paths and TUI screen discovery should remain stable. |
| `permission/**`, including `default_policy.yaml` and `prompt_generator.py` | `Permission/**`, `DefaultPolicy.yaml`, `PromptGenerator.py` | Skip | Imports, `pyproject.toml` package data, `.supermedicine/policies/default.yaml`, tests, docs | Policy and package-data paths are config/runtime-sensitive. |
| `agents/**`, including `base_agent.py` and `state_machine.py` | `Agents/**`, `BaseAgent.py`, `StateMachine.py` | Skip | Imports, tests, orchestration docs | Agent package/module import paths are runtime-sensitive. |
| `adapters/**` package directory | `Adapters/**` | Skip | Imports, setuptools package discovery, tests, docs | Adapter package import path is public and discovery-sensitive. |
| `adapters/base_adapter.py` | `adapters/BaseAdapter.py` | Skip | Imports/tests across adapter implementations | Python module path is import-sensitive. |
| `adapters/claude_code/**` | `adapters/ClaudeCode/**` | Skip | Imports, tests, docs, adapter availability logic, `SKILL.md` path assumptions | Adapter subpackage name and platform path are behavior-sensitive. |
| `adapters/opencode/**` | `adapters/OpenCode/**` | Skip | Imports, tests, `plugin.json`, agent/skill installation docs, OpenCode platform discovery | Plugin/adapter path and manifest ecosystem are platform-sensitive. |
| `adapters/opencode/agents/*.md` lowercase hyphen names | `AlphaAnalyst.md`, `BetaReviewer.md`, `DeltaOrchestrator.md`, `GammaWriter.md`, `Supermedicine.md` | Skip | `plugin.json`, installer/docs/tests, platform agent IDs | Filenames may be IDs or installation targets; hyphenated lowercase is platform-conventional. |
| `adapters/opencode/skills/*.md` lowercase hyphen names | `HarnessMonitor.md`, `MedicalCitation.md`, `MedicalWriting.md`, `PythonStats.md`, `RSurvival.md`, `RagQuery.md` | Skip | `plugin.json`, adapter docs/tests, platform skill IDs | Skill filenames are platform-facing identifiers; capitalization could break discovery. |
| `plugins/**` package directory | `Plugins/**` | Skip | Imports, setuptools package discovery, plugin registry, tests | Plugin package path is discovery-sensitive. |
| `plugins/harness/**`, `plugins/rag/**`, `plugins/standards/**`, `plugins/tools/**` | `Harness/**`, `Rag/**`, `Standards/**`, `Tools/**` | Skip | Plugin registry, imports, manifests, tests, docs | Plugin discovery and import paths should remain lowercase/stable. |
| `plugins/*/plugin.yaml` | `Plugin.yaml` | Skip | Plugin registry file lookup, tests, docs | Manifest basename is convention-sensitive and likely loaded literally. |
| `plugins/standards/medical_citation/**` | `MedicalCitation/**` | Skip | Imports, plugin manifests/tests/docs | Python package and plugin action paths are import/discovery-sensitive. |
| `plugins/standards/medical_writing/**` | `MedicalWriting/**` | Skip | Imports, plugin manifests/tests/docs, checklist references | Python package/resource paths are import/discovery-sensitive. |
| `plugins/tools/python_stats/**` | `PythonStats/**` | Skip | Imports, plugin manifest, tests, docs | Python package and plugin path are discovery-sensitive. |
| `plugins/tools/r_survival/**` | `RSurvival/**` | Skip | Imports, plugin manifest, tests, docs, optional R/rpy2 fallback paths | Python package and plugin path are discovery-sensitive. |
| Plugin reference docs such as `provider-interface.md`, `consort-checklist.md`, `prisma-checklist.md`, `stard-checklist.md`, `strobe-checklist.md` | `ProviderInterface.md`, `ConsortChecklist.md`, `PrismaChecklist.md`, `StardChecklist.md`, `StrobeChecklist.md` | Skip | Plugin resource loading, docs/tests, package-data inclusion if later added | Static resources are inside plugin trees and may be loaded by literal path. |
| `tests/**`, including all `test_*.py` | `Tests/**`, `Test*.py` | Skip | Pytest `testpaths`, `python_files = ["test_*.py"]`, imports, CI/docs | Pytest discovery convention requires lowercase `tests` and `test_*.py`; preserve over aesthetics. |
| `.supermedicine/**` | `.SuperMedicine/**` | Skip | Runtime config discovery, `.gitignore`, docs/tests, user local state | Dot-directory is a runtime/config convention; capitalization would break local workflows. |
| `.github/workflows/ci.yml` | `.GitHub/Workflows/CI.yml` | Skip | GitHub Actions discovery, badges/docs | GitHub requires conventional `.github/workflows`; do not rename. |
| `.gitignore` patterns | Capitalized patterns | Skip | Ignore behavior for caches/build outputs/runtime artifacts | Pattern changes could expose generated artifacts or hide source; keep conventional. |
| `install.json` | `Install.json` | Skip | Installer/config docs/tests and package metadata | Manifest/config path may be loaded by literal name. |
| `pyproject.toml`, `requirements.txt` | `PyProject.toml`, `Requirements.txt` | Skip | Packaging tools, installers, CI, docs | Tooling expects conventional lowercase names. |
| Conventional root docs `README.md`, `INSTALL.md`, `ARCHITECTURE.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `LICENSE` | `Readme.md`, `Install.md`, `Architecture.md`, etc. | Skip | GitHub rendering, packaging metadata, docs links, possible `Architecture/` case/name confusion | Conventional uppercase metadata names are intentional; `ARCHITECTURE.md` also risks confusion with `Architecture/` directory. |

### 10.3 Case-only and path-conflict risk notes

- Windows/Git case-only renames are unreliable unless performed carefully with an intermediate temporary name. This audit step intentionally did not perform any rename.
- Mixed-case changes such as `core` -> `Core`, `plugins` -> `Plugins`, or `ARCHITECTURE.md` -> `Architecture.md` can appear unchanged to case-insensitive tooling while still changing behavior on Linux/macOS CI or package consumers.
- `ARCHITECTURE.md` and `Architecture/` are already close in spelling. Any rename toward `Architecture.md` increases ambiguity in shell completion, docs links, and case-insensitive tooling.
- Hyphen-to-PascalCase renames under OpenCode agent/skill paths may also change platform IDs if filenames are treated as identifiers.
- Generated/ignored mirrors under `build/lib/**`, `supermedicine.egg-info/**`, and caches must not be renamed because they should be cleaned/regenerated, not treated as source paths.

### 10.4 Reference synchronization requirements if a future safe candidate is introduced

For any future rename that is judged truly safe, synchronize all of the following in the same step:

- Python imports, dynamic imports, package discovery settings, package data, and console entry points.
- Tests, pytest discovery configuration, fixtures, and path literals.
- Plugin manifests (`plugin.yaml`, `plugin.json`), plugin/action IDs, adapter installation metadata, OpenCode/Claude Code agent and skill path references.
- Configuration files, `.gitignore` patterns, runtime `.supermedicine` references, documentation links, install instructions, and CI workflow paths.
- Git rename mechanics on Windows: use a two-step intermediate path for case-only changes and verify Git records the rename as intended.

### 10.5 Step 3 recommendation

Execute no capitalization renames in Step 3 unless a new, clearly documentation-only candidate outside sensitive trees is identified. Prefer Step 3 work to focus on low-risk generated/ignored artifact cleanup and prose-only documentation cleanup. Explicitly skip Python modules/packages/tests, adapter subpackages, plugin IDs/manifests/import paths, config paths, `.supermedicine`, `.gitignore` patterns, and conventional repository metadata names.

## 11. Step 3 conservative naming normalization execution result

Scope: conservative naming normalization and reference synchronization follow-up to the Step 2 audit. No repository paths were renamed in this step.

Execution result:

- Renames performed: none.
- Risky Python module/package/test paths were left unchanged, including `Cli.py`, `Install.py`, `core/**`, `permission/**`, `agents/**`, `plugins/**`, `adapters/**`, and `tests/**`.
- Risky adapter, plugin, manifest, configuration, runtime, and discovery-sensitive paths were left unchanged, including OpenCode/Claude Code adapter resources, plugin manifests, `.supermedicine/**`, `.github/workflows/**`, `.gitignore`, `install.json`, `pyproject.toml`, and `requirements.txt`.
- Conventional repository metadata and documentation filenames were left unchanged, including `README.md`, `INSTALL.md`, `ARCHITECTURE.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, and `LICENSE`.
- No import, entry point, manifest, package-data, pytest-discovery, plugin-discovery, configuration, runtime-path, or documentation-link reference synchronization was required because no path rename occurred.

Rationale: Step 2 identified no low-risk source-of-truth rename candidate. The only apparent capitalization opportunities are tied to Python imports, setuptools/pytest discovery, plugin or adapter platform discovery, configuration/runtime paths, conventional tooling filenames, or case-only Git behavior on Windows. Preserving those paths avoids behavior changes and avoids unnecessary churn.

## 12. Step 4 duplicate and redundant content audit

Scope: repository duplicate/redundant content audit only. No source, runtime, configuration, documentation, generated, or ignored files were deleted or modified in this step except this audit section.

Inspection coverage:

- Exact file-content duplicates across the working tree, excluding `.git/` internals.
- Markdown paragraph-level duplicates in source-of-truth documentation and adapter/skill/agent/reference documents, excluding generated/build/cache trees.
- Repeated configuration/static fragments in YAML, JSON, TOML, and runtime checkpoint JSON files.
- Duplicate-looking Python imports/exports and generated mirrors, with code-duplication candidates recorded as skipped unless they are purely non-semantic and lint-level.
- Zero-byte files were checked; none were observed outside `.git/` internals.

### 12.1 Safe duplicate/redundant deletion candidates

No exact source-of-truth documentation, configuration, static text, export, empty-file, backup-file, or generated-file deletion candidate is recommended as a source/content duplicate in Step 5.

Rationale: duplicate-looking source/content items either carry distinct placement/context meaning, are runtime/config/discovery-sensitive, are intentionally repeated across agent/platform documents, are tests/examples/fixtures, or are code-level repetition that this audit is explicitly not allowed to abstract or rewrite. The only clearly removable duplicate material found is generated/ignored artifact material listed separately in section 12.2.

### 12.2 Generated/ignored artifacts eligible for cleanup in Step 5

The following generated or ignored artifacts are eligible for cleanup because they are not source-of-truth files and are reproducible runtime/build/cache outputs:

- `build/lib/**`: setuptools/build output mirror. Many files are exact byte-for-byte duplicates of source files such as `Cli.py`, `Install.py`, `core/**`, `permission/**`, `agents/**`, `plugins/**`, and `adapters/**`. Cleanup rationale: generated build mirror; source-of-truth copies live outside `build/`.
- `supermedicine.egg-info/**`: packaging metadata output from editable/build operations (`PKG-INFO`, `SOURCES.txt`, `entry_points.txt`, `requires.txt`, `top_level.txt`, `dependency_links.txt`). Cleanup rationale: generated package metadata; source-of-truth packaging input is `pyproject.toml` plus repository files.
- Python bytecode/cache artifacts: top-level `__pycache__/`, package/test `__pycache__/`, and `*.pyc` under `adapters/**`, `agents/**`, `core/**`, `permission/**`, `plugins/**`, and `tests/**`. Cleanup rationale: interpreter-generated bytecode caches.
- Tool caches: `.ruff_cache/**` and `.mypy_cache/**`. Cleanup rationale: linter/type-check cache data.
- Runtime local state: `.supermedicine/checkpoints/**` and `.supermedicine/policies/audit.jsonl`. Cleanup rationale: runtime execution/checkpoint/audit-log outputs, not source policy definitions.
- `.pytest_cache/**`: eligible by policy if accessible, but previous listing reported `Permission denied`; Step 5 should skip or document if deletion remains blocked.
- `Planning/NextSteps.md`: currently ignored local planning note, not tracked source-of-truth. Cleanup rationale: ignored local planning artifact; do not treat as repository documentation unless explicitly promoted/tracked first.

### 12.3 Duplicate-looking items intentionally skipped

The following duplicate-looking items are intentionally skipped and must not be deleted/merged by Step 5:

- `permission/default_policy.yaml` and `.supermedicine/policies/default.yaml` are exact byte-for-byte duplicates, but both are skipped. Rationale: `permission/default_policy.yaml` is package/source policy data, while `.supermedicine/policies/default.yaml` is the local runtime policy copy used by initialized workspaces; removing either could change packaging, runtime defaults, or user-local behavior.
- Repeated `rag.context.store`, `rag.context.retrieve`, `rag.external.query`, `security_level`, and similar YAML fragments inside the policy files are skipped. Rationale: permissions are role-specific entries under different agents; repeated action names do not imply semantic equivalence because scopes and agent contexts differ.
- The repeated OpenCode internal-role disclaimer paragraph in `adapters/opencode/agents/alpha-analyst.md`, `beta-reviewer.md`, `delta-orchestrator.md`, and `gamma-writer.md` is skipped. Rationale: each role document is independently installable/readable platform context; removing the repeated disclaimer from some files would weaken per-file safety/context metadata.
- The repeated install command block in `README.md` and `INSTALL.md` is skipped. Rationale: `README.md` quick-start content and `INSTALL.md` installation-guide content serve different documentation entry points; deleting one would reduce standalone usefulness.
- Repeated adapter/manifest fragments such as `"core_runtime_required": false` across `install.json` and `adapters/opencode/plugin.json` are skipped. Rationale: each manifest is consumed independently by different installer/platform surfaces.
- Repeated plugin manifest shapes across `plugins/**/plugin.yaml` are skipped. Rationale: shared schema fields are required per plugin and are not redundant files/fragments.
- Duplicate-looking test fixtures/assertions/import patterns in `tests/**` are skipped. Rationale: duplicate tests and fixtures may encode separate coverage intent and are explicitly protected by the hard constraints.
- Duplicate-looking Python imports found in `Cli.py`, `tests/test_integration.py`, `tests/test_permission_engine.py`, `tests/test_plugin_registry.py`, `tests/test_repo_hygiene.py`, and `tests/test_session_manager.py` are skipped. Rationale: these are code-level/local-import structure issues; even if a linter could flag some as non-semantic, this step must not rewrite code, and imports inside command/test scopes can preserve lazy-load or fixture-local meaning.
- Exact duplicates under `build/lib/**` are not source/content duplicates to merge into source. Rationale: they are generated mirrors and should be cleaned as generated artifacts, not used to drive source refactoring.
- Repeated runtime checkpoint JSON fields and repeated error/status messages under `.supermedicine/checkpoints/**` are skipped as content duplicates. Rationale: checkpoint files are generated runtime records; clean the whole generated checkpoint tree if desired rather than deduplicating individual records.
- Documentation overlap across `ARCHITECTURE.md`, `Architecture/OptimizationAudit.md`, `Architecture/PlatformIntegrationAudit.md`, `Architecture/ExecutionRoadmap.md`, and this audit file is skipped unless exact duplicate prose is proven safe in a later doc-only pass. Rationale: these files have different audit/planning purposes and may intentionally restate boundaries for local completeness.
- Platform skill/reference documents under `adapters/opencode/skills/**`, `adapters/claude_code/SKILL.md`, and `plugins/**/references/**` are skipped. Rationale: repeated safety, boundary, or checklist wording may be required for standalone platform/resource consumption.

### 12.4 Step 5 recommendation

Step 5 should clean only generated/ignored artifacts listed in section 12.2. Do not delete or merge source-of-truth documentation/prose/configuration/code in Step 5 because this audit found no semantically identical source/content duplicate whose removal is clearly safe under the no-behavior-change constraints.

Recommended Step 5 cleanup boundaries:

- Remove generated/cache/build/package/runtime artifacts only: `build/lib/**`, `supermedicine.egg-info/**`, `__pycache__/`, `*.pyc`, `.ruff_cache/**`, `.mypy_cache/**`, `.supermedicine/checkpoints/**`, `.supermedicine/policies/audit.jsonl`, and accessible `.pytest_cache/**`.
- Optionally remove ignored `Planning/NextSteps.md` only if Step 5 confirms it remains a local ignored planning artifact and is not needed as an intended untracked source document.
- Do not remove `.supermedicine/config.yaml` or `.supermedicine/policies/default.yaml`; they are tracked/local configuration and policy files, not generated cleanup artifacts.
- Do not remove untracked intended source/documentation files listed in section 2, including `Architecture/PlatformIntegrationAudit.md` and `adapters/opencode/agents/supermedicine.md`; also preserve this audit file, `Architecture/RepositoryOptimizationAudit.md`.
- Do not perform code deduplication, import cleanup, policy consolidation, manifest consolidation, test deduplication, or documentation merge work in Step 5.

## 13. Step 5 generated-artifact cleanup execution result

Scope: cleanup of clearly generated, ignored, reproducible artifacts only, based on the Step 4 audit. No source-of-truth documentation, configuration, source code, tests, platform adapter resources, or duplicate-looking content was deleted or merged.

Cleanup performed:

- Removed `build/` generated build mirror when present.
- Removed `supermedicine.egg-info/` generated packaging metadata when present.
- Removed `.ruff_cache/` and `.mypy_cache/` tool caches when present.
- Removed `.supermedicine/checkpoints/` runtime checkpoint output when present.
- Removed `.supermedicine/policies/audit.jsonl` runtime audit log when present.
- Removed Python bytecode/cache artifacts, including `__pycache__/` directories and `*.pyc` files, when present.

Cleanup intentionally skipped or preserved:

- Preserved tracked source/docs/config/test files and source-of-truth package/config inputs.
- Preserved duplicate-looking source/content items listed in section 12.3, including `permission/default_policy.yaml`, `.supermedicine/policies/default.yaml`, OpenCode agent documents, install documentation, plugin manifests, tests, and platform skill/reference documents.
- Preserved `Architecture/RepositoryOptimizationAudit.md` and `adapters/opencode/agents/supermedicine.md` under the explicit hard constraints.
- Preserved ignored local-only `Planning/NextSteps.md` because the Step 5 instruction said to preserve ignored local-only `Planning/` unless explicitly known generated.
- Skipped `.pytest_cache/` cleanup because the directory remained inaccessible; Git continued to report `Permission denied` while listing ignored files.

Post-cleanup ignored-artifact note: after removing accessible generated artifacts, the remaining ignored status was limited to preserved `Planning/`, with `.pytest_cache/` still inaccessible due to permission denial.

Retry cleanup note: after verification regenerated ignored artifacts, Step 5 cleanup was re-run for `build/`, `supermedicine.egg-info/`, `.ruff_cache/`, `.mypy_cache/`, `.supermedicine/checkpoints/`, `.supermedicine/policies/audit.jsonl`, `__pycache__/` trees, and `*.pyc` files. The final ignored status again showed only preserved `Planning/` plus the inaccessible `.pytest_cache/` warning.

## 14. Step 6 conservative consistency optimization result

Scope: documentation-only consistency pass after the Step 1-5 repository optimization work. No runtime source, tests, configuration, manifests, policies, dependency versions, CLI behavior, API behavior, execution order, permissions, or generated artifacts were changed in this step.

Consistency changes made:

- Clarified the Step 5 recommendation wording in section 12.4 so `Architecture/RepositoryOptimizationAudit.md` is described as this audit file, while the section 2 untracked intended files remain `Architecture/PlatformIntegrationAudit.md` and `adapters/opencode/agents/supermedicine.md`.
- Recorded this Step 6 outcome in the repository optimization audit for reviewer traceability.

Risky optimizations intentionally skipped:

- No path renames were performed, including capitalization-only renames, Python package/module/test renames, adapter or plugin path renames, manifest renames, configuration path renames, or conventional repository metadata renames.
- No duplicate source, documentation, configuration, policy, manifest, adapter, plugin, or test content was deleted or merged.
- No code imports, command handlers, output protocols, result schemas, permission/security policies, default values, package metadata, dependency versions, or tests were changed.
- No additional generated-artifact cleanup was attempted in this step, including the previously inaccessible `.pytest_cache/` and the intentionally preserved ignored `Planning/` path.
