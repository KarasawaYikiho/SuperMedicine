# Repository Optimization Audit

Date: 2026-05-26

Purpose: establish the immutable baseline and protection boundaries before any repository optimization. This step is audit-only: no runtime/source behavior changes are allowed in this step except creating this document.

## Audit pass index

Use this index as the canonical navigation layer for repeated repository-optimization passes. Later passes should link back here instead of restating long prior findings unless a fresh observation materially differs.

| Sections | Pass / step | Scope | Outcome |
| --- | --- | --- | --- |
| 1-9 | Initial baseline audit | Branch/worktree state, structure, commands, artifacts, and no-go boundaries | Established preservation boundaries and cleanup policy. |
| 10 | Initial Step 2 audit | Independent-word capitalization/path-risk audit | Found no safe source-of-truth rename candidate. |
| 11 | Initial Step 3 execution | Conservative naming normalization | Performed no path renames. |
| 12 | Initial Step 4 audit | Duplicate/redundant content and generated artifact audit | Recommended generated-artifact cleanup only; skipped source/content deduplication. |
| 13 | Initial Step 5 execution | Generated-artifact cleanup | Removed accessible generated/cache/runtime artifacts; skipped inaccessible `.pytest_cache/` and source content. |
| 14 | Initial Step 6 execution | Documentation-only consistency update | Clarified audit wording; changed no runtime/source behavior. |
| 15 | Repeated-pass baseline | Fresh state after commit `b4cc636` | Re-established clean tracked baseline and repeated-pass boundaries. |
| 16 | Repeated-pass Step 2 audit | Deep semantic-preserving audit | Identified generated cleanup and docs-navigation candidates; skipped risky duplicates/renames. |
| 17 | Repeated-pass Step 3 execution | Generated/cache cleanup | Removed accessible generated/cache/runtime artifacts only. |
| 18 | Repeated-pass Step 4 execution | Naming/capitalization follow-up | Performed no renames; no reference synchronization required. |
| 19 | Repeated-pass Step 5 execution | Safe duplicate reduction | Added this navigation index and recorded skipped duplicate-looking items; no source/prose deletion performed. |
| 20 | Repeated-pass Step 6 execution | Repository format and text hygiene | Applied minimal docs-only hygiene; skipped risky formatting churn. |
| 21 | Repeated-pass Step 7 assessment | Non-invasive repository hygiene test coverage | Added audit-only coverage assessment; no new test churn needed. |
| 22 | Repeated-pass Step 9 review | Final diff and semantic-preservation confirmation | Cleaned accessible regenerated artifacts and confirmed final diff scope remains audit-document only. |

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

## 15. Repeated optimization pass baseline audit after commit `b4cc636`

Date: 2026-05-26

Scope: read-only repository baseline audit for the repeated optimization request received after the prior optimization commit `b4cc636` was pushed. This section intentionally rechecks the repository state from fresh Git/project observations rather than assuming earlier audit conclusions remain true. No runtime/source behavior files are to be changed in this step; this audit document is the only intended modification.

### 15.1 Current branch, remote, HEAD, and initial worktree state

- Working directory: `D:\GIT\SuperMedicine`
- Current branch/tracking line from `git status --short --branch`: `## master...origin/master`
- Remote:
  - `origin https://github.com/KarasawaYikiho/SuperMedicine.git (fetch)`
  - `origin https://github.com/KarasawaYikiho/SuperMedicine.git (push)`
- Current HEAD / fresh baseline commit: `b4cc636 chore: align platform agents and clean repository`
- Recent commit baseline observed:
  - `b4cc636 chore: align platform agents and clean repository`
  - `08ee767 feat: add workspace research tools and TUI workflows`
  - `2815703 fix: harden Windows compatibility and packaging`
  - `9f59ff4 ci: harden Windows pytest temp handling`
  - `274839f ci: isolate pytest temp files on Windows`
  - `5ce638e chore: prepare Beta0.2.0 release candidate`
  - `d855e6b feat: enable manifest plugin execution paths`
  - `4ade2ca chore: align release readiness and repository hygiene`
  - `7a1b8ea refactor: rename cli.py→Cli.py, install.py→Install.py (capitalize entry scripts)`
  - `9c90b49 chore: remove unused format_authors imports from citation formatters`
- Initial tracked/staged/untracked state before this audit edit:
  - `git status --short --branch` reported only `## master...origin/master`; no modified, staged, deleted, renamed, or untracked non-ignored files were shown.
  - `git diff --stat` and `git diff --cached --stat` showed no file-change summary before this audit edit.
  - `git ls-files --others --exclude-standard` reported no untracked non-ignored files; it did emit `warning: could not open directory '.pytest_cache/': Permission denied`.
  - `Architecture/RepositoryOptimizationAudit.md` is tracked at mode `100644` and was the only intended file to update for this step.

### 15.2 Project type, major structure, and discovery-sensitive entry points

- Project type: Python package/application named `supermedicine`, version `0.2.1b0`, with setuptools build backend (`setuptools>=68.0`, `wheel`) and Python requirement `>=3.10`.
- Runtime model: standalone Python medical research agent framework with optional OpenCode, Claude Code, and standalone adapter surfaces around the core.
- Top-level structure currently observed:
  - Repository metadata/config: `.gitignore`, `pyproject.toml`, `requirements.txt`, `install.json`, `.github/workflows/ci.yml`.
  - Runtime/local config: `.supermedicine/` with tracked config/policy inputs plus ignored runtime outputs.
  - Documentation/governance: `README.md`, `INSTALL.md`, `ARCHITECTURE.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `LICENSE`, `Architecture/`, and `docs/`.
  - Python entry modules: `Cli.py`, `Install.py`.
  - Runtime packages: `core/`, `permission/`, `agents/`, `plugins/`, `adapters/`.
  - Tests: `tests/`.
  - Local/generated/ignored paths currently present: `__pycache__/`, `.mypy_cache/`, `.ruff_cache/`, `.pytest_cache/` (inaccessible), `.supermedicine/checkpoints/`, `.supermedicine/policies/audit.jsonl`, and `Planning/`.
- Discovery-sensitive entry points and paths:
  - Console script: `supermedicine = "Cli:main"`.
  - Setuptools top-level modules: `py-modules = ["Cli", "Install"]`.
  - Setuptools package discovery: `core*`, `permission*`, `agents*`, `plugins*`, `adapters*`.
  - Package data: `permission/default_policy.yaml`.
  - Pytest discovery: `testpaths = ["tests"]`, `python_files = ["test_*.py"]`, and `addopts = "-p no:cacheprovider"`.
  - Public direct CLI/documented commands include `python Install.py --init`, `python Cli.py status`, `python Cli.py run ...`, `supermedicine status`, `supermedicine init`, `supermedicine run ...`, `supermedicine workspace ...`, `supermedicine paper ...`, `supermedicine experience ...`, and `supermedicine tui`.
  - Platform/discovery paths include `install.json`, `adapters/opencode/plugin.json`, `adapters/opencode/agents/**`, `adapters/opencode/skills/**`, `adapters/claude_code/SKILL.md`, and `plugins/**/plugin.yaml`.

### 15.3 Available test, lint, type, build, and smoke commands

Commands inventoried from `pyproject.toml`, CI, and documentation for later Tester/verification steps only; Coder must not run test commands in this audit step.

- Environment/development install: `python -m pip install -e ".[dev]"`.
- Runtime install: `pip install -e .`.
- Optional R backend install: `pip install -e ".[r]"`.
- Lint gate: `python -m ruff check --select=E,F,W --ignore=E501 .`.
- Repository hygiene test gate: `python -m pytest tests/test_repo_hygiene.py -q --override-ini addopts= -p no:cacheprovider --basetemp <temp-dir>`.
- Full test suite gate: `python -m pytest tests/ -v --tb=short --override-ini addopts= -p no:cacheprovider --basetemp <temp-dir>`.
- Documented local test command through CLI: `python Cli.py test`.
- Documented direct local test command: `pytest tests/ -v`.
- Wheel smoke/build gate: `python -m pip wheel . --no-deps --wheel-dir <temp-wheel-dir>`.
- Source distribution smoke/build gate: `python -m build --sdist --outdir dist`.
- Optional type command availability: `mypy` is present in the `dev` optional dependency set and `[tool.mypy]` configuration exists; current CI file does not define a separate mypy gate.
- CLI smoke commands documented for later verification: `python Install.py --init`, `python Cli.py status`, `python Cli.py run "..."`, `supermedicine status`, `supermedicine init`, `supermedicine run ...`, workspace/paper/experience commands, and `supermedicine tui`.

### 15.4 Tracked, untracked, ignored, and generated artifact observations

- Tracked source-of-truth state at initial repeated-pass baseline: no tracked modifications were present before this audit edit.
- Untracked non-ignored state at initial repeated-pass baseline: none reported by Git before this audit edit.
- Ignored/generated artifacts observed by `git status --short --ignored` and `git ls-files --ignored --others --exclude-standard`:
  - Tool caches: `.mypy_cache/**`, `.ruff_cache/**`.
  - Inaccessible pytest cache: `.pytest_cache/` caused `warning: could not open directory '.pytest_cache/': Permission denied`.
  - Runtime outputs: `.supermedicine/checkpoints/**`, `.supermedicine/policies/audit.jsonl`.
  - Local planning note/tree: `Planning/`, including ignored `Planning/NextSteps.md`.
  - Python bytecode/cache artifacts: top-level `__pycache__/`, package/test `__pycache__/` directories, and `*.pyc` files under `adapters/**`, `agents/**`, `core/**`, `permission/**`, `plugins/**`, and `tests/**`.
- Cleanup policy for any later planned step:
  - Remove only clearly ignored, reproducible build/cache/runtime products when cleanup is explicitly requested and scoped.
  - Do not remove tracked source, docs, tests, configs, policies, manifests, package inputs, adapter resources, plugin resources, or runtime default policy/config source-of-truth files.
  - Treat `.pytest_cache/` permission denial as a boundary to document and skip rather than force.
  - Preserve `Planning/` unless a later step explicitly confirms it is disposable local-only material.
  - Do not mix generated-artifact cleanup with source/runtime behavior changes.

### 15.5 Hard no-go semantic preservation boundaries for the repeated pass

Absolute priority: do not change existing functionality or code meaning, even when code appears unused, duplicated, insecure, stylistically inconsistent, or suboptimal. Repeated optimization must remain conservative and must revalidate assumptions against current files.

- Preserve public API behavior, import paths, module/package names, class/function names, signatures, return shapes, exception behavior, and side effects.
- Preserve CLI command names, arguments, defaults, prompt/output meanings, exit behavior, console-script mapping, and direct `python Cli.py` / `python Install.py` workflows.
- Preserve package metadata semantics, version meaning, setuptools package discovery, package data inclusion, extras, dependency constraints, and build inputs.
- Preserve plugin IDs, plugin manifests, action IDs, schemas, discovery rules, resource paths, and deterministic plugin output meaning.
- Preserve adapter and platform behavior for OpenCode, Claude Code, and standalone surfaces, including degraded/unavailable states, manifest identities, agent/skill filenames, and install metadata.
- Preserve permission/security policy meanings, default allow/deny behavior, audit semantics, operation guard/path-safety behavior, and prompt-generation safety guidance. Do not “fix” a security concern if the fix changes behavior without explicit planning and verification.
- Preserve medical/statistical output meanings, R/rpy2 fallback behavior, RAG provider contracts, workspace/paper/experience workflows, TUI behavior, and deterministic fixtures.
- Preserve tests' coverage intent and assertion meaning; do not deduplicate or rewrite tests unless a later plan proves a purely mechanical non-semantic synchronization is required.
- Preserve configuration names, default values, `.supermedicine` runtime paths, policy filenames, local-state conventions, and ignored-artifact boundaries.
- Naming/capitalization cleanup must skip risky import/discovery/tooling/platform paths. Document risky capitalization candidates instead of forcing case-only or convention-breaking renames.
- Duplicate reduction is allowed only for semantically identical material whose removal provably loses no local context, warning, standalone usefulness, consumer contract, or coverage intent.
- Do not rename Python packages/modules/tests, plugin manifests, adapter resources, config paths, `.github` paths, `.supermedicine` paths, or conventional packaging files for aesthetics.

### 15.6 Repeated-pass baseline notes

- This is a repeated optimization pass after prior commit/push `b4cc636`; prior audit findings are useful history but are not sufficient authority for new edits.
- The fresh initial state was clean for tracked and non-ignored untracked files; only ignored/generated/local artifacts were observed before this audit edit.
- The prior generated-artifact cleanup conclusion must be rechecked because caches and runtime artifacts have reappeared after later activity.
- The previous naming/capitalization conclusion remains a high-risk area to revalidate rather than assume: Python imports, setuptools/pytest discovery, plugin/platform manifests, and Windows case-only rename behavior make most path capitalization changes unsafe.
- Any later intended changes should keep the repository clean, avoid runtime/source behavior changes, and be committed/pushed only after Brain/Tester verification confirms the planned scope.

## 16. Repeated-pass Step 2 semantic-preserving deep audit

Date: 2026-05-26

Scope: fresh audit-only pass over the current working tree after the repeated-pass baseline section. This pass re-scanned the requested documentation, `Architecture/**`, `Planning/**`, adapters, plugins, agents, core, permission, tests, install manifest, packaging config, and ignore rules for duplicate docs/descriptions, generated artifacts, naming/capitalization risk, hardcoded path references in tests/docs/manifests/imports, and platform adapter declaration paths. No source/runtime behavior, deletion, rename, staging, commit, push, tag, release, publish, upload, or generated-artifact cleanup was performed.

### 16.1 Concrete cleanup, formatting, and documentation de-duplication candidates

- `Architecture/RepositoryOptimizationAudit.md`: contains accumulated historical pass sections and repeated boundary language by design. Candidate: if a future docs-only optimization is explicitly requested, add a short index/table of prior optimization passes or move older closed-pass details into an archival document. Skip for now because this file is the authoritative audit trail and deleting/relocating sections could lose review context.
- `README.md` and `INSTALL.md`: both include clone/install/init/status/run snippets and optional platform/R notes. Candidate: in a future docs-only pass, keep `README.md` as quick-start and make `INSTALL.md` the detailed install guide with cross-links to reduce repeated prose. Skip now because each document remains useful as a standalone entry point and command blocks differ by audience (`pip install -e .` quick path versus `pip install -e ".[dev]"` development path).
- `README.md`, `ARCHITECTURE.md`, and `Architecture/PlatformIntegrationAudit.md`: all restate the core-independent plus optional OpenCode/Claude Code add-on model. Candidate: future docs-only optimization can cross-link to one canonical architecture/support-status section. Skip now because README is user-facing, `ARCHITECTURE.md` is architecture-facing, and `PlatformIntegrationAudit.md` is an audit artifact with historical evidence.
- `Architecture/ExecutionRoadmap.md`, `Architecture/PhaseImplementationPlan.md`, `Architecture/OptimizationAudit.md`, `Architecture/PlatformIntegrationAudit.md`, and this file: duplicate-looking no-go/boundary/checklist language appears intentional for local audit completeness. Candidate: future docs-only pass can add forward/back links to reduce navigation friction, not delete evidence.
- `adapters/opencode/agents/alpha-analyst.md`, `beta-reviewer.md`, `gamma-writer.md`, and `delta-orchestrator.md`: repeated internal-role/frontmatter/safety positioning is a possible prose de-dup candidate only if OpenCode consumption allows shared includes. Skip because each role document is independently installable and platform-readable.
- `adapters/opencode/skills/*.md` and `adapters/claude_code/SKILL.md`: repeated capability, permission, and medical-boundary descriptions are possible docs-only consolidation candidates. Skip because these are platform-facing standalone documents where local context is important.
- `plugins/standards/medical_writing/references/*-checklist.md`: checklist files are intentionally separate source references; do not merge. Candidate only for docs index/navigation if future users need a consolidated checklist map.
- `Planning/NextSteps.md`: ignored local planning note is a concrete cleanup candidate only if a later cleanup step confirms it is disposable. Skip now because the user explicitly requested audit-only recording and previous scope preserved ignored Planning material unless explicitly known generated.

### 16.2 Naming capitalization and path-case risk findings

- No safe rename/capitalization candidate was found in the requested source-of-truth scope. Current lowercase package/module paths (`core/**`, `permission/**`, `agents/**`, `plugins/**`, `adapters/**`) match Python import and packaging conventions and are referenced throughout code, tests, docs, manifests, and package discovery.
- `Cli.py` and `Install.py` remain intentionally capitalized entry modules. Skip any further rename because `pyproject.toml` declares `py-modules = ["Cli", "Install"]`, the console script points to `Cli:main`, and docs/tests use direct `python Cli.py` / `python Install.py` workflows.
- `ARCHITECTURE.md` and `Architecture/` remain a path-case ambiguity risk on case-insensitive tooling. Skip rename because root uppercase documentation names are conventional, `Architecture/` contains multiple audit/planning docs, and `Architecture.md` would increase ambiguity with the directory.
- `adapters/claude_code/**` and `adapters/opencode/**` are platform/discovery/import-sensitive. Skip capitalization to `ClaudeCode` or `OpenCode` because install manifest paths, tests, imports, adapter docs, and platform metadata reference the existing paths.
- OpenCode declaration files under `adapters/opencode/agents/*.md` and `adapters/opencode/skills/*.md` use lowercase hyphenated filenames. Skip PascalCase/case-only renames because `adapters/opencode/plugin.json`, tests, install docs, and potential platform IDs depend on those literal paths.
- Plugin directories and manifests (`plugins/rag/**`, `plugins/harness/**`, `plugins/tools/python_stats/**`, `plugins/tools/r_survival/**`, `plugins/standards/medical_writing/**`, `plugins/standards/medical_citation/**`, and `plugin.yaml`) are import/discovery-sensitive. Skip capitalization or manifest basename changes because `PluginRegistry` scans `plugin.yaml`, tests assert entries exist, and package discovery includes `plugins*`.
- Test paths (`tests/**`, `tests/test_*.py`, `tests/conftest.py`, `tests/__init__.py`) are pytest-discovery-sensitive and contain hardcoded path assertions for manifests/docs/adapters. Skip renames because `pyproject.toml` defines `testpaths = ["tests"]` and `python_files = ["test_*.py"]`.
- `.supermedicine/**`, `.gitignore`, `pyproject.toml`, `install.json`, `.github/workflows/**`, and conventional root docs remain tooling/config-sensitive. Skip aesthetics-driven capitalization because these names are loaded by tooling, runtime config, tests, docs, or platform installers.

### 16.3 Generated/cache artifacts observed and cleanup plan

Observed ignored/generated artifacts in the fresh pass:

- Python bytecode/cache artifacts: top-level `__pycache__/`, package/test `__pycache__/` directories, and `*.pyc` under `adapters/**`, `agents/**`, `core/**`, `permission/**`, `plugins/**`, and `tests/**`.
- Build/package outputs: `build/lib/**` source mirror and `supermedicine.egg-info/**` packaging metadata.
- Tool caches: `.mypy_cache/**` and `.ruff_cache/**`.
- Pytest cache: `.pytest_cache/` still produced `Permission denied` when Git tried to inspect ignored files.
- Runtime/local outputs: `.supermedicine/checkpoints/**` and `.supermedicine/policies/audit.jsonl`.
- Ignored local planning note: `Planning/NextSteps.md`.

Cleanup plan for a later explicit cleanup step only:

- Remove generated/cache/build/package/runtime artifacts that are already ignored and reproducible: `__pycache__/`, `*.pyc`, `build/`, `supermedicine.egg-info/`, `.mypy_cache/`, `.ruff_cache/`, `.supermedicine/checkpoints/`, and `.supermedicine/policies/audit.jsonl`.
- Attempt accessible `.pytest_cache/` cleanup only if permissions allow; otherwise document and skip without forcing permissions.
- Preserve tracked `.supermedicine/config.yaml` and `.supermedicine/policies/default.yaml`; they are bootstrap/config source-of-truth, not generated cleanup targets.
- Preserve `Planning/NextSteps.md` unless a later step explicitly decides ignored local planning notes are disposable.
- Do not clean, delete, rename, or merge any tracked source, docs, tests, manifests, policies, plugin references, or adapter resources as part of generated-artifact cleanup.

### 16.4 Duplicate-looking items skipped with rationale

- `permission/default_policy.yaml` and `.supermedicine/policies/default.yaml`: duplicate-looking policy content is skipped because the first is package data and the second is local runtime bootstrap policy.
- Repeated policy action names such as RAG, tool, workspace, and Claude scopes are skipped because rule meaning depends on agent, action, effect, and hard-limit context.
- `install.json` and `adapters/opencode/plugin.json`: overlapping optional-add-on fields and capability language are skipped because they serve different consumers: repository install metadata versus OpenCode plugin metadata.
- `pyproject.toml`, `install.json`, README release wording, and `CHANGELOG.md`: version labels intentionally differ between public release label `Beta0.2.1` and PEP 440 package metadata `0.2.1b0`; do not normalize away the documented distinction.
- Tests under `tests/**`: duplicate-looking path literals, fixture setup, and adapter assertions are skipped because they protect specific docs/manifests/import paths and discovery boundaries.
- Hardcoded test path checks in `tests/test_repo_hygiene.py`, `tests/test_opencode_adapter.py`, and `tests/test_claude_code_adapter.py` are skipped because they intentionally enforce install manifest paths, adapter resource paths, skill/agent paths, package entry points, and platform declaration contracts.
- Python imports from `core`, `permission`, `agents`, `plugins`, and `adapters` are skipped because import paths are behavior-sensitive. Apparent repeated imports in CLI command handlers and tests may preserve lazy import behavior, optional dependency boundaries, or local fixture meaning.
- Repeated command examples using `python Cli.py test` or direct pytest commands in docs are skipped in this audit step. They may be docs-only candidates later, but removing them now could reduce standalone guide usefulness.
- Generated mirrors under `build/lib/**` are skipped as source duplicates; they should be cleaned as generated artifacts, not used as a basis for source deletion or refactoring.

### 16.5 Potentially safe docs-only optimization candidates

- Add a short documentation navigation index linking `README.md`, `INSTALL.md`, `ARCHITECTURE.md`, `Architecture/WorkspaceTuiRagGuide.md`, `Architecture/PlatformIntegrationAudit.md`, and `Architecture/RepositoryOptimizationAudit.md` so repeated boundary material is easier to locate without deleting content.
- In `README.md`, convert detailed install/R/platform explanations into brief summaries that link to `INSTALL.md`, if a future user-facing documentation pass accepts the tradeoff.
- In `INSTALL.md`, add a short pointer back to README quick start and architecture support matrix instead of restating every platform boundary in full.
- In `Architecture/RepositoryOptimizationAudit.md`, add an audit-pass index at the top to reduce scrolling through historical sections. This is documentation-only and preserves the audit record.
- In `Architecture/PlatformIntegrationAudit.md`, mark older pre-remediation findings as historical in a compact table while preserving exact evidence and final status. This is docs-only but should be done carefully to avoid losing audit traceability.

### 16.6 Step 2 repeated-pass conclusion

No runtime/source behavior change, deletion, rename, or generated-artifact cleanup should be performed in this Step 2 audit. The concrete later-action candidates are limited to generated-artifact cleanup and cautious docs-only navigation/de-duplication. All naming/capitalization candidates in Python packages, tests, manifests, adapter resources, plugin resources, config paths, package metadata, and platform declarations are skipped due to import, discovery, tooling, platform, or case-sensitivity risk.

## 17. Repeated-pass Step 3 generated/cache cleanup result

Date: 2026-05-26

Scope: cleanup of clearly generated, ignored, reproducible cache/build/runtime artifacts identified in the repeated-pass audit. No source, documentation, configuration, tests, platform resources, package inputs, manifests, tracked policy defaults, or `Planning/` files were deleted or modified.

Cleanup result:

- Removed `.supermedicine/policies/audit.jsonl` runtime audit log when present.
- Re-ran cleanup for accessible `.mypy_cache/`, `.ruff_cache/`, `.supermedicine/checkpoints/`, `build/`, `supermedicine.egg-info/`, all `__pycache__/` trees, and `*.pyc` artifacts using normal workspace permissions; the bytecode cleanup was retried recursively after remaining accessible bytecode artifacts were reported.
- Attempted cleanup of `.pytest_cache/` within normal workspace permissions; no accessible cache entries were available through the repository file search at cleanup time.
- Final cleanup state for the requested accessible generated artifacts: no accessible `__pycache__/` trees, `*.pyc` files, `build/`, `supermedicine.egg-info/`, `.mypy_cache/`, `.ruff_cache/`, or `.supermedicine/checkpoints/` artifacts were present through the cleanup file search after retry 2 execution.

Preserved intentionally:

- Tracked source, docs, config, tests, package metadata inputs, adapter resources, plugin resources, `.supermedicine/config.yaml`, and `.supermedicine/policies/default.yaml`.
- Ignored local `Planning/` content, because this cleanup step explicitly preserves `Planning/` unless confirmed disposable.
- `.gitignore`, because the existing ignore rules already cover Python bytecode, build/package outputs, lint/type/test/coverage caches, SuperMedicine runtime artifacts, external assistant local artifacts, and local planning notes.

Inaccessible artifacts:

- `.pytest_cache/` had previously produced permission-denied warnings during Git/listing operations. During this cleanup pass, normal file search did not expose accessible entries and the cleanup command was limited to normal permissions; any still-inaccessible pytest cache material is treated as skipped rather than force-deleted.

## 18. Repeated-pass Step 4 independent-word initial capitalization naming execution result

Date: 2026-05-26

Scope: execution follow-up for the repeated-pass Step 2 naming/capitalization audit after generated/cache cleanup. This step was limited to deciding whether any independent-word initial capitalization path rename was now safe and, if so, synchronizing references. No behavior, import, entry point, manifest, configuration, runtime path, test discovery, platform declaration, staging, commit, push, tag, release, publish, or upload action was performed.

Renames performed:

- None.

Skipped/rationale:

- No newly obvious docs-only path rename was found that was both unreferenced and no-risk.
- Python modules, packages, tests, and entry files remained unchanged, including `Cli.py`, `Install.py`, `core/**`, `permission/**`, `agents/**`, `plugins/**`, `adapters/**`, and `tests/**`, because those names are import, packaging, pytest discovery, or public workflow sensitive.
- Adapter/plugin/platform paths remained unchanged, including `adapters/opencode/**`, `adapters/claude_code/**`, OpenCode agent/skill filenames, `adapters/opencode/plugin.json`, and `plugins/**/plugin.yaml`, because those paths can be referenced by manifests, installers, tests, documentation, or platform discovery.
- Tooling, manifest, configuration, runtime, and conventional metadata paths remained unchanged, including `.github/workflows/**`, `.supermedicine/**`, `.gitignore`, `install.json`, `pyproject.toml`, `requirements.txt`, `README.md`, `INSTALL.md`, `ARCHITECTURE.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, and `LICENSE`, because these names are conventional or consumer/tooling sensitive.
- Case-only or aesthetics-only renames were skipped because the current Windows workspace and Git case handling make such changes risky, and Step 2 already found no low-risk source-of-truth capitalization candidate.

Reference synchronization result:

- No import, entry point, package discovery, package data, pytest discovery, manifest, adapter/plugin declaration, configuration, runtime path, documentation link, or platform reference synchronization was required because no path rename occurred.

Execution conclusion: Step 4 intentionally records a no-rename result. This preserves the source-of-truth path contracts established by the repeated-pass Step 2 audit and avoids unsafe churn in import/discovery/tooling/platform-sensitive files.

## 19. Repeated-pass Step 5 safe duplicate reduction result

Date: 2026-05-26

Scope: documentation-only duplicate-reduction execution based on the repeated-pass Step 2 audit. The pass was limited to semantically identical, non-functional prose where context could be preserved by cross-reference. No code, tests, configuration, manifests, permission policies, examples, warnings, platform capability descriptions, CLI/API outputs, generated artifacts, staging, commit, push, tag, release, publish, or upload actions were performed.

Duplicate reductions performed:

- Added the `Audit pass index` near the top of this document as a cross-reference layer for sections 1-19. Semantic-equivalence rationale: the index summarizes existing audit sections without replacing their evidence, decisions, warnings, or historical context; future updates can link to the index rather than repeating long prior explanations.
- Recorded this Step 5 outcome in this section so future repeated passes have a single place to find the safe duplicate-reduction decision and the skipped-item rationale.

Content deletion or merge result:

- No existing source-of-truth documentation/prose was deleted or merged. The audit did not find exact duplicate documentation whose removal would preserve all standalone install, platform, safety, warning, example, and historical-audit context.
- No executable paths were affected: `Cli.py`, `Install.py`, `core/**`, `permission/**`, `agents/**`, `plugins/**`, `adapters/**`, `tests/**`, manifests, package metadata, policies, and runtime configuration paths remained unchanged.

Skipped duplicate-looking items and rationale:

- `README.md` and `INSTALL.md` install snippets were preserved. Rationale: the commands overlap but serve different entry points and audiences; README is a quick-start path while INSTALL is a standalone installation guide with prerequisites, verification, troubleshooting, optional R support, and platform-adapter context.
- README/architecture/platform-support overlap across `README.md`, `ARCHITECTURE.md`, and `Architecture/PlatformIntegrationAudit.md` was preserved. Rationale: the repeated core-independent plus optional-adapter model appears in user-facing, architecture-facing, and audit-evidence contexts; deleting any copy could reduce standalone usefulness or audit traceability.
- Boundary/checklist language across `Architecture/ExecutionRoadmap.md`, `Architecture/PhaseImplementationPlan.md`, `Architecture/OptimizationAudit.md`, `Architecture/PlatformIntegrationAudit.md`, and this audit was preserved. Rationale: repeated constraints are local guardrails for separate planning/audit documents, not exact redundant paragraphs safe to remove.
- OpenCode agent role documents under `adapters/opencode/agents/*.md` were preserved. Rationale: each role document is independently installable/platform-readable, so repeated safety/frontmatter/context wording must remain local to each file.
- Platform skill and reference documents under `adapters/opencode/skills/**`, `adapters/claude_code/SKILL.md`, and `plugins/**/references/**` were preserved. Rationale: repeated medical-boundary, permission, and checklist language supports standalone consumption and should not be centralized away without platform include semantics.
- Policy, manifest, test, example, command, and generated-mirror duplicate-looking content was preserved or left to generated-artifact cleanup rules. Rationale: these items are functional, discovery-sensitive, coverage-sensitive, consumer-specific, or generated outputs rather than safe docs-only duplicate prose.

Step 5 conclusion: the only strictly safe duplicate reduction in this pass was additive navigation/indexing inside the audit itself. All deletion/merge candidates were skipped because semantic identity and context preservation could not be proven under the hard constraints.

## 20. Repeated-pass Step 6 repository format and text hygiene result

Date: 2026-05-26

Scope: low-risk documentation text hygiene only, limited to this audit document. No source code, tests, configuration, manifests, dependency metadata, generated artifacts, staging, commit, push, tag, release, publish, or upload actions were performed.

Hygiene changes made:

- Added the repeated-pass Step 6 result to the audit pass index so the document heading/navigation pattern remains consistent for sections 1-20.
- Recorded this Step 6 outcome in a dedicated audit section with the same result-oriented heading style used by the repeated-pass execution sections.
- Kept the edit docs-only and minimal; no functional, configuration, test, manifest, policy, package, or runtime text was changed.

Skipped risky formatting:

- No repository-wide formatter, markdown formatter, import sorter, lint auto-fixer, line-ending normalization, or whitespace rewrite was run.
- No Python, TOML, JSON, YAML, manifest, policy, test, package metadata, generated artifact, or runtime-local file was modified for formatting.
- No broad markdown reflow, heading renumbering, prose deletion, duplicate-content merge, path rename, or capitalization cleanup was attempted because such churn could obscure semantic review.

Step 6 conclusion: the repeated-pass format work was intentionally limited to audit-document traceability and minimal text hygiene. Risky formatting and any change that could alter behavior, configuration meaning, test intent, package metadata, platform discovery, or review clarity was skipped.

## 21. Repeated-pass Step 7 repository hygiene test coverage assessment

Date: 2026-05-26

Scope: audit-only assessment of whether additional non-invasive repository hygiene tests are needed after the repeated optimization pass. No runtime/source behavior, test behavior, configuration, manifest, dependency metadata, generated artifact, staging, commit, push, tag, release, publish, or upload action was performed.

Existing repository hygiene coverage reviewed:

- `tests/test_repo_hygiene.py` already protects against tracking generated or forbidden artifacts, including bytecode, build/dist/package metadata output, test/lint caches, runtime audit logs, runtime checkpoints, external platform local configuration directories, and unexpected tracked `.supermedicine` content.
- Existing tests already verify `.gitignore` coverage for runtime/cache/external-platform artifacts without requiring external network access or platform runtimes.
- Existing tests already assert install manifest platform entries stay under adapter paths, point to existing adapter resources, and remain synchronized with adapter support declarations.
- Existing tests already enforce the single user-facing platform agent model, reject legacy platform agent names in platform-facing docs/resources, validate OpenCode declared entry skills and agents, and protect key OpenCode platform capability declarations.
- Existing tests already cover release label/package metadata synchronization, plugin manifest entry paths, console-script importability, and packaging of the top-level console-script module.

Test coverage decision:

- No additional test coverage was added in Step 7.
- Rationale: the repeated optimization changes since Step 3 were documentation/audit-only and did not introduce new runtime/source behavior, install paths, package discovery paths, manifest paths, platform agent names, version labels, generated-artifact categories, or forbidden-file categories. Adding another hygiene assertion would duplicate already covered invariants and create test churn without protecting a newly changed contract.
- If a later pass changes runtime/source paths, manifests, generated-artifact policy, installer behavior, adapter resources, or package metadata, add the smallest focused non-invasive hygiene test at that time. Until such a contract changes, the current tests are sufficient for the repository hygiene risks touched by this pass.

Step 7 conclusion: `tests/test_repo_hygiene.py` was intentionally left unchanged. The audit records why existing non-invasive coverage is sufficient for this docs-only repeated optimization pass, while preserving the rule that future functional/path/manifest changes should receive focused test coverage.

## 22. Repeated-pass Step 9 final diff review and semantic-preservation confirmation

Date: 2026-05-26

Scope: final repeated-pass review after Step 8 validation. This step was limited to cleaning regenerated artifacts that were safe to remove with normal workspace permissions, inspecting the final working-tree diff, and recording semantic-preservation confirmation in this audit document. No staging, commit, push, tag, release, publish, upload, runtime/source edit, configuration edit, test edit, manifest edit, dependency edit, policy edit, or package metadata edit was performed.

Generated artifact cleanup result:

- Rechecked and found no accessible `build/`, `supermedicine.egg-info/`, `.ruff_cache/`, `.mypy_cache/`, `__pycache__/`, `*.pyc`, or `.supermedicine/checkpoints/` artifacts at cleanup time.
- Removed regenerated `.supermedicine/policies/audit.jsonl` runtime audit log when present.
- Preserved ignored `Planning/` content as requested and because it is not confirmed disposable generated output.
- Preserved inaccessible `.pytest_cache/` material; prior passes observed permission-denied behavior and this final cleanup avoided forcing permissions or deleting source/docs/config/tests.

Final diff inspection:

- `git status --short` reported only `Architecture/RepositoryOptimizationAudit.md` as modified after cleanup.
- `git diff --name-status` reported only `M Architecture/RepositoryOptimizationAudit.md`.
- `git diff --stat` reported only `Architecture/RepositoryOptimizationAudit.md` with documentation insertions.
- Git emitted the existing line-ending warning for this audit file (`LF will be replaced by CRLF the next time Git touches it`); this is recorded as workspace line-ending metadata noise and not a semantic runtime/config/test/manifest change.

Semantic-preservation confirmation:

- Runtime and source files remained unchanged in this Step 9 pass: `Cli.py`, `Install.py`, `core/**`, `permission/**`, `agents/**`, `plugins/**`, and `adapters/**` were not edited.
- Configuration, policy, manifest, dependency, package, CI, and platform-declaration inputs remained unchanged in this Step 9 pass, including `.supermedicine/config.yaml`, `.supermedicine/policies/default.yaml`, `.gitignore`, `pyproject.toml`, `requirements.txt`, `install.json`, `.github/workflows/**`, and `adapters/opencode/plugin.json`.
- Test files remained unchanged in this Step 9 pass, including `tests/**`.
- Documentation changes in this step were limited to this audit trail and only record cleanup/diff-review evidence; they do not alter documented commands, runtime behavior, platform contracts, package metadata, permissions, tests, or source semantics.

Step 9 conclusion: final repeated-pass diff scope is intentionally restricted to `Architecture/RepositoryOptimizationAudit.md`. Accessible regenerated artifacts were cleaned or confirmed absent, inaccessible `.pytest_cache/` and ignored `Planning/` content were preserved, and no runtime/source/config/test/manifest semantics changed.
